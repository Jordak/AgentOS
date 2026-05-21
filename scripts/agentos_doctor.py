#!/usr/bin/env python3
"""Read-only AgentOS setup health check."""

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
PRIVATE_CONTENT_SENTINEL = "DO_NOT_LEAK_AGENTOS_DOCTOR_SELF_TEST"
DEFAULT_TIMEOUT_SECONDS = 30
INSTALLER_RESULT_STATUSES = (
    "rollback-error",
    "would create",
    "would update",
    "not run",
    "missing",
    "drift",
    "error",
    "skip",
    "ok",
)


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
        "--mirror-root",
        type=Path,
        default=Path.home() / ".agents" / "skills",
        help="Current-machine skill mirror root to audit. Default: the user's .agents/skills directory.",
    )
    parser.add_argument(
        "--all-default-adapters",
        action="store_true",
        help="Pass through to the adapter drift check so all default harness adapters are checked.",
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
        help="Print exact private-path diagnostics and subprocess output. Never prints file contents.",
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
            or args.mirror_root != Path.home() / ".agents" / "skills"
            or args.all_default_adapters
            or args.adapter
            or args.verbose
        ):
            print("error: --self-test cannot be combined with other options", file=sys.stderr)
            return 2
        return run_self_tests()

    report = run_doctor(
        requested_agentos_home=args.agentos_home,
        cwd=Path.cwd(),
        mirror_root=args.mirror_root,
        verbose=args.verbose,
        process_home=Path.home(),
        env=os.environ,
        adapter_args=adapter_args(args),
    )
    print_report(report, verbose=args.verbose)
    return exit_code_for(report.results)


def adapter_args(args: argparse.Namespace) -> list[str]:
    passthrough: list[str] = []
    if args.all_default_adapters:
        passthrough.append("--all-default-adapters")
    for adapter in args.adapter:
        passthrough.extend(["--adapter", adapter])
    return passthrough


def run_doctor(
    requested_agentos_home: Path | None,
    cwd: Path,
    mirror_root: Path,
    verbose: bool,
    process_home: Path,
    env: Mapping[str, str],
    adapter_args: list[str] | None = None,
) -> DoctorReport:
    agentos_home, discovery_result = resolve_agentos_home(requested_agentos_home, cwd)
    mirror_root = expand_path(mirror_root, cwd)
    adapter_args = adapter_args or []

    results = [discovery_result, check_agentos_home(agentos_home)]
    home_is_usable = results[-1].status != "FAIL"

    if home_is_usable:
        results.append(
            check_adapters(
                agentos_home=agentos_home,
                process_home=process_home,
                env=env,
                extra_args=adapter_args,
                verbose=verbose,
            )
        )
        results.append(check_skill_mirrors(agentos_home, mirror_root, env, verbose))
        results.append(check_personal_overlay(agentos_home, verbose))
        results.append(check_automations(agentos_home, process_home, verbose))
    else:
        results.append(
            CheckResult(
                "adapter drift",
                "INFO",
                "Skipped because the AgentOS home is not usable yet.",
                recommendations=[
                    "Run from an AgentOS checkout or pass --agentos-home <resolved-agentos-home>."
                ],
            )
        )
        results.append(
            CheckResult(
                "skill mirrors",
                "INFO",
                "Skipped because the AgentOS home is not usable yet.",
            )
        )
        results.append(
            CheckResult(
                "Personal Overlay",
                "INFO",
                "Skipped because the AgentOS home is not usable yet.",
            )
        )
        results.append(
            CheckResult(
                "automations",
                "INFO",
                "Skipped because the AgentOS home is not usable yet.",
            )
        )

    return DoctorReport(agentos_home=agentos_home, mirror_root=mirror_root, results=results)


def resolve_agentos_home(requested: Path | None, cwd: Path) -> tuple[Path, CheckResult]:
    if requested is not None:
        resolved = expand_path(requested, cwd)
        return (
            resolved,
            CheckResult(
                "home discovery",
                "PASS",
                "Using --agentos-home.",
                details=[f"Resolved AgentOS home: {resolved}"],
            ),
        )

    resolved_cwd = cwd.expanduser().resolve()
    for candidate in (resolved_cwd, *resolved_cwd.parents):
        if is_agentos_home(candidate):
            return (
                candidate,
                CheckResult(
                    "home discovery",
                    "PASS",
                    "Discovered AgentOS home from the current directory.",
                    details=[f"Resolved AgentOS home: {candidate}"],
                ),
            )

    return (
        resolved_cwd,
        CheckResult(
            "home discovery",
            "FAIL",
            "Could not discover an AgentOS checkout from the current directory.",
            details=[f"Resolved fallback home: {resolved_cwd}"],
            recommendations=[
                "Run this command from inside an AgentOS checkout.",
                "Or pass --agentos-home <resolved-agentos-home>.",
            ],
        ),
    )


