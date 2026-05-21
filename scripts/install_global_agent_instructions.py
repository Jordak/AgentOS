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
import shlex
import shutil
import stat
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
    import_style: str = "pointer"
    override_parts: tuple[str, ...] | None = None

    def path_for(
        self,
        home: Path,
        codex_home: Path | None = None,
        claude_config_dir: Path | None = None,
        gemini_cli_home: Path | None = None,
    ) -> Path:
        root = self.root_for(home, codex_home, claude_config_dir, gemini_cli_home)
        if self.override_parts:
            override = root.joinpath(*self.parts_for_root(self.override_parts, codex_home, claude_config_dir, gemini_cli_home))
            override_error = validate_target_path(override, allow_missing=True)
            if override_error:
                return override
            if path_is_nonempty_file(override):
                return override
        return root.joinpath(*self.parts_for_root(self.parts, codex_home, claude_config_dir, gemini_cli_home))

    def all_paths_for(
        self,
        home: Path,
        codex_home: Path | None = None,
        claude_config_dir: Path | None = None,
        gemini_cli_home: Path | None = None,
    ) -> tuple[Path, ...]:
        root = self.root_for(home, codex_home, claude_config_dir, gemini_cli_home)
        paths = [root.joinpath(*self.parts_for_root(self.parts, codex_home, claude_config_dir, gemini_cli_home))]
        if self.override_parts:
            paths.append(root.joinpath(*self.parts_for_root(self.override_parts, codex_home, claude_config_dir, gemini_cli_home)))
        return tuple(paths)

    def root_for(
        self,
        home: Path,
        codex_home: Path | None,
        claude_config_dir: Path | None,
        gemini_cli_home: Path | None,
    ) -> Path:
        if self.name == "codex" and codex_home is not None:
            return codex_home
        if self.name == "claude" and claude_config_dir is not None:
            return claude_config_dir
        if self.name == "gemini" and gemini_cli_home is not None:
            return gemini_cli_home
        return home

    def parts_for_root(
        self,
        parts: tuple[str, ...],
        codex_home: Path | None,
        claude_config_dir: Path | None,
        gemini_cli_home: Path | None,
    ) -> tuple[str, ...]:
        if self.name == "codex" and codex_home is not None and parts[:1] == (".codex",):
            return parts[1:]
        if self.name == "claude" and claude_config_dir is not None and parts[:1] == (".claude",):
            return parts[1:]
        return parts


@dataclass(frozen=True)
class Target:
    name: str
    path: Path
    kind: str
    import_style: str = "pointer"
    skipped_reason: str | None = None
    error_reason: str | None = None


@dataclass
class Result:
    ok: bool
    status: str
    path: Path
    message: str
    backup: Path | None = None


@dataclass
class FileSnapshot:
    path: Path
    existed: bool
    data: bytes | None
    mode: int | None
    missing_parents: tuple[Path, ...]


@dataclass
class RollbackError:
    path: Path
    message: str


DEFAULT_ADAPTERS = (
    AdapterSpec("codex", (".codex", "AGENTS.md"), "inline_global", (".codex", "AGENTS.override.md")),
    AdapterSpec("claude", (".claude", "CLAUDE.md"), "markdown_import"),
    AdapterSpec("gemini", (".gemini", "GEMINI.md"), "inline_global"),
)


