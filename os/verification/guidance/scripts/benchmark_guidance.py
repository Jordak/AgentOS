#!/usr/bin/env python3
"""Run AgentOS Guidance against real agent harnesses."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


KNOWN_HARNESSES = ("codex",)
KNOWN_JUDGES = ("codex",)
DEFAULT_FIXTURES_PATH = Path("os/verification/guidance/fixtures.json")
DEFAULT_JUDGE_SCHEMA_PATH = Path("os/verification/guidance/judge_response.schema.json")
DEFAULT_JUDGE_PROMPT_PATH = Path("os/verification/guidance/judge_prompt.md")
DEFAULT_JUDGE_BATCH_SIZE = 0
VERDICTS = {"pass", "fail", "fixture_stale", "needs_user_judgment"}
SOURCE_ALIGNMENTS = {"aligned", "partial", "missing", "wrong", "not_applicable"}
STALENESS_VALUES = {"current", "stale", "uncertain"}
CONFIDENCE_VALUES = {"high", "medium", "low"}
JUDGE_PROMPT_PLACEHOLDERS = (
    "CASES_JSON",
)
CODEX_MODEL_RE = re.compile(r"(?im)^model:\s*(.+?)\s*$")
CODEX_EFFORT_RE = re.compile(r"(?im)^reasoning effort:\s*(.+?)\s*$")
CONFIG_EFFORT_RE = re.compile(r"\bmodel_reasoning_effort\s*=\s*(.+?)\s*$")
HARNESS_UNAVAILABLE_PATTERNS = (
    "is not installed",
    "failed to initialize in-process app-server client",
    "failed to initialize state runtime",
    "attempt to write a readonly database",
    "Not inside a trusted directory",
    "Error finding codex home",
    "CODEX_HOME points to",
)
HUT_PROMPT_FORBIDDEN_SUBSTRINGS = (
    "You are being evaluated",
    "AgentOS guidance",
    "AgentOS guidance use",
    "local AgentOS repository guidance",
    "benchmark fixtures",
    "answer keys",
    "Fixture id:",
    "You are an agent working in the AgentOS repository.",
)
HUT_WORKSPACE_EXCLUSION_RULES = (
    ".git/**",
    "personal/**",
    "os/verification/**",
)
HUT_HOST_BOUNDARY_SENTINEL_REASON = "hut_host_boundary_sentinel_observed"
GIT_REGULAR_FILE_MODES = {"100644", "100755", "100664"}
GIT_EXECUTABLE_FILE_MODES = {"100755"}
HUT_PROJECT_PLACEHOLDER = Path("<external-project>")
SANITIZED_AGENTOS_PLACEHOLDER = Path("<sanitized-agentos>")
HOST_BOUNDARY_SENTINEL_PLACEHOLDER = Path("<host-boundary-sentinel>")
HARNESS_ADAPTER_FILENAMES = {
    "codex": "AGENTS.md",
}


def stderr_progress(message: str) -> None:
    print(f"Guidance progress: {message}", file=sys.stderr, flush=True)


def default_root() -> Path:
    return Path(__file__).resolve().parents[4]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def resolve_under_root(root: Path, path: Path | None) -> Path | None:
    if path is None:
        return None
    return path if path.is_absolute() else root / path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def display_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, RuntimeError, ValueError):
        return path.as_posix()


def same_resolved_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except (OSError, RuntimeError):
        return False


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_sha256_or_unknown(path: Path) -> str:
    try:
        return file_sha256(path)
    except OSError:
        return "unknown"


def output_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def hut_workspace_metadata(
    copied_file_count: int | None = None,
    excluded_file_count: int | None = None,
    adapter_files: list[str] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "mode": "external_project_with_sanitized_agentos",
        "exclusion_rules": list(HUT_WORKSPACE_EXCLUSION_RULES),
        "project_root": str(HUT_PROJECT_PLACEHOLDER),
        "agentos_root": str(SANITIZED_AGENTOS_PLACEHOLDER),
        "adapter_files": adapter_files or sorted(set(HARNESS_ADAPTER_FILENAMES.values())),
    }
    if copied_file_count is not None:
        metadata["copied_file_count"] = copied_file_count
    if excluded_file_count is not None:
        metadata["excluded_file_count"] = excluded_file_count
    return metadata


def host_boundary_sentinel_metadata(
    observed: bool | None = None,
    checked_output_count: int = 0,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "mode": "passive_host_boundary_tripwire",
        "sentinel_path": (HOST_BOUNDARY_SENTINEL_PLACEHOLDER / "personal/os/context/SENTINEL.md").as_posix(),
        "marker_observed": observed,
        "checked_output_count": checked_output_count,
        "proves_isolation": False,
        "eligibility_effect": HUT_HOST_BOUNDARY_SENTINEL_REASON,
    }
    return metadata


def create_host_boundary_sentinel(parent: Path) -> tuple[Path, str, dict[str, Any]]:
    sentinel_path = parent / "personal/os/context/SENTINEL.md"
    marker = f"AGENTOS_GUIDANCE_HOST_BOUNDARY_SENTINEL_{secrets.token_hex(16)}"
    sentinel_path.parent.mkdir(parents=True, exist_ok=True)
    sentinel_path.write_text(
        "\n".join(
            [
                "# Guidance Host Boundary Sentinel",
                "",
                "This file is non-private benchmark instrumentation.",
                marker,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return sentinel_path, marker, host_boundary_sentinel_metadata(observed=False)


def text_contains_marker(value: Any, marker: str) -> bool:
    return marker in output_text(value)


def harness_result_contains_marker(result: dict[str, Any], marker: str) -> bool:
    return any(
        text_contains_marker(result.get(field), marker)
        for field in ("raw_response", "stdout", "stderr")
    )


def project_local_adapter_text(agentos_root: Path) -> str:
    return f"""# AgentOS Adapter

AgentOS is installed at:

`{agentos_root}`

When a task would benefit from reusable guidance, skills, playbooks, verification habits, or routing context, read the relevant files under that AgentOS workspace.

Start with:

1. `{agentos_root / "AGENTS.md"}`
2. `{agentos_root / "os/INDEX.md"}`
3. `{agentos_root / "os/playbook/PERSONAL_OVERLAY.md"}`

