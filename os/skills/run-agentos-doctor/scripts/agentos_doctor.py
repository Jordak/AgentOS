#!/usr/bin/env python3
"""Thin, read-only AgentOS setup fact collector."""

from __future__ import annotations

import argparse
import os
import re
import stat
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping


REQUIRED_AGENTOS_FILES = (
    "AGENTS.md",
    "os/INDEX.md",
    "os/playbook/PERSONAL_OVERLAY.md",
)
DEFAULT_TIMEOUT_SECONDS = 30
OUTPUT_LINE_LIMIT = 20
VERBOSE_OUTPUT_LINE_LIMIT = 80
OUTPUT_LINE_CHAR_LIMIT = 240
VERBOSE_OUTPUT_LINE_CHAR_LIMIT = 1000
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
    cwd: Path,
    process_home: Path,
    env: Mapping[str, str],
    adapter_args: list[str],
    verbose: bool,
) -> DoctorReport:
    agentos_home, discovery = resolve_agentos_home(requested_agentos_home, cwd)
    primary_agentos_home = absolute_path(requested_primary_agentos_home, cwd) if requested_primary_agentos_home else agentos_home
    home_structure = check_required_core_files(agentos_home)
    split_roots = agentos_home != primary_agentos_home

    results = [
        discovery,
        home_structure,
    ]
    if home_structure.status == "PASS":
        results.extend(
            [
                check_adapters(
                    agentos_home,
                    env,
                    adapter_args,
                    verbose,
                    primary_agentos_home=primary_agentos_home,
                    omit_current_machine_write_guidance=split_roots,
                ),
            ]
        )
    else:
        results.extend(
            [
                skipped_subprocess_check("adapter drift", home_structure),
            ]
        )
    results.extend(
        [
            check_automation_locations(agentos_home, primary_agentos_home, process_home, env),
        ]
    )
    return DoctorReport(
        agentos_home=agentos_home,
        primary_agentos_home=primary_agentos_home,
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
            "Run: python3 os/skills/run-agentos-doctor/scripts/agentos_doctor.py --agentos-home <path-to-AgentOS>"
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
                read_error = read_probe(path)
                if read_error:
                    unreadable.append(f"{rel} ({read_error})")
                else:
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


def skipped_subprocess_check(name: str, home_structure: CheckResult) -> CheckResult:
    status = "FAIL" if home_structure.status == "FAIL" else "WARN"
    return CheckResult(
        name,
        status,
        "Skipped because the AgentOS checkout structure is not trusted enough to execute helper scripts.",
        details=[
            f"Home structure status: {home_structure.status}",
            "Inspect the checkout before running nested helper scripts.",
        ],
    )


def check_adapters(
    setup_agentos_home: Path,
    env: Mapping[str, str],
    extra_args: list[str],
    verbose: bool,
    primary_agentos_home: Path | None = None,
    omit_current_machine_write_guidance: bool = False,
) -> CheckResult:
    script, invalid = trusted_helper_script(
        setup_agentos_home,
        "scripts/install_global_agent_instructions.py",
        "adapter drift",
        "Adapter check helper",
    )
    if invalid:
        return invalid

    command = [
        sys.executable,
        str(script),
        "--agentos-home",
        str(setup_agentos_home),
        "--check",
        "--no-remediation",
        *extra_args,
    ]
    completed = run_subprocess(command, cwd=setup_agentos_home, env=env)
    details = subprocess_details(command, completed, verbose)
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
    recommendations = [
        "Review the adapter check command and bounded output above.",
        "Ask through Run AgentOS Doctor before changing adapter files.",
    ]
    if omit_current_machine_write_guidance:
        recommendations.extend(
            [
                "Feature-worktree split detected; Doctor omitted current-machine write guidance for the audit root.",
                "Before any adapter write, rerun the adapter check against the primary checkout:",
            ]
        )
        if primary_agentos_home is not None and primary_agentos_home != setup_agentos_home:
            primary_command = [
                sys.executable,
                str(script),
                "--agentos-home",
                str(primary_agentos_home),
                "--check",
                "--no-remediation",
                *extra_args,
            ]
            recommendations.append("Run: " + shell_command(primary_command))
    return CheckResult(
        "adapter drift",
        "WARN",
        "Adapter check helper reported output that needs review.",
        details=details,
        recommendations=recommendations,
    )


def check_automation_locations(
    agentos_home: Path,
    primary_agentos_home: Path,
    process_home: Path,
    env: Mapping[str, str],
) -> CheckResult:
    core_registry = agentos_home / "os" / "automations" / "AUTOMATIONS.md"
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


def trusted_helper_script(
    agentos_home: Path,
    rel: str,
    check_name: str,
    helper_label: str,
) -> tuple[Path | None, CheckResult | None]:
    rel_path = Path(rel)
    script = agentos_home / rel_path
    component_problem = helper_path_component_problem(agentos_home, rel_path)
    if component_problem:
        return None, CheckResult(
            check_name,
            "FAIL",
            f"{helper_label} is not trusted for execution.",
            details=[
                f"Expected helper with non-symlink path components: {script}",
                f"Observed state: {component_problem}",
            ],
            recommendations=[
                "Inspect the helper path before running it manually."
            ],
        )
    try:
        mode = script.lstat().st_mode
    except FileNotFoundError:
        return None, CheckResult(
            check_name,
            "FAIL",
            f"{helper_label} is missing.",
            details=[f"Expected helper: {script}"],
            recommendations=[
                "Inspect the AgentOS checkout path before running nested helper scripts."
            ],
        )
    except OSError as exc:
        return None, CheckResult(
            check_name,
            "FAIL",
            f"{helper_label} could not be inspected.",
            details=[f"Expected helper: {script} ({exc.__class__.__name__})"],
        )

    if stat.S_ISLNK(mode):
        state = "symlink"
    elif not stat.S_ISREG(mode):
        state = "not a regular file"
    else:
        read_error = read_probe(script)
        if not read_error:
            return script, None
        state = f"unreadable ({read_error})"

    return None, CheckResult(
        check_name,
        "FAIL",
        f"{helper_label} is not trusted for execution.",
        details=[f"Expected regular non-symlink helper: {script}", f"Observed state: {state}"],
        recommendations=[
            "Inspect the helper path before running it manually."
        ],
    )


def helper_path_component_problem(agentos_home: Path, rel_path: Path) -> str | None:
    # Runtime execution guard only: this checks the exact helper path Doctor will execute,
    # not the repository-wide symlink policy owned by AgentOS validation.
    if rel_path.is_absolute() or ".." in rel_path.parts:
        return "helper path must be root-relative and stay inside AgentOS home"

    try:
        root_mode = agentos_home.lstat().st_mode
    except FileNotFoundError:
        return f"AgentOS home is missing: {agentos_home}"
    except OSError as exc:
        return f"AgentOS home could not be inspected: {agentos_home} ({exc.__class__.__name__})"
    if stat.S_ISLNK(root_mode):
        return f"AgentOS home is a symlink: {agentos_home}"
    if not stat.S_ISDIR(root_mode):
        return f"AgentOS home is not a directory: {agentos_home}"

    current = agentos_home
    for part in rel_path.parts[:-1]:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            return f"parent directory is missing: {current}"
        except OSError as exc:
            return f"parent directory could not be inspected: {current} ({exc.__class__.__name__})"
        if stat.S_ISLNK(mode):
            return f"parent directory is a symlink: {current}"
        if not stat.S_ISDIR(mode):
            return f"parent path is not a directory: {current}"
    return None


def read_probe(path: Path) -> str | None:
    try:
        with path.open("rb") as handle:
            handle.read(1)
    except OSError as exc:
        return exc.__class__.__name__
    return None



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
    stdout = completed.stdout
    stderr = completed.stderr
    details = [
        "Command: " + shell_command(command),
        f"Exit code: {completed.returncode}",
    ]
    details.extend(format_output("stdout", stdout, line_limit, line_char_limit))
    details.extend(format_output("stderr", stderr, line_limit, line_char_limit))
    return details


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
    import importlib.util

    test_path = Path(__file__).with_name("tests") / "test_agentos_doctor.py"
    spec = importlib.util.spec_from_file_location("agentos_doctor_self_tests", test_path)
    if spec is None or spec.loader is None:
        print(f"FAIL loading agentos_doctor self-tests from {test_path}", file=sys.stderr)
        return 1
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - keeps --self-test failures readable.
        print(f"FAIL loading agentos_doctor self-tests: {exc}", file=sys.stderr)
        return 1
    return int(module.run_self_tests())


if __name__ == "__main__":
    raise SystemExit(main())