def expand_path(path: Path, cwd: Path) -> Path:
    expanded = Path(os.path.expanduser(str(path)))
    if not expanded.is_absolute():
        expanded = cwd / expanded
    return expanded.resolve()


def is_agentos_home(path: Path) -> bool:
    return all((path / rel).is_file() for rel in REQUIRED_AGENTOS_FILES)


def check_agentos_home(agentos_home: Path) -> CheckResult:
    missing = []
    wrong_kind = []
    for rel in REQUIRED_AGENTOS_FILES:
        path = agentos_home / rel
        try:
            path.lstat()
        except FileNotFoundError:
            missing.append(rel)
            continue
        except OSError as exc:
            return CheckResult(
                "home structure",
                "FAIL",
                "Could not inspect required AgentOS files.",
                details=[f"{rel}: {exc}"],
            )
        if not path.is_file():
            wrong_kind.append(rel)

    if missing or wrong_kind:
        details = []
        if missing:
            details.append("Missing: " + ", ".join(missing))
        if wrong_kind:
            details.append("Not regular files: " + ", ".join(wrong_kind))
        return CheckResult(
            "home structure",
            "FAIL",
            "The resolved home does not look like an AgentOS checkout.",
            details=details,
            recommendations=[
                "Point --agentos-home at the directory containing AGENTS.md and os/INDEX.md."
            ],
        )

    return CheckResult(
        "home structure",
        "PASS",
        "Required AgentOS Core entry files are present.",
        details=[f"Required files checked: {len(REQUIRED_AGENTOS_FILES)}"],
    )