If that workspace is unavailable, continue with the current project's local instructions and say that AgentOS context could not be loaded.
"""


def write_project_local_adapter(project_root: Path, agentos_root: Path, harness: str) -> str:
    filename = HARNESS_ADAPTER_FILENAMES.get(harness)
    if filename is None:
        raise ValueError(f"unsupported harness adapter: {harness}")
    (project_root / filename).write_text(project_local_adapter_text(agentos_root), encoding="utf-8")
    return filename


def indexed_file_modes(root: Path) -> dict[Path, str]:
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--stage", "-z"],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise RuntimeError("could not enumerate tracked files for HUT workspace")
    modes: dict[Path, str] = {}
    for raw in completed.stdout.split(b"\0"):
        if not raw:
            continue
        try:
            raw_metadata, raw_path = raw.split(b"\t", 1)
            mode, _object_id, stage = raw_metadata.decode("ascii").split()
        except (ValueError, UnicodeDecodeError):
            continue
        if stage != "0":
            continue
        relative_path = normalize_root_relative_path(raw_path.decode("utf-8"))
        if relative_path is not None:
            modes[relative_path] = mode
    return modes


def source_files_for_hut_workspace(root: Path) -> list[tuple[Path, str]]:
    return list(indexed_file_modes(root).items())


def normalize_root_relative_path(raw_path: str | Path) -> Path | None:
    path = Path(raw_path)
    if path.is_absolute():
        return None
    if not path.as_posix() or path.as_posix() == ".":
        return None
    if any(part in ("", ".", "..") for part in path.parts):
        return None
    return Path(*path.parts)


def path_has_prefix(path: Path, prefix: Path) -> bool:
    return path == prefix or path.parts[: len(prefix.parts)] == prefix.parts


def hut_workspace_path_is_excluded(path: Path) -> bool:
    relative_path = normalize_root_relative_path(path)
    if relative_path is None:
        return True
    return any(
        path_has_prefix(relative_path, excluded)
        for excluded in (
            Path(".git"),
            Path("os/verification"),
            Path("personal"),
        )
    )


def indexed_path_is_hut_regular_file(index_modes: dict[Path, str], relative_path: Path) -> bool:
    return index_modes.get(relative_path) in GIT_REGULAR_FILE_MODES


def read_index_file_bytes(root: Path, relative_path: Path) -> bytes | None:
    normalized = normalize_root_relative_path(relative_path)
    if normalized is None:
        return None
    completed = subprocess.run(
        ["git", "-C", str(root), "show", f":{normalized.as_posix()}"],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout


def read_index_file_text(root: Path, relative_path: Path) -> str | None:
    content = read_index_file_bytes(root, relative_path)
    if content is None:
        return None
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None


def source_path_is_safe_regular_file(root: Path, relative_path: Path) -> bool:
    normalized = normalize_root_relative_path(relative_path)
    if normalized is None:
        return False
    current = root
    for part in normalized.parts:
        current = current / part
        if current.is_symlink():
            return False
    source_path = root / normalized
    try:
        root_resolved = root.resolve(strict=True)
        resolved = source_path.resolve(strict=True)
        resolved.relative_to(root_resolved)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        return False
    return source_path.is_file()


def copy_index_file_to_workspace(root: Path, workspace: Path, relative_path: Path, mode: str) -> bool:
    normalized = normalize_root_relative_path(relative_path)
    if normalized is None or mode not in GIT_REGULAR_FILE_MODES:
        return False
    content = read_index_file_bytes(root, normalized)
    if content is None:
        return False
    target_path = workspace / normalized
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(content)
    os.chmod(target_path, 0o755 if mode in GIT_EXECUTABLE_FILE_MODES else 0o644)
    return True


def prepare_hut_workspace(root: Path, workspace: Path) -> dict[str, Any]:
    copied = 0
    excluded = 0
    workspace.mkdir(parents=True, exist_ok=True)
    for relative_path, mode in source_files_for_hut_workspace(root):
        if hut_workspace_path_is_excluded(relative_path):
            excluded += 1
            continue
        if mode not in GIT_REGULAR_FILE_MODES:
            excluded += 1
            continue
        if not copy_index_file_to_workspace(root, workspace, relative_path, mode):
            excluded += 1
            continue
        copied += 1
    rewrite_sanitized_agent_adapter(root, workspace)
    return hut_workspace_metadata(copied_file_count=copied, excluded_file_count=excluded)


def prepare_hut_project(root: Path, project_root: Path, agentos_root: Path, harnesses: list[str]) -> dict[str, Any]:
    project_root.mkdir(parents=True, exist_ok=True)
    metadata = prepare_hut_workspace(root, agentos_root)
    adapter_files = [
        write_project_local_adapter(project_root, agentos_root, harness)
        for harness in harnesses
    ]
    metadata["adapter_files"] = sorted(set(adapter_files))
    return metadata


def rewrite_sanitized_agent_adapter(root: Path, workspace: Path) -> None:
    adapter = workspace / "AGENTS.md"
    if not adapter.is_file():
        return
    text = rewrite_agentos_paths(adapter.read_text(encoding="utf-8"), root, workspace)
    adapter.write_text(text, encoding="utf-8")


def rewrite_agentos_paths(text: str, source_root: Path, replacement_root: Path) -> str:
    replacements = {
        str(source_root): str(replacement_root),
        str(Path.home() / "Developer/AgentOS"): str(replacement_root),
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def workspace_text_matches(workspace: Path, values: list[str]) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    wanted = [value for value in values if value]
    for path in workspace.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for value in wanted:
            if value in text:
                matches.setdefault(value, []).append(path.relative_to(workspace).as_posix())
    return matches


def git_value(root: Path, *args: str, timeout_seconds: int = 30) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def remote_main_commit(root: Path) -> str | None:
    output = git_value(root, "ls-remote", "--heads", "origin", "main", timeout_seconds=10)
    if not output:
        return None
    first_line = output.splitlines()[0]
    parts = first_line.split()
    return parts[0] if parts else None


def collect_git_state(root: Path, check_remote: bool = False) -> dict[str, Any]:
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
    remote_commit = remote_main_commit(root) if check_remote else None
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
        "remote_checked_at": utc_now().isoformat() if remote_commit else None,
        "remote_fresh": remote_fresh,
        "worktree_clean": worktree_clean,
        "eligible_fresh_main": bool(eligible_fresh_main),
    }


def load_fixtures(path: Path, selected_ids: set[str] | None = None) -> list[dict[str, Any]]:
    fixtures = read_json(path)
    if selected_ids is None:
        return fixtures
    return [fixture for fixture in fixtures if fixture.get("id") in selected_ids]


def validate_fixtures(root: Path, fixtures: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(fixtures, list) or not fixtures:
        return ["fixtures must be a non-empty list"]
    try:
        index_modes = indexed_file_modes(root)
    except RuntimeError:
        index_modes = {}

    seen_ids: set[str] = set()
    for index, fixture in enumerate(fixtures, start=1):
        label = f"fixtures[{index}]"
        if not isinstance(fixture, dict):
            errors.append(f"{label}: fixture must be an object")
            continue
        fixture_id = fixture.get("id")
        if not isinstance(fixture_id, str) or not fixture_id:
            errors.append(f"{label}: missing string id")
            fixture_id = label
        elif fixture_id in seen_ids:
            errors.append(f"{fixture_id}: duplicate fixture id")
        else:
            seen_ids.add(fixture_id)

        for field in ("category", "scenario"):
            if not isinstance(fixture.get(field), str) or not fixture[field].strip():
                errors.append(f"{fixture_id}: missing non-empty string field {field}")

        scenario = fixture.get("scenario", "")
        if isinstance(scenario, str):
            if "What should the agent do" in scenario:
                errors.append(f"{fixture_id}: scenario must use direct second-person framing")
            if "What do you do next?" not in scenario:
                errors.append(f"{fixture_id}: scenario should end with direct next-action framing")
            for forbidden in HUT_PROMPT_FORBIDDEN_SUBSTRINGS:
                if forbidden in scenario:
                    errors.append(f"{fixture_id}: scenario contains benchmark-priming text: {forbidden}")

        for field in ("source_paths", "expected_behavior", "failure_modes"):
            values = fixture.get(field)
            if not isinstance(values, list) or not values:
                errors.append(f"{fixture_id}: {field} must be a non-empty list")
                continue
            for value in values:
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{fixture_id}: {field} contains a non-string or empty value")

        source_paths = fixture.get("source_paths", [])
        if isinstance(source_paths, list):
            for raw_path in source_paths:
                if not isinstance(raw_path, str) or not raw_path:
                    continue
                normalized_source_path = normalize_root_relative_path(raw_path)
                if normalized_source_path is None:
                    errors.append(f"{fixture_id}: source path must be root-relative without traversal: {raw_path}")
                    continue
                if path_has_prefix(normalized_source_path, Path("os/verification/guidance")):
                    errors.append(f"{fixture_id}: source path must not point at Guidance answer keys")
                if hut_workspace_path_is_excluded(normalized_source_path):
                    errors.append(f"{fixture_id}: source path is excluded from the HUT workspace: {raw_path}")
                elif normalized_source_path not in index_modes:
                    errors.append(f"{fixture_id}: source path is not tracked in the HUT workspace index: {raw_path}")
                elif not indexed_path_is_hut_regular_file(index_modes, normalized_source_path):
                    errors.append(f"{fixture_id}: source path must be an indexed regular file in the HUT workspace: {raw_path}")
                elif read_index_file_text(root, normalized_source_path) is None:
                    errors.append(f"{fixture_id}: source path must be UTF-8 text in the HUT workspace index: {raw_path}")
    return errors


def build_harness_prompt(fixture: dict[str, Any]) -> str:
    return fixture["scenario"].strip() + "\n"


def validate_judge_prompt_template(template: str) -> list[str]:
    errors: list[str] = []
    for placeholder in JUDGE_PROMPT_PLACEHOLDERS:
        token = "{{" + placeholder + "}}"
        if token not in template:
            errors.append(f"judge prompt is missing placeholder {token}")
    return errors


def indexed_source_files(root: Path, fixture: dict[str, Any]) -> list[dict[str, str]]:
    source_files: list[dict[str, str]] = []
    for raw_path in fixture.get("source_paths", []):
        normalized = normalize_root_relative_path(raw_path)
        if normalized is None:
            continue
        content = read_index_file_text(root, normalized)
        if content is None:
            continue
        source_files.append(
            {
                "path": normalized.as_posix(),
                "content": content,
            }
        )
    return source_files


def build_judge_case(root: Path, fixture: dict[str, Any], harness: str, harness_answer: str) -> dict[str, Any]:
    return {
        "fixture_id": fixture["id"],
        "category": fixture["category"],
        "harness": harness,
        "scenario": fixture["scenario"],
        "source_paths": fixture["source_paths"],
        "source_files": indexed_source_files(root, fixture),
        "expected_behavior": fixture["expected_behavior"],
        "failure_modes": fixture["failure_modes"],
        "harness_answer": harness_answer,
    }


def build_judge_prompt(cases: list[dict[str, Any]], template: str) -> str:
    return template.replace("{{CASES_JSON}}", json.dumps(cases, indent=2))


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


def codex_command(
    root: Path,
    prompt: str,
    output_path: Path,
    schema_path: Path | None = None,
    model: str | None = None,
    effort: str | None = None,
    ignore_user_config: bool = False,
) -> list[str]:
    command = [
        "codex",
        "exec",
        "--cd",
        str(root),
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--ephemeral",
        "--color",
        "never",
        "--output-last-message",
        str(output_path),
    ]
    if ignore_user_config:
        command.append("--ignore-user-config")
    if schema_path is not None:
        command.extend(["--output-schema", str(schema_path)])
    if model:
        command.extend(["--model", model])
    if effort:
        command.extend(["--config", f"model_reasoning_effort={json.dumps(effort)}"])
    command.append("-")
    return command


def harness_command(
    harness: str,
    root: Path,
    prompt: str,
    output_path: Path,
    schema_path: Path | None = None,
    model: str | None = None,
    effort: str | None = None,
    ignore_user_config: bool = False,
) -> list[str]:
    if harness == "codex":
        return codex_command(
            root,
            prompt,
            output_path,
            schema_path=schema_path,
            model=model,
            effort=effort,
            ignore_user_config=ignore_user_config,
        )
    raise ValueError(f"unsupported harness: {harness}")


def command_shape(command: list[str]) -> str:
    if not command:
        return ""
    shaped = list(command)
    shaped[-1] = "<prompt>"
    return shlex.join(shaped)


def expand_harnesses(selected: list[str], dry_run: bool) -> list[str]:
    if not selected:
        if dry_run:
            return list(KNOWN_HARNESSES)
        raise ValueError("real Guidance runs require --harness codex or --harness all")
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
    return requested_model or "harness-default"


def observed_effort(harness: str, stderr: str, requested_effort: str | None) -> str:
    if harness == "codex":
        match = CODEX_EFFORT_RE.search(stderr) or CONFIG_EFFORT_RE.search(stderr)
        if match:
            return match.group(1).strip().strip('"')
    return requested_effort or "harness-default"


def run_harness_call(
    harness: str,
    root: Path,
    prompt: str,
    timeout_seconds: int,
    schema_path: Path | None = None,
    model: str | None = None,
    effort: str | None = None,
    ignore_user_config: bool = False,
    run_command_fn: Any = subprocess.run,
) -> dict[str, Any]:
    version = command_version(harness)
    if shutil.which(harness) is None:
        return {
            "harness": harness,
            "version": version,
            "command": [harness],
            "command_shape": harness,
            "exit_code": 127,
            "stdout": "",
            "stderr": f"{harness} is not installed",
            "raw_response": "",
            "model": requested_or_default(model),
            "effort": requested_or_default(effort),
        }

    with tempfile.TemporaryDirectory(prefix=f"agentos-guidance-{harness}-") as tmp:
        output_path = Path(tmp) / "last-message.txt"
        command = harness_command(
            harness,
            root,
            prompt,
            output_path,
            schema_path=schema_path,
            model=model,
            effort=effort,
            ignore_user_config=ignore_user_config,
        )
        try:
            completed = run_command_fn(
                command,
                check=False,
                capture_output=True,
                cwd=root,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                input=prompt,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            return timeout_harness_result(
                harness,
                version,
                command,
                timeout_seconds,
                error.stdout,
                error.stderr,
                model,
                effort,
            )
        except OSError as error:
            return process_error_harness_result(
                harness,
                version,
                command,
                error,
                model,
                effort,
            )

        raw_response = ""
        if output_path.exists():
            raw_response = output_path.read_text(encoding="utf-8").strip()
        if not raw_response:
            raw_response = completed.stdout.strip()
        return {
            "harness": harness,
            "version": version,
            "command": command,
            "command_shape": command_shape(command),
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "raw_response": raw_response,
            "model": observed_model(harness, completed.stderr, model),
            "effort": observed_effort(harness, completed.stderr, effort),
        }


def timeout_harness_result(
    harness: str,
    version: str,
    command: list[str],
    timeout_seconds: int,
    stdout: Any,
    stderr: Any,
    model: str | None,
    effort: str | None,
) -> dict[str, Any]:
    stderr_text = output_text(stderr)
    timeout_message = f"timed out after {timeout_seconds} seconds"
    if timeout_message not in stderr_text:
        stderr_text = (stderr_text + "\n" if stderr_text else "") + timeout_message
    return {
        "harness": harness,
        "version": version,
        "command": command,
        "command_shape": command_shape(command),
        "exit_code": 124,
        "stdout": output_text(stdout),
        "stderr": stderr_text,
        "raw_response": "",
        "model": requested_or_default(model),
        "effort": requested_or_default(effort),
    }


def process_error_harness_result(
    harness: str,
    version: str,
    command: list[str],
    error: OSError,
    model: str | None,
    effort: str | None,
) -> dict[str, Any]:
    return {
        "harness": harness,
        "version": version,
        "command": command,
        "command_shape": command_shape(command),
        "exit_code": 126,
        "stdout": "",
        "stderr": f"failed to start {harness}: {error}",
        "raw_response": "",
        "model": requested_or_default(model),
        "effort": requested_or_default(effort),
    }


def requested_or_default(value: str | None) -> str:
    return value or "harness-default"


def harness_unavailable_reason(result: dict[str, Any]) -> str | None:
    if int(result.get("exit_code", 0) or 0) == 0:
        return None
    combined = "\n".join(
        [
            str(result.get("stderr", "")),
            str(result.get("stdout", "")),
            str(result.get("raw_response", "")),
        ]
    )
    for pattern in HARNESS_UNAVAILABLE_PATTERNS:
        if pattern in combined:
            return pattern
    return None


def parse_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            parsed = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def validate_judge_response(value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["judge response must be an object"]

    required_fields = ("fixture_id", "verdict", "rationale", "source_alignment", "staleness", "confidence")
    for field in required_fields:
        if not isinstance(value.get(field), str) or not value[field].strip():
            errors.append(f"missing non-empty string field {field}")

    enum_checks = [
        ("verdict", VERDICTS),
        ("source_alignment", SOURCE_ALIGNMENTS),
        ("staleness", STALENESS_VALUES),
        ("confidence", CONFIDENCE_VALUES),
    ]
    for field, allowed in enum_checks:
        item = value.get(field)
        if isinstance(item, str) and item not in allowed:
            errors.append(f"{field} must be one of {', '.join(sorted(allowed))}")

    for field in ("source_alignment_rationale", "staleness_rationale"):
        if field in value and value[field] is not None and not isinstance(value[field], str):
            errors.append(f"{field} must be a string or null when present")

    allowed_fields = {
        "fixture_id",
        "verdict",
        "rationale",
        "source_alignment",
        "source_alignment_rationale",
        "staleness",
        "staleness_rationale",
        "confidence",
    }
    extra_fields = sorted(set(value) - allowed_fields)
    if extra_fields:
        errors.append(f"unexpected field(s): {', '.join(extra_fields)}")
    return errors


def validate_batch_judge_response(value: Any, expected_fixture_ids: list[str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["judge response must be an object"]
    results = value.get("results")
    if not isinstance(results, list):
        return ["judge response must contain a results list"]

    expected = set(expected_fixture_ids)
    seen: set[str] = set()
    for index, item in enumerate(results, start=1):
        item_errors = validate_judge_response(item)
        if item_errors:
            errors.extend(f"results[{index}]: {error}" for error in item_errors)
            continue
        fixture_id = item["fixture_id"]
        if fixture_id in seen:
            errors.append(f"duplicate fixture_id in judge results: {fixture_id}")
        seen.add(fixture_id)
        if fixture_id not in expected:
            errors.append(f"unexpected fixture_id in judge results: {fixture_id}")

    missing = sorted(expected - seen)
    if missing:
        errors.append(f"missing fixture_id(s) in judge results: {', '.join(missing)}")
    extra = sorted(seen - expected)
    if extra:
        errors.append(f"extra fixture_id(s) in judge results: {', '.join(extra)}")
    return errors


def fixture_run_metadata(
    root: Path,
    fixtures_path: Path,
    default_fixtures_path: Path,
    selected_ids: set[str] | None,
    fixtures: list[dict[str, Any]],
) -> dict[str, Any]:
    uses_default_path = same_resolved_path(fixtures_path, default_fixtures_path)
    selected = sorted(selected_ids or set())
    default_fixtures = read_json(default_fixtures_path) if default_fixtures_path.is_file() else []
    default_count = len(default_fixtures) if isinstance(default_fixtures, list) else None
    uses_full_default_set = uses_default_path and default_count == len(fixtures)
    return {
        "path": display_path(root, fixtures_path),
        "default_path": display_path(root, default_fixtures_path),
        "uses_default_path": uses_default_path,
        "uses_full_default_set": uses_full_default_set,
        "selected_ids": selected,
        "selected_subset": bool(selected),
        "count": len(fixtures),
        "default_count": default_count,
        "sha256": file_sha256(fixtures_path),
    }


def judge_protocol_metadata(
    root: Path,
    judge_schema_path: Path,
    default_judge_schema_path: Path,
    judge_prompt_path: Path,
    default_judge_prompt_path: Path,
    judge_batch_size: int,
) -> dict[str, Any]:
    return {
        "judge_schema_path": display_path(root, judge_schema_path),
        "default_judge_schema_path": display_path(root, default_judge_schema_path),
        "uses_default_judge_schema_path": same_resolved_path(judge_schema_path, default_judge_schema_path),
        "judge_schema_sha256": file_sha256_or_unknown(judge_schema_path),
        "judge_prompt_path": display_path(root, judge_prompt_path),
        "default_judge_prompt_path": display_path(root, default_judge_prompt_path),
        "uses_default_judge_prompt_path": same_resolved_path(judge_prompt_path, default_judge_prompt_path),
        "judge_prompt_sha256": file_sha256_or_unknown(judge_prompt_path),
        "judge_batch_size": judge_batch_size,
        "default_judge_batch_size": DEFAULT_JUDGE_BATCH_SIZE,
    }


def validate_codex_output_schema_compatibility(schema: Any) -> list[str]:
    if not isinstance(schema, dict):
        return ["judge schema must be an object"]
    errors = validate_schema_required_properties(schema)

    for field_schema in find_schema_properties(schema, {"source_alignment_rationale", "staleness_rationale"}):
        field = field_schema[0]
        schema_part = field_schema[1]
        field_type = schema_part.get("type") if isinstance(schema_part, dict) else None
        types = set(field_type) if isinstance(field_type, list) else {field_type}
        if "null" not in types:
            errors.append(f"{field} must allow null to preserve optional semantics")
    return errors


def validate_schema_required_properties(schema: Any, context: str = "$") -> list[str]:
    if not isinstance(schema, dict):
        return []
    errors: list[str] = []
    properties = schema.get("properties")
    if isinstance(properties, dict):
        required = schema.get("required")
        if not isinstance(required, list):
            errors.append(f"{context}: required field must be a list")
        else:
            missing = sorted(set(properties) - set(required))
            if missing:
                errors.append(
                    f"{context}: Codex output schemas must list every property in required; missing "
                    + ", ".join(missing)
                )
        for name, child in properties.items():
            errors.extend(validate_schema_required_properties(child, f"{context}.{name}"))
    items = schema.get("items")
    if isinstance(items, dict):
        errors.extend(validate_schema_required_properties(items, f"{context}[]"))
    return errors


def find_schema_properties(schema: Any, names: set[str]) -> list[tuple[str, dict[str, Any]]]:
    if not isinstance(schema, dict):
        return []
    found: list[tuple[str, dict[str, Any]]] = []
    properties = schema.get("properties")
    if isinstance(properties, dict):
        for name, child in properties.items():
            if name in names and isinstance(child, dict):
                found.append((name, child))
            found.extend(find_schema_properties(child, names))
    items = schema.get("items")
    if isinstance(items, dict):
        found.extend(find_schema_properties(items, names))
    return found


def planned_results(
    root: Path,
    fixtures: list[dict[str, Any]],
    harnesses: list[str],
    judge_harness: str,
    judge_schema_path: Path,
    judge_prompt_template: str,
    judge_batch_size: int,
    model: str | None = None,
    effort: str | None = None,
    judge_model: str | None = None,
    judge_effort: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    judge_batches: list[dict[str, Any]] = []
    for fixture in fixtures:
        harness_prompt = build_harness_prompt(fixture)
        for harness in harnesses:
            harness_output = Path("<tmp>") / "harness-last-message.txt"
            results.append(
                {
                    "fixture_id": fixture["id"],
                    "category": fixture["category"],
                    "harness": harness,
                    "status": "planned",
                    "harness_version": command_version(harness),
                    "harness_command_shape": command_shape(
                        harness_command(
                            harness,
                            HUT_PROJECT_PLACEHOLDER,
                            harness_prompt,
                            harness_output,
                            model=model,
                            effort=effort,
                            ignore_user_config=True,
                        )
                    ),
                    "harness_adapter": HARNESS_ADAPTER_FILENAMES[harness],
                }
            )
    batch_index = 0
    for harness in harnesses:
        harness_fixtures = [fixture for fixture in fixtures]
        for batch in chunks(harness_fixtures, effective_judge_batch_size(judge_batch_size, len(harness_fixtures))):
            batch_index += 1
            judge_cases = [
                build_judge_case(root, fixture, harness, "<harness answer>")
                for fixture in batch
            ]
            judge_prompt = build_judge_prompt(judge_cases, judge_prompt_template)
            judge_output = Path("<tmp>") / f"judge-batch-{batch_index}.json"
            judge_batches.append(
                {
                    "batch_id": batch_index,
                    "harness": harness,
                    "fixture_ids": [fixture["id"] for fixture in batch],
                    "judge_harness": judge_harness,
                    "judge_version": command_version(judge_harness),
                    "judge_command_shape": command_shape(
                        harness_command(
                            judge_harness,
                            root,
                            judge_prompt,
                            judge_output,
                            schema_path=judge_schema_path,
                            model=judge_model,
                            effort=judge_effort,
                        )
                    ),
                }
            )
    return results, judge_batches


def run_guidance(
    root: Path,
    fixtures: list[dict[str, Any]],
    harnesses: list[str],
    judge_harness: str,
    judge_schema_path: Path,
    judge_prompt_template: str,
    judge_batch_size: int,
    timeout_seconds: int,
    model: str | None = None,
    effort: str | None = None,
    judge_model: str | None = None,
    judge_effort: str | None = None,
    progress: Any = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    results: list[dict[str, Any]] = []
    judge_batches: list[dict[str, Any]] = []
    pending_by_harness: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    host_boundary = host_boundary_sentinel_metadata(observed=False)
    total_harness_calls = len(harnesses) * len(fixtures)
    completed_harness_calls = 0

    with tempfile.TemporaryDirectory(prefix="agentos-guidance-hut-") as workspace_parent, tempfile.TemporaryDirectory(
        prefix="agentos-guidance-host-boundary-"
    ) as sentinel_parent:
        project_root = Path(workspace_parent) / "external-project"
        agentos_root = Path(workspace_parent) / "agentos"
        if progress:
            progress(
                "preparing HUT workspace "
                f"(harnesses={', '.join(harnesses)}, fixtures={len(fixtures)})"
            )
        _sentinel_path, marker, host_boundary = create_host_boundary_sentinel(Path(sentinel_parent))
        hut_workspace = prepare_hut_project(root, project_root, agentos_root, harnesses)
        if progress:
            progress(
                "HUT workspace ready "
                f"(copied={hut_workspace.get('copied_file_count', 'unknown')}, "
                f"excluded={hut_workspace.get('excluded_file_count', 'unknown')})"
            )
        checked_output_count = 0

        for harness in harnesses:
            for fixture in fixtures:
                harness_prompt = build_harness_prompt(fixture)
                if progress:
                    progress(
                        "starting harness "
                        f"{harness} fixture {fixture['id']} "
                        f"({completed_harness_calls + 1}/{total_harness_calls})"
                    )
                harness_result = run_harness_call(
                    harness,
                    project_root,
                    harness_prompt,
                    timeout_seconds,
                    model=model,
                    effort=effort,
                    ignore_user_config=True,
                )
                checked_output_count += 1
                sentinel_observed = harness_result_contains_marker(harness_result, marker)
                if sentinel_observed:
                    host_boundary["marker_observed"] = True
                unavailable_reason = harness_unavailable_reason(harness_result)
                if unavailable_reason:
                    completed_harness_calls += 1
                    if progress:
                        progress(
                            "finished harness "
                            f"{harness} fixture {fixture['id']} "
                            f"status=harness-unavailable ({completed_harness_calls}/{total_harness_calls})"
                        )
                    results.append(
                        {
                            "fixture_id": fixture["id"],
                            "category": fixture["category"],
                            "harness": harness,
                            "status": "harness-unavailable",
                            "unavailable_reason": unavailable_reason,
                            "host_boundary_sentinel_observed": sentinel_observed,
                            "harness_result": harness_result,
                        }
                    )
                    continue
                if int(harness_result.get("exit_code", 0) or 0) != 0:
                    completed_harness_calls += 1
                    if progress:
                        progress(
                            "finished harness "
                            f"{harness} fixture {fixture['id']} "
                            f"status=harness-error ({completed_harness_calls}/{total_harness_calls})"
                        )
                    results.append(
                        {
                            "fixture_id": fixture["id"],
                            "category": fixture["category"],
                            "harness": harness,
                            "status": "harness-error",
                            "host_boundary_sentinel_observed": sentinel_observed,
                            "harness_result": harness_result,
                        }
                    )
                    continue
                result = {
                    "fixture_id": fixture["id"],
                    "category": fixture["category"],
                    "harness": harness,
                    "status": "pending-judge",
                    "host_boundary_sentinel_observed": sentinel_observed,
                    "harness_result": harness_result,
                }
                results.append(result)
                pending_by_harness.setdefault(harness, []).append((fixture, result))
                completed_harness_calls += 1
                if progress:
                    progress(
                        "finished harness "
                        f"{harness} fixture {fixture['id']} "
                        f"status=pending-judge ({completed_harness_calls}/{total_harness_calls})"
                    )
        host_boundary["checked_output_count"] = checked_output_count

        batch_id = 0
        for harness, pending in pending_by_harness.items():
            batch_size = effective_judge_batch_size(judge_batch_size, len(pending))
            for pending_batch in chunks(pending, batch_size):
                batch_id += 1
                expected_ids = [fixture["id"] for fixture, _ in pending_batch]
                if progress:
                    progress(
                        "starting judge batch "
                        f"{batch_id} harness={harness} fixtures={len(expected_ids)}"
                    )
                judge_cases = [
                    build_judge_case(root, fixture, harness, result["harness_result"].get("raw_response", ""))
                    for fixture, result in pending_batch
                ]
                judge_prompt = build_judge_prompt(judge_cases, judge_prompt_template)
                judge_result = run_harness_call(
                    judge_harness,
                    root,
                    judge_prompt,
                    timeout_seconds,
                    schema_path=judge_schema_path,
                    model=judge_model,
                    effort=judge_effort,
                )
                judge_unavailable = harness_unavailable_reason(judge_result)
                if judge_unavailable:
                    if progress:
                        progress(
                            "finished judge batch "
                            f"{batch_id} harness={harness} status=judge-unavailable results=0"
                        )
                    judge_batches.append(
                        judge_batch_record(batch_id, harness, expected_ids, judge_harness, judge_result, "judge-unavailable", 0)
                    )
                    for _, result in pending_batch:
                        result.update(
                            {
                                "status": "judge-unavailable",
                                "unavailable_reason": judge_unavailable,
                                "judge_batch_id": batch_id,
                            }
                        )
                    continue
                if int(judge_result.get("exit_code", 0) or 0) != 0:
                    if progress:
                        progress(
                            "finished judge batch "
                            f"{batch_id} harness={harness} status=judge-error results=0"
                        )
                    judge_batches.append(
                        judge_batch_record(batch_id, harness, expected_ids, judge_harness, judge_result, "judge-error", 0)
                    )
                    for _, result in pending_batch:
                        result.update(
                            {
                                "status": "judge-error",
                                "judge_batch_id": batch_id,
                            }
                        )
                    continue

                judge_response = parse_json_object(judge_result.get("raw_response", ""))
                judge_errors = validate_batch_judge_response(judge_response, expected_ids)
                if judge_errors:
                    batch_record = judge_batch_record(batch_id, harness, expected_ids, judge_harness, judge_result, "judge-invalid", 0)
                    batch_record["judge_errors"] = judge_errors
                    judge_batches.append(batch_record)
                    if progress:
                        progress(
                            "finished judge batch "
                            f"{batch_id} harness={harness} status=judge-invalid results=0"
                        )
                    for _, result in pending_batch:
                        result.update(
                            {
                                "status": "judge-invalid",
                                "judge_errors": judge_errors,
                                "judge_batch_id": batch_id,
                                "judge_response": judge_response,
                            }
                        )
                    continue

                judge_batches.append(
                    judge_batch_record(batch_id, harness, expected_ids, judge_harness, judge_result, "graded", len(pending_batch))
                )
                by_fixture_id = {
                    item["fixture_id"]: item
                    for item in judge_response["results"]
                }
                for fixture, result in pending_batch:
                    judge = by_fixture_id[fixture["id"]]
                    result.update(
                        {
                            "status": "graded",
                            "judge_batch_id": batch_id,
                            "judge": judge,
                            "verdict": judge["verdict"],
                        }
                    )
                if progress:
                    verdict_counts = {
                        verdict: sum(
                            1
                            for _, result in pending_batch
                            if result.get("verdict") == verdict
                        )
                        for verdict in sorted(VERDICTS)
                    }
                    verdict_summary = ", ".join(
                        f"{verdict}={count}"
                        for verdict, count in verdict_counts.items()
                        if count
                    ) or "none"
                    progress(
                        "finished judge batch "
                        f"{batch_id} harness={harness} status=graded "
                        f"results={len(pending_batch)} verdicts={verdict_summary}"
                    )
    return results, judge_batches, hut_workspace, host_boundary


def effective_judge_batch_size(judge_batch_size: int, item_count: int) -> int:
    if item_count <= 0:
        return 1
    if judge_batch_size <= 0:
        return item_count
    return judge_batch_size


def chunks(items: list[Any], size: int) -> list[list[Any]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def judge_batch_record(
    batch_id: int,
    harness: str,
    fixture_ids: list[str],
    judge_harness: str,
    judge_result: dict[str, Any],
    status: str,
    result_count: int,
) -> dict[str, Any]:
    return {
        "batch_id": batch_id,
        "harness": harness,
        "fixture_ids": fixture_ids,
        "judge_harness": judge_harness,
        "judge_version": judge_result.get("version", "unknown"),
        "judge_command_shape": judge_result.get("command_shape", "unknown"),
        "judge_exit_code": judge_result.get("exit_code"),
        "status": status,
        "result_count": result_count,
    }


def build_summary(
    mode: str,
    results: list[dict[str, Any]],
    git_state: dict[str, Any],
    model: str | None,
    effort: str | None,
    judge_harness: str,
    judge_model: str | None,
    judge_effort: str | None,
    fixture_scope: dict[str, Any] | None = None,
    judge_protocol: dict[str, Any] | None = None,
    host_boundary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    total = len(results)
    verdicts = [result.get("judge", {}).get("verdict") for result in results if result.get("status") == "graded"]
    behavioral_pass = sum(1 for verdict in verdicts if verdict == "pass")
    behavioral_fail = sum(1 for verdict in verdicts if verdict == "fail")
    fixture_stale = sum(1 for verdict in verdicts if verdict == "fixture_stale")
    needs_user_judgment = sum(1 for verdict in verdicts if verdict == "needs_user_judgment")
    harness_unavailable = sum(1 for result in results if result.get("status") == "harness-unavailable")
    harness_error = sum(1 for result in results if result.get("status") == "harness-error")
    judge_unavailable = sum(1 for result in results if result.get("status") == "judge-unavailable")
    judge_error = sum(1 for result in results if result.get("status") == "judge-error")
    judge_invalid = sum(1 for result in results if result.get("status") == "judge-invalid")
    planned = sum(1 for result in results if result.get("status") == "planned")
    behavioral_total = behavioral_pass + behavioral_fail
    overall_pass = behavioral_pass
    overall_fail = behavioral_fail

    summary = {
        "total": total,
        "overall_pass": overall_pass,
        "overall_fail": overall_fail,
        "behavioral_total": behavioral_total,
        "behavioral_pass": behavioral_pass,
        "behavioral_fail": behavioral_fail,
        "fixture_stale": fixture_stale,
        "needs_user_judgment": needs_user_judgment,
        "harness_unavailable": harness_unavailable,
        "harness_error": harness_error,
        "judge_unavailable": judge_unavailable,
        "judge_error": judge_error,
        "judge_invalid": judge_invalid,
        "planned": planned,
        "model": requested_or_default(model),
        "effort": requested_or_default(effort),
        "judge_harness": judge_harness,
        "judge_model": requested_or_default(judge_model),
        "judge_effort": requested_or_default(judge_effort),
        "host_boundary_sentinel_observed": bool(host_boundary and host_boundary.get("marker_observed") is True),
    }
    reasons = status_ineligible_reasons(mode, summary, git_state, fixture_scope, judge_protocol, host_boundary)
    summary["status_eligible"] = not reasons
    summary["status_ineligible_reasons"] = reasons
    return summary


def status_ineligible_reasons(
    mode: str,
    summary: dict[str, Any],
    git_state: dict[str, Any],
    fixture_scope: dict[str, Any] | None = None,
    judge_protocol: dict[str, Any] | None = None,
    host_boundary: dict[str, Any] | None = None,
) -> list[str]:
    reasons: list[str] = []
    if mode != "run":
        reasons.append(mode)
    if git_state.get("eligible_fresh_main") is not True:
        reasons.append("not_clean_remote_fresh_main")
    if fixture_scope is not None and not (
        fixture_scope.get("uses_default_path") is True
        and fixture_scope.get("uses_full_default_set") is True
        and fixture_scope.get("selected_subset") is False
    ):
        reasons.append("non_canonical_fixture_scope")
    if judge_protocol is None or not (
        judge_protocol.get("uses_default_judge_schema_path") is True
        and judge_protocol.get("uses_default_judge_prompt_path") is True
        and judge_protocol.get("judge_batch_size") == judge_protocol.get("default_judge_batch_size")
    ):
        reasons.append("non_canonical_judge_protocol")
    if host_boundary is not None and host_boundary.get("marker_observed") is True:
        reasons.append(HUT_HOST_BOUNDARY_SENTINEL_REASON)
    if summary.get("needs_user_judgment", 0):
        reasons.append("needs_user_judgment")
    if summary.get("harness_unavailable", 0):
        reasons.append("harness_unavailable")
    if summary.get("harness_error", 0):
        reasons.append("harness_error")
    if summary.get("judge_unavailable", 0):
        reasons.append("judge_unavailable")
    if summary.get("judge_error", 0):
        reasons.append("judge_error")
    if summary.get("judge_invalid", 0):
        reasons.append("judge_invalid")
    if summary.get("total", 0) == 0:
        reasons.append("no_results")
    if summary.get("behavioral_total", 0) + summary.get("fixture_stale", 0) == 0 and mode == "run":
        reasons.append("no_behavioral_or_stale_results")
    return reasons


def build_report(
    root: Path,
    fixtures: list[dict[str, Any]],
    fixtures_path: Path,
    default_fixtures_path: Path,
    selected_fixture_ids: set[str] | None,
    harnesses: list[str],
    dry_run: bool,
    judge_harness: str,
    judge_schema_path: Path,
    default_judge_schema_path: Path,
    judge_prompt_path: Path,
    default_judge_prompt_path: Path,
    judge_prompt_template: str,
    judge_batch_size: int,
    timeout_seconds: int,
    model: str | None = None,
    effort: str | None = None,
    judge_model: str | None = None,
    judge_effort: str | None = None,
    check_remote_main: bool = False,
    run_guidance_fn: Any = None,
    progress: Any = None,
) -> dict[str, Any]:
    mode = "dry-run" if dry_run else "run"
    git_state = collect_git_state(root, check_remote=check_remote_main)
    generated_at = utc_now().isoformat()
    judge_batches: list[dict[str, Any]] = []
    hut_workspace = hut_workspace_metadata()
    host_boundary = host_boundary_sentinel_metadata(observed=None)
    fixture_scope = fixture_run_metadata(root, fixtures_path, default_fixtures_path, selected_fixture_ids, fixtures)
    judge_protocol = judge_protocol_metadata(
        root,
        judge_schema_path,
        default_judge_schema_path,
        judge_prompt_path,
        default_judge_prompt_path,
        judge_batch_size,
    )
    if dry_run:
        results, judge_batches = planned_results(
            root,
            fixtures,
            harnesses,
            judge_harness,
            judge_schema_path,
            judge_prompt_template,
            judge_batch_size,
            model=model,
            effort=effort,
            judge_model=judge_model,
            judge_effort=judge_effort,
        )
    else:
        runner = run_guidance_fn or run_guidance
        run_output = runner(
            root,
            fixtures,
            harnesses,
            judge_harness,
            judge_schema_path,
            judge_prompt_template,
            judge_batch_size,
            timeout_seconds,
            model=model,
            effort=effort,
            judge_model=judge_model,
            judge_effort=judge_effort,
            progress=progress,
        )
        if len(run_output) == 3:
            results, judge_batches, hut_workspace = run_output
            host_boundary = host_boundary_sentinel_metadata(observed=None)
        else:
            results, judge_batches, hut_workspace, host_boundary = run_output
    summary = build_summary(
        mode,
        results,
        git_state,
        model,
        effort,
        judge_harness,
        judge_model,
        judge_effort,
        fixture_scope=fixture_scope,
        judge_protocol=judge_protocol,
        host_boundary=host_boundary,
    )
    return {
        "benchmark": "guidance",
        "mode": mode,
        "generated_at": generated_at,
        "git": git_state,
        "summary": summary,
        "fixtures": fixture_scope,
        "harnesses": harnesses,
        "judge_schema": str(judge_schema_path),
        "judge_prompt": str(judge_prompt_path),
        "judge_batch_size": judge_batch_size,
        "judge_protocol": judge_protocol,
        "hut_workspace": hut_workspace,
        "host_boundary": host_boundary,
        "judge_batches": judge_batches,
        "results": results,
    }


def render_bool(value: Any) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    git_state = report["git"]
    fixtures = report.get("fixtures", {})
    judge_protocol = report.get("judge_protocol", {})
    lines = [
        "# AgentOS Guidance Benchmark",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Mode: `{report['mode']}`",
        f"Git branch: `{git_state.get('branch', 'unknown')}`",
        f"Git commit: `{git_state.get('commit', 'unknown')}`",
        f"Worktree clean: `{render_bool(git_state.get('worktree_clean'))}`",
        f"Fresh main eligible: `{render_bool(git_state.get('eligible_fresh_main'))}`",
        f"Status eligible: `{render_bool(summary.get('status_eligible'))}`",
        f"Status ineligible reasons: `{', '.join(summary.get('status_ineligible_reasons', [])) or 'none'}`",
        "",
        "## Summary",
        "",
        f"Behavioral pass: {summary['behavioral_pass']}/{summary['behavioral_total']}",
        f"Behavioral fail: {summary['behavioral_fail']}",
        f"Fixture stale: {summary['fixture_stale']}",
        f"Needs user judgment: {summary['needs_user_judgment']}",
        f"Harness unavailable: {summary['harness_unavailable']}/{summary['total']}",
        f"Judge unavailable: {summary['judge_unavailable']}/{summary['total']}",
        f"Judge invalid: {summary['judge_invalid']}/{summary['total']}",
        f"Model: {summary.get('model', 'harness-default')}",
        f"Effort: {summary.get('effort', 'harness-default')}",
        f"Judge harness: {summary.get('judge_harness', 'codex')}",
        f"Judge model: {summary.get('judge_model', 'harness-default')}",
        f"Judge effort: {summary.get('judge_effort', 'harness-default')}",
        f"Judge schema uses default: `{render_bool(judge_protocol.get('uses_default_judge_schema_path'))}`",
        f"Judge prompt uses default: `{render_bool(judge_protocol.get('uses_default_judge_prompt_path'))}`",
        f"Judge batch size: `{judge_protocol.get('judge_batch_size', 'unknown')}`",
        f"HUT workspace: {report.get('hut_workspace', {}).get('mode', 'unknown')}",
        f"Host-boundary sentinel observed: `{render_bool(report.get('host_boundary', {}).get('marker_observed'))}`",
        f"Host-boundary sentinel proves isolation: `{render_bool(report.get('host_boundary', {}).get('proves_isolation'))}`",
        f"Fixture source: `{fixtures.get('path', 'unknown')}`",
        f"Fixture count: `{fixtures.get('count', 'unknown')}`",
        f"Fixture uses default path: `{render_bool(fixtures.get('uses_default_path'))}`",
        f"Fixture uses full default set: `{render_bool(fixtures.get('uses_full_default_set'))}`",
        f"Fixture selected subset: `{render_bool(fixtures.get('selected_subset'))}`",
        "",
    ]

    if report["mode"] == "dry-run":
        lines.extend(render_dry_run_results(report["results"], report.get("judge_batches", [])))
    else:
        lines.extend(render_run_results(report["results"]))
        lines.extend(render_judge_batches(report.get("judge_batches", [])))
    return "\n".join(lines) + "\n"


def render_dry_run_results(results: list[dict[str, Any]], judge_batches: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## Planned Runs",
        "",
        "| harness | fixture | harness command |",
        "| --- | --- | --- |",
    ]
    for result in results:
        lines.append(
            "| {harness} | {fixture} | `{harness_command}` |".format(
                harness=result["harness"],
                fixture=result["fixture_id"],
                harness_command=result["harness_command_shape"],
            )
        )
    lines.extend([
        "",
        "## Planned Judge Batches",
        "",
        "| batch | harness | fixtures | judge command |",
        "| --- | --- | --- | --- |",
    ])
    for batch in judge_batches:
        lines.append(
            "| {batch_id} | {harness} | {fixtures} | `{judge_command}` |".format(
                batch_id=batch["batch_id"],
                harness=batch["harness"],
                fixtures=", ".join(batch["fixture_ids"]),
                judge_command=batch["judge_command_shape"],
            )
        )
    return lines


def render_run_results(results: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## Results",
        "",
        "| harness | fixture | status | verdict | source alignment | staleness | confidence | rationale |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        judge = result.get("judge") or {}
        rationale = str(judge.get("rationale", result.get("unavailable_reason", ""))).replace("\n", " ")
        lines.append(
            "| {harness} | {fixture} | {status} | {verdict} | {source} | {staleness} | {confidence} | {rationale} |".format(
                harness=result.get("harness", "unknown"),
                fixture=result.get("fixture_id", "unknown"),
                status=result.get("status", "unknown"),
                verdict=judge.get("verdict", "n/a"),
                source=judge.get("source_alignment", "n/a"),
                staleness=judge.get("staleness", "n/a"),
                confidence=judge.get("confidence", "n/a"),
                rationale=rationale,
            )
        )
    return lines


def render_judge_batches(judge_batches: list[dict[str, Any]]) -> list[str]:
    if not judge_batches:
        return []
    lines = [
        "",
        "## Judge Batches",
        "",
        "| batch | harness | fixtures | status | results |",
        "| --- | --- | --- | --- | --- |",
    ]
    for batch in judge_batches:
        lines.append(
            "| {batch_id} | {harness} | {fixtures} | {status} | {result_count} |".format(
                batch_id=batch.get("batch_id", "unknown"),
                harness=batch.get("harness", "unknown"),
                fixtures=", ".join(batch.get("fixture_ids", [])),
                status=batch.get("status", "unknown"),
                result_count=batch.get("result_count", 0),
            )
        )
    return lines


def default_report_dir(root: Path) -> Path:
    stamp = utc_now().strftime("%Y-%m-%d-%H%M%S")
    base = root / "personal/os/verification/guidance/reports" / f"guidance-{stamp}"
    if not base.exists():
        return base
    for suffix in range(2, 1000):
        candidate = base.with_name(f"{base.name}-{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not allocate unique report directory for {base}")


def write_saved_report(directory: Path, report: dict[str, Any], markdown: str) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "report.md").write_text(markdown, encoding="utf-8")
    (directory / "run.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def write_report(path: Path, report: dict[str, Any], markdown: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".json":
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    else:
        path.write_text(markdown, encoding="utf-8")


def report_exit_code(report: dict[str, Any]) -> int:
    summary = report["summary"]
    if report["mode"] == "run" and (
        summary.get("behavioral_fail", 0)
        or summary.get("needs_user_judgment", 0)
        or summary.get("harness_unavailable", 0)
        or summary.get("harness_error", 0)
        or summary.get("judge_unavailable", 0)
        or summary.get("judge_error", 0)
        or summary.get("judge_invalid", 0)
    ):
        return 1
    return 0


def run_self_test(root: Path, fixtures_path: Path, judge_prompt_path: Path, judge_schema_path: Path) -> int:
    fixtures = read_json(fixtures_path)
    errors = validate_fixtures(root, fixtures)
    if errors:
        print("SELF-TEST FAIL: actual Guidance fixtures are invalid.")
        print("\n".join(errors))
        return 1

    judge_prompt_template = judge_prompt_path.read_text(encoding="utf-8")
    prompt_errors = validate_judge_prompt_template(judge_prompt_template)
    if prompt_errors:
        print("SELF-TEST FAIL: judge prompt template is invalid.")
        print("\n".join(prompt_errors))
        return 1

    schema_errors = validate_codex_output_schema_compatibility(read_json(judge_schema_path))
    if schema_errors:
        print("SELF-TEST FAIL: judge schema is not compatible with Codex structured output.")
        print("\n".join(schema_errors))
        return 1

    invalid_paths = [
        Path.cwd().anchor + "outside.md",
        "../outside.md",
        "os/../os/verification/guidance/fixtures.json",
        "os/verification",
        "personal/os/context/private.md",
    ]
    bad_path_results = {
        raw_path: {
            "normalized": normalize_root_relative_path(raw_path).as_posix()
            if normalize_root_relative_path(raw_path) is not None
            else None,
            "excluded": hut_workspace_path_is_excluded(Path(raw_path)),
        }
        for raw_path in invalid_paths
    }
    if any(result["normalized"] is not None for path, result in bad_path_results.items() if ".." in path or path.startswith("/")):
        print("SELF-TEST FAIL: unsafe root-relative paths were normalized.")
        print(json.dumps(bad_path_results, indent=2))
        return 1
    if any(result["excluded"] is not True for result in bad_path_results.values()):
        print("SELF-TEST FAIL: HUT workspace path exclusions missed unsafe paths.")
        print(json.dumps(bad_path_results, indent=2))
        return 1

    with tempfile.TemporaryDirectory(prefix="agentos-guidance-path-self-test-") as tmp:
        tmp_root = Path(tmp)
        (tmp_root / "docs").mkdir()
        (tmp_root / "docs" / "allowed.md").write_text("allowed", encoding="utf-8")
        (tmp_root / "personal" / "os" / "context").mkdir(parents=True)
        (tmp_root / "personal" / "os" / "context" / "private.md").write_text("private", encoding="utf-8")
        (tmp_root / "os" / "verification").mkdir(parents=True)
        (tmp_root / "os" / "verification" / "secret.md").write_text("secret", encoding="utf-8")
        (tmp_root / "docs" / "allowed-link.md").symlink_to("allowed.md")
        (tmp_root / "docs-link").symlink_to(tmp_root / "os" / "verification")
        init_result = subprocess.run(["git", "-C", str(tmp_root), "init"], check=False, capture_output=True)
        add_result = subprocess.run(
            [
                "git",
                "-C",
                str(tmp_root),
                "add",
                "docs/allowed.md",
                "docs/allowed-link.md",
                "personal/os/context/private.md",
            ],
            check=False,
            capture_output=True,
        )
        if init_result.returncode != 0 or add_result.returncode != 0:
            print("SELF-TEST FAIL: could not initialize temporary path git source.")
            print(json.dumps({"init": init_result.returncode, "add": add_result.returncode}, indent=2))
            return 1
        safety_results = {
            "allowed": source_path_is_safe_regular_file(tmp_root, Path("docs/allowed.md")),
            "file_symlink": source_path_is_safe_regular_file(tmp_root, Path("docs/allowed-link.md")),
            "directory_symlink": source_path_is_safe_regular_file(tmp_root, Path("docs-link/secret.md")),
        }
        if safety_results != {"allowed": True, "file_symlink": False, "directory_symlink": False}:
            print("SELF-TEST FAIL: HUT workspace file safety checks did not reject symlink paths.")
            print(json.dumps(safety_results, indent=2))
            return 1
        symlink_fixture = {
            "id": "symlink-source-path",
            "category": "self-test",
            "scenario": "The user asks you to check the docs.\n\nWhat do you do next?",
            "source_paths": ["docs/allowed-link.md"],
            "expected_behavior": ["Use the real file."],
            "failure_modes": ["Use a symlinked source path."],
        }
        symlink_errors = validate_fixtures(tmp_root, [symlink_fixture])
        if not any("indexed regular file" in error for error in symlink_errors):
            print("SELF-TEST FAIL: fixture validation accepted a symlinked source path.")
            print(json.dumps(symlink_errors, indent=2))
            return 1
        private_fixture = {
            "id": "private-source-path",
            "category": "self-test",
            "scenario": "The user asks you to check the private notes.\n\nWhat do you do next?",
            "source_paths": ["personal/os/context/private.md"],
            "expected_behavior": ["Use only public Core files."],
            "failure_modes": ["Use a private Personal Overlay source path."],
        }
        private_errors = validate_fixtures(tmp_root, [private_fixture])
        if not any("excluded from the HUT workspace" in error for error in private_errors):
            print("SELF-TEST FAIL: fixture validation accepted a private HUT-inaccessible source path.")
            print(json.dumps(private_errors, indent=2))
            return 1

    with tempfile.TemporaryDirectory(prefix="agentos-guidance-tracked-source-self-test-") as tmp:
        tmp_root = Path(tmp)
        source_root = tmp_root / "source"
        source_root.mkdir()
        (source_root / "AGENTS.md").write_text(f"AgentOS source at {source_root}\n", encoding="utf-8")
        (source_root / "os").mkdir()
        (source_root / "os" / "INDEX.md").write_text("tracked guidance\n", encoding="utf-8")
        (source_root / "docs").mkdir()
        (source_root / "docs" / "SOURCE.md").write_text("indexed source\n", encoding="utf-8")
        (source_root / "UNTRACKED_SECRET.md").write_text("do not copy\n", encoding="utf-8")
        init_result = subprocess.run(["git", "-C", str(source_root), "init"], check=False, capture_output=True)
        add_result = subprocess.run(
            ["git", "-C", str(source_root), "add", "AGENTS.md", "os/INDEX.md", "docs/SOURCE.md"],
            check=False,
            capture_output=True,
        )
        (source_root / "os" / "INDEX.md").write_text(
            "dirty working tree guidance\nDIRTY_TRACKED_SENTINEL\n",
            encoding="utf-8",
        )
        (source_root / "docs" / "SOURCE.md").unlink()
        (source_root / "docs" / "SOURCE.md").symlink_to(source_root / "UNTRACKED_SECRET.md")
        if init_result.returncode != 0 or add_result.returncode != 0:
            print("SELF-TEST FAIL: could not initialize temporary git source.")
            print(json.dumps({"init": init_result.returncode, "add": add_result.returncode}, indent=2))
            return 1
        indexed_source_fixture = {
            "id": "indexed-source-path",
            "category": "self-test",
            "scenario": "The user asks you to check the indexed docs.\n\nWhat do you do next?",
            "source_paths": ["docs/SOURCE.md"],
            "expected_behavior": ["Use the indexed source."],
            "failure_modes": ["Use dirty worktree state."],
        }
        indexed_source_errors = validate_fixtures(source_root, [indexed_source_fixture])
        if indexed_source_errors:
            print("SELF-TEST FAIL: fixture validation rejected an indexed source path because of dirty worktree state.")
            print(json.dumps(indexed_source_errors, indent=2))
            return 1
        indexed_source_case = build_judge_case(source_root, indexed_source_fixture, "codex", "<harness answer>")
        indexed_source_prompt = build_judge_prompt([indexed_source_case], judge_prompt_template)
        if (
            "indexed source" not in indexed_source_prompt
            or "do not copy" in indexed_source_prompt
            or "DIRTY_TRACKED_SENTINEL" in indexed_source_prompt
        ):
            print("SELF-TEST FAIL: judge source snapshot did not use indexed source content.")
            print(json.dumps({
                "has_indexed_source": "indexed source" in indexed_source_prompt,
                "leaked_symlink_target": "do not copy" in indexed_source_prompt,
                "leaked_dirty_content": "DIRTY_TRACKED_SENTINEL" in indexed_source_prompt,
            }, indent=2))
            return 1
        project_root = tmp_root / "external-project"
        agentos_root = tmp_root / "agentos"
        prepare_hut_project(source_root, project_root, agentos_root, ["codex"])
        copied_index_text = (
            (agentos_root / "os/INDEX.md").read_text(encoding="utf-8")
            if (agentos_root / "os/INDEX.md").is_file()
            else ""
        )
        copied_source_text = (
            (agentos_root / "docs/SOURCE.md").read_text(encoding="utf-8")
            if (agentos_root / "docs/SOURCE.md").is_file()
            else ""
        )
        if (
            copied_index_text != "tracked guidance\n"
            or copied_source_text != "indexed source\n"
            or (agentos_root / "UNTRACKED_SECRET.md").exists()
        ):
            print("SELF-TEST FAIL: HUT workspace copied dirty/untracked files or missed index contents.")
            print(json.dumps({
                "tracked_present": (agentos_root / "os/INDEX.md").is_file(),
                "copied_index_text": copied_index_text,
                "copied_source_text": copied_source_text,
                "untracked_present": (agentos_root / "UNTRACKED_SECRET.md").exists(),
            }, indent=2))
            return 1

    for fixture in fixtures:
        harness_prompt = build_harness_prompt(fixture)
        forbidden_values = [
            value for value in HUT_PROMPT_FORBIDDEN_SUBSTRINGS
            if value in harness_prompt
        ]
        if forbidden_values:
            print("SELF-TEST FAIL: harness prompt contained benchmark-priming text.")
            print(json.dumps({"fixture_id": fixture["id"], "values": forbidden_values}, indent=2))
            return 1
        hidden_values_for_fixture = [
            fixture["id"],
            *fixture["source_paths"],
            *fixture["expected_behavior"],
            *fixture["failure_modes"],
        ]
        leaked = [value for value in hidden_values_for_fixture if value in harness_prompt]
        if leaked:
            print("SELF-TEST FAIL: harness prompt leaked hidden fixture fields.")
            print(json.dumps({"fixture_id": fixture["id"], "values": leaked}, indent=2))
            return 1

    with tempfile.TemporaryDirectory(prefix="agentos-guidance-hut-self-test-") as tmp:
        project_root = Path(tmp) / "external-project"
        agentos_root = Path(tmp) / "agentos"
        metadata = prepare_hut_project(root, project_root, agentos_root, ["codex"])
        adapter = project_root / "AGENTS.md"
        sanitized_adapter = agentos_root / "AGENTS.md"
        forbidden_paths = [
            ".git",
            "os/verification",
            "personal",
        ]
        present_forbidden_paths = [
            raw_path for raw_path in forbidden_paths
            if (agentos_root / raw_path).exists()
        ]
        adapter_text = adapter.read_text(encoding="utf-8") if adapter.is_file() else ""
        sanitized_adapter_text = sanitized_adapter.read_text(encoding="utf-8") if sanitized_adapter.is_file() else ""
        leaked_source_paths = [
            value for value in (str(root), str(Path.home() / "Developer/AgentOS"))
            if value and (value in adapter_text or value in sanitized_adapter_text)
        ]
        if (
            present_forbidden_paths
            or not adapter.is_file()
            or not sanitized_adapter.is_file()
            or str(agentos_root) not in adapter_text
            or leaked_source_paths
            or metadata.get("adapter_files") != ["AGENTS.md"]
        ):
            print("SELF-TEST FAIL: HUT project did not isolate through a sanitized AgentOS adapter.")
            print(json.dumps({"present": present_forbidden_paths, "leaked_paths": leaked_source_paths, "metadata": metadata}, indent=2))
            return 1
        hidden_workspace_values: list[str] = []
        for fixture in fixtures:
            hidden_workspace_values.append(fixture["id"])
            hidden_workspace_values.extend(fixture["failure_modes"])
        workspace_matches = workspace_text_matches(agentos_root, hidden_workspace_values)
        if workspace_matches:
            print("SELF-TEST FAIL: sanitized AgentOS workspace leaked hidden fixture values.")
            print(json.dumps(workspace_matches, indent=2))
            return 1

    first = fixtures[0]
    hidden_values = [
        *first["source_paths"],
        *first["expected_behavior"],
        *first["failure_modes"],
    ]
    judge_case = build_judge_case(root, first, "codex", "<harness answer>")
    judge_prompt = build_judge_prompt([judge_case], judge_prompt_template)
    missing_from_judge = [value for value in hidden_values if value not in judge_prompt]
    if missing_from_judge:
        print("SELF-TEST FAIL: judge prompt did not include hidden fixture fields.")
        print(json.dumps(missing_from_judge, indent=2))
        return 1
    judge_command_shape = command_shape(
        harness_command(
            "codex",
            root,
            judge_prompt,
            Path("<tmp>") / "judge-last-message.json",
            schema_path=Path("os/verification/guidance/judge_response.schema.json"),
        )
    )
    leaked_to_command_shape = [value for value in hidden_values if value in judge_command_shape]
    if leaked_to_command_shape:
        print("SELF-TEST FAIL: dry-run command shape leaked hidden fixture fields.")
        print(json.dumps(leaked_to_command_shape, indent=2))
        return 1

    all_fixture_judge_prompt = build_judge_prompt(
        [
            build_judge_case(root, fixture, "codex", "<representative harness answer>")
            for fixture in fixtures
        ],
        judge_prompt_template,
    )
    all_fixture_judge_command = harness_command(
        "codex",
        root,
        all_fixture_judge_prompt,
        Path("<tmp>") / "judge-all-fixtures.json",
        schema_path=Path("os/verification/guidance/judge_response.schema.json"),
    )
    all_fixture_argv_bytes = sum(len(part.encode("utf-8")) + 1 for part in all_fixture_judge_command)
    if (
        all_fixture_judge_command[-1] != "-"
        or all_fixture_judge_prompt in all_fixture_judge_command
        or all_fixture_argv_bytes >= os.sysconf("SC_ARG_MAX")
    ):
        print("SELF-TEST FAIL: default judge prompt was not transported through stdin.")
        print(json.dumps({
            "last_argument": all_fixture_judge_command[-1],
            "prompt_in_argv": all_fixture_judge_prompt in all_fixture_judge_command,
            "argv_bytes": all_fixture_argv_bytes,
            "arg_max": os.sysconf("SC_ARG_MAX"),
        }, indent=2))
        return 1

    valid_judge = {
        "fixture_id": first["id"],
        "verdict": "pass",
        "rationale": "The answer makes the required decision.",
        "source_alignment": "missing",
        "source_alignment_rationale": None,
        "staleness": "current",
        "staleness_rationale": None,
        "confidence": "high",
    }
    if validate_judge_response(valid_judge):
        print("SELF-TEST FAIL: optional judge rationale fields were treated as required.")
        return 1

    stale_without_rationale = {
        "fixture_id": first["id"],
        "verdict": "fixture_stale",
        "rationale": "The current source differs from the expected behavior.",
        "source_alignment": "not_applicable",
        "source_alignment_rationale": None,
        "staleness": "stale",
        "staleness_rationale": None,
        "confidence": "medium",
    }
    if validate_judge_response(stale_without_rationale):
        print("SELF-TEST FAIL: staleness_rationale was hard-required.")
        return 1

    invalid_judge = {
        "fixture_id": first["id"],
        "verdict": "maybe",
        "source_alignment": "aligned",
        "staleness": "current",
        "confidence": "high",
    }
    if not validate_judge_response(invalid_judge):
        print("SELF-TEST FAIL: invalid judge response was accepted.")
        return 1

    valid_batch = {"results": [valid_judge]}
    if validate_batch_judge_response(valid_batch, [first["id"]]):
        print("SELF-TEST FAIL: valid batch judge response was rejected.")
        print(validate_batch_judge_response(valid_batch, [first["id"]]))
        return 1
    missing_batch = {"results": []}
    if not validate_batch_judge_response(missing_batch, [first["id"]]):
        print("SELF-TEST FAIL: missing batch judge result was accepted.")
        return 1

    planned, judge_batches = planned_results(
        root,
        fixtures[:2],
        ["codex"],
        "codex",
        Path("os/verification/guidance/judge_response.schema.json"),
        judge_prompt_template,
        0,
    )
    if len(planned) != 2 or len(judge_batches) != 1:
        print("SELF-TEST FAIL: default judge batching did not batch all fixtures per harness.")
        print(json.dumps({"planned": planned, "judge_batches": judge_batches}, indent=2))
        return 1
    if (
        "--ignore-user-config" not in planned[0]["harness_command_shape"]
        or str(HUT_PROJECT_PLACEHOLDER) not in planned[0]["harness_command_shape"]
        or planned[0].get("harness_adapter") != "AGENTS.md"
    ):
        print("SELF-TEST FAIL: planned HUT command did not use the external project adapter path.")
        print(json.dumps(planned[0], indent=2))
        return 1
    if (
        "--ignore-user-config" in judge_batches[0]["judge_command_shape"]
        or str(HUT_PROJECT_PLACEHOLDER) in judge_batches[0]["judge_command_shape"]
        or str(SANITIZED_AGENTOS_PLACEHOLDER) in judge_batches[0]["judge_command_shape"]
        or str(root) not in judge_batches[0]["judge_command_shape"]
    ):
        print("SELF-TEST FAIL: planned judge command did not stay in the trusted benchmark checkout.")
        print(json.dumps(judge_batches[0], indent=2))
        return 1
    planned_single, single_batches = planned_results(
        root,
        fixtures[:2],
        ["codex"],
        "codex",
        Path("os/verification/guidance/judge_response.schema.json"),
        judge_prompt_template,
        1,
    )
    if len(planned_single) != 2 or len(single_batches) != 2:
        print("SELF-TEST FAIL: judge_batch_size=1 did not isolate fixture judge batches.")
        print(json.dumps({"planned": planned_single, "judge_batches": single_batches}, indent=2))
        return 1
    fake_batch = judge_batch_record(
        4,
        "codex",
        ["fixture-a", "fixture-b"],
        "codex",
        {
            "version": "codex test",
            "command_shape": "codex exec '<prompt>'",
            "exit_code": 0,
        },
        "graded",
        2,
    )

    progress_messages: list[str] = []

    def fake_run_guidance(*_: Any, **kwargs: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
        progress = kwargs.get("progress")
        if progress:
            progress("self-test real-run progress")
        return [
            {
                "fixture_id": "fixture-a",
                "harness": "codex",
                "status": "graded",
                "judge_batch_id": 4,
                "judge": valid_judge,
            },
            {
                "fixture_id": "fixture-b",
                "harness": "codex",
                "status": "graded",
                "judge_batch_id": 4,
                "judge": {**valid_judge, "fixture_id": "fixture-b"},
            },
        ], [fake_batch], hut_workspace_metadata(copied_file_count=10, excluded_file_count=3), host_boundary_sentinel_metadata(
            observed=False,
            checked_output_count=2,
        )

    fake_report = build_report(
        root,
        fixtures[:2],
        fixtures_path,
        fixtures_path,
        None,
        ["codex"],
        False,
        "codex",
        Path("os/verification/guidance/judge_response.schema.json"),
        Path("os/verification/guidance/judge_response.schema.json"),
        Path("os/verification/guidance/judge_prompt.md"),
        Path("os/verification/guidance/judge_prompt.md"),
        judge_prompt_template,
        0,
        60,
        run_guidance_fn=fake_run_guidance,
        progress=progress_messages.append,
    )
    fake_markdown = render_markdown(fake_report)
    with tempfile.TemporaryDirectory(prefix="agentos-guidance-report-self-test-") as tmp:
        report_dir = Path(tmp) / "report"
        write_saved_report(report_dir, fake_report, fake_markdown)
        saved_report = read_json(report_dir / "run.json")
        saved_markdown = (report_dir / "report.md").read_text(encoding="utf-8")
    if (
        saved_report.get("judge_batches") != [fake_batch]
        or saved_report.get("hut_workspace", {}).get("mode") != "external_project_with_sanitized_agentos"
        or saved_report.get("host_boundary", {}).get("marker_observed") is not False
        or saved_report.get("host_boundary", {}).get("proves_isolation") is not False
        or "status_eligible_scope" in saved_report.get("fixtures", {})
        or "Canonical fixture scope" in saved_markdown
        or "## Judge Batches" not in saved_markdown
    ):
        print("SELF-TEST FAIL: saved real-run report did not preserve judge batch metadata.")
        print(json.dumps({
            "judge_batches": saved_report.get("judge_batches"),
            "fixtures": saved_report.get("fixtures"),
            "host_boundary": saved_report.get("host_boundary"),
            "has_old_markdown_label": "Canonical fixture scope" in saved_markdown,
        }, indent=2))
        return 1
    if progress_messages != ["self-test real-run progress"]:
        print("SELF-TEST FAIL: real-run progress callback was not threaded through build_report.")
        print(json.dumps(progress_messages, indent=2))
        return 1

    timeout_result = timeout_harness_result(
        "codex",
        "codex test",
        ["codex", "exec"],
        1,
        b"partial stdout\n",
        b"partial stderr\n",
        None,
        None,
    )
    timeout_report = {
        **fake_report,
        "results": [
            {
                "fixture_id": first["id"],
                "harness": "codex",
                "status": "harness-error",
                "harness_result": timeout_result,
            }
        ],
    }
    with tempfile.TemporaryDirectory(prefix="agentos-guidance-timeout-report-self-test-") as tmp:
        report_dir = Path(tmp) / "report"
        write_saved_report(report_dir, timeout_report, fake_markdown)
        saved_timeout_report = read_json(report_dir / "run.json")
    saved_timeout_result = saved_timeout_report["results"][0]["harness_result"]
    if (
        not isinstance(saved_timeout_result.get("stdout"), str)
        or not isinstance(saved_timeout_result.get("stderr"), str)
        or "partial stdout" not in saved_timeout_result["stdout"]
        or "partial stderr" not in saved_timeout_result["stderr"]
        or "timed out after 1 seconds" not in saved_timeout_result["stderr"]
    ):
        print("SELF-TEST FAIL: timeout report output was not string-serializable.")
        print(json.dumps(saved_timeout_result, indent=2))
        return 1

    if shutil.which("codex") is not None:
        def raise_os_error(*_: Any, **__: Any) -> Any:
            raise OSError(7, "Argument list too long")

        process_error_result = run_harness_call(
            "codex",
            root,
            "large prompt",
            1,
            run_command_fn=raise_os_error,
        )
        if (
            process_error_result.get("exit_code") != 126
            or "failed to start codex" not in process_error_result.get("stderr", "")
            or process_error_result.get("raw_response") != ""
            or process_error_result.get("command", [""])[-1] != "-"
        ):
            print("SELF-TEST FAIL: process-start errors were not converted to structured results.")
            print(json.dumps(process_error_result, indent=2))
            return 1

    leaked_to_planned_shape = [
        value
        for value in hidden_values
        if value in json.dumps(judge_batches)
    ]
    if leaked_to_planned_shape:
        print("SELF-TEST FAIL: planned judge batch shape leaked hidden fixture fields.")
        print(json.dumps(leaked_to_planned_shape, indent=2))
        return 1

    clean_git = {"eligible_fresh_main": True}
    canonical_judge_protocol = judge_protocol_metadata(
        root,
        judge_schema_path,
        judge_schema_path,
        judge_prompt_path,
        judge_prompt_path,
        DEFAULT_JUDGE_BATCH_SIZE,
    )
    mixed_results = [
        {"status": "graded", "judge": {**valid_judge, "verdict": "pass"}},
        {"status": "graded", "judge": {**valid_judge, "verdict": "fail"}},
        {"status": "graded", "judge": {**valid_judge, "verdict": "fixture_stale"}},
        {"status": "graded", "judge": {**valid_judge, "verdict": "needs_user_judgment"}},
        {"status": "harness-unavailable"},
        {"status": "judge-invalid"},
    ]
    mixed_summary = build_summary(
        "run",
        mixed_results,
        clean_git,
        None,
        None,
        "codex",
        None,
        None,
        judge_protocol=canonical_judge_protocol,
    )
    if (
        mixed_summary["behavioral_total"] != 2
        or mixed_summary["behavioral_pass"] != 1
        or mixed_summary["behavioral_fail"] != 1
        or mixed_summary["fixture_stale"] != 1
        or mixed_summary["needs_user_judgment"] != 1
        or mixed_summary["status_eligible"]
    ):
        print("SELF-TEST FAIL: mixed summary math or eligibility is wrong.")
        print(json.dumps(mixed_summary, indent=2))
        return 1

    unavailable_exit_checks = [
        ("harness-unavailable", {"harness_unavailable": 1}),
        ("judge-unavailable", {"judge_unavailable": 1}),
    ]
    for label, summary_delta in unavailable_exit_checks:
        unavailable_report = {
            "mode": "run",
            "summary": {
                "behavioral_fail": 0,
                "needs_user_judgment": 0,
                "harness_unavailable": 0,
                "harness_error": 0,
                "judge_unavailable": 0,
                "judge_error": 0,
                "judge_invalid": 0,
                **summary_delta,
            },
        }
        if report_exit_code(unavailable_report) != 1:
            print(f"SELF-TEST FAIL: {label} real run exited successfully.")
            print(json.dumps(unavailable_report, indent=2))
            return 1

    stale_allowed = [
        {"status": "graded", "judge": {**valid_judge, "verdict": "pass"}},
        {"status": "graded", "judge": {**valid_judge, "verdict": "fixture_stale"}},
    ]
    canonical_fixture_scope = fixture_run_metadata(root, fixtures_path, fixtures_path, None, fixtures)
    stale_summary = build_summary(
        "run",
        stale_allowed,
        clean_git,
        None,
        None,
        "codex",
        None,
        None,
        fixture_scope=canonical_fixture_scope,
        judge_protocol=canonical_judge_protocol,
        host_boundary=host_boundary_sentinel_metadata(observed=False, checked_output_count=2),
    )
    if not stale_summary["status_eligible"]:
        print("SELF-TEST FAIL: fixture_stale made an otherwise clean run ineligible.")
        print(json.dumps(stale_summary, indent=2))
        return 1

    sentinel_summary = build_summary(
        "run",
        stale_allowed,
        clean_git,
        None,
        None,
        "codex",
        None,
        None,
        fixture_scope=canonical_fixture_scope,
        judge_protocol=canonical_judge_protocol,
        host_boundary=host_boundary_sentinel_metadata(observed=True, checked_output_count=2),
    )
    if sentinel_summary["status_eligible"] or HUT_HOST_BOUNDARY_SENTINEL_REASON not in sentinel_summary["status_ineligible_reasons"]:
        print("SELF-TEST FAIL: observed host-boundary sentinel was status eligible.")
        print(json.dumps(sentinel_summary, indent=2))
        return 1

    sentinel_marker = "AGENTOS_GUIDANCE_HOST_BOUNDARY_SENTINEL_self_test"
    if not harness_result_contains_marker({"raw_response": "", "stdout": sentinel_marker, "stderr": ""}, sentinel_marker):
        print("SELF-TEST FAIL: host-boundary sentinel marker was not detected in HUT output.")
        return 1
    if harness_result_contains_marker({"raw_response": "", "stdout": "", "stderr": ""}, sentinel_marker):
        print("SELF-TEST FAIL: host-boundary sentinel marker false-positive detection.")
        return 1

    subset_fixture_scope = fixture_run_metadata(root, fixtures_path, fixtures_path, {first["id"]}, [first])
    subset_summary = build_summary(
        "run",
        stale_allowed,
        clean_git,
        None,
        None,
        "codex",
        None,
        None,
        fixture_scope=subset_fixture_scope,
        judge_protocol=canonical_judge_protocol,
    )
    if subset_summary["status_eligible"] or "non_canonical_fixture_scope" not in subset_summary["status_ineligible_reasons"]:
        print("SELF-TEST FAIL: selected fixture subset was status eligible.")
        print(json.dumps(subset_summary, indent=2))
        return 1

    with tempfile.TemporaryDirectory(prefix="agentos-guidance-fixture-scope-self-test-") as tmp:
        alternate_fixtures_path = Path(tmp) / "fixtures.json"
        alternate_fixtures_path.write_text(json.dumps(fixtures, indent=2), encoding="utf-8")
        alternate_fixture_scope = fixture_run_metadata(root, alternate_fixtures_path, fixtures_path, None, fixtures)
        alternate_summary = build_summary(
            "run",
            stale_allowed,
            clean_git,
            None,
            None,
            "codex",
            None,
            None,
            fixture_scope=alternate_fixture_scope,
            judge_protocol=canonical_judge_protocol,
        )
        if alternate_summary["status_eligible"] or "non_canonical_fixture_scope" not in alternate_summary["status_ineligible_reasons"]:
            print("SELF-TEST FAIL: alternate fixture file was status eligible.")
            print(json.dumps(alternate_summary, indent=2))
            return 1

    with tempfile.TemporaryDirectory(prefix="agentos-guidance-judge-protocol-self-test-") as tmp:
        alternate_judge_prompt_path = Path(tmp) / "judge_prompt.md"
        alternate_judge_schema_path = Path(tmp) / "judge_response.schema.json"
        alternate_judge_prompt_path.write_text(judge_prompt_template, encoding="utf-8")
        alternate_judge_schema_path.write_text(judge_schema_path.read_text(encoding="utf-8"), encoding="utf-8")
        alternate_prompt_protocol = judge_protocol_metadata(
            root,
            judge_schema_path,
            judge_schema_path,
            alternate_judge_prompt_path,
            judge_prompt_path,
            DEFAULT_JUDGE_BATCH_SIZE,
        )
        alternate_schema_protocol = judge_protocol_metadata(
            root,
            alternate_judge_schema_path,
            judge_schema_path,
            judge_prompt_path,
            judge_prompt_path,
            DEFAULT_JUDGE_BATCH_SIZE,
        )
        alternate_batch_protocol = judge_protocol_metadata(
            root,
            judge_schema_path,
            judge_schema_path,
            judge_prompt_path,
            judge_prompt_path,
            1,
        )
        for label, protocol in (
            ("alternate prompt", alternate_prompt_protocol),
            ("alternate schema", alternate_schema_protocol),
            ("alternate batch size", alternate_batch_protocol),
        ):
            protocol_summary = build_summary(
                "run",
                stale_allowed,
                clean_git,
                None,
                None,
                "codex",
                None,
                None,
                fixture_scope=canonical_fixture_scope,
                judge_protocol=protocol,
            )
            if (
                protocol_summary["status_eligible"]
                or "non_canonical_judge_protocol" not in protocol_summary["status_ineligible_reasons"]
            ):
                print(f"SELF-TEST FAIL: {label} was status eligible.")
                print(json.dumps(protocol_summary, indent=2))
                return 1

    dry_summary = build_summary(
        "dry-run",
        [{"status": "planned"}],
        clean_git,
        None,
        None,
        "codex",
        None,
        None,
        fixture_scope=canonical_fixture_scope,
        judge_protocol=canonical_judge_protocol,
    )
    if dry_summary["status_eligible"] or "dry-run" not in dry_summary["status_ineligible_reasons"]:
        print("SELF-TEST FAIL: dry-run summary was status eligible.")
        print(json.dumps(dry_summary, indent=2))
        return 1

    print("SELF-TEST PASS: Guidance fixture, judge, prompt, summary, and eligibility checks passed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run AgentOS Guidance.")
    parser.add_argument("--root", type=Path, default=default_root())
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES_PATH)
    parser.add_argument("--judge-schema", type=Path, default=DEFAULT_JUDGE_SCHEMA_PATH)
    parser.add_argument("--judge-prompt", type=Path, default=DEFAULT_JUDGE_PROMPT_PATH)
    parser.add_argument("--fixture-id", action="append", dest="fixture_ids")
    parser.add_argument(
        "--harness",
        action="append",
        choices=["codex", "all"],
        default=[],
        help="Select harnesses to preview or run. Real runs require an explicit harness selection.",
    )
    parser.add_argument(
        "--judge-harness",
        choices=KNOWN_JUDGES,
        default="codex",
        help="Select the judge harness.",
    )
    parser.add_argument("--output", type=Path, help="Write a single Markdown or JSON report to this path.")
    parser.add_argument(
        "--save-report",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Write report.md and run.json to a timestamped directory under personal/os/verification/guidance/reports/.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--model", help="Optional model override passed through to the harness under test.")
    parser.add_argument("--effort", help="Optional reasoning effort override passed through to the harness under test.")
    parser.add_argument("--judge-model", help="Optional model override passed through to the judge harness.")
    parser.add_argument("--judge-effort", help="Optional reasoning effort override passed through to the judge harness.")
    parser.add_argument(
        "--judge-batch-size",
        type=int,
        default=DEFAULT_JUDGE_BATCH_SIZE,
        help="Number of successful HUT answers per judge call. Use 0 to batch all answers for each harness.",
    )
    parser.add_argument(
        "--check-remote-main",
        action="store_true",
        help="Contact origin/main and include remote freshness eligibility in report Git metadata.",
    )
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Preview fixture, harness, and judge commands without invoking model-call harnesses. Default unless --no-dry-run is set.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress rendered report, progress, and report-path output. Errors and self-test output still print.",
    )
    parser.add_argument("--self-test", action="store_true", help="Run deterministic Guidance self-tests.")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    fixtures_path = resolve_under_root(root, args.fixtures)
    judge_schema_path = resolve_under_root(root, args.judge_schema)
    judge_prompt_path = resolve_under_root(root, args.judge_prompt)
    output_path = resolve_under_root(root, args.output) if args.output else None
    dry_run = args.dry_run if args.dry_run is not None else True

    if fixtures_path is None or judge_schema_path is None or judge_prompt_path is None:
        print("Internal error: fixture, judge schema, and judge prompt paths are required.", file=sys.stderr)
        return 2
    if args.self_test:
        return run_self_test(root, fixtures_path, judge_prompt_path, judge_schema_path)
    if args.output and args.save_report:
        print("Use either --output or --save-report, not both.", file=sys.stderr)
        return 2
    if args.timeout_seconds <= 0:
        print("--timeout-seconds must be positive.", file=sys.stderr)
        return 2
    if args.judge_batch_size < 0:
        print("--judge-batch-size must be non-negative.", file=sys.stderr)
        return 2

    all_fixtures = read_json(fixtures_path)
    try:
        judge_prompt_template = judge_prompt_path.read_text(encoding="utf-8")
    except OSError as error:
        print(f"Could not read judge prompt: {error}", file=sys.stderr)
        return 2
    prompt_errors = validate_judge_prompt_template(judge_prompt_template)
    if prompt_errors:
        for error in prompt_errors:
            print(f"Config error: {error}", file=sys.stderr)
        return 2

    config_errors = validate_fixtures(root, all_fixtures)
    if config_errors:
        for error in config_errors:
            print(f"Config error: {error}", file=sys.stderr)
        return 2

    selected_ids = set(args.fixture_ids) if args.fixture_ids else None
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

    try:
        harnesses = expand_harnesses(args.harness, dry_run)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    report = build_report(
        root=root,
        fixtures=fixtures,
        fixtures_path=fixtures_path,
        default_fixtures_path=resolve_under_root(root, DEFAULT_FIXTURES_PATH) or (root / DEFAULT_FIXTURES_PATH),
        selected_fixture_ids=selected_ids,
        harnesses=harnesses,
        dry_run=dry_run,
        judge_harness=args.judge_harness,
        judge_schema_path=judge_schema_path,
        default_judge_schema_path=resolve_under_root(root, DEFAULT_JUDGE_SCHEMA_PATH) or (root / DEFAULT_JUDGE_SCHEMA_PATH),
        judge_prompt_path=judge_prompt_path,
        default_judge_prompt_path=resolve_under_root(root, DEFAULT_JUDGE_PROMPT_PATH) or (root / DEFAULT_JUDGE_PROMPT_PATH),
        judge_prompt_template=judge_prompt_template,
        judge_batch_size=args.judge_batch_size,
        timeout_seconds=args.timeout_seconds,
        model=args.model,
        effort=args.effort,
        judge_model=args.judge_model,
        judge_effort=args.judge_effort,
        check_remote_main=args.check_remote_main,
        progress=stderr_progress if not dry_run and not args.quiet else None,
    )

    markdown = render_markdown(report)
    if not dry_run and not args.quiet:
        summary = report["summary"]
        stderr_progress(
            "run complete "
            f"(total={summary.get('total', 0)}, "
            f"behavioral_pass={summary.get('behavioral_pass', 0)}, "
            f"behavioral_fail={summary.get('behavioral_fail', 0)}, "
            f"status_eligible={render_bool(summary.get('status_eligible'))})"
        )
    if not args.quiet:
        print(markdown, end="")
    if args.save_report:
        report_dir = default_report_dir(root)
        write_saved_report(report_dir, report, markdown)
        if not args.quiet:
            print(f"Report written to {report_dir}", file=sys.stderr)
    if output_path:
        write_report(output_path, report, markdown)
        if not args.quiet:
            print(f"Report written to {output_path}", file=sys.stderr)
    return report_exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