class ManagedBlockError(ValueError):
    pass


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Install AgentOS managed global instruction adapters.",
    )
    p.add_argument(
        "--agentos-home",
        help="Resolved AgentOS checkout path. Required except with --self-test or --remove.",
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
    return run(
        args,
        home=Path.home(),
        out=sys.stdout,
        codex_home=codex_home_from_env(),
        claude_config_dir=claude_config_dir_from_env(),
        gemini_cli_home=gemini_cli_home_from_env(),
    )


def run(
    args: argparse.Namespace,
    home: Path,
    out: TextIO,
    codex_home: Path | None = None,
    claude_config_dir: Path | None = None,
    gemini_cli_home: Path | None = None,
) -> int:
    mode = "check" if args.check else "remove" if args.remove else "install"
    if args.check and args.remove:
        print("error: --check and --remove cannot be combined", file=out)
        return 2
    if args.check and args.no_dry_run:
        print("error: --check is read-only; do not combine it with --no-dry-run", file=out)
        return 2
    if not args.agentos_home and mode != "remove":
        print("error: --agentos-home is required", file=out)
        return 2

    agentos_home: Path | None = None
    if args.agentos_home:
        agentos_home = Path(args.agentos_home).expanduser()
        if not agentos_home.is_absolute():
            agentos_home = Path.cwd() / agentos_home
        agentos_home = agentos_home.resolve()

        if mode != "remove":
            validation_error = validate_agentos_home(agentos_home)
            if validation_error:
                print(f"error: {validation_error}", file=out)
                return 2

    home = home.expanduser().resolve()
    if mode != "remove":
        for label, path in (("home", home), ("AgentOS home", agentos_home)):
            if path is None:
                continue
            render_error = validate_prompt_safe_path(path)
            if render_error:
                print(
                    f"error: {label} path cannot be rendered safely in managed instructions: {render_error}",
                    file=out,
                )
                return 2
    targets = collect_targets(
        home=home,
        codex_home=codex_home,
        claude_config_dir=claude_config_dir,
        gemini_cli_home=gemini_cli_home,
        mode=mode,
        include_all_default_adapters=args.all_default_adapters,
        extra_adapters=args.adapter,
    )
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    dry_run = not args.no_dry_run
    if mode == "check":
        print("Checking AgentOS global instruction adapters.", file=out)
    elif dry_run:
        print("DRY-RUN: no files will be modified.", file=out)
    else:
        print("Applying AgentOS global instruction adapter changes.", file=out)
    if agentos_home is None:
        print("AgentOS home: not required for remove mode", file=out)
    else:
        print(f"AgentOS home: {agentos_home}", file=out)
    print(f"Canonical global file: {global_instructions_path(home)}", file=out)
    if codex_home is not None:
        print(f"Codex home: {codex_home}", file=out)
    if claude_config_dir is not None:
        print(f"Claude config dir: {claude_config_dir}", file=out)
    if gemini_cli_home is not None:
        print(f"Gemini CLI home: {gemini_cli_home}", file=out)
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

    path_errors = {
        target.path: path_error
        for target in targets
        if not target.skipped_reason
        for path_error in (validate_target_path(target.path, allow_missing=True),)
        if path_error
    }
    if path_errors:
        for target in targets:
            path_error = path_errors.get(target.path)
            if path_error:
                results.append(
                    Result(
                        ok=False,
                        status="error",
                        path=target.path,
                        message=path_error,
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
                        message="not evaluated because target path preflight failed",
                    )
                )
        for result in results:
            print(format_result(result), file=out)
        print("", file=out)
        print("Target path preflight failed; no files were modified.", file=out)
        return 1

    if mode != "check" and not dry_run:
        preflight_results = evaluate_targets(
            targets,
            mode,
            home,
            agentos_home,
            dry_run=True,
            timestamp=timestamp,
        )
        preflight_failures = [result for result in preflight_results if not result.ok]
        if preflight_failures:
            for result in preflight_results:
                print(format_result(result), file=out)
            print("", file=out)
            print("Target content preflight failed; no files were modified.", file=out)
            return 1

    rolled_back = False
    rollback_errors: list[RollbackError] = []
    if mode != "check" and not dry_run:
        results, rolled_back, rollback_errors = apply_targets_transactionally(
            targets,
            mode,
            home,
            agentos_home,
            preflight_results,
            timestamp=timestamp,
        )
    else:
        results = evaluate_targets(
            targets,
            mode,
            home,
            agentos_home,
            dry_run=dry_run,
            timestamp=timestamp,
        )

    for result in results:
        print(format_result(result), file=out)

    failures = [result for result in results if not result.ok]
    if failures:
        print("", file=out)
        if mode == "check":
            print("Drift detected. Remediation:", file=out)
            print(remediation_command(args, agentos_home), file=out)
        elif rolled_back:
            if rollback_errors:
                print(
                    "Some targets failed. Rollback was attempted but did not complete; inspect rollback-error entries above.",
                    file=out,
                )
            else:
                print("Some targets failed. Earlier changes were rolled back.", file=out)
        else:
            print("Some targets failed. Files reporting failure were not modified.", file=out)
        return 1

    return 0


def evaluate_targets(
    targets: list[Target],
    mode: str,
    home: Path,
    agentos_home: Path | None,
    dry_run: bool,
    timestamp: str,
) -> list[Result]:
    results: list[Result] = []
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
        results.append(evaluate_target(target, mode, home, agentos_home, dry_run, timestamp))
    return results


def apply_targets_transactionally(
    targets: list[Target],
    mode: str,
    home: Path,
    agentos_home: Path | None,
    preflight_results: list[Result],
    timestamp: str,
) -> tuple[list[Result], bool, list[RollbackError]]:
    results: list[Result] = []
    snapshots: list[FileSnapshot] = []

    for index, target in enumerate(targets):
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

        preflight = preflight_results[index]
        try:
            snapshots.append(capture_snapshot(target.path))
            if preflight.backup is not None:
                snapshots.append(capture_snapshot(preflight.backup))
        except OSError as exc:
            results.append(Result(False, "error", target.path, f"filesystem error before write: {exc}"))
            rollback_errors = rollback_snapshots(snapshots)
            append_rollback_error_results(results, rollback_errors)
            append_not_run_results(results, targets[index + 1 :])
            return results, True, rollback_errors

        result = evaluate_target(
            target,
            mode,
            home,
            agentos_home,
            dry_run=False,
            timestamp=timestamp,
        )
        results.append(result)
        if not result.ok:
            rollback_errors = rollback_snapshots(snapshots)
            append_rollback_error_results(results, rollback_errors)
            append_not_run_results(results, targets[index + 1 :])
            return results, True, rollback_errors

    return results, False, []


def append_not_run_results(results: list[Result], remaining_targets: list[Target]) -> None:
    for target in remaining_targets:
        if target.skipped_reason:
            results.append(Result(True, "skip", target.path, target.skipped_reason))
        else:
            results.append(Result(True, "not run", target.path, "not evaluated because an earlier write failed"))


def append_rollback_error_results(results: list[Result], rollback_errors: list[RollbackError]) -> None:
    for error in rollback_errors:
        results.append(Result(False, "rollback-error", error.path, f"rollback did not restore this path: {error.message}"))


def capture_snapshot(path: Path) -> FileSnapshot:
    missing_parents = tuple(missing_parent_dirs(path))
    if path.exists() and path.is_file() and not path.is_symlink():
        return FileSnapshot(
            path=path,
            existed=True,
            data=path.read_bytes(),
            mode=path.stat().st_mode & 0o7777,
            missing_parents=missing_parents,
        )
    return FileSnapshot(path=path, existed=False, data=None, mode=None, missing_parents=missing_parents)


def missing_parent_dirs(path: Path) -> list[Path]:
    missing: list[Path] = []
    parent = path.parent
    while not parent.exists():
        missing.append(parent)
        if parent.parent == parent:
            break
        parent = parent.parent
    return missing


def rollback_snapshots(snapshots: list[FileSnapshot]) -> list[RollbackError]:
    errors: list[RollbackError] = []
    existing_snapshots = [snapshot for snapshot in snapshots if snapshot.existed]
    missing_snapshots = [snapshot for snapshot in snapshots if not snapshot.existed]

    for snapshot in reversed(existing_snapshots):
        try:
            restore_snapshot(snapshot)
        except OSError as exc:
            errors.append(RollbackError(snapshot.path, str(exc)))

    if errors:
        return errors

    for snapshot in reversed(missing_snapshots):
        try:
            restore_snapshot(snapshot)
        except OSError as exc:
            errors.append(RollbackError(snapshot.path, str(exc)))
    return errors


def restore_snapshot(snapshot: FileSnapshot) -> None:
    if snapshot.existed:
        if snapshot.data is None:
            return
        write_bytes_atomic(snapshot.path, snapshot.data, mode=snapshot.mode)
    else:
        if snapshot.path.exists() or snapshot.path.is_symlink():
            if snapshot.path.is_dir() and not snapshot.path.is_symlink():
                snapshot.path.rmdir()
            else:
                snapshot.path.unlink()
    for parent in snapshot.missing_parents:
        try:
            parent.rmdir()
        except OSError:
            break


def codex_home_from_env() -> Path | None:
    raw = os.environ.get("CODEX_HOME")
    if not raw:
        return None
    return absolute_lexical_path(Path(os.path.expanduser(raw)))


def claude_config_dir_from_env() -> Path | None:
    raw = os.environ.get("CLAUDE_CONFIG_DIR")
    if not raw:
        return None
    return absolute_lexical_path(Path(os.path.expanduser(raw)))


def gemini_cli_home_from_env() -> Path | None:
    raw = os.environ.get("GEMINI_CLI_HOME")
    if not raw:
        return None
    return absolute_lexical_path(Path(os.path.expanduser(raw)))


def evaluate_target(
    target: Target,
    mode: str,
    home: Path,
    agentos_home: Path | None,
    dry_run: bool,
    timestamp: str,
) -> Result:
    try:
        if mode == "check":
            if agentos_home is None:
                return Result(False, "error", target.path, "--agentos-home is required for --check")
            return check_target(target, home, agentos_home)
        if mode == "remove":
            return remove_target(target, dry_run=dry_run, timestamp=timestamp)
        if agentos_home is None:
            return Result(False, "error", target.path, "--agentos-home is required for install")
        return install_target(
            target,
            home,
            agentos_home,
            dry_run=dry_run,
            timestamp=timestamp,
        )
    except ManagedBlockError as exc:
        return Result(False, "error", target.path, str(exc))
    except UnicodeError as exc:
        return Result(False, "error", target.path, f"could not read file as UTF-8: {exc}")
    except OSError as exc:
        return Result(False, "error", target.path, f"filesystem error: {exc}")


def validate_agentos_home(agentos_home: Path) -> str | None:
    required = (
        agentos_home / "AGENTS.md",
        agentos_home / "os" / "INDEX.md",
        agentos_home / "os" / "playbook" / "PERSONAL_OVERLAY.md",
    )
    try:
        home_stat = agentos_home.lstat()
        if not stat.S_ISDIR(home_stat.st_mode):
            return f"AgentOS home is not a directory: {agentos_home}"
        missing: list[str] = []
        for path in required:
            try:
                path_stat = path.lstat()
            except FileNotFoundError:
                missing.append(str(path))
                continue
            if not stat.S_ISREG(path_stat.st_mode):
                missing.append(str(path))
        if missing:
            return "AgentOS home is missing required files: " + ", ".join(missing)
    except FileNotFoundError:
        return f"AgentOS home does not exist: {agentos_home}"
    except OSError as exc:
        return f"AgentOS home filesystem probe failed: {exc}"
    return None


def validate_prompt_safe_path(path: Path) -> str | None:
    text = str(path)
    for char in text:
        code = ord(char)
        if char == "`":
            return "contains a backtick"
        if char in {"\n", "\r"}:
            return "contains a newline"
        if code < 32 or code == 127:
            return f"contains control character U+{code:04X}"
    for marker in (GLOBAL_START, GLOBAL_END, ADAPTER_START, ADAPTER_END):
        if marker in text:
            return "contains an AgentOS managed block marker"
    return None


def global_instructions_path(home: Path) -> Path:
    return home / ".agents" / "AGENTS.md"


def collect_targets(
    home: Path,
    codex_home: Path | None,
    claude_config_dir: Path | None,
    gemini_cli_home: Path | None,
    mode: str,
    include_all_default_adapters: bool,
    extra_adapters: Iterable[str],
) -> list[Target]:
    targets: list[Target] = []
    seen: dict[Path, int] = {}

    def add_target(target: Target) -> None:
        key = absolute_lexical_path(target.path)
        existing_index = seen.get(key)
        if existing_index is None:
            for existing in targets:
                if target_paths_conflict(existing.path, target.path):
                    targets.append(
                        Target(
                            target.name,
                            target.path,
                            target.kind,
                            target.import_style,
                            error_reason=f"target conflicts with {existing.kind} target {existing.path}",
                        )
                    )
                    return
            seen[key] = len(targets)
            targets.append(target)
            return
        existing = targets[existing_index]
        if existing.kind == target.kind:
            if existing.skipped_reason and not target.skipped_reason:
                targets[existing_index] = Target(
                    target.name,
                    target.path,
                    target.kind,
                    existing.import_style,
                )
            return
        targets.append(
            Target(
                target.name,
                target.path,
                target.kind,
                target.import_style,
                error_reason=f"target conflicts with {existing.kind} target {existing.path}",
            )
        )

    add_target(Target("global", global_instructions_path(home), "global"))
    for spec in DEFAULT_ADAPTERS:
        managed_paths = managed_paths_for_spec(spec, home, codex_home, claude_config_dir, gemini_cli_home)
        for path in managed_paths:
            parent_exists, parent_error = path_exists_for_planning(path.parent)
            if parent_error:
                add_target(
                    Target(
                        spec.name,
                        path,
                        "adapter",
                        spec.import_style,
                        error_reason=parent_error,
                    )
                )
                continue
            if include_all_default_adapters or parent_exists:
                add_target(Target(spec.name, path, "adapter", spec.import_style))
            else:
                add_target(
                    Target(
                        spec.name,
                        path,
                        "adapter",
                        spec.import_style,
                        skipped_reason=f"default {spec.name} adapter skipped because {path.parent} does not exist",
                    )
                )
        if mode in {"check", "remove"} and spec.override_parts:
            for sibling in spec.all_paths_for(home, codex_home, claude_config_dir, gemini_cli_home):
                if sibling in managed_paths:
                    continue
                sibling_error = validate_target_path(sibling, allow_missing=True)
                if sibling_error:
                    add_target(
                        Target(
                            f"{spec.name}:sibling",
                            sibling,
                            "adapter",
                            spec.import_style,
                            error_reason=sibling_error,
                        )
                    )
                    continue
                if should_check_sibling_target(sibling, mode):
                    if mode == "check":
                        add_target(
                            Target(
                                f"{spec.name}:sibling",
                                sibling,
                                "adapter",
                                spec.import_style,
                                error_reason="inactive adapter sibling contains an AgentOS managed block; run --remove to clean it or inspect it before relying on --check",
                            )
                        )
                    else:
                        add_target(Target(f"{spec.name}:sibling", sibling, "adapter", spec.import_style))
    for raw in extra_adapters:
        path = resolve_user_path(raw, home)
        add_target(Target(f"adapter:{raw}", path, "adapter"))
    return targets


def managed_paths_for_spec(
    spec: AdapterSpec,
    home: Path,
    codex_home: Path | None,
    claude_config_dir: Path | None,
    gemini_cli_home: Path | None,
) -> tuple[Path, ...]:
    active_path = spec.path_for(home, codex_home, claude_config_dir, gemini_cli_home)
    paths: list[Path] = [active_path]
    if spec.name == "codex" and spec.override_parts:
        all_paths = spec.all_paths_for(home, codex_home, claude_config_dir, gemini_cli_home)
        base_path = all_paths[0]
        if active_path != base_path:
            paths.insert(0, base_path)
    return tuple(dict.fromkeys(paths))


def should_check_sibling_target(path: Path, mode: str) -> bool:
    if mode == "remove":
        return path.exists() or path.is_symlink()
    if not (path.exists() or path.is_symlink()):
        return False
    if path.is_symlink():
        return True
    if not path.is_file():
        return True
    try:
        data = path.read_bytes()
    except OSError:
        return True
    return ADAPTER_START.encode("utf-8") in data or ADAPTER_END.encode("utf-8") in data


def resolve_user_path(raw: str, home: Path) -> Path:
    if raw == "<home>":
        return home
    for prefix in ("<home>/", "<home>\\"):
        if raw.startswith(prefix):
            rest = raw[len(prefix) :]
            parts = [part for part in re.split(r"[\\/]+", rest) if part]
            return absolute_lexical_path(home.joinpath(*parts))
    if raw == "~":
        return home
    tilde = "~"
    for prefix in (tilde + "/", tilde + "\\"):
        if raw.startswith(prefix):
            rest = raw[len(prefix) :]
            parts = [part for part in re.split(r"[\\/]+", rest) if part]
            return absolute_lexical_path(home.joinpath(*parts))
    path = Path(os.path.expanduser(raw))
    return absolute_lexical_path(path)


def absolute_lexical_path(path: Path) -> Path:
    if not path.is_absolute():
        path = Path.cwd() / path
    return Path(os.path.abspath(os.fspath(path)))


def target_paths_conflict(existing: Path, candidate: Path) -> bool:
    existing_abs = absolute_lexical_path(existing)
    candidate_abs = absolute_lexical_path(candidate)
    if existing_abs == candidate_abs:
        return True
    if casefolded_path_parts(existing_abs) == casefolded_path_parts(candidate_abs):
        return True
    try:
        if existing_abs.exists() and candidate_abs.exists() and existing_abs.samefile(candidate_abs):
            return True
    except OSError:
        pass
    if existing_abs.name.casefold() != candidate_abs.name.casefold():
        return False
    existing_parent = absolute_lexical_path(existing_abs.parent)
    candidate_parent = absolute_lexical_path(candidate_abs.parent)
    if existing_parent == candidate_parent:
        return True
    try:
        return existing_parent.exists() and candidate_parent.exists() and existing_parent.samefile(candidate_parent)
    except OSError:
        return False


def casefolded_path_parts(path: Path) -> tuple[str, ...]:
    return tuple(part.casefold() for part in path.parts)


def path_exists_for_planning(path: Path) -> tuple[bool, str | None]:
    try:
        path.lstat()
    except FileNotFoundError:
        return False, None
    except OSError as exc:
        return False, f"filesystem probe failed: {exc}"
    return True, None


def expected_block(target: Target, home: Path, agentos_home: Path) -> str:
    if target.kind == "global":
        return global_block(agentos_home)
    if target.import_style == "inline_global":
        return inline_global_adapter_block(home, agentos_home)
    return adapter_block(global_instructions_path(home), target.import_style)


def global_instructions_body(agentos_home: Path) -> str:
    agentos_home_text = prompt_path(agentos_home)
    agents_path_text = prompt_path(agentos_home / "AGENTS.md")
    index_path_text = prompt_path(agentos_home / "os" / "INDEX.md")
    return f"""# Global Agent Instructions

AgentOS is installed at:

`{agentos_home_text}`

When a task would benefit from reusable identity, context, skills, memory, connections, agents, verification habits, playbooks, or automations, read the relevant files under that workspace.

Start with:

1. `{agents_path_text}`
2. `{index_path_text}`

If that workspace is unavailable, continue with the current project's local instructions and say AgentOS context could not be loaded.

Before answering questions about fast-moving tools, check current official docs or primary sources.

Ask before sending messages, posting publicly, changing permissions, entering credentials, handling MFA, deleting nontrivial data, installing software, or granting external write access.

Keep global instructions lean. Put detailed project-specific instructions in each project's local agent instruction file.
"""


def global_block(agentos_home: Path) -> str:
    return f"""{GLOBAL_START}
{global_instructions_body(agentos_home).rstrip()}
{GLOBAL_END}
"""


def effective_global_instructions(home: Path, agentos_home: Path) -> str:
    block = global_block(agentos_home)
    existing = read_optional(global_instructions_path(home))
    if existing is None:
        return ensure_trailing_newline(block)
    return upsert_block(existing, block, GLOBAL_START, GLOBAL_END)


def inline_global_adapter_block(home: Path, agentos_home: Path) -> str:
    canonical = effective_global_instructions(home, agentos_home).rstrip()
    return f"""{ADAPTER_START}
{canonical}
{ADAPTER_END}
"""


def adapter_block(global_path: Path, import_style: str = "pointer") -> str:
    global_path_text = prompt_path(global_path)
    if import_style == "markdown_import":
        return f"""{ADAPTER_START}
AgentOS global instructions are managed at:

@{markdown_import_path(global_path)}

If your harness does not expand Markdown `@path` imports, read this file first:

`{global_path_text}`

Then continue with the rest of this file.
{ADAPTER_END}
"""
    return f"""{ADAPTER_START}
AgentOS global instructions are managed at:

`{global_path_text}`

Read that file first, then continue with the rest of this file.
{ADAPTER_END}
"""


def prompt_path(path: Path) -> str:
    path_error = validate_prompt_safe_path(path)
    if path_error:
        raise ManagedBlockError(f"path cannot be rendered safely in managed instructions: {path_error}")
    return str(path)


def markdown_import_path(path: Path) -> str:
    return re.sub(r"([ \t])", r"\\\1", prompt_path(path))


def check_target(target: Target, home: Path, agentos_home: Path) -> Result:
    path_error = validate_target_path(target.path, allow_missing=True)
    if path_error:
        return Result(False, "error", target.path, path_error)
    if not target.path.exists():
        return Result(False, "missing", target.path, "file is missing")
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
    path_error = validate_target_path(target.path, allow_missing=True)
    if path_error:
        return Result(False, "error", target.path, path_error)

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

    mode = target.path.stat().st_mode & 0o7777
    target.path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target.path, backup)
    write_text_atomic(target.path, desired, mode=mode)
    return Result(True, "updated", target.path, "managed block inserted or replaced", backup)


