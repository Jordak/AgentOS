#!/usr/bin/env python3
"""Install portable AgentOS global instruction adapters.

The script is intentionally conservative:

- dry-run by default;
- no symlinks;
- user content is preserved outside AgentOS managed blocks;
- writes create adjacent backups before changing existing files;
- self-tests run only inside temporary directories.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import shutil
import sys
import tempfile
from contextlib import redirect_stderr
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, TextIO


GLOBAL_START = "<!-- BEGIN AgentOS Managed Global Instructions -->"
GLOBAL_END = "<!-- END AgentOS Managed Global Instructions -->"
ADAPTER_START = "<!-- BEGIN AgentOS Managed Global Adapter -->"
ADAPTER_END = "<!-- END AgentOS Managed Global Adapter -->"


@dataclass(frozen=True)
class AdapterSpec:
    name: str
    parts: tuple[str, ...]

    def path_for(self, home: Path) -> Path:
        return home.joinpath(*self.parts)


@dataclass(frozen=True)
class Target:
    name: str
    path: Path
    kind: str
    skipped_reason: str | None = None
    error_reason: str | None = None


@dataclass
class Result:
    ok: bool
    status: str
    path: Path
    message: str
    backup: Path | None = None


DEFAULT_ADAPTERS = (
    AdapterSpec("codex", (".codex", "AGENTS.md")),
    AdapterSpec("claude", (".claude", "CLAUDE.md")),
    AdapterSpec("gemini", (".gemini", "GEMINI.md")),
)


class ManagedBlockError(ValueError):
    pass


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Install AgentOS managed global instruction adapters.",
    )
    p.add_argument(
        "--agentos-home",
        help="Resolved AgentOS checkout path. Required except with --self-test.",
    )
    p.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Write changes. Without this flag, only print the plan.",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="Check existing managed blocks for drift without writing.",
    )
    p.add_argument(
        "--remove",
        action="store_true",
        help="Remove only AgentOS managed blocks without deleting files.",
    )
    p.add_argument(
        "--all-default-adapters",
        action="store_true",
        help="Target Codex, Claude, and Gemini adapter files even if their directories do not exist.",
    )
    p.add_argument(
        "--adapter",
        action="append",
        default=[],
        metavar="PATH",
        help="Extra harness adapter file to manage. May be repeated. Supports <home>/... notation.",
    )
    p.add_argument(
        "--self-test",
        action="store_true",
        help="Run temporary-directory self-tests and exit.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.self_test:
        if (
            args.agentos_home
            or args.no_dry_run
            or args.check
            or args.remove
            or args.all_default_adapters
            or args.adapter
        ):
            print("error: --self-test cannot be combined with other options", file=sys.stderr)
            return 2
        return run_self_tests()
    return run(args, home=Path.home(), out=sys.stdout)


def run(args: argparse.Namespace, home: Path, out: TextIO) -> int:
    if args.check and args.remove:
        print("error: --check and --remove cannot be combined", file=out)
        return 2
    if args.check and args.no_dry_run:
        print("error: --check is read-only; do not combine it with --no-dry-run", file=out)
        return 2
    if not args.agentos_home:
        print("error: --agentos-home is required", file=out)
        return 2

    agentos_home = Path(args.agentos_home).expanduser()
    if not agentos_home.is_absolute():
        agentos_home = Path.cwd() / agentos_home
    agentos_home = agentos_home.resolve()

    validation_error = validate_agentos_home(agentos_home)
    if validation_error:
        print(f"error: {validation_error}", file=out)
        return 2

    home = home.expanduser().resolve()
    targets = collect_targets(
        home=home,
        include_all_default_adapters=args.all_default_adapters,
        extra_adapters=args.adapter,
    )
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    mode = "check" if args.check else "remove" if args.remove else "install"
    dry_run = not args.no_dry_run
    if mode == "check":
        print("Checking AgentOS global instruction adapters.", file=out)
    elif dry_run:
        print("DRY-RUN: no files will be modified.", file=out)
    else:
        print("Applying AgentOS global instruction adapter changes.", file=out)
    print(f"AgentOS home: {agentos_home}", file=out)
    print(f"Canonical global file: {global_instructions_path(home)}", file=out)
    print("", file=out)

    results: list[Result] = []
    if any(target.error_reason for target in targets):
        for target in targets:
            if target.error_reason:
                results.append(
                    Result(
                        ok=False,
                        status="error",
                        path=target.path,
                        message=target.error_reason,
                    )
                )
            elif target.skipped_reason:
                results.append(
                    Result(
                        ok=True,
                        status="skip",
                        path=target.path,
                        message=target.skipped_reason,
                    )
                )
            else:
                results.append(
                    Result(
                        ok=True,
                        status="not run",
                        path=target.path,
                        message="not evaluated because target planning failed",
                    )
                )
        for result in results:
            print(format_result(result), file=out)
        print("", file=out)
        print("Target planning failed; no files were modified.", file=out)
        return 1

    for target in targets:
        if target.skipped_reason:
            results.append(
                Result(
                    ok=True,
                    status="skip",
                    path=target.path,
                    message=target.skipped_reason,
                )
            )
            continue
        try:
            if mode == "check":
                result = check_target(target, home, agentos_home)
            elif mode == "remove":
                result = remove_target(target, dry_run=dry_run, timestamp=timestamp)
            else:
                result = install_target(
                    target,
                    home,
                    agentos_home,
                    dry_run=dry_run,
                    timestamp=timestamp,
                )
        except ManagedBlockError as exc:
            result = Result(False, "error", target.path, str(exc))
        results.append(result)

    for result in results:
        print(format_result(result), file=out)

    failures = [result for result in results if not result.ok]
    if failures:
        print("", file=out)
        if mode == "check":
            print("Drift detected. Remediation:", file=out)
            print(remediation_command(args, agentos_home), file=out)
        else:
            print("Some targets failed. Files reporting failure were not modified.", file=out)
        return 1

    return 0


def validate_agentos_home(agentos_home: Path) -> str | None:
    required = (
        agentos_home / "AGENTS.md",
        agentos_home / "os" / "INDEX.md",
        agentos_home / "os" / "playbook" / "PERSONAL_OVERLAY.md",
    )
    if not agentos_home.exists():
        return f"AgentOS home does not exist: {agentos_home}"
    if not agentos_home.is_dir():
        return f"AgentOS home is not a directory: {agentos_home}"
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        return "AgentOS home is missing required files: " + ", ".join(missing)
    return None


def global_instructions_path(home: Path) -> Path:
    return home / ".agents" / "AGENTS.md"


def collect_targets(
    home: Path,
    include_all_default_adapters: bool,
    extra_adapters: Iterable[str],
) -> list[Target]:
    targets: list[Target] = []
    seen: dict[Path, Target] = {}

    def add_target(target: Target) -> None:
        key = target.path.resolve()
        existing = seen.get(key)
        if existing is None:
            seen[key] = target
            targets.append(target)
            return
        if existing.kind == target.kind:
            return
        targets.append(
            Target(
                target.name,
                target.path,
                target.kind,
                error_reason=f"target conflicts with {existing.kind} target {existing.path}",
            )
        )

    add_target(Target("global", global_instructions_path(home), "global"))
    for spec in DEFAULT_ADAPTERS:
        path = spec.path_for(home)
        parent_exists = path.parent.exists()
        if include_all_default_adapters or parent_exists:
            add_target(Target(spec.name, path, "adapter"))
        else:
            add_target(
                Target(
                    spec.name,
                    path,
                    "adapter",
                    skipped_reason=f"default {spec.name} adapter skipped because {path.parent} does not exist",
                )
            )
    for raw in extra_adapters:
        path = resolve_user_path(raw, home)
        add_target(Target(f"adapter:{raw}", path, "adapter"))
    return targets


def resolve_user_path(raw: str, home: Path) -> Path:
    if raw == "<home>":
        return home
    for prefix in ("<home>/", "<home>\\"):
        if raw.startswith(prefix):
            rest = raw[len(prefix) :]
            parts = [part for part in re.split(r"[\\/]+", rest) if part]
            return home.joinpath(*parts)
    if raw == "~":
        return home
    tilde = "~"
    for prefix in (tilde + "/", tilde + "\\"):
        if raw.startswith(prefix):
            rest = raw[len(prefix) :]
            parts = [part for part in re.split(r"[\\/]+", rest) if part]
            return home.joinpath(*parts)
    path = Path(os.path.expanduser(raw))
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def expected_block(target: Target, home: Path, agentos_home: Path) -> str:
    if target.kind == "global":
        return global_block(agentos_home)
    return adapter_block(global_instructions_path(home))


def global_block(agentos_home: Path) -> str:
    return f"""{GLOBAL_START}
