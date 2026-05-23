#!/usr/bin/env python3
"""Thin, read-only AgentOS setup fact collector."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping


REQUIRED_AGENTOS_FILES = (
    "AGENTS.md",
    "os/INDEX.md",
    "os/playbook/PERSONAL_OVERLAY.md",
)
STARTER_HEADING_RE = re.compile(r"^## Starter Files\s*$", re.MULTILINE)
NEXT_HEADING_RE = re.compile(r"^##\s+", re.MULTILINE)
PERSONAL_PATH_RE = re.compile(r"`(personal/os/[^`]+)`")
DEFAULT_TIMEOUT_SECONDS = 30
OUTPUT_LINE_LIMIT = 20
VERBOSE_OUTPUT_LINE_LIMIT = 80
OUTPUT_LINE_CHAR_LIMIT = 240
VERBOSE_OUTPUT_LINE_CHAR_LIMIT = 1000
PRIVATE_CONTENT_SENTINEL = "DO_NOT_LEAK_AGENTOS_DOCTOR_SELF_TEST"
MIRROR_REQUIRED_FIELDS = {
    "name",
    "source_kind",
    "status",
    "canonical_source",
    "mirror_path",
    "missing_files",
    "changed_files",
    "extra_files",
    "notes",
}
MIRROR_LIST_FIELDS = {"missing_files", "changed_files", "extra_files", "notes"}
MIRROR_ALLOWED_STATUSES = {
    "in-sync",
    "missing",
    "stale",
    "extra-files",
    "source-missing",
    "source-unreadable",
    "mirror-unreadable",
}
MIRROR_ALLOWED_SOURCE_KINDS = {"core", "personal-overlay"}
IGNORED_COUNT_FILE_NAMES = {".DS_Store", ".gitkeep"}
IGNORED_COUNT_DIR_NAMES = {"__pycache__"}


@dataclass
class CheckResult:
    name: str
    status: str
    summary: str
    details: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class DoctorReport:
    agentos_home: Path
    primary_agentos_home: Path
    mirror_root: Path
    results: list[CheckResult]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agentos-home",
        type=Path,
        default=None,
        help="AgentOS checkout path. Defaults to discovery from the current directory.",
    )
    parser.add_argument(
        "--primary-agentos-home",
        type=Path,
        default=None,
        help="Primary AgentOS checkout that owns the canonical Personal Overlay. Defaults to --agentos-home.",
    )
    parser.add_argument(
        "--mirror-root",
        type=Path,
        default=Path.home() / ".agents" / "skills",
        help="Current-machine skill mirror root to audit. Default: the user's .agents/skills directory.",
    )
    parser.add_argument(
        "--all-default-adapters",
        action="store_true",
        help="Pass through to the adapter drift check.",
    )
    parser.add_argument(
        "--adapter",
        action="append",
        default=[],
        metavar="PATH",
        help="Extra harness adapter file to include in the adapter drift check. May be repeated.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print more helper output and path diagnostics. Never prints file contents.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero for WARN results as well as FAIL results.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run temporary-directory self-tests and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.self_test:
        if (
            args.agentos_home is not None
            or args.primary_agentos_home is not None
            or args.mirror_root != Path.home() / ".agents" / "skills"
            or args.all_default_adapters
            or args.adapter
            or args.verbose
            or args.strict
        ):
            print("error: --self-test cannot be combined with other options", file=sys.stderr)
            return 2
        return run_self_tests()

    cwd = Path.cwd()
    report = run_doctor(
        requested_agentos_home=args.agentos_home,
        requested_primary_agentos_home=args.primary_agentos_home,
        mirror_root=args.mirror_root,
        cwd=cwd,
        process_home=Path.home(),
        env=os.environ,
        adapter_args=adapter_args(args, cwd),
        verbose=args.verbose,
    )
    print_report(report, verbose=args.verbose)
    return exit_code_for(report.results, strict=args.strict)


def adapter_args(args: argparse.Namespace, cwd: Path) -> list[str]:
    passthrough: list[str] = []
    if args.all_default_adapters:
        passthrough.append("--all-default-adapters")
    for adapter in args.adapter:
        passthrough.extend(["--adapter", normalize_adapter_arg(adapter, cwd)])
    return passthrough


def normalize_adapter_arg(adapter: str, cwd: Path) -> str:
    if adapter == "<home>" or adapter.startswith("<home>/") or adapter.startswith("<home>\\"):
        return adapter
    expanded = os.path.expanduser(adapter)
    if not os.path.isabs(expanded):
        expanded = os.path.join(os.fspath(cwd), expanded)
    return os.path.abspath(expanded)


def run_doctor(
    requested_agentos_home: Path | None,
    requested_primary_agentos_home: Path | None,
    mirror_root: Path,
    cwd: Path,
    process_home: Path,
    env: Mapping[str, str],
    adapter_args: list[str],
    verbose: bool,
) -> DoctorReport:
    agentos_home, discovery = resolve_agentos_home(requested_agentos_home, cwd)
    primary_agentos_home = absolute_path(requested_primary_agentos_home, cwd) if requested_primary_agentos_home else agentos_home
    mirror_root = absolute_path(mirror_root, cwd)

    results = [
        discovery,
        check_required_core_files(agentos_home),
        check_adapters(agentos_home, env, adapter_args, verbose),
        check_skill_mirrors(agentos_home, mirror_root, env, verbose),
        check_personal_overlay_starters(agentos_home, primary_agentos_home),
        check_automation_locations(primary_agentos_home, process_home, env),
    ]
    return DoctorReport(
        agentos_home=agentos_home,
        primary_agentos_home=primary_agentos_home,
        mirror_root=mirror_root,
        results=results,
    )


def resolve_agentos_home(requested: Path | None, cwd: Path) -> tuple[Path, CheckResult]:
    if requested is not None:
        home = absolute_path(requested, cwd)
        return home, CheckResult(
            "home discovery",
            "PASS",
            "Using --agentos-home.",
            details=[f"AgentOS home: {home}"],
        )

    current = absolute_path(cwd, cwd)
    for candidate in (current, *current.parents):
        if looks_like_agentos(candidate):
            return candidate, CheckResult(
                "home discovery",
                "PASS",
                "Discovered AgentOS home from the current directory.",
                details=[f"AgentOS home: {candidate}"],
            )

    return current, CheckResult(
        "home discovery",
        "FAIL",
        "Could not discover an AgentOS checkout from the current directory.",
        details=[f"Starting directory: {current}"],
        recommendations=[
            "Run: python3 scripts/agentos_doctor.py --agentos-home <path-to-AgentOS>"
        ],
    )


def check_required_core_files(agentos_home: Path) -> CheckResult:
    present: list[str] = []
    missing: list[str] = []
    unreadable: list[str] = []
    symlinks: list[str] = []
    for rel in REQUIRED_AGENTOS_FILES:
        path = agentos_home / rel
        try:
            if path.is_symlink():
                symlinks.append(rel)
            if path.is_file():
                present.append(rel)
            else:
                missing.append(rel)
        except OSError as exc:
            unreadable.append(f"{rel} ({exc.__class__.__name__})")

    details = [
        "Required files present: " + str(len(present)) + "/" + str(len(REQUIRED_AGENTOS_FILES)),
    ]
    if missing:
        details.append("Missing required files: " + ", ".join(missing))
    if unreadable:
        details.append("Unreadable required files: " + ", ".join(unreadable))
    if symlinks:
        details.append("Symlinked required files: " + ", ".join(symlinks))

    if missing or unreadable:
        return CheckResult(
            "home structure",
            "FAIL",
            "Required AgentOS Core entry files are missing or unreadable.",
            details=details,
        )
    if symlinks:
        return CheckResult(
            "home structure",
            "WARN",
            "Required AgentOS Core entry files exist, but some are symlinks.",
            details=details,
            recommendations=[
                "Ask an agent or human to inspect symlinked Core files before trusting this checkout."
            ],
        )
    return CheckResult(
        "home structure",
        "PASS",
        "Required AgentOS Core entry files are present.",
        details=details,
    )


def check_adapters(
    setup_agentos_home: Path,
    env: Mapping[str, str],
    extra_args: list[str],
    verbose: bool,
) -> CheckResult:
    script = setup_agentos_home / "scripts" / "install_global_agent_instructions.py"
    if not script.is_file():
        return CheckResult(
            "adapter drift",
            "FAIL",
            "Adapter check helper is missing.",
            details=[f"Expected helper: {script}"],
            recommendations=[
                "Inspect the AgentOS checkout path or run the installer helper manually from the intended checkout."
            ],
        )

    command = [
        sys.executable,
        str(script),
        "--agentos-home",
        str(setup_agentos_home),
        "--check",
        *extra_args,
    ]
    completed = run_subprocess(command, cwd=setup_agentos_home, env=env)
    details = subprocess_details(command, completed, verbose)
    remediation = [
        sys.executable,
        str(script),
        "--agentos-home",
        str(setup_agentos_home),
        *extra_args,
        "--no-dry-run",
    ]
    if completed.returncode in {124, 127}:
        return CheckResult(
            "adapter drift",
            "FAIL",
            "Adapter check helper could not run.",
            details=details,
        )
    if completed.returncode == 0 and not completed.stderr.strip():
        return CheckResult(
            "adapter drift",
            "PASS",
            "Adapter check helper exited successfully.",
            details=details,
        )
    return CheckResult(
        "adapter drift",
        "WARN",
        "Adapter check helper reported output that needs review.",
        details=details,
        recommendations=[
            "Review the adapter check command and bounded output above.",
            "After approval only, consider: " + shell_command(remediation),
        ],
    )


def check_skill_mirrors(
    agentos_home: Path,
    mirror_root: Path,
    env: Mapping[str, str],
    verbose: bool,
) -> CheckResult:
    script = agentos_home / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py"
    if not script.is_file():
        return CheckResult(
            "skill mirrors",
            "FAIL",
            "Mirror-skills audit helper is missing.",
            details=[f"Expected helper: {script}"],
        )

    command = [
        sys.executable,
        str(script),
        "--agentos-root",
        str(agentos_home),
        "--mirror-root",
        str(mirror_root),
        "--json",
    ]
    completed = run_subprocess(command, cwd=agentos_home, env=env)
    details = mirror_subprocess_details(command, completed)
    parsed, schema_errors = parse_mirror_results(completed.stdout)
    mirror_needs_review = False
    if schema_errors:
        details.extend("Mirror audit JSON: " + error for error in schema_errors)
    else:
        statuses = Counter(str(item.get("status", "<missing>")) for item in parsed if isinstance(item, dict))
        source_kinds = Counter(str(item.get("source_kind", "<missing>")) for item in parsed if isinstance(item, dict))
        mirror_needs_review = any(status != "in-sync" for status in statuses)
        details.append(f"Mirror results: {len(parsed)}")
        if statuses:
            details.append("Mirror statuses: " + format_counts(statuses))
        if source_kinds:
            details.append("Mirror source kinds: " + format_counts(source_kinds))

    if completed.returncode in {124, 127}:
        return CheckResult(
            "skill mirrors",
            "FAIL",
            "Mirror-skills audit helper could not run.",
            details=details,
        )
    if completed.returncode == 0 and parsed is not None and not schema_errors and not mirror_needs_review and not completed.stderr.strip():
        return CheckResult(
            "skill mirrors",
            "PASS",
            "Mirror-skills audit helper exited successfully.",
            details=details,
        )
    return CheckResult(
        "skill mirrors",
        "WARN",
        "Mirror-skills audit output needs review.",
        details=details,
        recommendations=[
            "Review or rerun the audit command above; raw JSON is not printed by Doctor.",
            "After approval only, consider: " + shell_command([*command, "--sync"]),
        ],
    )


def check_personal_overlay_starters(agentos_home: Path, primary_agentos_home: Path) -> CheckResult:
    source = agentos_home / "os" / "playbook" / "GETTING_STARTED.md"
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        return CheckResult(
            "Personal Overlay starters",
            "WARN",
            "Could not read the documented starter path list.",
            details=[f"Starter source: {source} ({exc.__class__.__name__})"],
        )
    except UnicodeDecodeError:
        return CheckResult(
            "Personal Overlay starters",
            "WARN",
            "Could not decode the documented starter path list.",
            details=[f"Starter source: {source}"],
        )

    starter_paths = extract_starter_paths(text)
    if not starter_paths:
        return CheckResult(
            "Personal Overlay starters",
            "WARN",
            "No documented Personal Overlay starter paths were found.",
            details=[f"Starter source: {source}"],
        )

    present: list[str] = []
    missing: list[str] = []
    unreadable: list[str] = []
    for rel in starter_paths:
        path = primary_agentos_home / rel
        try:
            if path.exists():
                present.append(rel)
            else:
                missing.append(rel)
        except OSError as exc:
            unreadable.append(f"{rel} ({exc.__class__.__name__})")

    details = [
        f"Starter source: {source}",
        f"Primary Personal Overlay root: {primary_agentos_home / 'personal' / 'os'}",
        f"Starter paths present: {len(present)}/{len(starter_paths)}",
    ]
    if present:
        details.append("Present starter paths: " + ", ".join(present))
    if missing:
        details.append("Missing starter paths: " + ", ".join(missing))
    if unreadable:
        details.append("Unreadable starter paths: " + ", ".join(unreadable))

    if unreadable:
        return CheckResult(
            "Personal Overlay starters",
            "WARN",
            "Some documented starter paths could not be inspected.",
            details=details,
        )
    if missing:
        return CheckResult(
            "Personal Overlay starters",
            "WARN",
            "Some documented starter Personal Overlay paths are absent.",
            details=details,
            recommendations=[
                "Review documented starter paths: os/playbook/GETTING_STARTED.md"
            ],
        )
    return CheckResult(
        "Personal Overlay starters",
        "PASS",
        "Documented starter Personal Overlay paths exist.",
        details=details,
    )


def check_automation_locations(
    primary_agentos_home: Path,
    process_home: Path,
    env: Mapping[str, str],
) -> CheckResult:
    core_registry = primary_agentos_home / "os" / "automations" / "AUTOMATIONS.md"
    personal_root = primary_agentos_home / "personal" / "os" / "automations"
    personal_registry = personal_root / "AUTOMATIONS.md"
    codex_home = absolute_path(Path(env.get("CODEX_HOME", process_home / ".codex")), process_home)
    codex_automation_root = codex_home / "automations"

    personal_count, personal_error = count_files(personal_root)
    codex_count, codex_error = count_files(codex_automation_root)
    codex_toml_count, codex_toml_error = count_files(codex_automation_root, suffix=".toml")

    details = [
        f"Core automation registry: {path_state(core_registry)} ({core_registry})",
        f"Personal automation registry: {path_state(personal_registry)} ({personal_registry})",
        f"Personal automation directory: {path_state(personal_root)} ({personal_root})",
        f"Personal automation files: {count_or_unknown(personal_count, personal_error)}",
        f"Codex automation directory: {path_state(codex_automation_root)} ({codex_automation_root})",
        f"Codex automation files: {count_or_unknown(codex_count, codex_error)}",
        f"Codex automation TOML files: {count_or_unknown(codex_toml_count, codex_toml_error)}",
    ]
    if personal_error:
        details.append(f"Personal automation count error: {personal_error}")
    if codex_error:
        details.append(f"Codex automation count error: {codex_error}")
    if codex_toml_error and codex_toml_error != codex_error:
        details.append(f"Codex automation TOML count error: {codex_toml_error}")

    found_locations = any(
        [
            core_registry.exists(),
            personal_registry.exists(),
            bool(personal_count),
            bool(codex_count),
            bool(codex_toml_count),
        ]
    )
    if personal_error or codex_error or codex_toml_error:
        status = "WARN"
        summary = "Some automation locations could not be inspected."
    elif found_locations:
        status = "WARN"
        summary = "Automation locations found; active/disabled/draft state requires skill interpretation."
    else:
        status = "WARN"
        summary = "No automation registry or local automation files were found."

    return CheckResult(
        "automation locations",
        status,
        summary,
        details=details,
        recommendations=[
            "Review the automation locations listed above with the Run AgentOS Doctor skill.",
            "The helper did not read automation file contents or classify lifecycle state.",
        ],
    )


def looks_like_agentos(path: Path) -> bool:
    return all((path / rel).is_file() for rel in REQUIRED_AGENTOS_FILES)


def absolute_path(path: Path, cwd: Path) -> Path:
    raw = os.path.expanduser(os.fspath(path))
    if not os.path.isabs(raw):
        raw = os.path.join(os.fspath(cwd), raw)
    return Path(os.path.abspath(raw))


def extract_starter_paths(text: str) -> list[str]:
    match = STARTER_HEADING_RE.search(text)
    section = text
    if match:
        start = match.end()
        next_heading = NEXT_HEADING_RE.search(text, start)
        section = text[start : next_heading.start() if next_heading else len(text)]
    paths = []
    for path in PERSONAL_PATH_RE.findall(section):
        clean = path.rstrip(".,)")
        if clean not in paths:
            paths.append(clean)
    return paths


def parse_mirror_results(stdout: str) -> tuple[list[dict[str, object]] | None, list[str]]:
    if not stdout.strip():
        return None, ["missing."]
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return None, ["malformed."]
    if not isinstance(parsed, list):
        return None, ["expected a JSON list."]
    if not parsed:
        return None, ["JSON list was empty."]

    errors: list[str] = []
    results: list[dict[str, object]] = []
    for index, item in enumerate(parsed):
        if not isinstance(item, dict):
            errors.append(f"item {index} was not an object.")
            continue
        missing = sorted(MIRROR_REQUIRED_FIELDS - set(item))
        if missing:
            errors.append(f"item {index} missing fields: {', '.join(missing)}.")
        for field in MIRROR_REQUIRED_FIELDS - MIRROR_LIST_FIELDS:
            if field in item and not isinstance(item[field], str):
                errors.append(f"item {index} field {field} was not a string.")
        for field in MIRROR_LIST_FIELDS:
            if field in item and not isinstance(item[field], list):
                errors.append(f"item {index} field {field} was not a list.")
        status = item.get("status")
        if isinstance(status, str) and status not in MIRROR_ALLOWED_STATUSES:
            errors.append(f"item {index} status was not recognized.")
        source_kind = item.get("source_kind")
        if isinstance(source_kind, str) and source_kind not in MIRROR_ALLOWED_SOURCE_KINDS:
            errors.append(f"item {index} source_kind was not recognized.")
        results.append(item)
    return (results if results else None), errors


def count_files(root: Path, suffix: str | None = None) -> tuple[int | None, str | None]:
    try:
        if root.is_symlink():
            return None, "root is symlink"
        if not root.is_dir():
            return 0, None
        errors: list[str] = []

        def collect_error(error: OSError) -> None:
            errors.append(error.__class__.__name__)

        count = 0
        for current_root, dirs, files in os.walk(root, followlinks=False, onerror=collect_error):
            dirs[:] = [
                name
                for name in dirs
                if name not in IGNORED_COUNT_DIR_NAMES and not (Path(current_root) / name).is_symlink()
            ]
            for name in files:
                if should_count_file(name, suffix):
                    count += 1
        if errors:
            return None, "walk error: " + ", ".join(sorted(set(errors)))
        return count, None
    except OSError as exc:
        return None, exc.__class__.__name__


def should_count_file(name: str, suffix: str | None) -> bool:
    if name in IGNORED_COUNT_FILE_NAMES or name.endswith(".pyc"):
        return False
    return suffix is None or name.endswith(suffix)


def count_or_unknown(count: int | None, error: str | None) -> str:
    if error:
        return "unknown"
    return str(count or 0)


def path_state(path: Path) -> str:
    try:
        if path.exists():
            if path.is_symlink():
                return "present symlink"
            if path.is_dir():
                return "present directory"
            if path.is_file():
                return "present file"
            return "present other"
        return "absent"
    except OSError:
        return "unreadable"


def run_subprocess(
    command: list[str],
    cwd: Path,
    env: Mapping[str, str],
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            env=dict(env),
            text=True,
            errors="replace",
            capture_output=True,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = output_to_text(exc.stdout)
        stderr = output_to_text(exc.stderr)
        return subprocess.CompletedProcess(
            command,
            124,
            stdout=stdout,
            stderr=stderr + f"\nTimed out after {DEFAULT_TIMEOUT_SECONDS} seconds.",
        )
    except OSError as exc:
        return subprocess.CompletedProcess(command, 127, stdout="", stderr=str(exc))


def subprocess_details(
    command: list[str],
    completed: subprocess.CompletedProcess[str],
    verbose: bool,
) -> list[str]:
    line_limit = VERBOSE_OUTPUT_LINE_LIMIT if verbose else OUTPUT_LINE_LIMIT
    line_char_limit = VERBOSE_OUTPUT_LINE_CHAR_LIMIT if verbose else OUTPUT_LINE_CHAR_LIMIT
    details = [
        "Command: " + shell_command(command),
        f"Exit code: {completed.returncode}",
    ]
    details.extend(format_output("stdout", completed.stdout, line_limit, line_char_limit))
    details.extend(format_output("stderr", completed.stderr, line_limit, line_char_limit))
    return details


def mirror_subprocess_details(command: list[str], completed: subprocess.CompletedProcess[str]) -> list[str]:
    details = [
        "Command: " + shell_command(command),
        f"Exit code: {completed.returncode}",
        output_summary("stdout", completed.stdout, "not printed; parsed as mirror audit JSON"),
        output_summary("stderr", completed.stderr, "not printed to avoid leaking mirror metadata"),
    ]
    return details


def output_summary(label: str, text: str, note: str) -> str:
    if not text:
        return f"{label}: <empty>"
    return f"{label}: <{len(text.splitlines())} line(s), {len(text)} char(s); {note}>"


def format_output(label: str, text: str, line_limit: int, line_char_limit: int) -> list[str]:
    lines = text.splitlines()
    if not lines:
        return [f"{label}: <empty>"]
    shown = lines[:line_limit]
    result = [f"{label}: {truncate_line(line, line_char_limit)}" for line in shown]
    if len(lines) > line_limit:
        result.append(f"{label}: <{len(lines) - line_limit} additional line(s) omitted; rerun with --verbose>")
    return result


def truncate_line(line: str, limit: int) -> str:
    if len(line) <= limit:
        return line
    omitted = len(line) - limit
    return line[:limit] + f"... <{omitted} char(s) omitted>"


def shell_command(command: list[str]) -> str:
    rendered = []
    for part in command:
        if part == sys.executable:
            rendered.append("python3")
            continue
        rendered.append(sh_quote(part))
    return " ".join(rendered)


def sh_quote(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:=@+-]+", value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def format_counts(counts: Counter[str]) -> str:
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


def output_to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def print_report(report: DoctorReport, verbose: bool) -> None:
    print("AgentOS doctor (read-only facts)")
    print(f"AgentOS home: {report.agentos_home}")
    print(f"Primary AgentOS home: {report.primary_agentos_home}")
    print(f"Skill mirror root: {report.mirror_root}")
    print("No files were modified.")
    print()
    for result in report.results:
        print(f"[{result.status}] {result.name}: {result.summary}")
        for detail in result.details:
            print(f"  - {detail}")
        for recommendation in result.recommendations:
            print(f"  Next: {recommendation}")
        print()
    if not verbose:
        print("Tip: pass --verbose to show more helper output. File contents are never printed.")


def render_report_for_test(report: DoctorReport, verbose: bool = False) -> str:
    lines = [
        "AgentOS doctor (read-only facts)",
        f"AgentOS home: {report.agentos_home}",
        f"Primary AgentOS home: {report.primary_agentos_home}",
        f"Skill mirror root: {report.mirror_root}",
        "No files were modified.",
        "",
    ]
    for result in report.results:
        lines.append(f"[{result.status}] {result.name}: {result.summary}")
        lines.extend(f"  - {detail}" for detail in result.details)
        lines.extend(f"  Next: {recommendation}" for recommendation in result.recommendations)
        lines.append("")
    if not verbose:
        lines.append("Tip: pass --verbose to show more helper output. File contents are never printed.")
    return "\n".join(lines)


def exit_code_for(results: Iterable[CheckResult], strict: bool) -> int:
    statuses = [result.status for result in results]
    if "FAIL" in statuses:
        return 1
    if strict and "WARN" in statuses:
        return 1
    return 0


def run_self_tests() -> int:
    tests = [
        test_invalid_home_is_graceful,
        test_required_core_files_pass,
        test_personal_overlay_does_not_print_private_contents,
        test_adapter_check_is_read_only_check_only,
        test_adapter_check_uses_audit_root_when_primary_differs,
        test_adapter_helper_failure_warns,
        test_mirror_audit_never_syncs,
        test_mirror_malformed_json_warns,
        test_mirror_valid_json_schema_errors_warn,
        test_mirror_unknown_source_kind_warns_without_echo,
        test_mirror_output_does_not_print_private_metadata,
        test_helper_output_is_bounded,
        test_count_files_ignores_placeholder_noise,
        test_count_files_warns_on_walk_errors,
        test_count_files_warns_on_symlink_root,
        test_automation_locations_report_counts_not_contents,
        test_strict_warn_exit_code,
        test_adapter_home_notation_is_preserved,
    ]
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
            return 1
    print(f"PASS agentos_doctor self-tests ({len(tests)} tests)")
    return 0


def test_invalid_home_is_graceful() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "not-agentos"
        root.mkdir()
        report = run_doctor(
            requested_agentos_home=root,
            requested_primary_agentos_home=None,
            mirror_root=Path(tmp) / "mirrors",
            cwd=root,
            process_home=Path(tmp) / "home",
            env=minimal_env(Path(tmp) / "home"),
            adapter_args=[],
            verbose=False,
        )
        assert_true(result_named(report, "home structure").status == "FAIL", "invalid home should fail home structure")


def test_required_core_files_pass() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        result = check_required_core_files(root)
        assert_true(result.status == "PASS", "fake AgentOS should have required files")


def test_personal_overlay_does_not_print_private_contents() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        secret = root / "personal" / "os" / "identity" / "USER.md"
        secret.parent.mkdir(parents=True, exist_ok=True)
        secret.write_text(PRIVATE_CONTENT_SENTINEL, encoding="utf-8")
        report = run_doctor(
            requested_agentos_home=root,
            requested_primary_agentos_home=root,
            mirror_root=Path(tmp) / "mirrors",
            cwd=root,
            process_home=Path(tmp) / "home",
            env=minimal_env(Path(tmp) / "home"),
            adapter_args=[],
            verbose=True,
        )
        rendered = render_report_for_test(report, verbose=True)
        assert_true(PRIVATE_CONTENT_SENTINEL not in rendered, "private file contents leaked")
        assert_true("personal/os/identity/USER.md" in rendered, "private path presence should be reported")


def test_adapter_check_is_read_only_check_only() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        result = check_adapters(root, minimal_env(Path(tmp) / "home"), [], verbose=True)
        joined = "\n".join(result.details + result.recommendations)
        assert_true(result.status == "PASS", "default fake adapter check should pass")
        assert_true("--check" in joined, "adapter command must use --check")
        assert_true("--no-dry-run" not in joined, "doctor must not request adapter writes")


def test_adapter_check_uses_audit_root_when_primary_differs() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        audit_root = Path(tmp) / "audit-AgentOS"
        primary_root = Path(tmp) / "primary-AgentOS"
        make_fake_agentos(audit_root)
        make_fake_agentos(primary_root)
        (audit_root / "scripts" / "install_global_agent_instructions.py").write_text(
            "print('AUDIT_HELPER')\n",
            encoding="utf-8",
        )
        (primary_root / "scripts" / "install_global_agent_instructions.py").write_text(
            "print('PRIMARY_HELPER')\n",
            encoding="utf-8",
        )
        report = run_doctor(
            requested_agentos_home=audit_root,
            requested_primary_agentos_home=primary_root,
            mirror_root=Path(tmp) / "mirrors",
            cwd=audit_root,
            process_home=Path(tmp) / "home",
            env=minimal_env(Path(tmp) / "home"),
            adapter_args=[],
            verbose=True,
        )
        rendered = render_report_for_test(report, verbose=True)
        assert_true("AUDIT_HELPER" in rendered, "adapter check should use the audited AgentOS root")
        assert_true("PRIMARY_HELPER" not in rendered, "adapter check should not use the primary overlay root")


def test_adapter_helper_failure_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        installer = root / "scripts" / "install_global_agent_instructions.py"
        installer.write_text(
            "import sys\nprint('adapter drift or helper warning', file=sys.stderr)\nsys.exit(1)\n",
            encoding="utf-8",
        )
        result = check_adapters(root, minimal_env(Path(tmp) / "home"), [], verbose=False)
        joined = "\n".join(result.details + result.recommendations)
        assert_true(result.status == "WARN", "helper nonzero output should warn for interpretation")
        assert_true("adapter drift or helper warning" in joined, "stderr should be reported")


def test_mirror_audit_never_syncs() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        result = check_skill_mirrors(root, Path(tmp) / "mirrors", minimal_env(Path(tmp) / "home"), verbose=True)
        joined = "\n".join(result.details + result.recommendations)
        assert_true(result.status == "PASS", "default fake mirror audit should pass")
        assert_true("--json" in joined, "mirror audit should request JSON")
        assert_true("--sync" not in joined, "doctor must not sync mirrors")


def test_mirror_malformed_json_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        mirror = root / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py"
        mirror.write_text("print('not json')\n", encoding="utf-8")
        result = check_skill_mirrors(root, Path(tmp) / "mirrors", minimal_env(Path(tmp) / "home"), verbose=False)
        assert_true(result.status == "WARN", "malformed mirror JSON should warn")
        assert_true(any("malformed" in detail for detail in result.details), "malformed JSON should be reported")


def test_mirror_valid_json_schema_errors_warn() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        mirror = root / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py"
        mirror.write_text("import json\nprint(json.dumps([{'name': 'partial'}]))\n", encoding="utf-8")
        result = check_skill_mirrors(root, Path(tmp) / "mirrors", minimal_env(Path(tmp) / "home"), verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "schema-invalid mirror JSON should warn")
        assert_true("missing fields" in joined, "schema error should be reported")


def test_mirror_unknown_source_kind_warns_without_echo() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        mirror = root / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py"
        mirror.write_text(
            "import json\n"
            "print(json.dumps([{\n"
            "  'name': 'example-skill',\n"
            "  'source_kind': 'private-client-secret',\n"
            "  'status': 'in-sync',\n"
            "  'canonical_source': 'os/skills/example-skill/SKILL.md',\n"
            "  'mirror_path': 'mirror/example-skill',\n"
            "  'missing_files': [],\n"
            "  'changed_files': [],\n"
            "  'extra_files': [],\n"
            "  'notes': []\n"
            "}]))\n",
            encoding="utf-8",
        )
        result = check_skill_mirrors(root, Path(tmp) / "mirrors", minimal_env(Path(tmp) / "home"), verbose=True)
        joined = "\n".join(result.details + result.recommendations)
        assert_true(result.status == "WARN", "unknown source_kind should warn")
        assert_true("source_kind was not recognized" in joined, "source_kind schema error should be reported")
        assert_true("private-client-secret" not in joined, "unknown source_kind value leaked")


def test_mirror_output_does_not_print_private_metadata() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        mirror = root / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py"
        mirror.write_text(
            "import json\n"
            "print(json.dumps([{\n"
            "  'name': 'private-client-skill',\n"
            "  'source_kind': 'personal-overlay',\n"
            "  'status': 'stale',\n"
            "  'canonical_source': 'personal/os/skills/private-client-skill/SKILL.md',\n"
            "  'mirror_path': 'mirror/private-client-skill',\n"
            "  'missing_files': ['secret-plan.md'],\n"
            "  'changed_files': ['client-notes.md'],\n"
            "  'extra_files': [],\n"
            "  'notes': ['private note']\n"
            "}]))\n",
            encoding="utf-8",
        )
        result = check_skill_mirrors(root, Path(tmp) / "mirrors", minimal_env(Path(tmp) / "home"), verbose=True)
        joined = "\n".join(result.details + result.recommendations)
        assert_true(result.status == "WARN", "stale mirror result should warn")
        assert_true("private-client-skill" not in joined, "mirror skill name leaked")
        assert_true("secret-plan.md" not in joined, "mirror file name leaked")
        assert_true("Mirror statuses: stale=1" in joined, "safe aggregate status missing")


def test_helper_output_is_bounded() -> None:
    long_line = "x" * (OUTPUT_LINE_CHAR_LIMIT + 50)
    lines = format_output("stdout", "\n".join([long_line] * (OUTPUT_LINE_LIMIT + 2)), OUTPUT_LINE_LIMIT, OUTPUT_LINE_CHAR_LIMIT)
    rendered = "\n".join(lines)
    assert_true(len(lines) == OUTPUT_LINE_LIMIT + 1, "line count should be capped with an omission note")
    assert_true("char(s) omitted" in rendered, "long line should be capped")


def test_count_files_ignores_placeholder_noise() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        personal_root = root / "personal" / "os" / "automations"
        (personal_root / "AUTOMATIONS.md").unlink()
        (personal_root / ".gitkeep").write_text("", encoding="utf-8")
        (personal_root / ".DS_Store").write_text("noise", encoding="utf-8")
        count, error = count_files(personal_root)
        assert_true(error is None, "placeholder-only directory should be readable")
        assert_true(count == 0, "placeholder/noise files should not count as automation files")


def test_count_files_warns_on_walk_errors() -> None:
    original_walk = os.walk

    def fake_walk(root: Path, topdown: bool = True, onerror=None, followlinks: bool = False):
        yield os.fspath(root), ["blocked"], ["visible.md"]
        if onerror is not None:
            onerror(OSError("blocked"))

    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "automations"
        root.mkdir()
        try:
            os.walk = fake_walk  # type: ignore[assignment]
            count, error = count_files(root)
        finally:
            os.walk = original_walk  # type: ignore[assignment]
        assert_true(count is None, "walk errors should make counts unknown")
        assert_true(error is not None and "walk error" in error, "walk error should be reported")


def test_count_files_warns_on_symlink_root() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        target = Path(tmp) / "target"
        target.mkdir()
        (target / "automation.md").write_text("private", encoding="utf-8")
        link = Path(tmp) / "linked-automations"
        link.symlink_to(target, target_is_directory=True)
        count, error = count_files(link)
        assert_true(count is None, "symlink roots should make counts unknown")
        assert_true(error == "root is symlink", "symlink root should be reported")


def test_automation_locations_report_counts_not_contents() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        note = root / "personal" / "os" / "automations" / "private-note.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text(PRIVATE_CONTENT_SENTINEL, encoding="utf-8")
        codex_auto = home / ".codex" / "automations" / "daily" / "automation.toml"
        codex_auto.parent.mkdir(parents=True, exist_ok=True)
        codex_auto.write_text(PRIVATE_CONTENT_SENTINEL, encoding="utf-8")
        report = run_doctor(
            requested_agentos_home=root,
            requested_primary_agentos_home=root,
            mirror_root=Path(tmp) / "mirrors",
            cwd=root,
            process_home=home,
            env=minimal_env(home),
            adapter_args=[],
            verbose=True,
        )
        rendered = render_report_for_test(report, verbose=True)
        assert_true(PRIVATE_CONTENT_SENTINEL not in rendered, "automation file contents leaked")
        assert_true("Personal automation files: 2" in rendered, "personal automation count missing")
        assert_true("Codex automation TOML files: 1" in rendered, "Codex TOML count missing")


def test_strict_warn_exit_code() -> None:
    results = [CheckResult("example", "WARN", "warning")]
    assert_true(exit_code_for(results, strict=False) == 0, "WARN should exit 0 outside strict mode")
    assert_true(exit_code_for(results, strict=True) == 1, "WARN should exit 1 in strict mode")


def test_adapter_home_notation_is_preserved() -> None:
    args = argparse.Namespace(all_default_adapters=False, adapter=["<home>", "<home>/AGENTS.md"])
    assert_true(
        adapter_args(args, Path("/tmp")) == ["--adapter", "<home>", "--adapter", "<home>/AGENTS.md"],
        "<home> notation should pass through",
    )


def make_fake_agentos(root: Path) -> None:
    (root / "os" / "playbook").mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "os" / "skills" / "mirror-skills" / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "os" / "automations").mkdir(parents=True, exist_ok=True)
    (root / "personal" / "os" / "automations").mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (root / "os" / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    (root / "os" / "playbook" / "PERSONAL_OVERLAY.md").write_text("# Personal Overlay\n", encoding="utf-8")
    (root / "os" / "automations" / "AUTOMATIONS.md").write_text("# Automations\n", encoding="utf-8")
    (root / "personal" / "os" / "automations" / "AUTOMATIONS.md").write_text("# Private Automations\n", encoding="utf-8")
    (root / "os" / "playbook" / "GETTING_STARTED.md").write_text(
        "# Getting Started\n\n"
        "## Starter Files\n\n"
        "- `personal/os/identity/USER.md`\n"
        "- `personal/os/context/TOOLS.md`\n",
        encoding="utf-8",
    )
    (root / "scripts" / "install_global_agent_instructions.py").write_text(
        "print('[OK] ok global - managed block current')\n",
        encoding="utf-8",
    )
    (root / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py").write_text(
        "import json\n"
        "print(json.dumps([{\n"
        "  'name': 'example-skill',\n"
        "  'source_kind': 'core',\n"
        "  'status': 'in-sync',\n"
        "  'canonical_source': 'os/skills/example-skill/SKILL.md',\n"
        "  'mirror_path': 'mirror/example-skill',\n"
        "  'missing_files': [],\n"
        "  'changed_files': [],\n"
        "  'extra_files': [],\n"
        "  'notes': []\n"
        "}]))\n",
        encoding="utf-8",
    )


def minimal_env(home: Path) -> dict[str, str]:
    home.mkdir(parents=True, exist_ok=True)
    env = {
        "HOME": str(home),
        "PATH": os.environ.get("PATH", ""),
    }
    if "SYSTEMROOT" in os.environ:
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    return env


def result_named(report: DoctorReport, name: str) -> CheckResult:
    for result in report.results:
        if result.name == name:
            return result
    raise AssertionError(f"missing result {name!r}")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    raise SystemExit(main())