def remove_target(target: Target, dry_run: bool, timestamp: str) -> Result:
    path_error = validate_target_path(target.path, allow_missing=True)
    if path_error:
        return Result(False, "error", target.path, path_error)
    if not target.path.exists():
        return Result(True, "skip", target.path, "file is missing")
    original = read_text_preserve_newlines(target.path)
    desired = remove_block(original, *markers_for(target.kind))
    if desired == original:
        return Result(True, "unchanged", target.path, "managed block was not present")

    backup = backup_path_for(target.path, timestamp)
    if dry_run:
        return Result(True, "would update", target.path, "managed block would be removed", backup)

    mode = target.path.stat().st_mode & 0o7777
    shutil.copy2(target.path, backup)
    write_text_atomic(target.path, desired, mode=mode)
    return Result(True, "updated", target.path, "managed block removed", backup)


def validate_target_path(path: Path, allow_missing: bool) -> str | None:
    try:
        for ancestor in path.parents:
            try:
                ancestor_stat = ancestor.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(ancestor_stat.st_mode):
                return f"ancestor directory is a symlink: {ancestor}; refusing to modify managed instruction files through links"
            if not stat.S_ISDIR(ancestor_stat.st_mode):
                return f"ancestor path is not a directory: {ancestor}"

        try:
            path_stat = path.lstat()
        except FileNotFoundError:
            if not allow_missing:
                return "file is missing"
        else:
            if stat.S_ISLNK(path_stat.st_mode):
                return "path is a symlink; refusing to modify managed instruction files through links"
            if stat.S_ISDIR(path_stat.st_mode):
                return "path is a directory, expected a file"
            if not stat.S_ISREG(path_stat.st_mode):
                return "path is not a regular file"

        parent = path.parent
        try:
            parent_stat = parent.lstat()
        except FileNotFoundError:
            pass
        else:
            if stat.S_ISLNK(parent_stat.st_mode):
                return "parent directory is a symlink; refusing to modify managed instruction files through links"
            if not stat.S_ISDIR(parent_stat.st_mode):
                return "parent path is not a directory"
    except OSError as exc:
        return f"filesystem probe failed: {exc}"
    return None


