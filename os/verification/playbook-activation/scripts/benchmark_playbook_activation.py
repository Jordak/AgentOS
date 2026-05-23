#!/usr/bin/env python3
"""Verify that realistic tasks activate required AgentOS playbook guidance."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


KNOWN_HARNESSES = ("codex",)
ACCESS_COMMAND_RE = re.compile(
    r"\b(cat|sed|nl|head|tail|less|more|rg|grep|find|ls|wc|awk|python3?|perl|jq)\b"
)
DIRECT_COMMAND_RE = re.compile(
    r"^(?:[$+>]\s*)?(?:(?:/[\w.-]+)+/)?"
    r"(?:cat|sed|nl|head|tail|less|more|rg|grep|find|ls|wc|awk|python3?|perl|jq)\b"
)
SHELL_WRAPPER_RE = re.compile(
    r"^(?:[$+>]\s*)?(?:(?:/[\w.-]+)+/)?(?:bash|sh|zsh)\s+-[a-z]*c\s+"
)
CODE_ACCESS_RE = re.compile(r"\b(read_text|open)\s*\(")
CODEX_MODEL_RE = re.compile(r"(?im)^model:\s*(.+?)\s*$")
CODEX_EFFORT_RE = re.compile(r"(?im)^reasoning effort:\s*(.+?)\s*$")
HARNESS_UNAVAILABLE_PATTERNS = (
    "is not installed",
    "failed to initialize in-process app-server client",
    "failed to initialize state runtime",
    "attempt to write a readonly database",
    "Error finding codex home",
    "CODEX_HOME points to",
)


def default_root() -> Path:
    return Path(__file__).resolve().parents[4]


def git_value(root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def remote_main_commit(root: Path) -> str | None:
    output = git_value(root, "ls-remote", "--heads", "origin", "main")
    if not output:
        return None
    first_line = output.splitlines()[0]
    parts = first_line.split()
    return parts[0] if parts else None


def collect_git_state(root: Path) -> dict[str, Any]:
    status = git_value(root, "status", "--porcelain=v1")
    branch = git_value(root, "branch", "--show-current")
    commit = git_value(root, "rev-parse", "HEAD")
    commit_time = git_value(root, "show", "-s", "--format=%cI", "HEAD")
    upstream = git_value(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    upstream_commit = git_value(root, "rev-parse", "@{u}") if upstream else None
    ahead = behind = None
    if upstream:
        counts = git_value(root, "rev-list", "--left-right", "--count", "HEAD...@{u}")
        if counts:
            parts = counts.split()
            if len(parts) == 2 and all(part.isdigit() for part in parts):
                ahead = int(parts[0])
                behind = int(parts[1])

    worktree_clean = status == "" if status is not None else None
    local_upstream_fresh = ahead == 0 and behind == 0 if ahead is not None and behind is not None else None
    remote_commit = remote_main_commit(root)
    remote_fresh = commit == remote_commit if commit and remote_commit else None
    eligible_fresh_main = (
        branch == "main"
        and upstream == "origin/main"
        and worktree_clean is True
        and local_upstream_fresh is True
        and remote_fresh is True
        and bool(commit)
    )
    return {
        "branch": branch or "unknown",
        "commit": commit or "unknown",
        "commit_time": commit_time or "unknown",
        "upstream": upstream or "none",
        "upstream_commit": upstream_commit or "unknown",
        "ahead": ahead,
        "behind": behind,
        "upstream_fresh": local_upstream_fresh,
        "local_upstream_fresh": local_upstream_fresh,
        "remote_main_commit": remote_commit or "unknown",
        "remote_checked_at": datetime.now(timezone.utc).isoformat() if remote_commit else None,
        "remote_fresh": remote_fresh,
        "worktree_clean": worktree_clean,
        "eligible_fresh_main": bool(eligible_fresh_main),
    }


def resolve_under_root(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_fixtures(path: Path, selected_ids: set[str] | None = None) -> list[dict[str, Any]]:
    fixtures = read_json(path)
    if selected_ids is None:
        return fixtures
    return [fixture for fixture in fixtures if fixture.get("id") in selected_ids]


def validate_benchmark_config(root: Path, fixtures: list[dict[str, Any]], coverage: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    fixture_ids: dict[str, dict[str, Any]] = {}
    for fixture in fixtures:
        fixture_id = fixture.get("id")
        if not isinstance(fixture_id, str) or not fixture_id:
            errors.append("fixture is missing a string id")
            continue
        if fixture_id in fixture_ids:
            errors.append(f"duplicate fixture id: {fixture_id}")
        fixture_ids[fixture_id] = fixture
        for field in ("category", "task", "rationale"):
            if not isinstance(fixture.get(field), str) or not fixture[field].strip():
                errors.append(f"{fixture_id}: missing string field {field}")
        must_access = fixture.get("must_access")
        if not isinstance(must_access, list) or not must_access:
            errors.append(f"{fixture_id}: must_access must be a non-empty list")
            continue
        for path in must_access:
            if not isinstance(path, str) or not path:
                errors.append(f"{fixture_id}: must_access contains a non-string path")
                continue
            if not resolve_under_root(root, Path(path)).exists():
                errors.append(f"{fixture_id}: required path does not exist: {path}")

    coverage_ids: set[str] = set()
    for item in coverage:
        coverage_id = item.get("id")
        if not isinstance(coverage_id, str) or not coverage_id:
            errors.append("coverage row is missing a string id")
            continue
        if coverage_id in coverage_ids:
            errors.append(f"duplicate coverage id: {coverage_id}")
        coverage_ids.add(coverage_id)
        guidance_path = item.get("guidance_path")
        if not isinstance(guidance_path, str) or not guidance_path:
            errors.append(f"{coverage_id}: missing string guidance_path")
            continue
        if not resolve_under_root(root, Path(guidance_path)).exists():
            errors.append(f"{coverage_id}: guidance_path does not exist: {guidance_path}")
        row_fixture_ids = item.get("fixture_ids", [])
        if not isinstance(row_fixture_ids, list):
            errors.append(f"{coverage_id}: fixture_ids must be a list")
            continue
        if item.get("status") == "covered" and not row_fixture_ids:
            errors.append(f"{coverage_id}: covered status requires at least one fixture id")
        for fixture_id in row_fixture_ids:
            fixture = fixture_ids.get(fixture_id)
            if fixture is None:
                errors.append(f"{coverage_id}: unknown fixture id: {fixture_id}")
                continue
            if guidance_path not in fixture.get("must_access", []):
                errors.append(
                    f"{coverage_id}: fixture {fixture_id} does not require guidance_path {guidance_path}"
                )
    return errors


def load_transcript(paths: list[Path]) -> str:
    parts: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        parts.append(extract_transcript_text(text))
    return "\n".join(parts)


def extract_transcript_text(text: str) -> str:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text
    parts: list[str] = []
    collect_transcript_parts(parsed, parts)
    return "\n".join(parts)


def collect_transcript_parts(value: Any, parts: list[str]) -> None:
    if isinstance(value, dict):
        for key in ("stderr", "stdout", "transcript", "tool_activity", "log"):
            item = value.get(key)
            if isinstance(item, str):
                parts.append(item)
        for key in ("results", "runs", "items"):
            nested = value.get(key)
            if isinstance(nested, list):
                collect_transcript_parts(nested, parts)
    elif isinstance(value, list):
        for item in value:
            collect_transcript_parts(item, parts)


def access_lines(transcript: str) -> list[str]:
    lines: list[str] = []
    for line in transcript.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        command_like = DIRECT_COMMAND_RE.search(stripped) or SHELL_WRAPPER_RE.search(stripped)
        if command_like and (ACCESS_COMMAND_RE.search(stripped) or CODE_ACCESS_RE.search(stripped)):
            lines.append(stripped)
    return lines


def path_variants(root: Path, rel_path: str) -> list[str]:
    absolute = root / rel_path
    return [
        rel_path,
        f"./{rel_path}",
        str(absolute),
        absolute.as_posix(),
    ]


def observed_access(root: Path, rel_path: str, transcript: str) -> dict[str, Any]:
    variants = path_variants(root, rel_path)
    matches = [
        line
        for line in access_lines(transcript)
        if any(variant in line for variant in variants)
    ]
    return {
        "path": rel_path,
        "accessed": bool(matches),
        "matches": matches[:5],
    }


def grade_fixture(root: Path, fixture: dict[str, Any], transcript: str) -> dict[str, Any]:
    accesses = [
        observed_access(root, path, transcript)
        for path in fixture["must_access"]
    ]
    return {
        "fixture_id": fixture["id"],
        "category": fixture["category"],
        "must_access": fixture["must_access"],
        "access": accesses,
        "overall_pass": all(item["accessed"] for item in accesses),
    }


def command_version(binary: str) -> str:
    if shutil.which(binary) is None:
        return "not installed"
    try:
        completed = subprocess.run(
            [binary, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except OSError as error:
        return f"version unavailable: {error}"
    text = (completed.stdout or completed.stderr).strip()
    return text or f"version command exited {completed.returncode}"


def codex_command(root: Path, task: str, model: str | None = None, effort: str | None = None) -> list[str]:
    command = [
        "codex",
        "exec",
        "--cd",
        str(root),
        "--sandbox",
        "read-only",
        "--ephemeral",
        "--color",
        "never",
    ]
    if model:
        command.extend(["--model", model])
    if effort:
        command.extend(["--config", f"model_reasoning_effort={json.dumps(effort)}"])
    command.append(task)
    return command


def harness_command(
    harness: str,
    root: Path,
    fixture: dict[str, Any],
    model: str | None = None,
    effort: str | None = None,
) -> list[str]:
    if harness == "codex":
        return codex_command(root, fixture["task"], model=model, effort=effort)
    raise ValueError(f"unsupported harness: {harness}")


def expand_harnesses(selected: list[str]) -> list[str]:
    if not selected:
        return list(KNOWN_HARNESSES)
    if "all" in selected:
        return list(KNOWN_HARNESSES)
    expanded: list[str] = []
    for harness in selected:
        if harness not in KNOWN_HARNESSES:
            raise ValueError(f"unsupported harness: {harness}")
        if harness not in expanded:
            expanded.append(harness)
    return expanded


def observed_model(harness: str, stderr: str, requested_model: str | None) -> str:
    if harness == "codex":
        match = CODEX_MODEL_RE.search(stderr)
        if match:
            return match.group(1).strip()
    return requested_model or "unknown"


def observed_effort(harness: str, stderr: str, requested_effort: str | None) -> str:
    if harness == "codex":
        match = CODEX_EFFORT_RE.search(stderr)
        if match:
            return match.group(1).strip()
    return requested_effort or "unknown"


def run_harness_fixture(
    harness: str,
    root: Path,
    fixture: dict[str, Any],
    timeout_seconds: int,
    model: str | None = None,
    effort: str | None = None,
) -> dict[str, Any]:
    version = command_version(harness)
    if shutil.which(harness) is None:
        return {
            "harness": harness,
            "version": version,
            "fixture_id": fixture["id"],
            "command": [harness],
            "exit_code": 127,
            "stdout": "",
            "stderr": f"{harness} is not installed",
            "model": model or "unknown",
            "effort": effort or "unknown",
        }
    command = harness_command(harness, root, fixture, model=model, effort=effort)
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            cwd=root,
            timeout=timeout_seconds,
        )
        return {
            "harness": harness,
            "version": version,
            "fixture_id": fixture["id"],
            "command": [shlex.quote(part) for part in command],
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "model": observed_model(harness, completed.stderr, model),
            "effort": observed_effort(harness, completed.stderr, effort),
        }
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout if isinstance(error.stdout, str) else ""
        stderr = error.stderr if isinstance(error.stderr, str) else ""
        return {
            "harness": harness,
            "version": version,
            "fixture_id": fixture["id"],
            "command": [shlex.quote(part) for part in command],
            "exit_code": 124,
            "stdout": stdout,
            "stderr": stderr + f"\ntimed out after {timeout_seconds} seconds",
            "model": model or "unknown",
            "effort": effort or "unknown",
        }


def summarize_field(results: list[dict[str, Any]], field: str) -> str:
    values = sorted({result[field] for result in results if result.get(field)})
    if not values:
        return "unknown"
    if len(values) == 1:
        return values[0]
    by_harness: dict[str, set[str]] = {}
    for result in results:
        value = result.get(field)
        if value:
            by_harness.setdefault(result["harness"], set()).add(value)
    return "; ".join(
        f"{harness}={','.join(sorted(harness_values))}"
        for harness, harness_values in sorted(by_harness.items())
    )


def build_status_evidence(kind: str, git_state: dict[str, Any], can_refresh_status: bool) -> dict[str, Any]:
    eligible = can_refresh_status and git_state.get("eligible_fresh_main") is True
    reason = "eligible behavior-bearing run from clean, remote-fresh main" if eligible else "not eligible for Core status refresh"
    if not can_refresh_status:
        reason = f"{kind} is not behavior-bearing evidence for Core status refresh"
    elif git_state.get("eligible_fresh_main") is not True:
        reason = "Git metadata does not prove clean, remote-fresh main at run time"
    return {
        "kind": kind,
        "eligible_for_status_refresh": eligible,
        "reason": reason,
    }


def build_dry_run_report(
    root: Path,
    fixtures: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    harnesses: list[str],
    model: str | None = None,
    effort: str | None = None,
) -> dict[str, Any]:
    planned_runs = [
        {
            "harness": harness,
            "version": command_version(harness),
            "fixture_id": fixture["id"],
            "command": harness_command(harness, root, fixture, model=model, effort=effort),
        }
        for harness in harnesses
        for fixture in fixtures
    ]
    git_state = collect_git_state(root)
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agentos_git": git_state,
        "status_evidence": build_status_evidence("dry-run-plan", git_state, False),
        "root": str(root),
        "mode": "dry-run",
        "summary": {
            "total": len(fixtures),
            "planned": len(fixtures),
            "harness_runs": len(planned_runs),
            "model": model or "harness-default",
            "effort": effort or "harness-default",
        },
        "fixtures": fixtures,
        "planned_runs": planned_runs,
        "coverage": coverage_report(coverage, fixtures),
    }


def build_transcript_report(
    root: Path,
    fixtures: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    transcript_paths: list[Path],
) -> dict[str, Any]:
    transcript = load_transcript(transcript_paths)
    results = [grade_fixture(root, fixture, transcript) for fixture in fixtures]
    passed = sum(1 for result in results if result["overall_pass"])
    git_state = collect_git_state(root)
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agentos_git": git_state,
        "status_evidence": build_status_evidence("transcript-regrade", git_state, False),
        "root": str(root),
        "mode": "transcript",
        "transcripts": [str(path) for path in transcript_paths],
        "summary": {
            "total": len(results),
            "overall_pass": passed,
            "overall_fail": len(results) - passed,
        },
        "results": results,
        "coverage": coverage_report(coverage, fixtures),
    }


def build_harness_report(
    root: Path,
    fixtures: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    harnesses: list[str],
    timeout_seconds: int,
    model: str | None = None,
    effort: str | None = None,
) -> dict[str, Any]:
    raw_results = [
        run_harness_fixture(harness, root, fixture, timeout_seconds, model=model, effort=effort)
        for harness in harnesses
        for fixture in fixtures
    ]
    fixtures_by_id = {fixture["id"]: fixture for fixture in fixtures}
    results: list[dict[str, Any]] = []
    for raw_result in raw_results:
        fixture = fixtures_by_id[raw_result["fixture_id"]]
        transcript = "\n".join([raw_result["stderr"], raw_result["stdout"]])
        grade = grade_fixture(root, fixture, transcript)
        unavailable_reason = harness_unavailable_reason(raw_result)
        results.append({
            **raw_result,
            "status": "harness-unavailable" if unavailable_reason else "graded",
            "unavailable_reason": unavailable_reason,
            "grade": grade,
        })
    unavailable = sum(1 for result in results if result["status"] == "harness-unavailable")
    behavioral_results = [result for result in results if result["status"] != "harness-unavailable"]
    passed = sum(1 for result in results if result["grade"]["overall_pass"])
    behavioral_passed = sum(1 for result in behavioral_results if result["grade"]["overall_pass"])
    git_state = collect_git_state(root)
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agentos_git": git_state,
        "status_evidence": build_status_evidence("live-harness-run", git_state, True),
        "root": str(root),
        "mode": "run",
        "summary": {
            "total": len(results),
            "overall_pass": passed,
            "overall_fail": len(results) - passed,
            "harness_unavailable": unavailable,
            "behavioral_total": len(behavioral_results),
            "behavioral_pass": behavioral_passed,
            "behavioral_fail": len(behavioral_results) - behavioral_passed,
            "model": summarize_field(results, "model"),
            "effort": summarize_field(results, "effort"),
        },
        "results": results,
        "coverage": coverage_report(coverage, fixtures),
    }


def harness_unavailable_reason(raw_result: dict[str, Any]) -> str | None:
    if raw_result.get("exit_code") == 0:
        return None
    combined = "\n".join([raw_result.get("stderr", ""), raw_result.get("stdout", "")])
    for pattern in HARNESS_UNAVAILABLE_PATTERNS:
        if pattern in combined:
            return pattern
    return None


def coverage_report(coverage: list[dict[str, Any]], fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    fixture_ids = {fixture["id"] for fixture in fixtures}
    rows: list[dict[str, Any]] = []
    covered = 0
    for item in coverage:
        existing_fixture_ids = [
            fixture_id for fixture_id in item.get("fixture_ids", [])
            if fixture_id in fixture_ids
        ]
        is_covered = bool(existing_fixture_ids)
        covered += 1 if is_covered else 0
        rows.append(
            {
                "id": item["id"],
                "guidance_path": item["guidance_path"],
                "status": item.get("status", "candidate"),
                "fixture_ids": item.get("fixture_ids", []),
                "covered": is_covered,
            }
        )
    return {
        "total_rules": len(rows),
        "covered_rules": covered,
        "rows": rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    git_state = report.get("agentos_git", {})
    status_evidence = report.get("status_evidence", {})
    lines = [
        "# AgentOS Playbook Activation Verification",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- AgentOS commit: `{git_state.get('commit', 'unknown')}`",
        f"- AgentOS branch: `{git_state.get('branch', 'unknown')}`",
        f"- Worktree clean: `{render_bool(git_state.get('worktree_clean'))}`",
        f"- Remote main fresh: `{render_bool(git_state.get('remote_fresh'))}`",
        f"- Fresh main eligible: `{render_bool(git_state.get('eligible_fresh_main'))}`",
        f"- Status evidence kind: `{status_evidence.get('kind', 'unknown')}`",
        f"- Status refresh eligible: `{render_bool(status_evidence.get('eligible_for_status_refresh'))}`",
        f"- Mode: `{report['mode']}`",
        "",
        "> Scope: this benchmark grades only observed access to required guidance files. Task completion, write success, read-only sandbox failures, and final-answer quality are diagnostic context, not scoring inputs.",
        "",
    ]
    if report["mode"] == "dry-run":
        lines.extend(render_dry_run(report))
    else:
        lines.extend(render_results(report))
    lines.extend(render_coverage(report["coverage"]))
    return "\n".join(lines).rstrip() + "\n"


def render_dry_run(report: dict[str, Any]) -> list[str]:
    lines = [
        "## Fixture Plan",
        "",
        f"Fixtures: {report['summary']['planned']}",
        "",
        "| fixture | category | must access |",
        "| --- | --- | --- |",
    ]
    for fixture in report["fixtures"]:
        lines.append(
            "| {id} | {category} | {paths} |".format(
                id=fixture["id"],
                category=fixture["category"],
                paths=", ".join(fixture["must_access"]),
            )
        )
    if report["planned_runs"]:
        lines.extend(
            [
                "",
                "## Harness Plan",
                "",
                "| harness | fixture | version | command shape |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item in report["planned_runs"]:
            lines.append(
                "| {harness} | {fixture} | {version} | `{command}` |".format(
                    harness=item["harness"],
                    fixture=item["fixture_id"],
                    version=one_line(item["version"]),
                    command=summarize_command(item["command"]),
                )
            )
    lines.append("")
    return lines


def render_results(report: dict[str, Any]) -> list[str]:
    summary = report["summary"]
    behavioral_total = summary.get("behavioral_total", summary["total"])
    behavioral_pass = summary.get("behavioral_pass", summary["overall_pass"])
    behavioral_fail = summary.get("behavioral_fail", summary["overall_fail"])
    unavailable = summary.get("harness_unavailable", 0)
    lines = [
        "## Activation Results",
        "",
        f"Overall pass: {summary['overall_pass']}/{summary['total']}",
        f"Behavioral pass: {behavioral_pass}/{behavioral_total}",
        f"Behavioral fail: {behavioral_fail}",
        f"Harness unavailable: {unavailable}/{summary['total']}",
        f"Model: {summary.get('model', 'n/a')}",
        f"Effort: {summary.get('effort', 'n/a')}",
        "",
        "| harness | fixture | status | must access | observed | overall |",
        "| --- | --- | --- | --- | ---: | ---: |",
    ]
    for result in report["results"]:
        grade = result.get("grade", result)
        status = result.get("status", "graded")
        if status == "harness-unavailable":
            lines.append(
                "| {harness} | {id} | {status}: {reason} | {paths} | n/a | unavailable |".format(
                    harness=result.get("harness", "transcript"),
                    id=grade["fixture_id"],
                    status=status,
                    reason=one_line(result.get("unavailable_reason") or "unknown"),
                    paths=", ".join(grade["must_access"]),
                )
            )
            continue
        observed = all(item["accessed"] for item in grade["access"])
        lines.append(
            "| {harness} | {id} | {status} | {paths} | {observed} | {overall} |".format(
                harness=result.get("harness", "transcript"),
                id=grade["fixture_id"],
                status=status,
                paths=", ".join(grade["must_access"]),
                observed=mark(observed),
                overall=mark(grade["overall_pass"]),
            )
        )
    lines.append("")
    return lines


def render_coverage(coverage: dict[str, Any]) -> list[str]:
    lines = [
        "## Fixture Coverage Inventory",
        "",
        f"Fixture-covered rules: {coverage['covered_rules']}/{coverage['total_rules']}",
        "",
        "This inventory measures whether each configured activation rule has at least one fixture. It is not the activation pass rate; use `Overall pass` for observed guidance access results.",
        "",
        "| rule | guidance | status | fixture coverage |",
        "| --- | --- | --- | ---: |",
    ]
    for row in coverage["rows"]:
        lines.append(
            "| {id} | {guidance} | {status} | {covered} |".format(
                id=row["id"],
                guidance=row["guidance_path"],
                status=row["status"],
                covered=mark(row["covered"]),
            )
        )
    lines.append("")
    return lines


def mark(value: bool) -> str:
    return "yes" if value else "no"


def render_bool(value: Any) -> str:
    if value is None:
        return "unknown"
    return str(value).lower()


def one_line(text: str) -> str:
    return " ".join(text.split())


def summarize_command(command: list[str]) -> str:
    summarized: list[str] = []
    for part in command:
        if "\n" in part:
            summarized.append("<prompt>")
        else:
            summarized.append(part)
    return " ".join(shlex.quote(part) for part in summarized)


def write_report(path: Path, report: dict[str, Any], markdown: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".json":
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    else:
        path.write_text(markdown, encoding="utf-8")


def write_saved_report(directory: Path, report: dict[str, Any], markdown: str) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "report.md").write_text(markdown, encoding="utf-8")
    (directory / "run.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def default_report_dir(root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    base = root / "personal/os/verification/playbook-activation/reports" / f"playbook-activation-{timestamp}"
    if not base.exists():
        return base
    for suffix in range(2, 100):
        candidate = base.with_name(f"{base.name}-{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not allocate unique report directory for {base}")


def run_self_test(root: Path) -> int:
    fixture = {
        "id": "self-test-cli",
        "category": "programming",
        "must_access": ["os/playbook/programming/CLI.md"],
    }
    positive = "exec\n/bin/bash -lc \"sed -n '1,120p' os/playbook/programming/CLI.md\"\n"
    negative = "assistant says it read os/playbook/programming/CLI.md, but no tool command did.\n"
    source_string = "positive = \"exec\\n/bin/bash -lc \\\"sed -n 1,120p os/playbook/programming/CLI.md\\\"\\n\"\n"
    positive_grade = grade_fixture(root, fixture, positive)
    negative_grade = grade_fixture(root, fixture, negative)
    source_string_grade = grade_fixture(root, fixture, source_string)
    absolute_grade = grade_fixture(
        root,
        fixture,
        f"exec\n/bin/bash -lc 'cat {root / 'os/playbook/programming/CLI.md'}'\n",
    )
    if not positive_grade["overall_pass"]:
        print("SELF-TEST FAIL: command transcript was not accepted.")
        print(json.dumps(positive_grade, indent=2))
        return 1
    if negative_grade["overall_pass"]:
        print("SELF-TEST FAIL: model claim without tool access was accepted.")
        print(json.dumps(negative_grade, indent=2))
        return 1
    if source_string_grade["overall_pass"]:
        print("SELF-TEST FAIL: source-code string was accepted as observed tool access.")
        print(json.dumps(source_string_grade, indent=2))
        return 1
    if not absolute_grade["overall_pass"]:
        print("SELF-TEST FAIL: absolute path transcript was not accepted.")
        print(json.dumps(absolute_grade, indent=2))
        return 1
    reason = harness_unavailable_reason({
        "exit_code": 1,
        "stderr": "Error: failed to initialize in-process app-server client: Operation not permitted (os error 1)",
        "stdout": "",
    })
    if reason is None:
        print("SELF-TEST FAIL: harness startup failure was not detected.")
        return 1
    if not run_git_state_self_test():
        return 1
    print("SELF-TEST PASS: playbook activation grader accepted observed tool access.")
    return 0


def run_git_state_self_test() -> bool:
    with tempfile.TemporaryDirectory(prefix="agentos-playbook-git-self-test-") as tmp:
        root = Path(tmp)
        repo = root / "repo"
        remote = root / "origin.git"
        sibling = root / "sibling"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-b", "main"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "agentos-test"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "AgentOS Test"], check=True)
        (repo / "README.md").write_text("initial\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "initial"], check=True)
        subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(remote)], check=True)
        subprocess.run(["git", "-C", str(repo), "push", "-q", "-u", "origin", "main"], check=True)
        subprocess.run(["git", "--git-dir", str(remote), "symbolic-ref", "HEAD", "refs/heads/main"], check=True)
        clean_state = collect_git_state(repo)
        if clean_state["worktree_clean"] is not True:
            print("SELF-TEST FAIL: clean git worktree was not detected.")
            print(json.dumps(clean_state, indent=2))
            return False
        if clean_state["eligible_fresh_main"] is not True:
            print("SELF-TEST FAIL: clean remote-fresh main was not eligible.")
            print(json.dumps(clean_state, indent=2))
            return False
        subprocess.run(["git", "clone", "-q", str(remote), str(sibling)], check=True)
        subprocess.run(["git", "-C", str(sibling), "config", "user.email", "agentos-test"], check=True)
        subprocess.run(["git", "-C", str(sibling), "config", "user.name", "AgentOS Test"], check=True)
        (sibling / "README.md").write_text("advanced\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(sibling), "commit", "-q", "-am", "advance remote"], check=True)
        subprocess.run(["git", "-C", str(sibling), "push", "-q", "origin", "main"], check=True)
        stale_state = collect_git_state(repo)
        if stale_state["local_upstream_fresh"] is not True or stale_state["remote_fresh"] is not False:
            print("SELF-TEST FAIL: stale remote main was not distinguished from local upstream parity.")
            print(json.dumps(stale_state, indent=2))
            return False
        if stale_state["eligible_fresh_main"]:
            print("SELF-TEST FAIL: stale remote main was eligible.")
            print(json.dumps(stale_state, indent=2))
            return False
        (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        dirty_state = collect_git_state(repo)
        if dirty_state["worktree_clean"] is not False:
            print("SELF-TEST FAIL: dirty git worktree was not detected.")
            print(json.dumps(dirty_state, indent=2))
            return False
    return True


def report_exit_code(report: dict[str, Any]) -> int:
    if report["mode"] in {"run", "transcript"} and report["summary"].get("behavioral_fail", report["summary"]["overall_fail"]):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run AgentOS playbook activation verification.")
    parser.add_argument("--root", type=Path, default=default_root())
    parser.add_argument("--fixtures", type=Path, default=Path("os/verification/playbook-activation/fixtures.json"))
    parser.add_argument("--coverage", type=Path, default=Path("os/verification/playbook-activation/coverage.json"))
    parser.add_argument("--fixture-id", action="append", dest="fixture_ids")
    parser.add_argument("--transcript", type=Path, action="append", default=[], help="Saved transcript, log, or JSON run to grade.")
    parser.add_argument(
        "--harness",
        action="append",
        choices=["codex", "all"],
        default=[],
        help="Select harnesses to preview or run. Defaults to all known harnesses.",
    )
    parser.add_argument("--output", type=Path, help="Write a single Markdown or JSON report to this path.")
    parser.add_argument(
        "--save-report",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Write report.md and run.json to a timestamped directory under personal/os/verification/playbook-activation/reports/.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--model", help="Optional model override passed through to selected harnesses.")
    parser.add_argument("--effort", help="Optional reasoning effort override passed through to selected harnesses.")
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Preview fixtures and harness commands without invoking a harness. Default unless --no-dry-run is set.",
    )
    parser.add_argument("--self-test", action="store_true", help="Run the deterministic transcript-grader self-test.")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    fixtures_path = resolve_under_root(root, args.fixtures)
    coverage_path = resolve_under_root(root, args.coverage)
    output_path = resolve_under_root(root, args.output) if args.output else None
    transcript_paths = [resolve_under_root(root, path) for path in args.transcript]
    selected_ids = set(args.fixture_ids) if args.fixture_ids else None
    transcript_mode = bool(transcript_paths)
    dry_run = args.dry_run if args.dry_run is not None else not transcript_mode

    if args.self_test:
        return run_self_test(root)
    if args.output and args.save_report:
        print("Use either --output or --save-report, not both.", file=sys.stderr)
        return 2
    if transcript_paths and args.harness:
        print("Use either --transcript or --harness, not both.", file=sys.stderr)
        return 2

    all_fixtures = load_fixtures(fixtures_path)
    coverage = read_json(coverage_path)
    config_errors = validate_benchmark_config(root, all_fixtures, coverage)
    if config_errors:
        for error in config_errors:
            print(f"Config error: {error}", file=sys.stderr)
        return 2

    if selected_ids:
        available_ids = {fixture["id"] for fixture in all_fixtures}
        unknown_ids = sorted(selected_ids - available_ids)
        if unknown_ids:
            print(f"Unknown fixture id(s): {', '.join(unknown_ids)}", file=sys.stderr)
            return 2
    fixtures = load_fixtures(fixtures_path, selected_ids)
    if not fixtures:
        print("No fixtures selected.", file=sys.stderr)
        return 2

    harnesses: list[str] = []
    if not transcript_mode:
        try:
            harnesses = expand_harnesses(args.harness)
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 2

    if transcript_paths:
        report = build_transcript_report(root, fixtures, coverage, transcript_paths)
    elif dry_run:
        report = build_dry_run_report(root, fixtures, coverage, harnesses, model=args.model, effort=args.effort)
    else:
        report = build_harness_report(
            root,
            fixtures,
            coverage,
            harnesses,
            timeout_seconds=args.timeout_seconds,
            model=args.model,
            effort=args.effort,
        )

    markdown = render_markdown(report)
    print(markdown, end="")
    if args.save_report:
        report_dir = default_report_dir(root)
        write_saved_report(report_dir, report, markdown)
        print(f"Report written to {report_dir}", file=sys.stderr)
    if output_path:
        write_report(output_path, report, markdown)
        print(f"Report written to {output_path}", file=sys.stderr)
    return report_exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