def check_adapters(
    agentos_home: Path,
    process_home: Path,
    env: Mapping[str, str],
    extra_args: list[str],
    verbose: bool,
) -> CheckResult:
    script = agentos_home / "scripts" / "install_global_agent_instructions.py"
    if not script.is_file():
        return CheckResult(
            "adapter drift",
            "FAIL",
            "Adapter drift check script is missing.",
            details=[root_relative(agentos_home, script)],
        )

    command = [
        sys.executable,
        str(script),
        "--agentos-home",
        str(agentos_home),
        "--check",
        *extra_args,
    ]
    completed = run_subprocess(command, cwd=agentos_home, env=env_with_home(env, process_home))
    check_lines = managed_result_lines(completed.stdout)
    counts = Counter(line_status(line) for line in check_lines)
    result_statuses = installer_result_statuses(check_lines)
    details = [
        f"Command: {shell_command(command, agentos_home)}",
        f"Managed targets checked: {len(check_lines)}",
    ]
    if counts:
        details.append("Statuses: " + format_counts(counts))
    if result_statuses:
        details.append("Result statuses: " + format_counts(result_statuses))
    if verbose:
        details.extend(prefix_lines("installer", completed.stdout, completed.stderr))

    if completed.returncode == 0:
        return CheckResult(
            "adapter drift",
            "PASS",
            "Global instruction adapters are current for the checked targets.",
            details=details,
        )

    if completed.returncode in {124, 127} or not check_lines:
        details.extend(subprocess_failure_details(completed, verbose))
        return CheckResult(
            "adapter drift",
            "FAIL",
            "Adapter drift check could not complete.",
            details=details,
            recommendations=[
                "Fix the adapter check command or environment, then re-run this doctor command."
            ],
        )

    hard_failure_statuses = {
        status
        for status in result_statuses
        if status not in {"missing", "drift"}
        and any(line.startswith("[FAIL]") and installer_result_status(line) == status for line in check_lines)
    }
    if hard_failure_statuses:
        details.extend(subprocess_failure_details(completed, verbose))
        return CheckResult(
            "adapter drift",
            "FAIL",
            "Adapter drift check reported command or configuration errors.",
            details=details,
            recommendations=[
                "Fix the adapter command, target paths, or reported configuration errors before running install remediation."
            ],
        )

    dry_run_command = [
        sys.executable,
        str(script),
        "--agentos-home",
        str(agentos_home),
        *extra_args,
    ]
    write_command = [*dry_run_command, "--no-dry-run"]
    recommendations = [
        "Review the dry-run/write flow before applying any remediation.",
        f"Dry-run: {shell_command(dry_run_command, agentos_home)}",
        f"After approving writes: {shell_command(write_command, agentos_home)}",
        "Then re-run this doctor command.",
    ]
    return CheckResult(
        "adapter drift",
        "WARN",
        "Adapter check reported missing, stale, or unreadable managed blocks.",
        details=details,
        recommendations=recommendations,
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
            "Mirror-skills audit script is missing.",
            details=[root_relative(agentos_home, script)],
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
    base_details = [
        f"Command: {shell_command(command, agentos_home)}",
        f"Exit code: {completed.returncode}",
    ]
    if not completed.stdout.strip():
        base_details.extend(subprocess_failure_details(completed, verbose))
        return CheckResult(
            "skill mirrors",
            "FAIL",
            "Mirror-skills audit did not return JSON output.",
            details=base_details,
            recommendations=[
                "Fix the mirror-skills command or reported skill configuration, then re-run this doctor command."
            ],
        )

    try:
        results = json.loads(completed.stdout)
    except json.JSONDecodeError:
        details = list(base_details)
        if verbose:
            details.extend(prefix_lines("mirror-skills", completed.stdout, completed.stderr))
        else:
            details.append("Subprocess output suppressed; re-run with --verbose for exact diagnostics.")
        return CheckResult(
            "skill mirrors",
            "FAIL",
            "Mirror-skills audit did not return valid JSON.",
            details=details,
        )

    if not isinstance(results, list) or not all(isinstance(result, dict) for result in results):
        details = list(base_details)
        details.append("JSON output shape was not a list of mirror result objects.")
        if verbose:
            details.extend(prefix_lines("mirror-skills", completed.stdout, completed.stderr))
        return CheckResult(
            "skill mirrors",
            "FAIL",
            "Mirror-skills audit returned unexpected JSON output.",
            details=details,
        )

    statuses = Counter(str(result.get("status", "unknown")) for result in results)
    source_kinds = Counter(str(result.get("source_kind", "unknown")) for result in results)
    details = [
        f"Command: {shell_command(command, agentos_home)}",
        f"Exit code: {completed.returncode}",
        f"Mirror root: {mirror_root}",
        f"Skills audited: {len(results)}",
        "Source kinds: " + format_counts(source_kinds),
        "Statuses: " + format_counts(statuses),
    ]
    if verbose:
        details.extend(verbose_mirror_details(results))
        details.extend(prefix_lines("mirror-skills", "", completed.stderr))

    bad_statuses = {
        "source-missing",
        "source-unreadable",
        "mirror-unreadable",
        "missing",
        "stale",
        "extra-files",
        "unknown",
    }
    if completed.returncode == 0 and not any(status in bad_statuses for status in statuses):
        return CheckResult(
            "skill mirrors",
            "PASS",
            "Skill mirrors are in sync for the checked mirror root.",
            details=details,
        )

    hard_statuses = {"source-missing", "source-unreadable", "mirror-unreadable", "unknown"}
    audit_command = mirror_command(agentos_home, mirror_root)
    if any(status in hard_statuses for status in statuses):
        recommendations = [
            "Fix the reported source, readability, or audit-shape errors before syncing mirrors.",
            "Inspect the audit: " + shell_command(audit_command, agentos_home),
        ]
        return CheckResult(
            "skill mirrors",
            "FAIL",
            "Mirror-skills audit found source, readability, or output-shape errors.",
            details=details,
            recommendations=recommendations,
        )

    recommendations = [
        "Inspect the audit: " + shell_command(audit_command, agentos_home),
    ]
    if statuses.get("missing") or statuses.get("stale"):
        sync_command = [*audit_command, "--sync"]
        recommendations.append(
            "After approving current-machine mirror writes: "
            + shell_command(sync_command, agentos_home)
        )
    if statuses.get("extra-files"):
        recommendations.append(
            "Extra mirror files are not deleted by default; inspect them before considering --prune-extra."
        )

    return CheckResult(
        "skill mirrors",
        "WARN",
        "Mirror-skills audit found missing, stale, extra, or unreadable mirrors.",
        details=details,
        recommendations=recommendations,
    )


def check_personal_overlay(agentos_home: Path, verbose: bool) -> CheckResult:
    personal_root = agentos_home / "personal" / "os"
    getting_started = agentos_home / "os" / "playbook" / "GETTING_STARTED.md"
    starter_paths, starter_error = starter_personal_paths(getting_started)
    if not personal_root.exists():
        return CheckResult(
            "Personal Overlay",
            "WARN",
            "Personal Overlay root is missing.",
            details=[
                "Starter paths documented: " + str(len(starter_paths)),
                f"Expected root: {root_relative(agentos_home, personal_root)}",
            ],
            recommendations=[
                "Create approved private starter files under personal/os/ using os/playbook/GETTING_STARTED.md."
            ],
        )

    if not personal_root.is_dir():
        return CheckResult(
            "Personal Overlay",
            "FAIL",
            "Personal Overlay path exists but is not a directory.",
            details=[root_relative(agentos_home, personal_root)],
        )

    existing_starters = [rel for rel in starter_paths if (agentos_home / rel).is_file()]
    missing_starters = [rel for rel in starter_paths if rel not in existing_starters]
    private_file_count = count_non_gitkeep_files(personal_root)
    details = [
        f"Private files under personal/os/: {private_file_count}",
        f"Starter files present: {len(existing_starters)}/{len(starter_paths)}",
    ]
    if starter_error:
        details.append(starter_error)
    if missing_starters:
        details.append("Missing starter paths: " + ", ".join(missing_starters))
    if verbose and existing_starters:
        details.append("Present starter paths: " + ", ".join(existing_starters))

    if starter_error:
        return CheckResult(
            "Personal Overlay",
            "WARN",
            "Could not determine documented starter Personal Overlay files.",
            details=details,
            recommendations=[
                "Restore or repair os/playbook/GETTING_STARTED.md so the Starter Files section can be audited."
            ],
        )

    if missing_starters:
        return CheckResult(
            "Personal Overlay",
            "WARN",
            "Some documented starter Personal Overlay files are absent.",
            details=details,
            recommendations=[
                "Run a guided first-pass setup using os/playbook/GETTING_STARTED.md.",
                "Ask before writing private state; create only approved files under personal/os/.",
            ],
        )

    return CheckResult(
        "Personal Overlay",
        "PASS",
        "Documented starter Personal Overlay files are present.",
        details=details,
    )


def starter_personal_paths(getting_started: Path) -> tuple[list[str], str | None]:
    try:
        text = getting_started.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [], "GETTING_STARTED.md is missing; starter path audit skipped."
    except OSError as exc:
        return [], f"Could not read GETTING_STARTED.md: {exc}"

    heading = STARTER_HEADING_RE.search(text)
    if not heading:
        return [], "Starter Files section not found in GETTING_STARTED.md."
    next_heading = NEXT_HEADING_RE.search(text, heading.end())
    section = text[heading.end() : next_heading.start() if next_heading else len(text)]
    paths: list[str] = []
    seen: set[str] = set()
    for raw in PERSONAL_PATH_RE.findall(section):
        rel = raw.strip().rstrip(":")
        if rel not in seen:
            seen.add(rel)
            paths.append(rel)
    if not paths:
        return [], "Starter Files section did not list any personal/os/ starter paths."
    return paths, None


def mirror_command(agentos_home: Path, mirror_root: Path) -> list[str]:
    return [
        sys.executable,
        str(agentos_home / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py"),
        "--agentos-root",
        str(agentos_home),
        "--mirror-root",
        str(mirror_root),
    ]


def check_automations(agentos_home: Path, process_home: Path, verbose: bool) -> CheckResult:
    core_registry = agentos_home / "os" / "automations" / "AUTOMATIONS.md"
    personal_automations = agentos_home / "personal" / "os" / "automations"
    personal_registry = personal_automations / "AUTOMATIONS.md"
    codex_automations = process_home / ".codex" / "automations"
    personal_file_count = count_non_gitkeep_files(personal_automations)
    codex_file_count = count_non_gitkeep_files(codex_automations)
    registry_mentions_checks = personal_registry_mentions_agentos_checks(personal_registry)
    recurring_check_evidence = registry_mentions_checks or codex_file_count > 0

    details = [
        "Core automation registry: " + ("present" if core_registry.is_file() else "missing"),
        "Personal automation registry: " + ("present" if personal_registry.is_file() else "missing"),
        f"Personal automation files: {personal_file_count}",
        "Codex automation mirror dir: " + presence_with_count(codex_automations),
        "Recurring AgentOS check evidence: " + ("found" if recurring_check_evidence else "not found"),
    ]
    if verbose:
        details.extend(
            [
                f"Core registry path: {root_relative(agentos_home, core_registry)}",
                f"Personal automation root: {root_relative(agentos_home, personal_automations)}",
                f"Codex automation mirror path: {codex_automations}",
            ]
        )

    if not core_registry.is_file():
        return CheckResult(
            "automations",
            "FAIL",
            "Core automation registry is missing.",
            details=details,
        )
    if personal_automations.exists() and personal_file_count and not personal_registry.is_file():
        return CheckResult(
            "automations",
            "WARN",
            "Personal automation files exist but no personal automation registry was found.",
            details=details,
            recommendations=[
                "If those files are live automations, record the registry in personal/os/automations/AUTOMATIONS.md."
            ],
        )
    if not recurring_check_evidence:
        return CheckResult(
            "automations",
            "WARN",
            "No recurring AgentOS update or drift-check automation evidence was found.",
            details=details,
            recommendations=[
                "Live automations are optional; if desired, use os/playbook/GETTING_STARTED.md to choose a cadence before creating one."
            ],
        )

    return CheckResult(
        "automations",
        "PASS",
        "Automation policy is present and recurring check evidence was found.",
        details=details,
    )


def personal_registry_mentions_agentos_checks(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False
    except OSError:
        return False
    lowered = text.lower()
    return "agentos" in lowered and any(term in lowered for term in ("drift", "update", "repository"))


def count_non_gitkeep_files(root: Path) -> int:
    if not root.exists() or not root.is_dir():
        return 0
    count = 0
    for path in root.rglob("*"):
        if path.is_file() and path.name != ".gitkeep":
            count += 1
    return count


def presence_with_count(path: Path) -> str:
    if not path.exists():
        return "missing"
    if not path.is_dir():
        return "present but not a directory"
    return f"present ({count_non_gitkeep_files(path)} files)"


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


def env_with_home(env: Mapping[str, str], home: Path) -> dict[str, str]:
    result = dict(env)
    result["HOME"] = str(home)
    return result


def managed_result_lines(stdout: str) -> list[str]:
    return [line for line in stdout.splitlines() if line.startswith("[OK]") or line.startswith("[FAIL]")]


def line_status(line: str) -> str:
    match = re.match(r"^\[([A-Z]+)\]", line)
    if match:
        return match.group(1)
    return "unknown"


def installer_result_status(line: str) -> str:
    match = re.match(r"^\[(?:OK|FAIL)\]\s+(.+?)\s+-\s+", line)
    if not match:
        return "unknown"
    body = match.group(1)
    for status in INSTALLER_RESULT_STATUSES:
        if body.startswith(status + " ") or body == status:
            return status
    return "unknown"


def installer_result_statuses(lines: Iterable[str]) -> Counter[str]:
    return Counter(installer_result_status(line) for line in lines)


def format_counts(counts: Counter[str]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


def verbose_mirror_details(results: Iterable[object]) -> list[str]:
    lines: list[str] = []
    for raw in results:
        if not isinstance(raw, dict):
            continue
        name = raw.get("name", "<unknown>")
        status = raw.get("status", "<unknown>")
        source_kind = raw.get("source_kind", "<unknown>")
        canonical_source = raw.get("canonical_source", "<unknown>")
        mirror_path = raw.get("mirror_path", "<unknown>")
        lines.append(
            f"Mirror detail: {status} {source_kind} {name} "
            f"canonical={canonical_source} mirror={mirror_path}"
        )
    return lines


def prefix_lines(label: str, stdout: str, stderr: str) -> list[str]:
    lines: list[str] = []
    for stream_name, text in (("stdout", stdout), ("stderr", stderr)):
        for line in text.splitlines():
            lines.append(f"{label} {stream_name}: {line}")
    return lines


def output_to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def subprocess_failure_details(completed: subprocess.CompletedProcess[str], verbose: bool) -> list[str]:
    details = [f"Subprocess exit code: {completed.returncode}"]
    if verbose:
        details.extend(prefix_lines("subprocess", completed.stdout, completed.stderr))
        return details

    stderr_lines = [line for line in completed.stderr.splitlines() if line.strip()]
    if stderr_lines:
        details.append("Subprocess stderr: " + " / ".join(stderr_lines[:3]))
    else:
        details.append("Subprocess produced no stderr; re-run with --verbose for exact diagnostics.")
    return details


def shell_command(command: list[str], agentos_home: Path) -> str:
    rendered = []
    for part in command:
        if part == sys.executable:
            rendered.append("python3")
            continue
        path = Path(part)
        if path == agentos_home:
            rendered.append(str(path))
            continue
        try:
            if path.is_absolute() and path.is_relative_to(agentos_home):
                rendered.append(path.relative_to(agentos_home).as_posix())
                continue
        except ValueError:
            pass
        rendered.append(part)
    return " ".join(sh_quote(part) for part in rendered)


def sh_quote(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:=@+-]+", value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def root_relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def print_report(report: DoctorReport, verbose: bool) -> None:
    print("AgentOS doctor (read-only)")
    print(f"AgentOS home: {report.agentos_home}")
    print(f"Skill mirror root: {report.mirror_root}")
    print("No files were modified.")
    print("")

    for result in report.results:
        print(f"[{result.status}] {result.name}: {result.summary}")
        for detail in result.details:
            print(f"  - {detail}")
        for recommendation in result.recommendations:
            print(f"  Next: {recommendation}")
        print("")

    if not verbose:
        print("Tip: pass --verbose to include exact private-path diagnostics without file contents.")


def exit_code_for(results: Iterable[CheckResult]) -> int:
    statuses = {result.status for result in results}
    if "FAIL" in statuses:
        return 2
    if "WARN" in statuses:
        return 1
    return 0


def run_self_tests() -> int:
    tests = [
        test_home_discovery_and_personal_overlay_privacy,
        test_personal_overlay_source_error_warns,
        test_personal_overlay_empty_starter_list_warns,
        test_invalid_home_is_graceful,
        test_adapter_check_uses_temp_home,
        test_adapter_check_command_failure_is_not_drift,
        test_adapter_check_preflight_error_is_not_drift,
        test_subprocess_timeout_output_is_text,
        test_mirror_smoke_uses_temp_dirs,
        test_mirror_command_failure_is_not_sync_advice,
        test_mirror_source_failure_is_not_sync_advice,
        test_mirror_recommendations_quote_paths,
        test_automation_no_evidence_warns,
        test_automation_registry_evidence_passes,
        test_automation_files_without_registry_warns,
    ]
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
            return 1
    print(f"PASS agentos_doctor self-tests ({len(tests)} tests)")
    return 0


def test_home_discovery_and_personal_overlay_privacy() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        secret_file = root / "personal" / "os" / "identity" / "USER.md"
        secret_file.write_text(PRIVATE_CONTENT_SENTINEL, encoding="utf-8")
        nested = root / "os" / "playbook"
        report = run_doctor(
            requested_agentos_home=None,
            cwd=nested,
            mirror_root=Path(tmp) / "mirrors",
            verbose=False,
            process_home=Path(tmp) / "home",
            env=minimal_env(Path(tmp) / "home"),
        )
        assert_true(report.agentos_home == root.resolve(), "home discovery failed")
        rendered = render_report_for_test(report, verbose=False)
        assert_true(PRIVATE_CONTENT_SENTINEL not in rendered, "private contents leaked")
        assert_true("personal/os/identity/COMMUNICATION.md" in rendered, "missing starter path not reported")


def test_personal_overlay_source_error_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        (root / "os" / "playbook" / "GETTING_STARTED.md").write_text(
            "# Getting Started\n\n## Renamed Starter Checklist\n\n- `personal/os/identity/USER.md`\n",
            encoding="utf-8",
        )
        result = check_personal_overlay(root, verbose=False)
        assert_true(result.status == "WARN", "unreadable starter checklist should warn")
        assert_true("Could not determine" in result.summary, "starter source warning summary missing")


def test_personal_overlay_empty_starter_list_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        (root / "os" / "playbook" / "GETTING_STARTED.md").write_text(
            "# Getting Started\n\n## Starter Files\n\nNo starter paths yet.\n",
            encoding="utf-8",
        )
        result = check_personal_overlay(root, verbose=False)
        assert_true(result.status == "WARN", "empty starter checklist should warn")
        assert_true("Could not determine" in result.summary, "empty starter warning summary missing")


def test_invalid_home_is_graceful() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "not-agentos"
        root.mkdir()
        report = run_doctor(
            requested_agentos_home=root,
            cwd=root,
            mirror_root=Path(tmp) / "mirrors",
            verbose=False,
            process_home=Path(tmp) / "home",
            env=minimal_env(Path(tmp) / "home"),
        )
        statuses = [result.status for result in report.results]
        assert_true("FAIL" in statuses, "invalid home should fail gracefully")
        assert_true(report.agentos_home == root.resolve(), "explicit home was not printed/resolved")


def test_adapter_check_uses_temp_home() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        home.mkdir()
        result = check_adapters(
            agentos_home=root,
            process_home=home,
            env=minimal_env(home),
            extra_args=[],
            verbose=True,
        )
        joined = "\n".join(result.details)
        assert_true(str(home) in joined, "adapter check did not use temp HOME")
        assert_true(str(Path.home()) not in joined, "adapter check leaked real HOME")


def test_adapter_check_command_failure_is_not_drift() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        home.mkdir()
        installer = root / "scripts" / "install_global_agent_instructions.py"
        installer.write_text(
            "import sys\nprint('installer exploded', file=sys.stderr)\nsys.exit(127)\n",
            encoding="utf-8",
        )
        result = check_adapters(
            agentos_home=root,
            process_home=home,
            env=minimal_env(home),
            extra_args=[],
            verbose=False,
        )
        joined = "\n".join(result.details + result.recommendations)
        assert_true(result.status == "FAIL", "adapter command failure should fail")
        assert_true("--no-dry-run" not in joined, "command failure should not recommend adapter writes")


def test_adapter_check_preflight_error_is_not_drift() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        home.mkdir()
        result = check_adapters(
            agentos_home=root,
            process_home=home,
            env=minimal_env(home),
            extra_args=["--adapter", str(root)],
            verbose=False,
        )
        joined = "\n".join(result.details + result.recommendations)
        assert_true(result.status == "FAIL", "adapter preflight error should fail")
        assert_true("--no-dry-run" not in joined, "preflight error should not recommend adapter writes")
        assert_true("error=1" in joined, "preflight result status should be reported")


def test_subprocess_timeout_output_is_text() -> None:
    global DEFAULT_TIMEOUT_SECONDS
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        home.mkdir()
        installer = root / "scripts" / "install_global_agent_instructions.py"
        installer.write_text(
            "import sys, time\n"
            "print('[FAIL] error example-adapter - partial stdout before timeout')\n"
            "sys.stdout.flush()\n"
            "print('partial stderr before timeout', file=sys.stderr)\n"
            "sys.stderr.flush()\n"
            "time.sleep(5)\n",
            encoding="utf-8",
        )
        old_timeout = DEFAULT_TIMEOUT_SECONDS
        DEFAULT_TIMEOUT_SECONDS = 1
        try:
            result = check_adapters(
                agentos_home=root,
                process_home=home,
                env=minimal_env(home),
                extra_args=[],
                verbose=False,
            )
        finally:
            DEFAULT_TIMEOUT_SECONDS = old_timeout
        joined = "\n".join(result.details)
        assert_true(result.status == "FAIL", "timeout should return a failure result")
        assert_true("Timed out after 1 seconds." in joined, "timeout stderr should be preserved as text")


def test_mirror_smoke_uses_temp_dirs() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        mirror_root = Path(tmp) / "mirrors"
        make_fake_agentos(root)
        script = root / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py"
        command = [
            sys.executable,
            str(script),
            "--agentos-root",
            str(root),
            "--mirror-root",
            str(mirror_root),
            "--sync",
        ]
        completed = run_subprocess(command, cwd=root, env=minimal_env(Path(tmp) / "home"))
        assert_true(completed.returncode == 0, completed.stderr or completed.stdout)
        result = check_skill_mirrors(root, mirror_root, minimal_env(Path(tmp) / "home"), verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "PASS", "mirror audit should pass after temp sync")
        assert_true("core=1" in joined, "core skill source kind not audited")
        assert_true("personal-overlay=1" in joined, "Personal Overlay skill source kind not audited")


def test_mirror_command_failure_is_not_sync_advice() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        mirror_root = Path(tmp) / "mirrors"
        make_fake_agentos(root)
        duplicate = root / "personal" / "os" / "skills" / "example-skill" / "SKILL.md"
        duplicate.parent.mkdir(parents=True)
        duplicate.write_text("# Duplicate Private Skill\n", encoding="utf-8")
        result = check_skill_mirrors(root, mirror_root, minimal_env(Path(tmp) / "home"), verbose=False)
        joined = "\n".join(result.details + result.recommendations)
        assert_true(result.status == "FAIL", "mirror command failure should fail")
        assert_true("--sync" not in joined, "command failure should not recommend mirror sync")


def test_mirror_source_failure_is_not_sync_advice() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        mirror_root = Path(tmp) / "mirrors"
        make_fake_agentos(root)
        manifest = root / "os" / "skills" / "MANIFEST.md"
        manifest.write_text(
            manifest.read_text(encoding="utf-8")
            + """

### `missing-source-skill`

- Canonical source: `os/skills/missing-source-skill/SKILL.md`.
""",
            encoding="utf-8",
        )
        result = check_skill_mirrors(root, mirror_root, minimal_env(Path(tmp) / "home"), verbose=False)
        joined = "\n".join(result.details + result.recommendations)
        assert_true(result.status == "FAIL", "missing canonical source should fail")
        assert_true("source-missing=1" in joined, "source-missing status should be reported")
        assert_true("--sync" not in joined, "source failure should not recommend mirror sync")


def test_mirror_recommendations_quote_paths() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS With Spaces"
        mirror_root = Path(tmp) / "mirrors with spaces"
        make_fake_agentos(root)
        result = check_skill_mirrors(root, mirror_root, minimal_env(Path(tmp) / "home"), verbose=False)
        joined = "\n".join(result.recommendations)
        assert_true(result.status == "WARN", "missing mirrors should warn")
        assert_true("mirrors with spaces'" in joined, "mirror path should be shell quoted")
        assert_true("AgentOS With Spaces'" in joined, "AgentOS path should be shell quoted")


def test_automation_no_evidence_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        result = check_automations(root, Path(tmp) / "home", verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "missing recurring check evidence should warn")
        assert_true("Recurring AgentOS check evidence: not found" in joined, "missing evidence should be explicit")


def test_automation_registry_evidence_passes() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        registry = root / "personal" / "os" / "automations" / "AUTOMATIONS.md"
        registry.write_text("AgentOS repository update and adapter drift check automation.\n", encoding="utf-8")
        result = check_automations(root, Path(tmp) / "home", verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "PASS", "registry evidence should pass")
        assert_true("Recurring AgentOS check evidence: found" in joined, "found evidence should be explicit")


def test_automation_files_without_registry_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        (root / "personal" / "os" / "automations" / "drift-check.md").write_text(
            "AgentOS drift check draft.\n",
            encoding="utf-8",
        )
        result = check_automations(root, Path(tmp) / "home", verbose=False)
        assert_true(result.status == "WARN", "automation files without registry should warn")
        assert_true("registry" in result.summary, "warning should mention missing registry")


def render_report_for_test(report: DoctorReport, verbose: bool) -> str:
    lines = [
        "AgentOS doctor (read-only)",
        f"AgentOS home: {report.agentos_home}",
        f"Skill mirror root: {report.mirror_root}",
    ]
    for result in report.results:
        lines.append(f"[{result.status}] {result.name}: {result.summary}")
        lines.extend(result.details)
        lines.extend(result.recommendations)
    if not verbose:
        lines.append("Tip: pass --verbose to include exact private-path diagnostics without file contents.")
    return "\n".join(lines)


def make_fake_agentos(root: Path) -> None:
    root.mkdir(parents=True)
    (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (root / "os" / "INDEX.md").parent.mkdir(parents=True)
    (root / "os" / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    (root / "os" / "playbook").mkdir(parents=True)
    (root / "os" / "playbook" / "PERSONAL_OVERLAY.md").write_text("# Overlay\n", encoding="utf-8")
    (root / "os" / "playbook" / "GETTING_STARTED.md").write_text(
        """# Getting Started

## Starter Files

- `personal/os/identity/USER.md`: durable identity.
- `personal/os/identity/COMMUNICATION.md`: communication.

## Next Section
""",
        encoding="utf-8",
    )
    (root / "personal" / "os" / "identity").mkdir(parents=True)
    (root / "personal" / "os" / "automations").mkdir(parents=True)
    (root / "os" / "automations").mkdir(parents=True)
    (root / "os" / "automations" / "AUTOMATIONS.md").write_text("No active Core automations.\n", encoding="utf-8")

    copy_script(
        Path(__file__).resolve().parent / "install_global_agent_instructions.py",
        root / "scripts" / "install_global_agent_instructions.py",
    )
    mirror_source = (
        Path(__file__).resolve().parents[1]
        / "os"
        / "skills"
        / "mirror-skills"
        / "scripts"
        / "mirror_skills.py"
    )
    copy_script(mirror_source, root / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py")
    (root / "os" / "skills" / "example-skill").mkdir(parents=True)
    (root / "os" / "skills" / "example-skill" / "SKILL.md").write_text("# Example Skill\n", encoding="utf-8")
    (root / "personal" / "os" / "skills" / "private-skill").mkdir(parents=True)
    (root / "personal" / "os" / "skills" / "private-skill" / "SKILL.md").write_text(
        "# Private Skill\n",
        encoding="utf-8",
    )
    (root / "os" / "skills" / "MANIFEST.md").write_text(
        """# Skills Manifest

### `example-skill`

- Canonical source: `os/skills/example-skill/SKILL.md`.
""",
        encoding="utf-8",
    )


def copy_script(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def minimal_env(home: Path) -> dict[str, str]:
    env = {
        "HOME": str(home),
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
    }
    return {key: value for key, value in env.items() if value}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    sys.exit(main())