def path_is_nonempty_file(path: Path) -> bool:
    try:
        return path.exists() and path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def write_text_atomic(path: Path, text: str, mode: int | None = None) -> None:
    write_bytes_atomic(path, text.encode("utf-8"), mode=mode)


def write_bytes_atomic(path: Path, data: bytes, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        if mode is not None:
            if hasattr(os, "fchmod"):
                os.fchmod(fd, mode)
            else:
                os.chmod(tmp_path, mode)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
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
        separator = "" if not text else newline
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
    backup_error = validate_target_path(candidate, allow_missing=True)
    if backup_error:
        raise ManagedBlockError(f"unsafe backup path {candidate}: {backup_error}")
    if not candidate.exists():
        return candidate
    counter = 2
    while True:
        next_candidate = path.with_name(f"{path.name}.agentos-backup-{timestamp}-{counter}")
        backup_error = validate_target_path(next_candidate, allow_missing=True)
        if backup_error:
            raise ManagedBlockError(f"unsafe backup path {next_candidate}: {backup_error}")
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
        str(agentos_home),
        "--no-dry-run",
    ]
    if args.all_default_adapters:
        command.append("--all-default-adapters")
    for adapter in args.adapter:
        command.extend(["--adapter", adapter])
    return shlex.join(command)


def run_args(args: list[str], home: Path) -> tuple[int, str]:
    parsed = parser().parse_args(args)
    output = io.StringIO()
    code = run(parsed, home=home, out=output)
    return code, output.getvalue()


def run_args_with_codex_home(args: list[str], home: Path, codex_home: Path | None) -> tuple[int, str]:
    parsed = parser().parse_args(args)
    output = io.StringIO()
    code = run(parsed, home=home, out=output, codex_home=codex_home)
    return code, output.getvalue()


