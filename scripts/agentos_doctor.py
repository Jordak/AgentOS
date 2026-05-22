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
AUTOMATION_CHECK_TERMS = (
    "drift",
    "update",
    "repository",
    "review",
    "doctor",
    "health",
    "setup",
)
AUTOMATION_NEGATIVE_MARKERS = (
    "do not run",
    "do not use",
    "disabled",
    "retired",
    "inactive",
    "paused",
    "draft",
    "candidate",
    "deprecated",
    "not active",
)
AUTOMATION_NEGATIVE_PROSE_MARKERS = (
    "do not run",
    "do not use",
    "disabled",
    "retired",
    "inactive",
    "paused",
    "not active",
    "draft-only",
    "draft only",
    "draft mode",
    "candidate",
    "deprecated",
)
AUTOMATION_ACTIVE_STATUS_MARKERS = ("active", "enabled", "scheduled", "running")
AUTOMATION_NONRECURRING_SCHEDULE_MARKERS = (
    "",
    "none",
    "n/a",
    "na",
    "manual",
    "manual only",
    "manual-only",
    "once",
    "one time",
    "one-time",
    "tbd",
    "todo",
    "unscheduled",
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
    primary_agentos_home: Path
    setup_agentos_home: Path
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
        "--primary-agentos-home",
        type=Path,
        default=None,
        help="Primary AgentOS checkout that owns the canonical Personal Overlay. Defaults to --agentos-home.",
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

    report = run_doctor(
        requested_agentos_home=args.agentos_home,
        requested_primary_agentos_home=args.primary_agentos_home,
        cwd=Path.cwd(),
        mirror_root=args.mirror_root,
        verbose=args.verbose,
        process_home=Path.home(),
        env=os.environ,
        adapter_args=adapter_args(args, Path.cwd()),
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
    mirror_root: Path,
    verbose: bool,
    process_home: Path,
    env: Mapping[str, str],
    adapter_args: list[str] | None = None,
) -> DoctorReport:
    agentos_home, discovery_result = resolve_agentos_home(requested_agentos_home, cwd)
    primary_agentos_home = expand_path(requested_primary_agentos_home, cwd) if requested_primary_agentos_home else agentos_home
    setup_agentos_home = primary_agentos_home if requested_primary_agentos_home else agentos_home
    mirror_root = expand_path(mirror_root, cwd)
    adapter_args = adapter_args or []
    linked_worktree_without_primary = requested_primary_agentos_home is None and is_linked_git_worktree(agentos_home)
    current_machine_recommendations_allowed = not linked_worktree_without_primary

    results = [discovery_result, check_agentos_home(agentos_home)]
    home_is_usable = results[-1].status != "FAIL"
    if home_is_usable and primary_agentos_home != agentos_home:
        primary_result = check_primary_agentos_home(primary_agentos_home)
        results.append(primary_result)
        home_is_usable = primary_result.status != "FAIL"

    if home_is_usable:
        if linked_worktree_without_primary:
            results.append(linked_worktree_without_primary_result(agentos_home))
        results.append(
            check_adapters(
                agentos_home=setup_agentos_home,
                process_home=process_home,
                env=env,
                extra_args=adapter_args,
                verbose=verbose,
                allow_remediation=current_machine_recommendations_allowed,
            )
        )
        results.append(
            check_skill_mirrors(
                agentos_home,
                primary_agentos_home,
                mirror_root,
                env,
                verbose,
                allow_sync_recommendation=current_machine_recommendations_allowed
                and setup_agentos_home == agentos_home,
                mirror_agentos_home=agentos_home,
                script_agentos_home=agentos_home,
            )
        )
        results.append(
            check_personal_overlay(
                agentos_home,
                primary_agentos_home,
                verbose,
                private_root_is_canonical=not linked_worktree_without_primary,
            )
        )
        results.append(
            check_automations(
                agentos_home,
                primary_agentos_home,
                process_home,
                verbose,
                private_root_is_canonical=not linked_worktree_without_primary,
            )
        )
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

    return DoctorReport(
        agentos_home=agentos_home,
        primary_agentos_home=primary_agentos_home,
        setup_agentos_home=setup_agentos_home,
        mirror_root=mirror_root,
        results=results,
    )


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


def is_linked_git_worktree(path: Path) -> bool:
    git_entry = path / ".git"
    try:
        if not git_entry.is_file():
            return False
        text = git_entry.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return False
    return text.lower().startswith("gitdir:") and "/worktrees/" in text.replace("\\", "/")


def linked_worktree_without_primary_result(agentos_home: Path) -> CheckResult:
    return CheckResult(
        "worktree mode",
        "WARN",
        "Linked Git worktree detected without --primary-agentos-home.",
        details=[f"Linked worktree: {agentos_home}"],
        recommendations=[
            "Re-run with --primary-agentos-home <primary-agentos-home> before applying current-machine setup recommendations.",
            "Adapter write and skill mirror sync recommendations are suppressed for this run.",
        ],
    )


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


def check_primary_agentos_home(primary_agentos_home: Path) -> CheckResult:
    result = check_agentos_home(primary_agentos_home)
    if result.status == "FAIL":
        result.name = "primary home structure"
        result.summary = "The primary AgentOS home does not look like an AgentOS checkout."
        return result
    return CheckResult(
        "primary home structure",
        "PASS",
        "Primary AgentOS home is usable for Personal Overlay reads.",
        details=[f"Primary AgentOS home: {primary_agentos_home}"],
    )


def check_adapters(
    agentos_home: Path,
    process_home: Path,
    env: Mapping[str, str],
    extra_args: list[str],
    verbose: bool,
    allow_remediation: bool = True,
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

    if allow_remediation:
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
    else:
        recommendations = [
            "Adapter write recommendations are suppressed because this run is using a linked worktree without --primary-agentos-home.",
            "Re-run from the canonical checkout or pass --primary-agentos-home <primary-agentos-home> before applying adapter remediation.",
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
    primary_agentos_home: Path,
    mirror_root: Path,
    env: Mapping[str, str],
    verbose: bool,
    allow_sync_recommendation: bool = True,
    mirror_agentos_home: Path | None = None,
    script_agentos_home: Path | None = None,
) -> CheckResult:
    mirror_agentos_home = mirror_agentos_home or agentos_home
    script_agentos_home = script_agentos_home or agentos_home
    script = script_agentos_home / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py"
    if not script.is_file():
        return CheckResult(
            "skill mirrors",
            "FAIL",
            "Mirror-skills audit script is missing.",
            details=[root_relative(script_agentos_home, script)],
        )

    command = [
        sys.executable,
        str(script),
        "--agentos-root",
        str(mirror_agentos_home),
        "--mirror-root",
        str(mirror_root),
        "--personal-overlay-root",
        str(primary_agentos_home / "personal" / "os"),
        "--json",
    ]
    completed = run_subprocess(command, cwd=script_agentos_home, env=env)
    base_details = [
        f"Command: {shell_command(command, script_agentos_home)}",
        f"Exit code: {completed.returncode}",
    ]
    if not completed.stdout.strip():
        if verbose:
            base_details.extend(subprocess_failure_details(completed, verbose))
        else:
            base_details.append(
                "Mirror-skills diagnostics suppressed; re-run with --verbose or the lower-level mirror audit for exact names."
            )
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
        f"Command: {shell_command(command, script_agentos_home)}",
        f"Exit code: {completed.returncode}",
        f"AgentOS root audited: {mirror_agentos_home}",
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
    audit_command = mirror_command(script_agentos_home, mirror_agentos_home, primary_agentos_home, mirror_root)
    if any(status in hard_statuses for status in statuses):
        recommendations = [
            "Fix the reported source, readability, or audit-shape errors before syncing mirrors.",
            "Inspect the audit: " + shell_command(audit_command, script_agentos_home),
        ]
        return CheckResult(
            "skill mirrors",
            "FAIL",
            "Mirror-skills audit found source, readability, or output-shape errors.",
            details=details,
            recommendations=recommendations,
        )

    recommendations = [
        "Inspect the audit: " + shell_command(audit_command, script_agentos_home),
    ]
    if statuses.get("missing") or statuses.get("stale"):
        if allow_sync_recommendation:
            sync_command = [*audit_command, "--sync"]
            recommendations.append(
                "After approving current-machine mirror writes: "
                + shell_command(sync_command, script_agentos_home)
            )
        else:
            recommendations.append(
                "Mirror sync recommendation suppressed because this run is auditing a checkout that should not be used for current-machine mirror writes."
            )
            recommendations.append(
                "Re-run from the canonical checkout after merging or pulling this Core change before syncing mirrors."
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


def check_personal_overlay(
    agentos_home: Path,
    primary_agentos_home: Path,
    verbose: bool,
    private_root_is_canonical: bool = True,
) -> CheckResult:
    personal_root = primary_agentos_home / "personal" / "os"
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
            recommendations=private_state_recommendations(
                private_root_is_canonical,
                "Create approved private starter files under personal/os/ using os/playbook/GETTING_STARTED.md.",
            ),
        )

    if not personal_root.is_dir():
        return CheckResult(
            "Personal Overlay",
            "FAIL",
            "Personal Overlay path exists but is not a directory.",
            details=[root_relative(agentos_home, personal_root)],
        )

    existing_starters = [rel for rel in starter_paths if (primary_agentos_home / rel).is_file()]
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
            recommendations=private_state_recommendations(
                private_root_is_canonical,
                "Run a guided first-pass setup using os/playbook/GETTING_STARTED.md.",
                "Ask before writing private state; create only approved files under personal/os/.",
            ),
        )

    return CheckResult(
        "Personal Overlay",
        "PASS",
        "Documented starter Personal Overlay files are present.",
        details=details,
    )


def private_state_recommendations(private_root_is_canonical: bool, *canonical_recommendations: str) -> list[str]:
    if private_root_is_canonical:
        return list(canonical_recommendations)
    return [
        "Re-run with --primary-agentos-home <primary-agentos-home> before creating or updating private AgentOS state from a linked worktree.",
        "Do not write private state into this feature worktree unless it is the canonical AgentOS home.",
    ]


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


def mirror_command(
    script_agentos_home: Path,
    mirror_agentos_home: Path,
    primary_agentos_home: Path,
    mirror_root: Path,
) -> list[str]:
    return [
        sys.executable,
        str(script_agentos_home / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py"),
        "--agentos-root",
        str(mirror_agentos_home),
        "--mirror-root",
        str(mirror_root),
        "--personal-overlay-root",
        str(primary_agentos_home / "personal" / "os"),
    ]


def check_automations(
    agentos_home: Path,
    primary_agentos_home: Path,
    process_home: Path,
    verbose: bool,
    private_root_is_canonical: bool = True,
) -> CheckResult:
    core_registry = agentos_home / "os" / "automations" / "AUTOMATIONS.md"
    personal_automations = primary_agentos_home / "personal" / "os" / "automations"
    personal_registry = personal_automations / "AUTOMATIONS.md"
    codex_automations = process_home / ".codex" / "automations"
    personal_file_count = count_non_gitkeep_files(personal_automations)
    codex_file_count = count_non_gitkeep_files(codex_automations)
    personal_registry_text = read_text_or_empty(personal_registry)
    registry_mentions_checks = text_mentions_agentos_checks(personal_registry_text)
    registry_active_checks = personal_registry_active_agentos_check_evidence(personal_registry_text)
    registry_negative_checks = personal_registry_negative_agentos_check_evidence(personal_registry_text)
    codex_active_checks, codex_negative_checks, codex_possible_checks = codex_automation_evidence(codex_automations)
    negative_check_evidence = registry_negative_checks or codex_negative_checks
    possible_check_evidence = registry_mentions_checks or negative_check_evidence or codex_possible_checks
    recurring_check_evidence = (registry_active_checks or codex_active_checks) and not negative_check_evidence

    details = [
        "Core automation registry: " + ("present" if core_registry.is_file() else "missing"),
        "Personal automation registry: " + ("present" if personal_registry.is_file() else "missing"),
        f"Personal automation files: {personal_file_count}",
        "Codex automation mirror dir: " + presence_with_count(codex_automations),
        "Personal automation mention: " + ("found" if registry_mentions_checks else "not found"),
        "Personal active AgentOS check evidence: " + ("found" if registry_active_checks else "not found"),
        "Personal negative AgentOS check evidence: " + ("found" if registry_negative_checks else "not found"),
        "Codex active AgentOS check evidence: " + ("found" if codex_active_checks else "not found"),
        "Codex negative AgentOS check evidence: " + ("found" if codex_negative_checks else "not found"),
        "Possible AgentOS check mention: " + ("found" if possible_check_evidence else "not found"),
        "Recurring AgentOS check evidence: " + ("active" if recurring_check_evidence else "not found"),
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
            recommendations=private_state_recommendations(
                private_root_is_canonical,
                "If those files are live automations, record the registry in personal/os/automations/AUTOMATIONS.md.",
            ),
        )
    if negative_check_evidence and (registry_active_checks or codex_active_checks):
        return CheckResult(
            "automations",
            "WARN",
            "Conflicting AgentOS automation evidence was found.",
            details=details,
            recommendations=private_state_recommendations(
                private_root_is_canonical,
                "Use the Run AgentOS Doctor skill to compare Personal Overlay automation notes with current Codex automation metadata.",
            ),
        )
    if not recurring_check_evidence:
        if possible_check_evidence:
            return CheckResult(
                "automations",
                "WARN",
                "Possible AgentOS automation mention found, but no active scheduled evidence was detected.",
                details=details,
                recommendations=private_state_recommendations(
                    private_root_is_canonical,
                    "Use the Run AgentOS Doctor skill to inspect automation notes and confirm whether a recurring check is active.",
                ),
            )
        return CheckResult(
            "automations",
            "WARN",
            "No recurring AgentOS update or drift-check automation evidence was found.",
            details=details,
            recommendations=private_state_recommendations(
                private_root_is_canonical,
                "Live automations are optional; if desired, use os/playbook/GETTING_STARTED.md to choose a cadence before creating one.",
            ),
        )

    return CheckResult(
        "automations",
        "PASS",
        "Automation policy is present and recurring check evidence was found.",
        details=details,
    )


def read_text_or_empty(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except OSError:
        return ""
    except UnicodeDecodeError:
        return ""


def text_mentions_agentos_checks(text: str) -> bool:
    lowered = text.lower()
    return "agentos" in lowered and any(term in lowered for term in AUTOMATION_CHECK_TERMS)


def text_has_negative_automation_marker(text: str) -> bool:
    return text_has_marker(text, AUTOMATION_NEGATIVE_MARKERS)


def text_has_negative_automation_prose(text: str) -> bool:
    return text_has_marker(text, AUTOMATION_NEGATIVE_PROSE_MARKERS)


def text_has_marker(text: str, markers: Iterable[str]) -> bool:
    lowered = text.lower()
    for marker in markers:
        if not marker:
            continue
        pattern = rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])"
        if re.search(pattern, lowered):
            return True
    return False


def personal_registry_active_agentos_check_evidence(text: str) -> bool:
    active_section = markdown_section(text, "Active Automations")
    if not active_section:
        return False
    for heading, body in markdown_subsections(active_section):
        entry_marker = "\n".join(
            value
            for value in (heading.strip(), markdown_field_value(body, "Automation id"))
            if value
        )
        entry_text = heading + "\n" + body
        if not text_mentions_agentos_checks(entry_marker):
            continue
        if text_has_negative_automation_marker(entry_marker):
            continue
        if text_has_negative_automation_prose(entry_text):
            continue
        status = markdown_field_value(body, "Status")
        schedule = markdown_field_value(body, "Schedule rule")
        if automation_status_is_active(status) and automation_schedule_is_recurring(schedule):
            return True
    return False


def personal_registry_negative_agentos_check_evidence(text: str) -> bool:
    for section_name in (
        "Active Automations",
        "Candidate Automations",
        "Disabled Automations",
        "Retired Automations",
    ):
        section = markdown_section(text, section_name)
        if not section:
            continue
        for heading, body in markdown_subsections(section):
            entry_marker = "\n".join(
                value
                for value in (heading.strip(), markdown_field_value(body, "Automation id"))
                if value
            )
            entry_text = heading + "\n" + body
            marker_mentions_checks = text_mentions_agentos_checks(entry_marker)
            entry_mentions_checks = text_mentions_agentos_checks(entry_text)
            if not entry_mentions_checks:
                continue
            if not marker_mentions_checks:
                if text_has_negative_automation_prose(entry_text):
                    return True
                continue
            if section_name != "Active Automations":
                return True
            status = markdown_field_value(body, "Status")
            schedule = markdown_field_value(body, "Schedule rule")
            review_mode = markdown_field_value(body, "Review mode")
            if automation_status_is_negative(status):
                return True
            if automation_schedule_is_negative_or_nonrecurring(schedule):
                return True
            if text_has_negative_automation_marker(review_mode):
                return True
            if text_has_negative_automation_prose(entry_text):
                return True
    return False


def markdown_section(text: str, heading: str) -> str:
    match = re.search(rf"(?im)^##\s+{re.escape(heading)}\s*$", text)
    if not match:
        return ""
    next_match = re.search(r"(?m)^##\s+", text[match.end() :])
    if not next_match:
        return text[match.end() :]
    return text[match.end() : match.end() + next_match.start()]


def markdown_subsections(section: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?m)^###\s+(.+?)\s*$", section))
    if not matches:
        return [("", section)]
    entries: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        entries.append((match.group(1), section[match.end() : end]))
    return entries


def markdown_field_value(text: str, field: str) -> str:
    match = re.search(rf"(?im)^\s*{re.escape(field)}\s*:\s*(.*?)\s*$", text)
    if not match:
        return ""
    return match.group(1).strip()


def automation_status_is_active(status: str) -> bool:
    lowered = normalized_marker_text(status)
    return lowered in AUTOMATION_ACTIVE_STATUS_MARKERS


def automation_status_is_negative(status: str) -> bool:
    lowered = normalized_marker_text(status)
    if not lowered:
        return False
    if automation_status_is_active(lowered):
        return False
    return text_has_negative_automation_marker(lowered) or bool(
        re.search(r"\b(no|not|previously|pending)\b", lowered)
    )


def automation_schedule_is_recurring(schedule: str) -> bool:
    lowered = schedule.strip().lower()
    if not lowered:
        return False
    if automation_schedule_is_negative_or_nonrecurring(lowered):
        return False
    return bool(re.search(r"\b(?:rrule:)?freq\s*=\s*(daily|weekly|monthly|yearly|hourly)\b", lowered))


def automation_schedule_is_negative_or_nonrecurring(schedule: str) -> bool:
    lowered = schedule.strip().lower()
    if not lowered:
        return False
    if text_has_negative_automation_marker(lowered):
        return True
    if re.search(r"\b(no|not|pending)\b", lowered):
        return True
    if text_has_marker(lowered, AUTOMATION_NONRECURRING_SCHEDULE_MARKERS):
        return True
    return bool(re.search(r"\b(count|until)\s*=", lowered))


def normalized_marker_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower().strip(".:;"))