# Global Agent Instructions

AgentOS is installed at:

`{agentos_home}`

When a task would benefit from reusable identity, context, skills, memory, connections, agents, verification habits, playbooks, or automations, read the relevant files under that workspace.

Start with:

1. `{agentos_home / "AGENTS.md"}`
2. `{agentos_home / "os" / "INDEX.md"}`

If that workspace is unavailable, continue with the current project's local instructions and say AgentOS context could not be loaded.

Before answering questions about fast-moving tools, check current official docs or primary sources.

Ask before sending messages, posting publicly, changing permissions, entering credentials, handling MFA, deleting nontrivial data, installing software, or granting external write access.

Keep global instructions lean. Put detailed project-specific instructions in each project's local agent instruction file.
{GLOBAL_END}
"""


def adapter_block(global_path: Path) -> str:
    return f"""{ADAPTER_START}
AgentOS global instructions are managed at:

`{global_path}`

Read that file first, then continue with the rest of this file.
{ADAPTER_END}
"""


def check_target(target: Target, home: Path, agentos_home: Path) -> Result:
    if not target.path.exists():
        return Result(False, "missing", target.path, "file is missing")
    if target.path.is_dir():
        return Result(False, "error", target.path, "path is a directory, expected a file")
    text = read_text_preserve_newlines(target.path)
    start, end = markers_for(target.kind)
    found = find_block(text, start, end)
    if found is None:
        return Result(False, "drift", target.path, "managed block is missing")
    actual = text[found[0] : found[1]]
    expected = expected_block(target, home, agentos_home)
    if normalize_newlines(actual).strip() != normalize_newlines(expected).strip():
        return Result(False, "drift", target.path, "managed block is stale")
    return Result(True, "ok", target.path, "managed block is current")


def install_target(
    target: Target,
    home: Path,
    agentos_home: Path,
    dry_run: bool,
    timestamp: str,
) -> Result:
    if target.path.exists() and target.path.is_dir():
        return Result(False, "error", target.path, "path is a directory, expected a file")

    original = read_optional(target.path)
    block = expected_block(target, home, agentos_home)
    if original is None:
        desired = ensure_trailing_newline(block)
        if dry_run:
            return Result(True, "would create", target.path, "new managed file")
        target.path.parent.mkdir(parents=True, exist_ok=True)
        write_text_atomic(target.path, desired)
        return Result(True, "created", target.path, "new managed file")

    desired = upsert_block(original, block, *markers_for(target.kind))
    if desired == original:
        return Result(True, "unchanged", target.path, "already current")

    backup = backup_path_for(target.path, timestamp)
    if dry_run:
        return Result(True, "would update", target.path, "managed block would be inserted or replaced", backup)

    target.path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target.path, backup)
    write_text_atomic(target.path, desired)
    return Result(True, "updated", target.path, "managed block inserted or replaced", backup)


def remove_target(target: Target, dry_run: bool, timestamp: str) -> Result:
    if not target.path.exists():
        return Result(True, "skip", target.path, "file is missing")
    if target.path.is_dir():
        return Result(False, "error", target.path, "path is a directory, expected a file")
    original = read_text_preserve_newlines(target.path)
    desired = remove_block(original, *markers_for(target.kind))
    if desired == original:
        return Result(True, "unchanged", target.path, "managed block was not present")

    backup = backup_path_for(target.path, timestamp)
    if dry_run:
        return Result(True, "would update", target.path, "managed block would be removed", backup)

    shutil.copy2(target.path, backup)
    write_text_atomic(target.path, desired)
    return Result(True, "updated", target.path, "managed block removed", backup)


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def read_optional(path: Path) -> str | None:
    if not path.exists():
        return None
    return read_text_preserve_newlines(path)


def read_text_preserve_newlines(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def markers_for(kind: str) -> tuple[str, str]:
    if kind == "global":
        return GLOBAL_START, GLOBAL_END
    return ADAPTER_START, ADAPTER_END


def find_block(text: str, start_marker: str, end_marker: str) -> tuple[int, int] | None:
    starts = [match.start() for match in re.finditer(re.escape(start_marker), text)]
    ends = [match.start() for match in re.finditer(re.escape(end_marker), text)]
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1:
        raise ManagedBlockError("managed block markers are missing or duplicated")
    start = starts[0]
    end_start = ends[0]
    if end_start < start:
        raise ManagedBlockError("managed block end marker appears before start marker")
    end = end_start + len(end_marker)
    return start, end


def upsert_block(text: str, block: str, start_marker: str, end_marker: str) -> str:
    newline = detect_newline(text)
    block = convert_newlines(ensure_trailing_newline(block), newline)
    found = find_block(text, start_marker, end_marker)
    if found is None:
        separator = newline if not text else newline + newline
        return block + separator + text
    return text[: found[0]] + block.rstrip("\r\n") + text[found[1] :]


def remove_block(text: str, start_marker: str, end_marker: str) -> str:
    found = find_block(text, start_marker, end_marker)
    if found is None:
        return text
    start, end = found
    end = consume_following_newlines(text, end, max_count=2)
    return text[:start] + text[end:]


def consume_following_newlines(text: str, index: int, max_count: int) -> int:
    count = 0
    while count < max_count:
        if text.startswith("\r\n", index):
            index += 2
        elif text.startswith("\n", index):
            index += 1
        else:
            break
        count += 1
    return index


def detect_newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def convert_newlines(text: str, newline: str) -> str:
    return normalize_newlines(text).replace("\n", newline)


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def backup_path_for(path: Path, timestamp: str) -> Path:
    candidate = path.with_name(f"{path.name}.agentos-backup-{timestamp}")
    if not candidate.exists():
        return candidate
    counter = 2
    while True:
        next_candidate = path.with_name(f"{path.name}.agentos-backup-{timestamp}-{counter}")
        if not next_candidate.exists():
            return next_candidate
        counter += 1


def format_result(result: Result) -> str:
    prefix = "[OK]" if result.ok else "[FAIL]"
    parts = [prefix, result.status, str(result.path), "-", result.message]
    if result.backup:
        parts.extend(["backup:", str(result.backup)])
    return " ".join(parts)


def remediation_command(args: argparse.Namespace, agentos_home: Path) -> str:
    command = [
        "python3",
        "scripts/install_global_agent_instructions.py",
        "--agentos-home",
        quote_arg(str(agentos_home)),
        "--no-dry-run",
    ]
    if args.all_default_adapters:
        command.append("--all-default-adapters")
    for adapter in args.adapter:
        command.extend(["--adapter", quote_arg(adapter)])
    return " ".join(command)


def quote_arg(value: str) -> str:
    if re.search(r"\s", value):
        return '"' + value.replace('"', '\\"') + '"'
    return value


def run_args(args: list[str], home: Path) -> tuple[int, str]:
    parsed = parser().parse_args(args)
    output = io.StringIO()
    code = run(parsed, home=home, out=output)
    return code, output.getvalue()


def make_fake_agentos(root: Path, name: str = "AgentOS") -> Path:
    agentos = root / name
    (agentos / "os" / "playbook").mkdir(parents=True)
    (agentos / "AGENTS.md").write_text("# AgentOS Adapter\n", encoding="utf-8")
    (agentos / "os" / "INDEX.md").write_text("# AgentOS Index\n", encoding="utf-8")
    (agentos / "os" / "playbook" / "PERSONAL_OVERLAY.md").write_text(
        "# Personal Overlay\n",
        encoding="utf-8",
    )
    return agentos


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_self_tests() -> int:
    tests = [
        test_dry_run_does_not_write,
        test_install_preserves_content_and_targets_existing_default_adapters,
        test_idempotent_rerun_and_path_update,
        test_check_pass_and_fail,
        test_remove_preserves_unmanaged_content,
        test_all_default_adapters_and_explicit_adapter,
        test_crlf_paths_with_spaces_and_duplicate_blocks,
        test_duplicate_adapter_dedupes_and_conflicting_adapter_fails,
        test_tilde_windows_and_relative_adapter_paths,
        test_mode_conflicts,
        test_invalid_agentos_home_fails,
    ]
    try:
        for test in tests:
            test()
    except Exception as exc:  # pragma: no cover - useful for direct script runs.
        print(f"SELF-TEST FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"SELF-TEST PASS: {len(tests)} scenario group(s) passed.")
    return 0


def test_dry_run_does_not_write() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        agentos = make_fake_agentos(root)
        code, output = run_args(["--agentos-home", str(agentos)], home)
        assert_true(code == 0, output)
        assert_true(not (home / ".agents").exists(), "dry-run created .agents")


def test_install_preserves_content_and_targets_existing_default_adapters() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        (home / ".codex").mkdir()
        codex = home / ".codex" / "AGENTS.md"
        codex.write_text("Existing Codex guidance.\n", encoding="utf-8")
        agentos = make_fake_agentos(root)
        code, output = run_args(["--agentos-home", str(agentos), "--no-dry-run"], home)
        assert_true(code == 0, output)
        global_file = global_instructions_path(home)
        assert_true(global_file.exists(), "global file was not created")
        assert_true(GLOBAL_START in read_text_preserve_newlines(global_file), "global block missing")
        codex_text = read_text_preserve_newlines(codex)
        assert_true(codex_text.startswith(ADAPTER_START), "adapter block was not prepended")
        assert_true("Existing Codex guidance." in codex_text, "existing adapter content lost")
        assert_true(not (home / ".claude").exists(), "missing default harness dir was created")
        backups = list((home / ".codex").glob("AGENTS.md.agentos-backup-*"))
        assert_true(len(backups) == 1, "expected one adapter backup")


def test_idempotent_rerun_and_path_update() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        agentos = make_fake_agentos(root, "AgentOS-one")
        code, output = run_args(["--agentos-home", str(agentos), "--no-dry-run"], home)
        assert_true(code == 0, output)
        before = read_text_preserve_newlines(global_instructions_path(home))
        backups_before = list((home / ".agents").glob("AGENTS.md.agentos-backup-*"))
        code, output = run_args(["--agentos-home", str(agentos), "--no-dry-run"], home)
        assert_true(code == 0, output)
        after = read_text_preserve_newlines(global_instructions_path(home))
        backups_after = list((home / ".agents").glob("AGENTS.md.agentos-backup-*"))
        assert_true(before == after, "idempotent rerun changed content")
        assert_true(backups_before == backups_after, "idempotent rerun created backups")

        agentos_two = make_fake_agentos(root, "AgentOS-two")
        code, output = run_args(["--agentos-home", str(agentos_two), "--no-dry-run"], home)
        assert_true(code == 0, output)
        updated = read_text_preserve_newlines(global_instructions_path(home))
        assert_true(str(agentos_two) in updated, "AgentOS path was not updated")
        assert_true(str(agentos) not in updated, "old AgentOS path remains in managed block")
        backups = list((home / ".agents").glob("AGENTS.md.agentos-backup-*"))
        assert_true(len(backups) == 1, "path update should create one backup")


def test_check_pass_and_fail() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        (home / ".gemini").mkdir()
        agentos = make_fake_agentos(root)
        args = ["--agentos-home", str(agentos), "--no-dry-run"]
        code, output = run_args(args, home)
        assert_true(code == 0, output)
        code, output = run_args(["--agentos-home", str(agentos), "--check"], home)
        assert_true(code == 0, output)

        gemini = home / ".gemini" / "GEMINI.md"
        gemini.write_text("stale\n", encoding="utf-8")
        code, output = run_args(["--agentos-home", str(agentos), "--check"], home)
        assert_true(code == 1, "check should fail on stale adapter")
        assert_true("Drift detected" in output, "check did not print remediation")


def test_remove_preserves_unmanaged_content() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        (home / ".codex").mkdir()
        codex = home / ".codex" / "AGENTS.md"
        codex.write_text("Keep me.\n", encoding="utf-8")
        agentos = make_fake_agentos(root)
        code, output = run_args(["--agentos-home", str(agentos), "--no-dry-run"], home)
        assert_true(code == 0, output)
        code, output = run_args(["--agentos-home", str(agentos), "--remove", "--no-dry-run"], home)
        assert_true(code == 0, output)
        assert_true(codex.exists(), "remove deleted adapter file")
        text = read_text_preserve_newlines(codex)
        assert_true(ADAPTER_START not in text, "remove left adapter block")
        assert_true("Keep me." in text, "remove lost unmanaged content")
        global_text = read_text_preserve_newlines(global_instructions_path(home))
        assert_true(GLOBAL_START not in global_text, "remove left global block")
        assert_true(global_instructions_path(home).exists(), "remove deleted global file")


def test_all_default_adapters_and_explicit_adapter() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        agentos = make_fake_agentos(root)
        extra = "<home>/.openclaw/AGENTS.md"
        code, output = run_args(
            [
                "--agentos-home",
                str(agentos),
                "--all-default-adapters",
                "--adapter",
                extra,
                "--no-dry-run",
            ],
            home,
        )
        assert_true(code == 0, output)
        for path in (
            home / ".codex" / "AGENTS.md",
            home / ".claude" / "CLAUDE.md",
            home / ".gemini" / "GEMINI.md",
            home / ".openclaw" / "AGENTS.md",
        ):
            assert_true(path.exists(), f"expected adapter file missing: {path}")
            assert_true(ADAPTER_START in read_text_preserve_newlines(path), f"adapter block missing: {path}")


def test_crlf_paths_with_spaces_and_duplicate_blocks() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos global installer ") as tmp:
        root = Path(tmp)
        home = root / "home with spaces and apostrophe's"
        home.mkdir()
        (home / ".codex").mkdir()
        codex = home / ".codex" / "AGENTS.md"
        codex.write_text("Existing\r\n", encoding="utf-8")
        agentos = make_fake_agentos(root, "AgentOS with spaces unicode-\u2603")
        code, output = run_args(["--agentos-home", str(agentos), "--no-dry-run"], home)
        assert_true(code == 0, output)
        codex_text = read_text_preserve_newlines(codex)
        assert_true("\r\n" in codex_text, "CRLF style was not preserved")
        assert_true(str(agentos) in read_text_preserve_newlines(global_instructions_path(home)), "path with spaces missing")

        codex.write_text(codex_text + "\n" + adapter_block(global_instructions_path(home)), encoding="utf-8")
        code, output = run_args(["--agentos-home", str(agentos), "--check"], home)
        assert_true(code == 1, "duplicate blocks should fail check")
        assert_true("duplicated" in output, "duplicate block failure should be explicit")


def test_duplicate_adapter_dedupes_and_conflicting_adapter_fails() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        agentos = make_fake_agentos(root)
        extra = "<home>/.openclaw/AGENTS.md"
        code, output = run_args(
            [
                "--agentos-home",
                str(agentos),
                "--adapter",
                extra,
                "--adapter",
                extra,
                "--no-dry-run",
            ],
            home,
        )
        assert_true(code == 0, output)
        assert_true((home / ".openclaw" / "AGENTS.md").exists(), "deduped adapter was not created")

        code, output = run_args(
            [
                "--agentos-home",
                str(agentos),
                "--adapter",
                "<home>/.agents/AGENTS.md",
            ],
            home,
        )
        assert_true(code == 1, "adapter conflicting with global target should fail")
        assert_true("conflicts" in output, "conflict failure should be explicit")


def test_tilde_windows_and_relative_adapter_paths() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        agentos = make_fake_agentos(root)
        tilde_adapter = "~" + "/.hermes/AGENTS.md"
        code, output = run_args(
            [
                "--agentos-home",
                str(agentos),
                "--adapter",
                tilde_adapter,
                "--adapter",
                r"<home>\.openclaw\AGENTS.md",
                "--no-dry-run",
            ],
            home,
        )
        assert_true(code == 0, output)
        assert_true((home / ".hermes" / "AGENTS.md").exists(), "tilde adapter did not use fake home")
        assert_true((home / ".openclaw" / "AGENTS.md").exists(), "Windows-style <home> adapter missing")

        code, output = run_args(
            [
                "--agentos-home",
                str(agentos),
                "--adapter",
                "relative-adapter/AGENTS.md",
            ],
            home,
        )
        assert_true(code == 0, output)
        assert_true(str(Path.cwd() / "relative-adapter" / "AGENTS.md") in output, "relative adapter was not resolved")
        assert_true(not (Path.cwd() / "relative-adapter").exists(), "relative dry-run created a directory")


def test_mode_conflicts() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        agentos = make_fake_agentos(root)
        code, _output = run_args(["--agentos-home", str(agentos), "--check", "--remove"], home)
        assert_true(code == 2, "--check --remove should fail")
        code, _output = run_args(["--agentos-home", str(agentos), "--check", "--no-dry-run"], home)
        assert_true(code == 2, "--check --no-dry-run should fail")
        code, _output = run_args([], home)
        assert_true(code == 2, "missing --agentos-home should fail")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = main(["--self-test", "--agentos-home", str(agentos)])
        assert_true(code == 2, "--self-test with extra flags should fail")


def test_invalid_agentos_home_fails() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        code, _output = run_args(["--agentos-home", str(root / "missing")], home)
        assert_true(code == 2, "invalid AgentOS home should fail closed")


if __name__ == "__main__":
    raise SystemExit(main())