def run_args_with_adapter_homes(
    args: list[str],
    home: Path,
    codex_home: Path | None = None,
    claude_config_dir: Path | None = None,
    gemini_cli_home: Path | None = None,
) -> tuple[int, str]:
    parsed = parser().parse_args(args)
    output = io.StringIO()
    code = run(
        parsed,
        home=home,
        out=output,
        codex_home=codex_home,
        claude_config_dir=claude_config_dir,
        gemini_cli_home=gemini_cli_home,
    )
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
        test_remove_does_not_require_live_agentos_home,
        test_inline_adapters_mirror_effective_global_file,
        test_codex_override_file_is_effective_adapter_target,
        test_claude_config_dir_targets_profile_root,
        test_gemini_cli_home_targets_profile_root,
        test_all_default_adapters_and_explicit_adapter,
        test_explicit_default_adapter_overrides_skipped_default,
        test_import_adapters_escape_spaces,
        test_prompt_rendered_paths_reject_prompt_breakout_chars,
        test_inaccessible_targets_fail_structured,
        test_crlf_paths_with_spaces_and_duplicate_blocks,
        test_preflight_prevents_partial_writes,
        test_symlink_targets_fail_closed_and_modes_are_preserved,
        test_remediation_command_shell_quotes_dynamic_args,
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
        assert_true("# Global Agent Instructions" in codex_text, "Codex adapter did not inline global instructions")
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
        codex_original = "Keep me.\n"
        codex.write_text(codex_original, encoding="utf-8")
        global_original = "Global keep.\n"
        global_instructions_path(home).parent.mkdir()
        global_instructions_path(home).write_text(global_original, encoding="utf-8")
        agentos = make_fake_agentos(root)
        code, output = run_args(["--agentos-home", str(agentos), "--no-dry-run"], home)
        assert_true(code == 0, output)
        code, output = run_args(["--agentos-home", str(agentos), "--remove", "--no-dry-run"], home)
        assert_true(code == 0, output)
        assert_true(codex.exists(), "remove deleted adapter file")
        text = read_text_preserve_newlines(codex)
        assert_true(ADAPTER_START not in text, "remove left adapter block")
        assert_true(text == codex_original, "remove did not restore unmanaged adapter content exactly")
        global_text = read_text_preserve_newlines(global_instructions_path(home))
        assert_true(GLOBAL_START not in global_text, "remove left global block")
        assert_true(global_text == global_original, "remove did not restore unmanaged global content exactly")
        assert_true(global_instructions_path(home).exists(), "remove deleted global file")


def test_remove_does_not_require_live_agentos_home() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        agentos = make_fake_agentos(root)
        code, output = run_args(["--agentos-home", str(agentos), "--no-dry-run"], home)
        assert_true(code == 0, output)
        agentos.rename(root / "AgentOS-moved")
        code, output = run_args(["--remove", "--no-dry-run"], home)
        assert_true(code == 0, output)
        assert_true(GLOBAL_START not in read_text_preserve_newlines(global_instructions_path(home)), "remove needed live AgentOS home")


def test_inline_adapters_mirror_effective_global_file() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        (home / ".codex").mkdir()
        (home / ".gemini").mkdir()
        global_file = global_instructions_path(home)
        global_file.parent.mkdir()
        global_file.write_text("Existing global guidance.\n", encoding="utf-8")
        agentos = make_fake_agentos(root)
        code, output = run_args(["--agentos-home", str(agentos), "--no-dry-run"], home)
        assert_true(code == 0, output)
        global_text = read_text_preserve_newlines(global_file)
        codex_text = read_text_preserve_newlines(home / ".codex" / "AGENTS.md")
        gemini_text = read_text_preserve_newlines(home / ".gemini" / "GEMINI.md")
        assert_true("Existing global guidance." in global_text, "global file lost unmanaged content")
        assert_true("Existing global guidance." in codex_text, "inline Codex adapter did not mirror unmanaged global content")
        assert_true("Existing global guidance." in gemini_text, "inline Gemini adapter did not mirror unmanaged global content")
        assert_true(GLOBAL_START in codex_text, "inline Codex adapter did not mirror managed global block")
        assert_true(GLOBAL_START in gemini_text, "inline Gemini adapter did not mirror managed global block")
        code, output = run_args(["--agentos-home", str(agentos), "--check"], home)
        assert_true(code == 0, output)


def test_codex_override_file_is_effective_adapter_target() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        (home / ".codex").mkdir()
        override = home / ".codex" / "AGENTS.override.md"
        override.write_text("Existing override guidance.\n", encoding="utf-8")
        agentos = make_fake_agentos(root)
        code, output = run_args(["--agentos-home", str(agentos), "--no-dry-run"], home)
        assert_true(code == 0, output)
        base = home / ".codex" / "AGENTS.md"
        override_text = read_text_preserve_newlines(override)
        base_text = read_text_preserve_newlines(base)
        assert_true(override_text.startswith(ADAPTER_START), "Codex override adapter block was not prepended")
        assert_true(base_text.startswith(ADAPTER_START), "durable Codex base adapter block was not created")
        assert_true("# Global Agent Instructions" in override_text, "Codex override adapter did not inline global instructions")
        assert_true("# Global Agent Instructions" in base_text, "Codex base adapter did not inline global instructions")
        assert_true("Existing override guidance." in override_text, "Codex override content was lost")
        code, output = run_args(["--agentos-home", str(agentos), "--check"], home)
        assert_true(code == 0, output)

        fallback_home = root / "fallback-home"
        fallback_home.mkdir()
        (fallback_home / ".codex").mkdir()
        agentos_one = make_fake_agentos(root, "AgentOS-one")
        code, output = run_args(["--agentos-home", str(agentos_one), "--no-dry-run"], fallback_home)
        assert_true(code == 0, output)
        fallback_codex = fallback_home / ".codex" / "AGENTS.md"
        fallback_override = fallback_home / ".codex" / "AGENTS.override.md"
        fallback_override.write_text("Later override.\n", encoding="utf-8")
        agentos_two = make_fake_agentos(root, "AgentOS-two")
        code, output = run_args(["--agentos-home", str(agentos_two), "--no-dry-run"], fallback_home)
        assert_true(code == 0, output)
        code, output = run_args(["--agentos-home", str(agentos_two), "--check"], fallback_home)
        assert_true(code == 0, "Codex override and durable base should both check clean")
        assert_true(ADAPTER_START in read_text_preserve_newlines(fallback_codex), "durable Codex base was not managed")
        assert_true(ADAPTER_START in read_text_preserve_newlines(fallback_override), "Codex override was not managed")
        assert_true(str(agentos_two) in read_text_preserve_newlines(global_instructions_path(fallback_home)), "global path was not updated")
        code, output = run_args(["--agentos-home", str(agentos_one), "--remove", "--no-dry-run"], fallback_home)
        assert_true(code == 0, output)
        assert_true(ADAPTER_START not in read_text_preserve_newlines(fallback_codex), "remove left managed block in Codex fallback")
        assert_true(ADAPTER_START not in read_text_preserve_newlines(fallback_override), "remove left managed block in Codex override")

        unsafe_home = root / "unsafe-home"
        unsafe_home.mkdir()
        (unsafe_home / ".codex").mkdir()
        (unsafe_home / ".codex" / "AGENTS.override.md").write_text("Active override.\n", encoding="utf-8")
        unsafe_sibling_target = root / "unsafe-sibling-target"
        (unsafe_home / ".codex" / "AGENTS.md").symlink_to(unsafe_sibling_target)
        code, output = run_args(["--agentos-home", str(agentos), "--check"], unsafe_home)
        assert_true(code == 1, "unsafe inactive Codex sibling should fail check")
        assert_true("symlink" in output, "unsafe inactive sibling check should be explicit")

        linked_codex_home = root / "linked-codex-home"
        linked_codex_home.mkdir()
        linked_codex_target = root / "linked-codex-target"
        linked_codex_target.mkdir()
        (linked_codex_target / "AGENTS.override.md").write_text("Outside override.\n", encoding="utf-8")
        (linked_codex_home / ".codex").symlink_to(linked_codex_target, target_is_directory=True)
        code, output = run_args(["--agentos-home", str(agentos), "--check"], linked_codex_home)
        assert_true(code == 1, "symlinked Codex home should fail check")
        assert_true("symlink" in output, "symlinked Codex home failure should be explicit")

        profile_home = root / "profile-home"
        profile_home.mkdir()
        codex_profile = root / "codex-profile"
        codex_profile.mkdir()
        agentos_profile = make_fake_agentos(root, "AgentOS-profile")
        code, output = run_args_with_codex_home(
            ["--agentos-home", str(agentos_profile), "--no-dry-run"],
            profile_home,
            codex_profile.resolve(),
        )
        assert_true(code == 0, output)
        assert_true((codex_profile / "AGENTS.md").exists(), "CODEX_HOME adapter was not created")
        assert_true(not (profile_home / ".codex").exists(), "default Codex home was used despite CODEX_HOME")
        code, output = run_args_with_codex_home(
            ["--agentos-home", str(agentos_profile), "--check"],
            profile_home,
            codex_profile.resolve(),
        )
        assert_true(code == 0, output)