def codex_automation_evidence(root: Path) -> tuple[bool, bool, bool]:
    active = False
    negative = False
    possible = False
    if not root.exists() or not root.is_dir():
        return active, negative, possible
    for path in root.rglob("*"):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        text = path.name + "\n" + read_text_or_empty(path)
        if not text_mentions_agentos_checks(text):
            continue
        if path.name == "automation.toml":
            if (
                codex_automation_toml_is_active_scheduled(text)
                and codex_automation_toml_has_active_agentos_marker(text)
            ):
                active = True
            elif codex_automation_toml_has_agentos_marker(text) and (
                codex_automation_toml_has_active_status(text)
                or text_has_negative_automation_prose(text)
            ):
                negative = True
            else:
                possible = True
        elif text_has_negative_automation_prose(text):
            negative = True
        else:
            possible = True
    return active, negative, possible


def codex_automation_toml_is_active_scheduled(text: str) -> bool:
    return bool(
        codex_automation_toml_has_active_status(text)
        and any(
            automation_schedule_is_recurring(value)
            for value in simple_config_field_values(text, ("rrule", "schedule"))
        )
    )


def codex_automation_toml_has_active_status(text: str) -> bool:
    return bool(re.search(r"(?im)^\s*status\s*=\s*[\"']ACTIVE[\"']\s*$", text))


