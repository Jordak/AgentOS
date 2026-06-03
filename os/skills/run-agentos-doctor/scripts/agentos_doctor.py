#!/usr/bin/env python3
"""Thin, read-only AgentOS setup fact collector."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
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
KNOWN_INSTALLED_ADAPTER_SMOKE_HARNESSES = ("codex",)
SMOKE_STARTER_FILES = (
    "AGENTS.md",
    "os/INDEX.md",
    "os/playbook/PERSONAL_OVERLAY.md",
)
SMOKE_FORBIDDEN_OUTPUT_PATTERNS = (
    "personal/os/",
    "personal\\os\\",
    "os/verification/",
    "os\\verification\\",
    "fixtures.json",
    "judge_prompt",
    "judge_response",
    "answer key",
)
SMOKE_FORBIDDEN_PROMPT_PATTERNS = (
    "personal/os/",
    "personal\\os\\",
    "os/verification/",
    "os\\verification\\",
    "fixtures.json",
    "judge_prompt",
    "judge_response",
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
        "--installed-adapter-smoke",
        action="append",
        default=[],
        metavar="HARNESS",
        choices=[*KNOWN_INSTALLED_ADAPTER_SMOKE_HARNESSES, "all"],
        help="Plan an installed global adapter smoke check for a harness. Real harness execution requires --run-installed-adapter-smoke.",
    )
    parser.add_argument(
        "--run-installed-adapter-smoke",
        action="store_true",
        help="Actually run requested installed adapter smoke checks. May invoke local harnesses and model/auth paths.",
    )
    parser.add_argument(
        "--installed-adapter-smoke-timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        metavar="SECONDS",
        help="Timeout for each real installed adapter smoke check.",
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
            or args.installed_adapter_smoke
            or args.run_installed_adapter_smoke
            or args.installed_adapter_smoke_timeout != DEFAULT_TIMEOUT_SECONDS
            or args.verbose
            or args.strict
        ):
            print("error: --self-test cannot be combined with other options", file=sys.stderr)
            return 2
        return run_self_tests()
    if args.run_installed_adapter_smoke and not args.installed_adapter_smoke:
        print("error: --run-installed-adapter-smoke requires --installed-adapter-smoke HARNESS", file=sys.stderr)
        return 2

    cwd = Path.cwd()
    report = run_doctor(
        requested_agentos_home=args.agentos_home,
        requested_primary_agentos_home=args.primary_agentos_home,
        cwd=cwd,
        process_home=Path.home(),
        env=os.environ,
        adapter_args=adapter_args(args, cwd),
        verbose=args.verbose,
        smoke_harnesses=installed_adapter_smoke_harnesses(args.installed_adapter_smoke),
        run_installed_adapter_smoke=args.run_installed_adapter_smoke,
        smoke_timeout_seconds=args.installed_adapter_smoke_timeout,
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


def installed_adapter_smoke_harnesses(raw_harnesses: Iterable[str]) -> list[str]:
    selected: list[str] = []
    for harness in raw_harnesses:
        if harness == "all":
            for known in KNOWN_INSTALLED_ADAPTER_SMOKE_HARNESSES:
                if known not in selected:
                    selected.append(known)
            continue
        if harness not in KNOWN_INSTALLED_ADAPTER_SMOKE_HARNESSES:
            raise ValueError(f"unsupported installed adapter smoke harness: {harness}")
        if harness not in selected:
            selected.append(harness)
    return selected


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
    smoke_harnesses: list[str] | None = None,
    run_installed_adapter_smoke: bool = False,
    smoke_timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> DoctorReport:
    agentos_home, discovery = resolve_agentos_home(requested_agentos_home, cwd)
    primary_agentos_home = absolute_path(requested_primary_agentos_home, cwd) if requested_primary_agentos_home else agentos_home
    home_structure = check_required_core_files(agentos_home)
    split_roots = agentos_home != primary_agentos_home
    primary_home_structure = check_primary_agentos_home(primary_agentos_home) if split_roots else None
    primary_home_trusted = primary_home_structure is None or primary_home_structure.status == "PASS"
    smoke_agentos_home = primary_agentos_home if primary_home_trusted else agentos_home
    smoke_agentos_home_label = "primary AgentOS home" if primary_home_trusted and split_roots else "AgentOS home"

    results = [
        discovery,
        home_structure,
    ]
    if primary_home_structure is not None:
        results.append(primary_home_structure)
    if home_structure.status == "PASS":
        results.extend(
            [
                check_adapters(
                    agentos_home,
                    env,
                    adapter_args,
                    verbose,
                    primary_agentos_home=primary_agentos_home if primary_home_trusted else None,
                    omit_current_machine_write_guidance=split_roots,
                ),
            ]
        )
        for harness in smoke_harnesses or []:
            results.append(
                check_installed_adapter_smoke(
                    harness,
                    smoke_agentos_home,
                    smoke_agentos_home_label,
                    env,
                    run_smoke=run_installed_adapter_smoke,
                    timeout_seconds=smoke_timeout_seconds,
                )
            )
    else:
        results.extend(
            [
                skipped_subprocess_check("adapter drift", home_structure),
            ]
        )
        for harness in smoke_harnesses or []:
            results.append(skipped_subprocess_check(f"installed adapter smoke ({harness})", home_structure))
    results.extend(
        [
            check_automation_locations(
                agentos_home,
                primary_agentos_home,
                process_home,
                env,
                primary_home_trusted=primary_home_trusted,
            ),
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


def check_primary_agentos_home(primary_agentos_home: Path) -> CheckResult:
    root_problem = agentos_root_problem(primary_agentos_home)
    if root_problem:
        return CheckResult(
            "primary home structure",
            "WARN",
            "Primary AgentOS home is not trusted; Personal Overlay evidence is unknown.",
            details=[
                f"Primary AgentOS home: {primary_agentos_home}",
                f"Observed state: {root_problem}",
            ],
            recommendations=[
                "Fix --primary-agentos-home before interpreting Personal Overlay evidence."
            ],
        )

    required = check_required_core_files(primary_agentos_home)
    details = [
        f"Primary AgentOS home: {primary_agentos_home}",
        *required.details,
    ]
    if required.status != "PASS":
        return CheckResult(
            "primary home structure",
            "WARN",
            "Primary AgentOS home is not trusted; Personal Overlay evidence is unknown.",
            details=details,
            recommendations=[
                "Fix --primary-agentos-home before interpreting Personal Overlay evidence."
            ],
        )
    return CheckResult(
        "primary home structure",
        "PASS",
        "Primary AgentOS home is trusted for Personal Overlay evidence.",
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


def check_installed_adapter_smoke(
    harness: str,
    expected_agentos_home: Path,
    expected_agentos_home_label: str,
    env: Mapping[str, str],
    run_smoke: bool,
    timeout_seconds: int,
) -> CheckResult:
    if harness != "codex":
        return CheckResult(
            f"installed adapter smoke ({harness})",
            "WARN",
            "Installed adapter smoke harness is not implemented.",
            details=[f"Harness: {harness}"],
        )

    prompt = installed_adapter_smoke_prompt()
    command = codex_smoke_command(Path("<external-project>"), Path("<last-message>"))
    privacy_errors = smoke_privacy_errors(prompt, command, expected_agentos_home)
    details = [
        "Harness: codex",
        f"Mode: {'real smoke' if run_smoke else 'dry-run plan'}",
        f"Comparison target: {expected_agentos_home_label}",
        "Expected AgentOS path is hidden from the smoke prompt.",
        "Expected starter files: " + ", ".join(SMOKE_STARTER_FILES),
        "Command shape: " + shell_command(command),
    ]
    if privacy_errors:
        return CheckResult(
            "installed adapter smoke (codex)",
            "FAIL",
            "Smoke prompt or command shape violates privacy guardrails.",
            details=[*details, *[f"Privacy guard: {error}" for error in privacy_errors]],
        )

    if not run_smoke:
        return CheckResult(
            "installed adapter smoke (codex)",
            "WARN",
            "Dry-run only; real harness smoke was not executed.",
            details=details,
            recommendations=[
                "Run again with --run-installed-adapter-smoke only after approving a real Codex harness/model-call diagnostic.",
            ],
        )

    if shutil.which("codex") is None:
        return CheckResult(
            "installed adapter smoke (codex)",
            "WARN",
            "Codex executable is not available.",
            details=details,
        )

    smoke = run_codex_installed_adapter_smoke(expected_agentos_home, prompt, env, timeout_seconds)
    return classify_smoke_output("codex", expected_agentos_home, smoke, details)


def installed_adapter_smoke_prompt() -> str:
    return (
        "Report any AgentOS installation path and the initial AgentOS files named by your active instructions. "
        "Use only active instructions and public AgentOS Core guidance if needed. "
        "Do not inspect private user files, benchmark materials, generated reports, or other non-Core files. "
        "Return a concise answer."
    )


def codex_smoke_command(project_root: Path, output_path: Path) -> list[str]:
    return [
        "codex",
        "exec",
        "--cd",
        str(project_root),
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--ephemeral",
        "--color",
        "never",
        "--output-last-message",
        str(output_path),
        "-",
    ]


@dataclass
class SmokeRun:
    command: list[str]
    exit_code: int
    output: str
    output_error: str | None = None
    timed_out: bool = False


def run_codex_installed_adapter_smoke(
    expected_agentos_home: Path,
    prompt: str,
    env: Mapping[str, str],
    timeout_seconds: int,
) -> SmokeRun:
    del expected_agentos_home  # The expected path must stay out of the harness prompt and argv.
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-installed-adapter-") as tmp:
        project_root = Path(tmp) / "external-project"
        project_root.mkdir()
        output_path = Path(tmp) / "last-message.txt"
        command = codex_smoke_command(project_root, output_path)
        try:
            completed = subprocess.run(
                command,
                cwd=project_root,
                env={**dict(env), "GIT_TERMINAL_PROMPT": "0"},
                input=prompt,
                text=True,
                errors="replace",
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return SmokeRun(command=command, exit_code=124, output="", output_error=None, timed_out=True)
        except OSError as exc:
            return SmokeRun(command=command, exit_code=127, output="", output_error=str(exc))

        try:
            output = output_path.read_text(encoding="utf-8", errors="replace") if output_path.is_file() else ""
        except OSError as exc:
            output = ""
            output_error = exc.__class__.__name__
        else:
            output_error = None
        return SmokeRun(command=command, exit_code=completed.returncode, output=output, output_error=output_error)


def classify_smoke_output(
    harness: str,
    expected_agentos_home: Path,
    smoke: SmokeRun,
    base_details: list[str],
) -> CheckResult:
    observed = parse_smoke_observations(smoke.output, expected_agentos_home)
    details = [
        *base_details,
        "Executed command shape: " + shell_command(codex_smoke_command(Path("<external-project>"), Path("<last-message>"))),
        f"Exit code: {smoke.exit_code}",
        f"Output bytes: {len(smoke.output.encode('utf-8', errors='replace'))}",
        f"Observed expected AgentOS path: {yes_no(observed['expected_path'])}",
        "Observed starter files: " + ", ".join(observed["starter_files"]) if observed["starter_files"] else "Observed starter files: none",
    ]
    if smoke.output_error:
        details.append(f"Output capture error: {smoke.output_error}")
    if observed["forbidden_patterns"]:
        return CheckResult(
            f"installed adapter smoke ({harness})",
            "FAIL",
            "Smoke output referenced forbidden private or verification material.",
            details=[*details, "Forbidden output markers: " + ", ".join(observed["forbidden_patterns"])],
        )
    if smoke.timed_out:
        return CheckResult(
            f"installed adapter smoke ({harness})",
            "WARN",
            "Harness smoke timed out.",
            details=details,
        )
    if smoke.exit_code == 127:
        return CheckResult(
            f"installed adapter smoke ({harness})",
            "WARN",
            "Harness smoke could not start.",
            details=details,
        )
    if smoke.exit_code != 0:
        return CheckResult(
            f"installed adapter smoke ({harness})",
            "WARN",
            "Harness smoke exited nonzero.",
            details=details,
        )
    if observed["no_agentos"]:
        return CheckResult(
            f"installed adapter smoke ({harness})",
            "FAIL",
            "Harness reported that no AgentOS instructions are active.",
            details=details,
        )
    if observed["wrong_agentos_path"]:
        return CheckResult(
            f"installed adapter smoke ({harness})",
            "FAIL",
            "Harness reported a different AgentOS checkout.",
            details=[*details, "Observed other AgentOS-like paths: " + ", ".join(observed["other_agentos_paths"])],
        )
    if observed["expected_path"] and set(SMOKE_STARTER_FILES).issubset(set(observed["starter_files"])):
        return CheckResult(
            f"installed adapter smoke ({harness})",
            "PASS",
            "Harness reported the expected AgentOS setup facts from an external project.",
            details=details,
        )
    return CheckResult(
        f"installed adapter smoke ({harness})",
        "WARN",
        "Harness smoke output was ambiguous.",
        details=details,
        recommendations=[
            "Inspect the raw smoke evidence only in a private Personal Overlay report if a future saved-report mode is added.",
        ],
    )


def parse_smoke_observations(output: str, expected_agentos_home: Path) -> dict[str, object]:
    normalized = output.replace("\\", "/")
    lower = normalized.lower()
    expected_text = str(expected_agentos_home)
    expected_seen = expected_text in output or expected_text.replace("\\", "/") in normalized
    starter_files = [rel for rel in SMOKE_STARTER_FILES if rel in normalized]
    forbidden = [pattern for pattern in SMOKE_FORBIDDEN_OUTPUT_PATTERNS if pattern.lower() in lower]
    other_paths = [
        path
        for path in sorted(set(re.findall(r"(/[^\s`'\"<>]*AgentOS[^\s`'\"<>]*)", output)))
        if path != expected_text
    ]
    no_agentos = any(
        phrase in lower
        for phrase in (
            "no agentos instructions",
            "no active agentos",
            "agentos instructions are not active",
            "agentos guidance is not active",
        )
    )
    return {
        "expected_path": expected_seen,
        "starter_files": starter_files,
        "forbidden_patterns": forbidden,
        "other_agentos_paths": other_paths,
        "wrong_agentos_path": bool(other_paths and not expected_seen),
        "no_agentos": no_agentos,
    }


def smoke_privacy_errors(prompt: str, command: list[str], expected_agentos_home: Path) -> list[str]:
    errors: list[str] = []
    command_text = "\n".join(command)
    if str(expected_agentos_home) in prompt:
        errors.append("prompt contains expected AgentOS path")
    if str(expected_agentos_home) in command_text:
        errors.append("command contains expected AgentOS path")
    prompt_lower = prompt.lower()
    command_lower = command_text.lower()
    for pattern in SMOKE_FORBIDDEN_PROMPT_PATTERNS:
        if pattern.lower() in prompt_lower:
            errors.append(f"prompt contains forbidden pattern {pattern!r}")
        if pattern.lower() in command_lower:
            errors.append(f"command contains forbidden pattern {pattern!r}")
    return errors


def yes_no(value: object) -> str:
    return "yes" if value else "no"


def check_automation_locations(
    agentos_home: Path,
    primary_agentos_home: Path,
    process_home: Path,
    env: Mapping[str, str],
    primary_home_trusted: bool = True,
) -> CheckResult:
    core_registry = agentos_home / "os" / "automations" / "AUTOMATIONS.md"
    personal_root = primary_agentos_home / "personal" / "os" / "automations"
    personal_registry = personal_root / "AUTOMATIONS.md"
    codex_home = absolute_path(Path(env.get("CODEX_HOME", process_home / ".codex")), process_home)
    codex_automation_root = codex_home / "automations"

    if primary_home_trusted:
        personal_count, personal_error = count_files(personal_root)
        personal_registry_state = path_state(personal_registry)
        personal_root_state = path_state(personal_root)
    else:
        personal_count = None
        personal_error = "primary AgentOS home invalid/untrusted"
        personal_registry_state = "unknown"
        personal_root_state = "unknown"
    codex_count, codex_error = count_files(codex_automation_root)
    codex_toml_count, codex_toml_error = count_files(codex_automation_root, suffix=".toml")

    details = [
        f"Core automation registry: {path_state(core_registry)} ({core_registry})",
        f"Personal automation registry: {personal_registry_state} ({personal_registry})",
        f"Personal automation directory: {personal_root_state} ({personal_root})",
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
            primary_home_trusted and personal_registry.exists(),
            primary_home_trusted and bool(personal_count),
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


def agentos_root_problem(agentos_home: Path) -> str | None:
    try:
        mode = agentos_home.lstat().st_mode
    except FileNotFoundError:
        return "path is missing"
    except OSError as exc:
        return f"{exc.__class__.__name__}: {exc}"
    if stat.S_ISLNK(mode):
        return "symbolic link is not allowed"
    if not stat.S_ISDIR(mode):
        return "not a directory"
    return None


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