def test_gemini_cli_home_targets_profile_root() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        gemini_cli_home = root / "gemini-cli-home"
        (gemini_cli_home / ".gemini").mkdir(parents=True)
        agentos = make_fake_agentos(root)
        code, output = run_args_with_adapter_homes(
            ["--agentos-home", str(agentos), "--no-dry-run"],
            home,
            gemini_cli_home=gemini_cli_home.resolve(),
        )
        assert_true(code == 0, output)
        assert_true((gemini_cli_home / ".gemini" / "GEMINI.md").exists(), "GEMINI_CLI_HOME adapter was not created")
        assert_true(not (home / ".gemini").exists(), "default Gemini home was used despite GEMINI_CLI_HOME")
        code, output = run_args_with_adapter_homes(
            ["--agentos-home", str(agentos), "--check"],
            home,
            gemini_cli_home=gemini_cli_home.resolve(),
        )
        assert_true(code == 0, output)


def test_claude_config_dir_targets_profile_root() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        claude_config_dir = root / "claude-config"
        claude_config_dir.mkdir()
        agentos = make_fake_agentos(root)
        code, output = run_args_with_adapter_homes(
            ["--agentos-home", str(agentos), "--no-dry-run"],
            home,
            claude_config_dir=claude_config_dir.resolve(),
        )
        assert_true(code == 0, output)
        assert_true((claude_config_dir / "CLAUDE.md").exists(), "CLAUDE_CONFIG_DIR adapter was not created")
        assert_true(not (home / ".claude").exists(), "default Claude home was used despite CLAUDE_CONFIG_DIR")
        code, output = run_args_with_adapter_homes(
            ["--agentos-home", str(agentos), "--check"],
            home,
            claude_config_dir=claude_config_dir.resolve(),
        )
        assert_true(code == 0, output)


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
        resolved_global = global_instructions_path(home.resolve())
        claude_text = read_text_preserve_newlines(home / ".claude" / "CLAUDE.md")
        codex_text = read_text_preserve_newlines(home / ".codex" / "AGENTS.md")
        gemini_text = read_text_preserve_newlines(home / ".gemini" / "GEMINI.md")
        openclaw_text = read_text_preserve_newlines(home / ".openclaw" / "AGENTS.md")
        assert_true("# Global Agent Instructions" in codex_text, "Codex adapter did not inline global instructions")
        assert_true(f"@{resolved_global}" not in codex_text, "Codex adapter should not rely on transitive pointer/import behavior")
        assert_true(f"@{resolved_global}" in claude_text, "Claude adapter import missing")
        assert_true("# Global Agent Instructions" in gemini_text, "Gemini adapter did not inline global instructions")
        assert_true(str(agentos.resolve()) in gemini_text, "Gemini inline adapter missing AgentOS path")
        assert_true(f"@{resolved_global}" not in gemini_text, "Gemini adapter should not import outside its context root")
        assert_true(f"@{resolved_global}" not in openclaw_text, "unknown adapter should not assume import support")


def test_explicit_default_adapter_overrides_skipped_default() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        agentos = make_fake_agentos(root)
        code, output = run_args(
            [
                "--agentos-home",
                str(agentos),
                "--adapter",
                "<home>/.claude/CLAUDE.md",
                "--no-dry-run",
            ],
            home,
        )
        assert_true(code == 0, output)
        claude = home / ".claude" / "CLAUDE.md"
        assert_true(claude.exists(), "explicit default-path adapter was skipped")
        assert_true(f"@{global_instructions_path(home.resolve())}" in read_text_preserve_newlines(claude), "known default import style was lost")


def test_import_adapters_escape_spaces() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos global installer ") as tmp:
        root = Path(tmp)
        home = root / "home with spaces"
        home.mkdir()
        (home / ".claude").mkdir()
        (home / ".gemini").mkdir()
        agentos = make_fake_agentos(root)
        code, output = run_args(["--agentos-home", str(agentos), "--no-dry-run"], home)
        assert_true(code == 0, output)
        escaped_global = markdown_import_path(global_instructions_path(home.resolve()))
        claude_text = read_text_preserve_newlines(home / ".claude" / "CLAUDE.md")
        gemini_text = read_text_preserve_newlines(home / ".gemini" / "GEMINI.md")
        assert_true(f"@{escaped_global}" in claude_text, "Claude import path did not escape spaces")
        assert_true("# Global Agent Instructions" in gemini_text, "Gemini adapter did not inline global instructions")
        assert_true(str(agentos.resolve()) in gemini_text, "Gemini inline adapter missing AgentOS path")
        assert_true(f"@{escaped_global}" not in gemini_text, "Gemini adapter should not import a path with spaces")


def test_prompt_rendered_paths_reject_prompt_breakout_chars() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        unsafe_agentos = make_fake_agentos(root, "AgentOS\nINJECTED")
        home = root / "home"
        home.mkdir()
        code, output = run_args(["--agentos-home", str(unsafe_agentos), "--no-dry-run"], home)
        assert_true(code == 2, "unsafe AgentOS home path should fail before writing")
        assert_true("cannot be rendered safely" in output, "unsafe AgentOS home path failure should be explicit")
        assert_true(not global_instructions_path(home).exists(), "unsafe AgentOS home path wrote global instructions")

        unsafe_home = root / "home`bad"
        unsafe_home.mkdir()
        agentos = make_fake_agentos(root)
        code, output = run_args(["--agentos-home", str(agentos), "--no-dry-run"], unsafe_home)
        assert_true(code == 2, "unsafe home path should fail before writing")
        assert_true("cannot be rendered safely" in output, "unsafe home path failure should be explicit")

        marker_agentos = make_fake_agentos(root, f"AgentOS {GLOBAL_END}")
        marker_home = root / "marker-home"
        marker_home.mkdir()
        code, output = run_args(["--agentos-home", str(marker_agentos), "--no-dry-run"], marker_home)
        assert_true(code == 2, "managed marker in AgentOS home path should fail before writing")
        assert_true("managed block marker" in output, "managed marker path failure should be explicit")