def codex_automation_toml_has_agentos_marker(text: str) -> bool:
    marker = "\n".join(simple_config_field_values(text, ("id", "name", "title")))
    return bool(marker and text_mentions_agentos_checks(marker))


def codex_automation_toml_has_active_agentos_marker(text: str) -> bool:
    marker = "\n".join(simple_config_field_values(text, ("id", "name", "title")))
    return bool(
        marker
        and text_mentions_agentos_checks(marker)
        and not text_has_negative_automation_marker(marker)
        and not text_has_negative_automation_prose(text)
    )


def simple_config_field_values(text: str, fields: Iterable[str]) -> list[str]:
    values: list[str] = []
    for field in fields:
        quoted = re.compile(rf"(?im)^\s*{re.escape(field)}\s*=\s*([\"'])(.*?)\1\s*$")
        for match in quoted.finditer(text):
            values.append(match.group(2))
        unquoted = re.compile(rf"(?im)^\s*{re.escape(field)}\s*=\s*([^#\n]+?)\s*$")
        for match in unquoted.finditer(text):
            raw = match.group(1).strip()
            if raw and not (raw.startswith('"') or raw.startswith("'")):
                values.append(raw)
    return values


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
    if report.primary_agentos_home != report.agentos_home:
        print(f"Primary AgentOS home: {report.primary_agentos_home}")
    if report.setup_agentos_home != report.agentos_home:
        print(f"Current-machine setup home: {report.setup_agentos_home}")
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