def test_inaccessible_targets_fail_structured() -> None:
    if os.name != "posix":
        return
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        blocked_agentos_parent = (root / "blocked-agentos-parent").resolve()
        blocked_agentos_parent.mkdir()
        blocked_agentos = make_fake_agentos(blocked_agentos_parent)
        home = root / "home"
        home.mkdir()
        unreadable_codex = home / ".codex"
        unreadable_codex.mkdir()
        agentos = make_fake_agentos(root)
        os.chmod(blocked_agentos_parent, 0)
        try:
            code, output = run_args(["--agentos-home", str(blocked_agentos)], home)
        finally:
            os.chmod(blocked_agentos_parent, 0o700)
        assert_true(code == 2, "unreadable AgentOS home should fail")
        assert_true("error:" in output, "unreadable AgentOS home failure should be structured")
        assert_true("filesystem probe failed" in output, "unreadable AgentOS home failure should mention probe failure")

        os.chmod(unreadable_codex, 0)
        try:
            code, output = run_args(["--agentos-home", str(agentos)], home)
        finally:
            os.chmod(unreadable_codex, 0o700)
        assert_true(code == 1, "unreadable default adapter directory should fail")
        assert_true("[FAIL]" in output, "unreadable default adapter failure should be structured")
        assert_true("filesystem probe failed" in output, "unreadable default adapter failure should mention probe failure")

        explicit_home = root / "explicit-home"
        explicit_home.mkdir()
        unreadable_explicit = explicit_home / "blocked"
        unreadable_explicit.mkdir()
        os.chmod(unreadable_explicit, 0)
        try:
            code, output = run_args(
                [
                    "--agentos-home",
                    str(agentos),
                    "--adapter",
                    str((unreadable_explicit / "AGENTS.md").resolve()),
                ],
                explicit_home,
            )
        finally:
            os.chmod(unreadable_explicit, 0o700)
        assert_true(code == 1, "unreadable explicit adapter directory should fail")
        assert_true("[FAIL]" in output, "unreadable explicit adapter failure should be structured")
        assert_true("filesystem probe failed" in output, "unreadable explicit adapter failure should mention probe failure")

        for label, kwargs in (
            ("CODEX_HOME", {"codex_home": (root / "blocked-codex-parent" / "codex").resolve()}),
            (
                "CLAUDE_CONFIG_DIR",
                {"claude_config_dir": (root / "blocked-claude-parent" / "claude-config").resolve()},
            ),
            (
                "GEMINI_CLI_HOME",
                {"gemini_cli_home": (root / "blocked-gemini-parent" / "gemini").resolve()},
            ),
        ):
            blocked_parent = next(iter(kwargs.values())).parent
            blocked_parent.mkdir()
            os.chmod(blocked_parent, 0)
            try:
                code, output = run_args_with_adapter_homes(
                    ["--agentos-home", str(agentos)],
                    home,
                    **kwargs,
                )
            finally:
                os.chmod(blocked_parent, 0o700)
            assert_true(code == 1, f"unreadable {label} adapter home should fail")
            assert_true("[FAIL]" in output, f"unreadable {label} failure should be structured")
            assert_true("filesystem probe failed" in output, f"unreadable {label} failure should mention probe failure")


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


def test_preflight_prevents_partial_writes() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        (home / ".codex").mkdir()
        codex = home / ".codex" / "AGENTS.md"
        codex.write_text(
            adapter_block(global_instructions_path(home))
            + "\n"
            + adapter_block(global_instructions_path(home)),
            encoding="utf-8",
        )
        agentos = make_fake_agentos(root)
        code, output = run_args(["--agentos-home", str(agentos), "--no-dry-run"], home)
        assert_true(code == 1, "duplicate marker preflight should fail")
        assert_true("preflight failed; no files were modified" in output, "preflight failure message missing")
        assert_true(not global_instructions_path(home).exists(), "global file was created before later target failed")

        bad_home = root / "bad-home"
        bad_home.mkdir()
        (bad_home / ".codex").mkdir()
        bad_codex = bad_home / ".codex" / "AGENTS.md"
        bad_codex.write_bytes(b"\xff\xfe\x00")
        code, output = run_args(["--agentos-home", str(agentos), "--no-dry-run"], bad_home)
        assert_true(code == 1, "invalid UTF-8 preflight should fail")
        assert_true("UTF-8" in output, "invalid UTF-8 failure should be explicit")
        assert_true(not global_instructions_path(bad_home).exists(), "global file was created before invalid UTF-8 target failed")

        if os.name == "posix":
            write_fail_home = root / "write-fail-home"
            write_fail_home.mkdir()
            blocked_adapter_dir = write_fail_home / "blocked-adapter"
            blocked_adapter_dir.mkdir()
            os.chmod(blocked_adapter_dir, 0o500)
            try:
                code, output = run_args(
                    [
                        "--agentos-home",
                        str(agentos),
                        "--adapter",
                        str((blocked_adapter_dir / "AGENTS.md").resolve()),
                        "--no-dry-run",
                    ],
                    write_fail_home,
                )
            finally:
                os.chmod(blocked_adapter_dir, 0o700)
            assert_true(code == 1, "later write failure should fail")
            assert_true("rolled back" in output, "write failure should report rollback")
            assert_true(not global_instructions_path(write_fail_home).exists(), "global file remained after rollback")

            incomplete_home = root / "incomplete-rollback-home"
            incomplete_home.mkdir()
            (incomplete_home / ".codex").mkdir()
            incomplete_codex = (incomplete_home / ".codex" / "AGENTS.md").resolve()
            incomplete_original = b"Existing Codex guidance.\n"
            incomplete_codex.write_bytes(incomplete_original)
            blocked_incomplete_dir = incomplete_home / "blocked-adapter"
            blocked_incomplete_dir.mkdir()
            os.chmod(blocked_incomplete_dir, 0o500)
            original_write_bytes_atomic = globals()["write_bytes_atomic"]

            def fail_codex_restore(path: Path, data: bytes, mode: int | None = None) -> None:
                if path == incomplete_codex and data == incomplete_original:
                    raise OSError("restore blocked")
                original_write_bytes_atomic(path, data, mode=mode)

            globals()["write_bytes_atomic"] = fail_codex_restore
            try:
                code, output = run_args(
                    [
                        "--agentos-home",
                        str(agentos),
                        "--adapter",
                        str((blocked_incomplete_dir / "AGENTS.md").resolve()),
                        "--no-dry-run",
                    ],
                    incomplete_home,
                )
            finally:
                globals()["write_bytes_atomic"] = original_write_bytes_atomic
                os.chmod(blocked_incomplete_dir, 0o700)
            assert_true(code == 1, "incomplete rollback should fail")
            assert_true("rollback-error" in output, "incomplete rollback should report rollback-error entries")
            assert_true("did not complete" in output, "incomplete rollback summary should not claim success")
            backups = list((incomplete_home / ".codex").glob("AGENTS.md.agentos-backup-*"))
            assert_true(backups, "failed rollback should preserve backup artifact")


def test_symlink_targets_fail_closed_and_modes_are_preserved() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        (home / ".codex").mkdir()
        codex = home / ".codex" / "AGENTS.md"
        codex.write_text("Existing Codex guidance.\n", encoding="utf-8")
        os.chmod(codex, 0o644)
        agentos = make_fake_agentos(root)
        code, output = run_args(["--agentos-home", str(agentos), "--no-dry-run"], home)
        assert_true(code == 0, output)
        mode = codex.stat().st_mode & 0o777
        if os.name == "posix":
            assert_true(mode == 0o644, f"existing file mode changed to {oct(mode)}")

        link_home = root / "link-home"
        link_home.mkdir()
        (link_home / ".codex").mkdir()
        real_target = root / "real-AGENTS.md"
        real_target.write_text("Real target.\n", encoding="utf-8")
        symlink = link_home / ".codex" / "AGENTS.md"
        try:
            symlink.symlink_to(real_target)
        except OSError:
            return
        code, output = run_args(["--agentos-home", str(agentos), "--no-dry-run"], link_home)
        assert_true(code == 1, "symlink target should fail closed")
        assert_true("symlink" in output, "symlink failure should be explicit")
        assert_true(not global_instructions_path(link_home).exists(), "preflight failure should not create global file")
        assert_true(symlink.is_symlink(), "symlink was replaced")
        assert_true(read_text_preserve_newlines(real_target) == "Real target.\n", "symlink target was modified")

        nested_home = root / "nested-home"
        nested_home.mkdir()
        outside = root / "outside"
        outside.mkdir()
        (nested_home / "linked-adapters").symlink_to(outside, target_is_directory=True)
        nested_adapter = "<home>/linked-adapters/nested/AGENTS.md"
        code, output = run_args(
            ["--agentos-home", str(agentos), "--adapter", nested_adapter, "--no-dry-run"],
            nested_home,
        )
        assert_true(code == 1, "symlink ancestor should fail closed")
        assert_true("symlink" in output, "symlink ancestor failure should be explicit")
        assert_true(not (outside / "nested").exists(), "nested directory was created through a symlink ancestor")

        raw_home = root / "raw-home"
        raw_home.mkdir()
        raw_outside = root / "raw-outside"
        raw_outside.mkdir()
        (raw_home / "adapter-link").symlink_to(raw_outside, target_is_directory=True)

        raw_absolute_adapter = str(raw_home / "adapter-link" / "nested-absolute" / "AGENTS.md")
        code, output = run_args(
            ["--agentos-home", str(agentos), "--adapter", raw_absolute_adapter, "--no-dry-run"],
            raw_home,
        )
        assert_true(code == 1, "raw absolute symlink ancestor should fail closed")
        assert_true("symlink" in output, "raw absolute symlink ancestor failure should be explicit")
        assert_true(not (raw_outside / "nested-absolute").exists(), "raw absolute adapter wrote through a symlink ancestor")

        previous_cwd = Path.cwd()
        try:
            os.chdir(raw_home)
            code, output = run_args(
                [
                    "--agentos-home",
                    str(agentos),
                    "--adapter",
                    "adapter-link/nested-relative/AGENTS.md",
                    "--no-dry-run",
                ],
                raw_home,
            )
        finally:
            os.chdir(previous_cwd)
        assert_true(code == 1, "raw relative symlink ancestor should fail closed")
        assert_true("symlink" in output, "raw relative symlink ancestor failure should be explicit")
        assert_true(not (raw_outside / "nested-relative").exists(), "raw relative adapter wrote through a symlink ancestor")

        backup_home = root / "backup-home"
        backup_home.mkdir()
        (backup_home / ".codex").mkdir()
        resolved_backup_home = backup_home.resolve()
        backup_codex = resolved_backup_home / ".codex" / "AGENTS.md"
        backup_codex.write_text("Existing backup source.\n", encoding="utf-8")
        timestamp = "20990101T000000Z"
        backup_symlink = backup_codex.with_name(f"{backup_codex.name}.agentos-backup-{timestamp}")
        outside_backup = root / "outside-backup-target"
        backup_symlink.symlink_to(outside_backup)
        try:
            install_target(
                Target("codex", backup_codex, "adapter"),
                resolved_backup_home,
                agentos.resolve(),
                dry_run=False,
                timestamp=timestamp,
            )
        except ManagedBlockError as exc:
            assert_true("unsafe backup path" in str(exc), "backup symlink failure should be explicit")
        else:
            raise AssertionError("backup symlink should fail closed")
        assert_true(not outside_backup.exists(), "backup was written through a symlink")
        assert_true(read_text_preserve_newlines(backup_codex) == "Existing backup source.\n", "source changed after backup failure")


def test_remediation_command_shell_quotes_dynamic_args() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-global-installer-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        agentos = make_fake_agentos(root, "AgentOS;dollar$paren()")
        adapter = "<home>/.openclaw/AGENTS.md"
        code, output = run_args(["--agentos-home", str(agentos), "--check", "--adapter", adapter], home)
        assert_true(code == 1, "check should report missing managed files")
        command_line = output.strip().splitlines()[-1]
        parsed = shlex.split(command_line)
        assert_true(str(agentos.resolve()) in parsed, "quoted AgentOS path did not round-trip")
        assert_true(adapter in parsed, "quoted adapter path did not round-trip")


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

        code, output = run_args(
            [
                "--agentos-home",
                str(agentos),
                "--adapter",
                "<home>/.agents/agents.md",
            ],
            home,
        )
        assert_true(code == 1, "case-only adapter conflict with global target should fail")
        assert_true("conflicts" in output, "case-only conflict failure should be explicit")

        code, output = run_args(
            [
                "--agentos-home",
                str(agentos),
                "--adapter",
                "<home>/.Agents/AGENTS.md",
            ],
            home,
        )
        assert_true(code == 1, "case-only adapter parent conflict with global target should fail")
        assert_true("conflicts" in output, "case-only parent conflict failure should be explicit")

        code, output = run_args(
            [
                "--agentos-home",
                str(agentos),
                "--all-default-adapters",
                "--adapter",
                "<home>/.codex/agents.md",
            ],
            home,
        )
        assert_true(code == 1, "case-only adapter conflict with default Codex target should fail")
        assert_true("conflicts" in output, "default adapter case conflict failure should be explicit")

        code, output = run_args(
            [
                "--agentos-home",
                str(agentos),
                "--all-default-adapters",
                "--adapter",
                "<home>/.Codex/AGENTS.md",
            ],
            home,
        )
        assert_true(code == 1, "case-only adapter parent conflict with default Codex target should fail")
        assert_true("conflicts" in output, "default adapter parent case conflict failure should be explicit")

        if hasattr(os, "link"):
            hardlink_home = root / "hardlink-home"
            hardlink_home.mkdir()
            hardlink_global = global_instructions_path(hardlink_home)
            hardlink_global.parent.mkdir()
            hardlink_global.write_text("Existing global guidance.\n", encoding="utf-8")
            hardlink_adapter = hardlink_home / ".hardlink" / "AGENTS.md"
            hardlink_adapter.parent.mkdir()
            try:
                os.link(hardlink_global, hardlink_adapter)
            except OSError:
                pass
            else:
                code, output = run_args(
                    [
                        "--agentos-home",
                        str(agentos),
                        "--adapter",
                        str(hardlink_adapter),
                    ],
                    hardlink_home,
                )
                assert_true(code == 1, "hardlinked adapter conflict with global target should fail")
                assert_true("conflicts" in output, "hardlink conflict failure should be explicit")


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

        cwd = root / "cwd"
        cwd.mkdir()
        original_cwd = Path.cwd()
        try:
            os.chdir(cwd)
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
            assert_true(str(cwd / "relative-adapter" / "AGENTS.md") in output, "relative adapter was not resolved")
            assert_true(not (cwd / "relative-adapter").exists(), "relative dry-run created a directory")
        finally:
            os.chdir(original_cwd)


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