def exit_code_for(results: Iterable[CheckResult], strict: bool = False) -> int:
    statuses = {result.status for result in results}
    if "FAIL" in statuses:
        return 2
    if strict and "WARN" in statuses:
        return 1
    return 0


def run_self_tests() -> int:
    tests = [
        test_home_discovery_and_personal_overlay_privacy,
        test_personal_overlay_source_error_warns,
        test_personal_overlay_empty_starter_list_warns,
        test_invalid_home_is_graceful,
        test_adapter_check_uses_temp_home,
        test_relative_adapter_args_resolve_from_invocation_cwd,
        test_relative_adapter_args_preserve_symlink_ancestors,
        test_home_adapter_args_are_preserved,
        test_adapter_check_command_failure_is_not_drift,
        test_adapter_check_preflight_error_is_not_drift,
        test_subprocess_timeout_output_is_text,
        test_mirror_smoke_uses_temp_dirs,
        test_mirror_command_failure_is_not_sync_advice,
        test_mirror_source_failure_is_not_sync_advice,
        test_mirror_failure_suppresses_private_names_without_verbose,
        test_mirror_recommendations_quote_paths,
        test_recommendations_are_cwd_stable,
        test_primary_agentos_home_supplies_private_skill_mirrors,
        test_primary_agentos_home_drives_current_machine_recommendations,
        test_linked_worktree_without_primary_suppresses_writes,
        test_automation_no_evidence_warns,
        test_automation_registry_mention_warns,
        test_personal_active_automation_registry_passes,
        test_personal_disabled_automation_registry_warns,
        test_personal_negative_status_warns,
        test_personal_negative_schedule_warns,
        test_personal_draft_candidate_automation_registry_warns,
        test_personal_one_off_schedule_warns,
        test_personal_bounded_rrule_warns,
        test_personal_prompt_only_agentos_mention_warns,
        test_personal_disabled_registry_conflicts_with_codex_active_warns,
        test_personal_prompt_only_negative_conflicts_with_codex_active_warns,
        test_active_personal_conflicts_with_negative_codex_warns,
        test_active_personal_conflicts_with_bounded_codex_warns,
        test_unrelated_codex_automation_does_not_pass,
        test_disabled_codex_agentos_automation_does_not_pass,
        test_negative_codex_agentos_automation_toml_warns,
        test_codex_manual_schedule_does_not_pass,
        test_codex_negative_schedule_warns,
        test_codex_one_off_schedule_warns,
        test_codex_bounded_rrule_warns,
        test_codex_draft_candidate_automation_toml_warns,
        test_codex_agentos_automation_evidence_passes,
        test_automation_files_without_registry_warns,
        test_primary_agentos_home_supplies_personal_overlay,
        test_primary_overlay_uses_worktree_starter_checklist,
        test_warn_exit_code_is_zero_by_default,
        test_strict_warn_exit_code_is_nonzero,
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
            requested_primary_agentos_home=None,
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
        result = check_personal_overlay(root, root, verbose=False)
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
        result = check_personal_overlay(root, root, verbose=False)
        assert_true(result.status == "WARN", "empty starter checklist should warn")
        assert_true("Could not determine" in result.summary, "empty starter warning summary missing")


def test_invalid_home_is_graceful() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "not-agentos"
        root.mkdir()
        report = run_doctor(
            requested_agentos_home=root,
            requested_primary_agentos_home=None,
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


def test_relative_adapter_args_resolve_from_invocation_cwd() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        invocation = Path(tmp) / "invocation"
        invocation.mkdir()
        args = argparse.Namespace(all_default_adapters=False, adapter=["custom/AGENTS.md"])
        resolved = adapter_args(args, invocation)
        assert_true(resolved == ["--adapter", os.path.abspath(invocation / "custom" / "AGENTS.md")], "relative adapter path was not cwd-resolved")


def test_relative_adapter_args_preserve_symlink_ancestors() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        invocation = Path(tmp) / "invocation"
        linked_target = Path(tmp) / "linked-target"
        make_fake_agentos(root)
        home.mkdir()
        invocation.mkdir()
        linked_target.mkdir()
        symlink = invocation / "linked-adapters"
        symlink.symlink_to(linked_target, target_is_directory=True)

        args = argparse.Namespace(all_default_adapters=False, adapter=["linked-adapters/AGENTS.md"])
        extra_args = adapter_args(args, invocation)
        expected = os.path.abspath(invocation / "linked-adapters" / "AGENTS.md")
        assert_true(extra_args == ["--adapter", expected], "adapter path should stay lexical through symlink ancestors")

        result = check_adapters(
            agentos_home=root,
            process_home=home,
            env=minimal_env(home),
            extra_args=extra_args,
            verbose=True,
        )
        joined = "\n".join(result.details + result.recommendations)
        assert_true(result.status == "FAIL", "symlink ancestor should be reported as a hard adapter failure")
        assert_true("symlink" in joined, "symlink failure should be preserved from installer output")
        assert_true("--no-dry-run" not in joined, "symlink failure should not recommend adapter writes")


def test_home_adapter_args_are_preserved() -> None:
    invocation = Path("agentos-doctor-invocation")
    windows_home_adapter = "<home>" + "\\" + ".openclaw" + "\\" + "AGENTS.md"
    args = argparse.Namespace(
        all_default_adapters=False,
        adapter=["<home>", "<home>/.openclaw/AGENTS.md", windows_home_adapter],
    )
    resolved = adapter_args(args, invocation)
    assert_true(
        resolved
        == [
            "--adapter",
            "<home>",
            "--adapter",
            "<home>/.openclaw/AGENTS.md",
            "--adapter",
            windows_home_adapter,
        ],
        "<home> adapter notation should pass through to installer",
    )


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
        result = check_skill_mirrors(root, root, mirror_root, minimal_env(Path(tmp) / "home"), verbose=False)
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
        result = check_skill_mirrors(root, root, mirror_root, minimal_env(Path(tmp) / "home"), verbose=False)
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
        result = check_skill_mirrors(root, root, mirror_root, minimal_env(Path(tmp) / "home"), verbose=False)
        joined = "\n".join(result.details + result.recommendations)
        assert_true(result.status == "FAIL", "missing canonical source should fail")
        assert_true("source-missing=1" in joined, "source-missing status should be reported")
        assert_true("--sync" not in joined, "source failure should not recommend mirror sync")


def test_mirror_failure_suppresses_private_names_without_verbose() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        mirror_root = Path(tmp) / "mirrors"
        make_fake_agentos(root)
        duplicate = root / "personal" / "os" / "skills" / "example-skill" / "SKILL.md"
        duplicate.parent.mkdir(parents=True)
        duplicate.write_text("# Duplicate Private Skill\n", encoding="utf-8")
        result = check_skill_mirrors(root, root, mirror_root, minimal_env(Path(tmp) / "home"), verbose=False)
        joined = "\n".join(result.details + result.recommendations)
        assert_true(result.status == "FAIL", "mirror command failure should fail")
        assert_true("example-skill" not in joined, "non-verbose mirror diagnostics should not print skill names")
        assert_true("diagnostics suppressed" in joined, "suppression hint should be explicit")


def test_mirror_recommendations_quote_paths() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS With Spaces"
        mirror_root = Path(tmp) / "mirrors with spaces"
        make_fake_agentos(root)
        result = check_skill_mirrors(root, root, mirror_root, minimal_env(Path(tmp) / "home"), verbose=False)
        joined = "\n".join(result.recommendations)
        assert_true(result.status == "WARN", "missing mirrors should warn")
        assert_true("mirrors with spaces'" in joined, "mirror path should be shell quoted")
        assert_true("AgentOS With Spaces'" in joined, "AgentOS path should be shell quoted")


def test_recommendations_are_cwd_stable() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS With Spaces"
        mirror_root = Path(tmp) / "mirrors"
        make_fake_agentos(root)
        write_drift_installer(root)
        adapter_result = check_adapters(
            agentos_home=root,
            process_home=Path(tmp) / "home",
            env=minimal_env(Path(tmp) / "home"),
            extra_args=[],
            verbose=False,
        )
        mirror_result = check_skill_mirrors(root, root, mirror_root, minimal_env(Path(tmp) / "home"), verbose=False)
        joined = "\n".join(adapter_result.recommendations + mirror_result.recommendations)
        assert_true(str(root / "scripts" / "install_global_agent_instructions.py") in joined, "adapter recommendation should use an absolute script path")
        assert_true(str(root / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py") in joined, "mirror recommendation should use an absolute script path")
        assert_true("python3 scripts/install_global_agent_instructions.py" not in joined, "adapter recommendation should not depend on caller cwd")
        assert_true("python3 os/skills/mirror-skills/scripts/mirror_skills.py" not in joined, "mirror recommendation should not depend on caller cwd")


def test_primary_agentos_home_supplies_private_skill_mirrors() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        worktree = Path(tmp) / "worktree"
        primary = Path(tmp) / "primary"
        mirror_root = Path(tmp) / "mirrors"
        make_fake_agentos(worktree)
        make_fake_agentos(primary)
        result = check_skill_mirrors(worktree, primary, mirror_root, minimal_env(Path(tmp) / "home"), verbose=False)
        joined = "\n".join(result.details)
        assert_true("personal-overlay=1" in joined, "primary Personal Overlay skill was not audited")


def test_primary_agentos_home_drives_current_machine_recommendations() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        worktree = Path(tmp) / "worktree"
        primary = Path(tmp) / "primary"
        mirror_root = Path(tmp) / "mirrors"
        make_fake_agentos(worktree)
        make_fake_agentos(primary)
        write_drift_installer(primary)
        report = run_doctor(
            requested_agentos_home=worktree,
            requested_primary_agentos_home=primary,
            cwd=worktree,
            mirror_root=mirror_root,
            verbose=False,
            process_home=Path(tmp) / "home",
            env=minimal_env(Path(tmp) / "home"),
        )
        adapter_result = result_named(report, "adapter drift")
        mirror_result = result_named(report, "skill mirrors")
        adapter_text = "\n".join(adapter_result.details + adapter_result.recommendations)
        mirror_text = "\n".join(mirror_result.details + mirror_result.recommendations)
        assert_true(report.setup_agentos_home == primary.resolve(), "primary home should drive current-machine setup checks")
        assert_true(str(primary.resolve()) in adapter_text, "adapter recommendations should target primary home")
        assert_true(str(worktree.resolve()) not in adapter_text, "adapter recommendations should not target feature worktree")
        assert_true(f"--agentos-root {worktree.resolve()}" in mirror_text, "mirror audit should use the current Core checkout")
        assert_true(f"--personal-overlay-root {primary.resolve() / 'personal' / 'os'}" in mirror_text, "mirror audit should use the primary Personal Overlay")
        assert_true("--sync" not in mirror_text, "mirror recommendations should not sync from feature worktree")


def test_linked_worktree_without_primary_suppresses_writes() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        worktree = Path(tmp) / "worktree"
        mirror_root = Path(tmp) / "mirrors"
        make_fake_agentos(worktree)
        make_linked_worktree_marker(worktree)
        write_drift_installer(worktree)
        report = run_doctor(
            requested_agentos_home=worktree,
            requested_primary_agentos_home=None,
            cwd=worktree,
            mirror_root=mirror_root,
            verbose=False,
            process_home=Path(tmp) / "home",
            env=minimal_env(Path(tmp) / "home"),
        )
        worktree_result = result_named(report, "worktree mode")
        adapter_result = result_named(report, "adapter drift")
        mirror_result = result_named(report, "skill mirrors")
        overlay_result = result_named(report, "Personal Overlay")
        automation_result = result_named(report, "automations")
        joined = "\n".join(
            worktree_result.recommendations
            + adapter_result.recommendations
            + mirror_result.recommendations
            + overlay_result.recommendations
            + automation_result.recommendations
        )
        assert_true(worktree_result.status == "WARN", "linked worktree without primary should be explicit")
        assert_true("--no-dry-run" not in joined, "adapter write command should be suppressed")
        assert_true("--sync" not in joined, "mirror sync command should be suppressed")
        assert_true("--primary-agentos-home" in joined, "recommendations should ask for primary home")
        assert_true("Do not write private state into this feature worktree" in joined, "private writes should be discouraged")


def test_automation_no_evidence_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        result = check_automations(root, root, Path(tmp) / "home", verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "missing recurring check evidence should warn")
        assert_true("Recurring AgentOS check evidence: not found" in joined, "missing evidence should be explicit")


def test_automation_registry_mention_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        registry = root / "personal" / "os" / "automations" / "AUTOMATIONS.md"
        registry.write_text("AgentOS repository update and adapter drift check automation.\n", encoding="utf-8")
        result = check_automations(root, root, Path(tmp) / "home", verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "registry prose should not be treated as deterministic active evidence")
        assert_true("Personal automation mention: found" in joined, "registry mention should remain visible")
        assert_true("Recurring AgentOS check evidence: not found" in joined, "ambiguous registry prose should not pass")


def test_personal_active_automation_registry_passes() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        registry = root / "personal" / "os" / "automations" / "AUTOMATIONS.md"
        registry.write_text(
            """# Automations

## Active Automations

### Weekly AgentOS Review

Automation id: weekly-agentos-review

Status: Active

Schedule rule: RRULE:FREQ=WEEKLY

Invocation prompt:

```text
Run the AgentOS weekly review workflow.
```

## Candidate Automations

### Candidate Weather Digest

Status: Candidate
""",
            encoding="utf-8",
        )
        result = check_automations(root, root, Path(tmp) / "home", verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "PASS", "documented active Personal Overlay automation should pass")
        assert_true("Personal active AgentOS check evidence: found" in joined, "active personal evidence should be explicit")


def test_personal_disabled_automation_registry_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        registry = root / "personal" / "os" / "automations" / "AUTOMATIONS.md"
        registry.write_text(
            """# Automations

## Active Automations

### Retired AgentOS Repository Update

Automation id: retired-agentos-update

Status: Disabled

Schedule rule: RRULE:FREQ=WEEKLY

Invocation prompt:

```text
Do not run AgentOS repository update automation.
```
""",
            encoding="utf-8",
        )
        result = check_automations(root, root, Path(tmp) / "home", verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "disabled Personal Overlay automation should not pass")
        assert_true("Personal automation mention: found" in joined, "disabled registry mention should remain visible")
        assert_true("Personal active AgentOS check evidence: not found" in joined, "disabled personal evidence should not be active")
        assert_true("Recurring AgentOS check evidence: not found" in joined, "disabled personal evidence should not be recurring")


def test_personal_negative_status_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        registry = root / "personal" / "os" / "automations" / "AUTOMATIONS.md"
        registry.write_text(
            """# Automations

## Active Automations

### Weekly AgentOS Doctor

Automation id: weekly-agentos-doctor

Status: not enabled

Schedule rule: RRULE:FREQ=WEEKLY
""",
            encoding="utf-8",
        )
        result = check_automations(root, root, Path(tmp) / "home", verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "negative Personal Overlay status should not pass")
        assert_true("Personal negative AgentOS check evidence: found" in joined, "negative personal status should be explicit")
        assert_true("Recurring AgentOS check evidence: not found" in joined, "negative personal status should not be recurring")


def test_personal_negative_schedule_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        registry = root / "personal" / "os" / "automations" / "AUTOMATIONS.md"
        registry.write_text(
            """# Automations

## Active Automations

### Weekly AgentOS Doctor

Automation id: weekly-agentos-doctor

Status: Active

Schedule rule: no weekly schedule yet
""",
            encoding="utf-8",
        )
        result = check_automations(root, root, Path(tmp) / "home", verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "negative Personal Overlay schedule should not pass")
        assert_true("Personal negative AgentOS check evidence: found" in joined, "negative personal schedule should be explicit")
        assert_true("Recurring AgentOS check evidence: not found" in joined, "negative personal schedule should not be recurring")


def test_personal_draft_candidate_automation_registry_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        registry = root / "personal" / "os" / "automations" / "AUTOMATIONS.md"
        registry.write_text(
            """# Automations

## Active Automations

### Weekly AgentOS Doctor

Automation id: weekly-agentos-doctor

Status: Active

Schedule rule: RRULE:FREQ=WEEKLY

Invocation prompt:

```text
Draft-only candidate AgentOS doctor rollout.
```
""",
            encoding="utf-8",
        )
        result = check_automations(root, root, Path(tmp) / "home", verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "draft candidate Personal Overlay automation should not pass")
        assert_true("Personal automation mention: found" in joined, "draft candidate mention should remain visible")
        assert_true("Personal active AgentOS check evidence: not found" in joined, "draft candidate personal evidence should not be active")


def test_personal_one_off_schedule_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        registry = root / "personal" / "os" / "automations" / "AUTOMATIONS.md"
        registry.write_text(
            """# Automations

## Active Automations

### Weekly AgentOS Doctor

Automation id: weekly-agentos-doctor

Status: Active

Schedule rule: once on 2026-05-22

Invocation prompt:

```text
Run AgentOS Doctor.
```
""",
            encoding="utf-8",
        )
        result = check_automations(root, root, Path(tmp) / "home", verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "one-off Personal Overlay schedule should not pass")
        assert_true("Personal automation mention: found" in joined, "one-off personal mention should remain visible")
        assert_true("Personal active AgentOS check evidence: not found" in joined, "one-off personal schedule should not be active")


def test_personal_bounded_rrule_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        registry = root / "personal" / "os" / "automations" / "AUTOMATIONS.md"
        registry.write_text(
            """# Automations

## Active Automations

### Weekly AgentOS Doctor

Automation id: weekly-agentos-doctor

Status: Active

Schedule rule: RRULE:FREQ=WEEKLY;COUNT = 1

Invocation prompt:

```text
Run AgentOS Doctor.
```
""",
            encoding="utf-8",
        )
        result = check_automations(root, root, Path(tmp) / "home", verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "bounded Personal Overlay RRULE should not pass")
        assert_true("Personal automation mention: found" in joined, "bounded RRULE mention should remain visible")
        assert_true("Personal active AgentOS check evidence: not found" in joined, "bounded personal RRULE should not be active")


def test_personal_prompt_only_agentos_mention_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        registry = root / "personal" / "os" / "automations" / "AUTOMATIONS.md"
        registry.write_text(
            """# Automations

## Active Automations

### Weekly Repository Check

Automation id: weekly-repository-check

Status: Active

Schedule rule: RRULE:FREQ=WEEKLY

Invocation prompt:

```text
Run AgentOS Doctor.
```
""",
            encoding="utf-8",
        )
        result = check_automations(root, root, Path(tmp) / "home", verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "prompt-only Personal Overlay AgentOS mention should not pass")
        assert_true("Personal automation mention: found" in joined, "prompt-only mention should remain possible evidence")
        assert_true("Personal active AgentOS check evidence: not found" in joined, "prompt-only mention should not be active evidence")


def test_personal_disabled_registry_conflicts_with_codex_active_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        registry = root / "personal" / "os" / "automations" / "AUTOMATIONS.md"
        registry.write_text(
            """# Automations

## Active Automations

### Weekly AgentOS Doctor

Automation id: weekly-agentos-doctor

Status: Disabled

Schedule rule: RRULE:FREQ=WEEKLY
""",
            encoding="utf-8",
        )
        codex_automation = home / ".codex" / "automations" / "agentos-doctor" / "automation.toml"
        codex_automation.parent.mkdir(parents=True)
        codex_automation.write_text(
            'name = "AgentOS doctor health check"\n'
            'status = "ACTIVE"\n'
            'rrule = "RRULE:FREQ=WEEKLY"\n',
            encoding="utf-8",
        )
        result = check_automations(root, root, home, verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "disabled Personal Overlay registry should conflict with active Codex evidence")
        assert_true("Conflicting AgentOS automation evidence" in result.summary, "conflict warning should be explicit")
        assert_true("Codex active AgentOS check evidence: found" in joined, "codex active evidence should remain visible")
        assert_true("Recurring AgentOS check evidence: not found" in joined, "conflicting evidence should not pass as recurring")


def test_personal_prompt_only_negative_conflicts_with_codex_active_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        registry = root / "personal" / "os" / "automations" / "AUTOMATIONS.md"
        registry.write_text(
            """# Automations

## Active Automations

### Weekly Repository Check

Automation id: weekly-repository-check

Status: Active

Schedule rule: RRULE:FREQ=WEEKLY

Invocation prompt:

```text
Do not run AgentOS Doctor.
```
""",
            encoding="utf-8",
        )
        codex_automation = home / ".codex" / "automations" / "agentos-doctor" / "automation.toml"
        codex_automation.parent.mkdir(parents=True)
        codex_automation.write_text(
            'name = "AgentOS doctor health check"\n'
            'status = "ACTIVE"\n'
            'rrule = "RRULE:FREQ=WEEKLY"\n',
            encoding="utf-8",
        )
        result = check_automations(root, root, home, verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "prompt-only negative Personal Overlay prose should conflict with active Codex evidence")
        assert_true("Personal negative AgentOS check evidence: found" in joined, "prompt-only negative evidence should be explicit")
        assert_true("Recurring AgentOS check evidence: not found" in joined, "prompt-only conflict should not pass as recurring")


def test_active_personal_conflicts_with_negative_codex_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        registry = root / "personal" / "os" / "automations" / "AUTOMATIONS.md"
        registry.write_text(
            """# Automations

## Active Automations

### Weekly AgentOS Doctor

Automation id: weekly-agentos-doctor

Status: Active

Schedule rule: RRULE:FREQ=WEEKLY
""",
            encoding="utf-8",
        )
        codex_automation = home / ".codex" / "automations" / "agentos-doctor" / "automation.toml"
        codex_automation.parent.mkdir(parents=True)
        codex_automation.write_text(
            'name = "AgentOS doctor health check"\n'
            'prompt = "Do not run AgentOS Doctor."\n'
            'status = "ACTIVE"\n'
            'rrule = "RRULE:FREQ=WEEKLY"\n',
            encoding="utf-8",
        )
        result = check_automations(root, root, home, verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "negative Codex metadata should conflict with active Personal Overlay evidence")
        assert_true("Codex negative AgentOS check evidence: found" in joined, "negative Codex evidence should be explicit")
        assert_true("Recurring AgentOS check evidence: not found" in joined, "Codex conflict should not pass as recurring")


def test_active_personal_conflicts_with_bounded_codex_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        registry = root / "personal" / "os" / "automations" / "AUTOMATIONS.md"
        registry.write_text(
            """# Automations

## Active Automations

### Weekly AgentOS Doctor

Automation id: weekly-agentos-doctor

Status: Active

Schedule rule: RRULE:FREQ=WEEKLY
""",
            encoding="utf-8",
        )
        codex_automation = home / ".codex" / "automations" / "agentos-doctor" / "automation.toml"
        codex_automation.parent.mkdir(parents=True)
        codex_automation.write_text(
            'name = "AgentOS doctor health check"\n'
            'status = "ACTIVE"\n'
            'rrule = "RRULE:FREQ=WEEKLY;COUNT = 1"\n',
            encoding="utf-8",
        )
        result = check_automations(root, root, home, verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "bounded Codex metadata should conflict with active Personal Overlay evidence")
        assert_true("Codex negative AgentOS check evidence: found" in joined, "bounded Codex evidence should be explicit")
        assert_true("Recurring AgentOS check evidence: not found" in joined, "bounded Codex conflict should not pass as recurring")


def test_unrelated_codex_automation_does_not_pass() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        codex_automation = home / ".codex" / "automations" / "daily-weather.txt"
        codex_automation.parent.mkdir(parents=True)
        codex_automation.write_text("Daily weather reminder.\n", encoding="utf-8")
        result = check_automations(root, root, home, verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "unrelated Codex automation should not pass")
        assert_true("Codex automation mirror dir: present (1 files)" in joined, "Codex presence should remain visible")
        assert_true("Codex active AgentOS check evidence: not found" in joined, "unrelated Codex file should not be evidence")


def test_disabled_codex_agentos_automation_does_not_pass() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        codex_automation = home / ".codex" / "automations" / "disabled-note.md"
        codex_automation.parent.mkdir(parents=True)
        codex_automation.write_text("Do not run AgentOS repository update automation.\n", encoding="utf-8")
        result = check_automations(root, root, home, verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "disabled prose note should not pass")
        assert_true("Possible AgentOS check mention: found" in joined, "possible mention should remain visible")
        assert_true("Recurring AgentOS check evidence: not found" in joined, "disabled prose should not be active evidence")


def test_negative_codex_agentos_automation_toml_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        codex_automation = home / ".codex" / "automations" / "disabled-agentos-note" / "automation.toml"
        codex_automation.parent.mkdir(parents=True)
        codex_automation.write_text(
            'name = "AgentOS repository update automation"\n'
            'prompt = "Do not run this AgentOS repository update automation."\n'
            'status = "ACTIVE"\n'
            'rrule = "RRULE:FREQ=WEEKLY"\n',
            encoding="utf-8",
        )
        result = check_automations(root, root, home, verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "negative active Codex TOML should not pass")
        assert_true("Possible AgentOS check mention: found" in joined, "negative TOML should remain possible evidence")
        assert_true("Codex active AgentOS check evidence: not found" in joined, "negative TOML should not be active evidence")
        assert_true("Recurring AgentOS check evidence: not found" in joined, "negative TOML should not be recurring")


def test_codex_manual_schedule_does_not_pass() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        codex_automation = home / ".codex" / "automations" / "manual-agentos-doctor" / "automation.toml"
        codex_automation.parent.mkdir(parents=True)
        codex_automation.write_text(
            'name = "AgentOS doctor health check"\n'
            'prompt = "Run AgentOS Doctor."\n'
            'status = "ACTIVE"\n'
            'schedule = "manual"\n',
            encoding="utf-8",
        )
        result = check_automations(root, root, home, verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "manual Codex schedule should not pass as recurring")
        assert_true("Possible AgentOS check mention: found" in joined, "manual schedule should remain possible evidence")
        assert_true("Codex active AgentOS check evidence: not found" in joined, "manual schedule should not be active evidence")


def test_codex_negative_schedule_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        codex_automation = home / ".codex" / "automations" / "pending-agentos-doctor" / "automation.toml"
        codex_automation.parent.mkdir(parents=True)
        codex_automation.write_text(
            'name = "AgentOS doctor health check"\n'
            'prompt = "Run AgentOS Doctor."\n'
            'status = "ACTIVE"\n'
            'schedule = "no weekly schedule yet"\n',
            encoding="utf-8",
        )
        result = check_automations(root, root, home, verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "negative Codex schedule should not pass")
        assert_true("Possible AgentOS check mention: found" in joined, "negative Codex schedule should remain possible evidence")
        assert_true("Codex active AgentOS check evidence: not found" in joined, "negative Codex schedule should not be active evidence")


def test_codex_one_off_schedule_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        codex_automation = home / ".codex" / "automations" / "one-off-agentos-doctor" / "automation.toml"
        codex_automation.parent.mkdir(parents=True)
        codex_automation.write_text(
            'name = "AgentOS doctor health check"\n'
            'prompt = "Run AgentOS Doctor."\n'
            'status = "ACTIVE"\n'
            'schedule = "once on 2026-05-22"\n',
            encoding="utf-8",
        )
        result = check_automations(root, root, home, verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "one-off Codex schedule should not pass as recurring")
        assert_true("Possible AgentOS check mention: found" in joined, "one-off schedule should remain possible evidence")
        assert_true("Codex active AgentOS check evidence: not found" in joined, "one-off schedule should not be active evidence")


def test_codex_bounded_rrule_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        codex_automation = home / ".codex" / "automations" / "bounded-agentos-doctor" / "automation.toml"
        codex_automation.parent.mkdir(parents=True)
        codex_automation.write_text(
            'name = "AgentOS doctor health check"\n'
            'prompt = "Run AgentOS Doctor."\n'
            'status = "ACTIVE"\n'
            'rrule = "RRULE:FREQ=WEEKLY;UNTIL = 20260522T000000Z"\n',
            encoding="utf-8",
        )
        result = check_automations(root, root, home, verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "bounded Codex RRULE should not pass as recurring")
        assert_true("Possible AgentOS check mention: found" in joined, "bounded RRULE should remain possible evidence")
        assert_true("Codex active AgentOS check evidence: not found" in joined, "bounded RRULE should not be active evidence")


def test_codex_draft_candidate_automation_toml_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        codex_automation = home / ".codex" / "automations" / "draft-agentos-doctor" / "automation.toml"
        codex_automation.parent.mkdir(parents=True)
        codex_automation.write_text(
            'name = "AgentOS doctor health check"\n'
            'prompt = "Run AgentOS doctor in draft-only mode."\n'
            'status = "ACTIVE"\n'
            'rrule = "RRULE:FREQ=WEEKLY"\n',
            encoding="utf-8",
        )
        result = check_automations(root, root, home, verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "draft candidate Codex TOML should not pass")
        assert_true("Possible AgentOS check mention: found" in joined, "draft candidate TOML should remain possible evidence")
        assert_true("Codex active AgentOS check evidence: not found" in joined, "draft candidate TOML should not be active evidence")


def test_codex_agentos_automation_evidence_passes() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        codex_automation = home / ".codex" / "automations" / "agentos-drift-check" / "automation.toml"
        codex_automation.parent.mkdir(parents=True)
        codex_automation.write_text(
            'name = "AgentOS drift check"\n'
            'prompt = "Check AgentOS repository updates and adapter drift."\n'
            'status = "ACTIVE"\n'
            'rrule = "RRULE:FREQ=WEEKLY"\n',
            encoding="utf-8",
        )
        result = check_automations(root, root, home, verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "PASS", "active scheduled Codex automation evidence should pass")
        assert_true("Codex active AgentOS check evidence: found" in joined, "Codex evidence should be explicit")


def test_automation_files_without_registry_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        (root / "personal" / "os" / "automations" / "drift-check.md").write_text(
            "AgentOS drift check draft.\n",
            encoding="utf-8",
        )
        result = check_automations(root, root, Path(tmp) / "home", verbose=False)
        assert_true(result.status == "WARN", "automation files without registry should warn")
        assert_true("registry" in result.summary, "warning should mention missing registry")


def test_primary_agentos_home_supplies_personal_overlay() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        worktree = Path(tmp) / "worktree"
        primary = Path(tmp) / "primary"
        make_fake_agentos(worktree)
        make_fake_agentos(primary)
        for rel in ("personal/os/identity/USER.md", "personal/os/identity/COMMUNICATION.md"):
            path = primary / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# private starter\n", encoding="utf-8")
        result = check_personal_overlay(worktree, primary, verbose=False)
        assert_true(result.status == "PASS", "primary Personal Overlay starter files should be used")
        report = run_doctor(
            requested_agentos_home=worktree,
            requested_primary_agentos_home=primary,
            cwd=worktree,
            mirror_root=Path(tmp) / "mirrors",
            verbose=False,
            process_home=Path(tmp) / "home",
            env=minimal_env(Path(tmp) / "home"),
        )
        assert_true(report.agentos_home == worktree.resolve(), "worktree should remain Core home")
        assert_true(report.primary_agentos_home == primary.resolve(), "primary home should be recorded")


def test_primary_overlay_uses_worktree_starter_checklist() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        worktree = Path(tmp) / "worktree"
        primary = Path(tmp) / "primary"
        make_fake_agentos(worktree)
        make_fake_agentos(primary)
        (worktree / "os" / "playbook" / "GETTING_STARTED.md").write_text(
            """# Getting Started

## Starter Files

- `personal/os/identity/USER.md`: durable identity.
- `personal/os/identity/COMMUNICATION.md`: communication.
- `personal/os/context/SOURCE_MAP.md`: source map.
""",
            encoding="utf-8",
        )
        for rel in ("personal/os/identity/USER.md", "personal/os/identity/COMMUNICATION.md"):
            path = primary / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# private starter\n", encoding="utf-8")
        result = check_personal_overlay(worktree, primary, verbose=False)
        joined = "\n".join(result.details)
        assert_true(result.status == "WARN", "worktree checklist missing primary file should warn")
        assert_true("personal/os/context/SOURCE_MAP.md" in joined, "worktree starter path should be audited")


def test_warn_exit_code_is_zero_by_default() -> None:
    results = [CheckResult("example", "WARN", "advisory gap")]
    assert_true(exit_code_for(results) == 0, "WARN should be advisory by default")


def test_strict_warn_exit_code_is_nonzero() -> None:
    results = [CheckResult("example", "WARN", "advisory gap")]
    assert_true(exit_code_for(results, strict=True) == 1, "strict WARN should be nonzero")


def render_report_for_test(report: DoctorReport, verbose: bool) -> str:
    lines = [
        "AgentOS doctor (read-only)",
        f"AgentOS home: {report.agentos_home}",
        f"Primary AgentOS home: {report.primary_agentos_home}",
        f"Current-machine setup home: {report.setup_agentos_home}",
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


def write_drift_installer(root: Path) -> None:
    installer = root / "scripts" / "install_global_agent_instructions.py"
    installer.write_text(
        "import sys\nprint('[FAIL] drift codex - stale managed block')\nsys.exit(1)\n",
        encoding="utf-8",
    )


def make_linked_worktree_marker(root: Path) -> None:
    (root / ".git").write_text(
        f"gitdir: {root.parent / '.git' / 'worktrees' / root.name}\n",
        encoding="utf-8",
    )


def result_named(report: DoctorReport, name: str) -> CheckResult:
    for result in report.results:
        if result.name == name:
            return result
    raise AssertionError(f"missing result named {name}")


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
