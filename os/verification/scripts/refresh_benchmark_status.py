#!/usr/bin/env python3
"""Emit public-safe benchmark status refresh candidates from saved reports."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path("os/verification/BENCHMARKS.json")
DEFAULT_STATUS = Path("os/verification/BENCHMARK_STATUS.md")

EXIT_OK = 0
EXIT_NO_FRESH_CANDIDATE = 1
EXIT_CONFIG_ERROR = 2
EXIT_PRIVACY_ERROR = 3

STATUS_LABELS = {"passing", "attention needed", "not run", "unknown"}
GUIDANCE_RESULT_STATUSES = {
    "graded",
    "harness-unavailable",
    "harness-error",
    "judge-unavailable",
    "judge-error",
    "judge-invalid",
}
GUIDANCE_VERDICTS = {"pass", "fail", "fixture_stale", "needs_user_judgment"}
SOURCE_ALIGNMENTS = {"aligned", "partial", "missing", "wrong", "not_applicable"}
STALENESS_VALUES = {"current", "stale", "uncertain"}
PUBLIC_DIAGNOSTIC_CLASSES = {
    "api_auth_or_model_access",
    "api_rate_limit_or_quota",
    "codex_sandbox_or_permission",
    "codex_timeout",
    "codex_empty_response",
    "codex_process_start_error",
    "codex_cli_error",
    "investigation_needed",
    "unknown_harness_error",
}
DEFAULT_PUBLIC_SAFE_DIAGNOSIS = "investigation_needed"
DEFAULT_SUGGESTED_NEXT_STEP = "Investigation needed."
SAFE_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SAFE_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ./_-]*$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
PRIVATE_MARKERS = (
    "/" + "Users" + "/",
    "\\Users\\",
    "personal/os/",
    "raw_response",
    "harness_result",
    "stdout",
    "stderr",
    "rationale",
)


class RefreshCandidateError(ValueError):
    """Base error for candidate generation failures."""


class UnsupportedBenchmarkSuiteError(RefreshCandidateError):
    """Raised when a current status-refresh target has no v1 parser."""


class PublicSafeOutputError(RefreshCandidateError):
    """Raised when generated public-safe output violates schema boundaries."""


@dataclass(frozen=True)
class BenchmarkTarget:
    benchmark_id: str
    reports_dir: Path
    run_glob: str
    summary_path: tuple[str, ...]
    min_status_counting_total: int
    max_age_days: int


@dataclass(frozen=True)
class GuidanceReport:
    path: Path
    data: dict[str, Any]
    generated_at: datetime
    generated_raw: str
    commit: str
    behavioral_total: int
    behavioral_pass: int
    behavioral_fail: int
    fixture_stale: int
    status_counting_total: int
    status_eligible: bool
    ineligible_reasons: tuple[str, ...]


@dataclass(frozen=True)
class StatusEntry:
    section_found: bool
    status: str | None
    reviewed_core_revision: str | None
    last_reviewed_evidence: str | None
    last_reviewed_at: datetime | None


def default_root() -> Path:
    return Path(__file__).resolve().parents[3]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(raw: str) -> datetime:
    value = raw.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_status_timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return parse_timestamp(raw)
    except ValueError:
        pass
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) (PDT|PST|UTC)", raw)
    if not match:
        return None
    date_part, time_part, zone = match.groups()
    offsets = {"PDT": "-07:00", "PST": "-08:00", "UTC": "+00:00"}
    return parse_timestamp(f"{date_part}T{time_part}:00{offsets[zone]}")


def root_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(root: Path, raw_path: Path) -> Path:
    expanded = raw_path.expanduser()
    if expanded.is_absolute():
        return expanded
    return root / expanded


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RefreshCandidateError(f"report not found: {path}") from error
    except json.JSONDecodeError as error:
        raise RefreshCandidateError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(value, dict):
        raise RefreshCandidateError(f"expected object JSON in {path}")
    return value


def int_field(value: dict[str, Any], field: str, default: int = 0) -> int | None:
    raw = value.get(field, default)
    if raw is None:
        raw = default
    if type(raw) is bool:
        return None
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def nested_get(value: dict[str, Any], path: tuple[str, ...]) -> dict[str, Any] | None:
    current: Any = value
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current if isinstance(current, dict) else None


def git_value(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def current_head(root: Path) -> str | None:
    value = git_value(root, "rev-parse", "HEAD")
    return value if value and COMMIT_RE.fullmatch(value) else None


def load_manifest_targets(root: Path, manifest_path: Path, personal_root: Path) -> list[BenchmarkTarget]:
    data = read_json(manifest_path)
    benchmarks = data.get("benchmarks")
    if not isinstance(benchmarks, list) or not benchmarks:
        raise RefreshCandidateError("manifest must contain a non-empty benchmarks list")

    targets: list[BenchmarkTarget] = []
    for index, benchmark in enumerate(benchmarks, start=1):
        label = f"benchmarks[{index}]"
        if not isinstance(benchmark, dict):
            raise RefreshCandidateError(f"{label} must be an object")
        weekly_review = benchmark.get("weekly_review", {})
        if not isinstance(weekly_review, dict):
            raise RefreshCandidateError(f"{label}.weekly_review must be an object")
        if weekly_review.get("check_freshness") is not True:
            continue

        benchmark_id = benchmark.get("id")
        reports_dir = benchmark.get("reports_dir")
        run_glob = benchmark.get("run_glob")
        summary_path = benchmark.get("summary_path")
        min_total = weekly_review.get("min_status_counting_total")
        max_age = weekly_review.get("max_age_days")

        if not isinstance(benchmark_id, str) or not benchmark_id:
            raise RefreshCandidateError(f"{label}.id must be a non-empty string")
        if not isinstance(reports_dir, str) or not reports_dir:
            raise RefreshCandidateError(f"{benchmark_id}.reports_dir must be a non-empty string")
        if not isinstance(run_glob, str) or not run_glob:
            raise RefreshCandidateError(f"{benchmark_id}.run_glob must be a non-empty string")
        if not isinstance(summary_path, list) or not summary_path:
            raise RefreshCandidateError(f"{benchmark_id}.summary_path must be a non-empty string list")
        if not all(isinstance(part, str) and part for part in summary_path):
            raise RefreshCandidateError(f"{benchmark_id}.summary_path must contain only non-empty strings")
        if type(min_total) is not int or min_total <= 0:
            raise RefreshCandidateError(f"{benchmark_id}.weekly_review.min_status_counting_total must be positive")
        if type(max_age) is not int or max_age <= 0:
            raise RefreshCandidateError(f"{benchmark_id}.weekly_review.max_age_days must be positive")

        targets.append(
            BenchmarkTarget(
                benchmark_id=benchmark_id,
                reports_dir=resolve_path(personal_root, Path(reports_dir)),
                run_glob=run_glob,
                summary_path=tuple(summary_path),
                min_status_counting_total=min_total,
                max_age_days=max_age,
            )
        )

    if not targets:
        raise RefreshCandidateError("manifest does not define any current status-refresh targets")
    for target in targets:
        if target.benchmark_id != "guidance":
            raise UnsupportedBenchmarkSuiteError(f"unsupported current status-refresh target: {target.benchmark_id}")
    return targets


def parse_status_entry(status_path: Path, benchmark_id: str) -> StatusEntry:
    try:
        text = status_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return StatusEntry(False, None, None, None, None)

    heading = "## " + benchmark_id.replace("-", " ").title()
    start = text.find(heading)
    if start < 0:
        return StatusEntry(False, None, None, None, None)
    rest = text[start + len(heading) :]
    next_match = re.search(r"\n## ", rest)
    section = rest[: next_match.start()] if next_match else rest

    status = field_value(section, "Status")
    revision = field_value(section, "Reviewed Core revision")
    evidence = field_value(section, "Last reviewed evidence")
    if status and status not in STATUS_LABELS:
        raise RefreshCandidateError(f"unsupported status label in {status_path}: {status}")
    if revision and not COMMIT_RE.fullmatch(revision):
        raise RefreshCandidateError(f"malformed reviewed core revision in {status_path}: {revision}")
    return StatusEntry(True, status, revision, evidence, parse_status_timestamp(evidence))


def field_value(section: str, label: str) -> str | None:
    pattern = re.compile(rf"^- {re.escape(label)}: `([^`]+)`$", re.MULTILINE)
    match = pattern.search(section)
    return match.group(1) if match else None


def parse_guidance_report(path: Path, summary_path: tuple[str, ...]) -> GuidanceReport | None:
    data = read_json(path)
    if data.get("benchmark") != "guidance":
        return None
    generated_raw = data.get("generated_at")
    if not isinstance(generated_raw, str):
        return None
    try:
        generated_at = parse_timestamp(generated_raw)
    except ValueError:
        return None
    summary = nested_get(data, summary_path)
    if summary is None:
        return None
    git_state = data.get("git")
    if not isinstance(git_state, dict):
        return None
    commit = git_state.get("commit")
    if not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
        return None

    behavioral_total = int_field(summary, "behavioral_total")
    behavioral_pass = int_field(summary, "behavioral_pass", int_field(summary, "overall_pass", 0) or 0)
    behavioral_fail = int_field(summary, "behavioral_fail", int_field(summary, "overall_fail", 0) or 0)
    fixture_stale = int_field(summary, "fixture_stale")
    if behavioral_total is None or behavioral_pass is None or behavioral_fail is None or fixture_stale is None:
        return None

    ineligible = summary.get("status_ineligible_reasons", [])
    if not isinstance(ineligible, list) or not all(isinstance(item, str) for item in ineligible):
        ineligible = []
    status_eligible = (
        data.get("mode") == "run"
        and summary.get("status_eligible") is True
        and git_state.get("eligible_fresh_main") is True
    )
    return GuidanceReport(
        path=path,
        data=data,
        generated_at=generated_at,
        generated_raw=generated_raw,
        commit=commit,
        behavioral_total=behavioral_total,
        behavioral_pass=behavioral_pass,
        behavioral_fail=behavioral_fail,
        fixture_stale=fixture_stale,
        status_counting_total=behavioral_total + fixture_stale,
        status_eligible=status_eligible,
        ineligible_reasons=tuple(ineligible),
    )


def discover_guidance_reports(target: BenchmarkTarget, explicit_report: Path | None) -> list[GuidanceReport]:
    paths: list[Path]
    if explicit_report is not None:
        paths = [explicit_report]
    elif target.reports_dir.exists():
        paths = sorted(target.reports_dir.glob(target.run_glob))
    else:
        paths = []
    reports = [
        report
        for path in paths
        for report in [parse_guidance_report(path, target.summary_path)]
        if report is not None
    ]
    return sorted(reports, key=lambda item: item.generated_at, reverse=True)


def latest_eligible_report(reports: list[GuidanceReport], min_status_counting_total: int) -> GuidanceReport | None:
    for report in reports:
        if report.status_eligible and report.status_counting_total >= min_status_counting_total:
            return report
    return None


def age_days(now: datetime, generated_at: datetime) -> float:
    return (now - generated_at).total_seconds() / 86400


def candidate_status(report: GuidanceReport) -> str:
    if report.behavioral_fail or report.fixture_stale:
        return "attention needed"
    return "passing"


def result_class(result: dict[str, Any]) -> str | None:
    status = result.get("status")
    judge = result.get("judge")
    verdict = judge.get("verdict") if isinstance(judge, dict) else None
    if status == "graded" and verdict == "fail":
        return "Behavioral failure"
    if status == "graded" and verdict == "fixture_stale":
        return "Fixture stale"
    if status == "graded" and verdict == "needs_user_judgment":
        return "Needs user judgment"
    classes = {
        "harness-unavailable": "Harness unavailable",
        "harness-error": "Harness error",
        "judge-unavailable": "Judge unavailable",
        "judge-error": "Judge error",
        "judge-invalid": "Judge invalid",
    }
    return classes.get(str(status))


def guidance_non_passing_details(report: GuidanceReport, private_report_path: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    public_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    results = report.data.get("results", [])
    if not isinstance(results, list):
        return public_rows, private_rows
    for index, result in enumerate(results):
        if not isinstance(result, dict):
            continue
        classification = result_class(result)
        if classification is None:
            continue
        judge = result.get("judge") if isinstance(result.get("judge"), dict) else {}
        fixture = result.get("fixture_id")
        category = result.get("category")
        status = result.get("status")
        verdict = judge.get("verdict") if isinstance(judge, dict) else None
        source_alignment = judge.get("source_alignment") if isinstance(judge, dict) else None
        staleness = judge.get("staleness") if isinstance(judge, dict) else None
        host_observed = result.get("host_boundary_sentinel_observed")
        row = {
            "fixture": safe_slug(fixture, "fixture_id"),
            "category": safe_label(category, "category"),
            "result": safe_result_class(classification),
            "status": safe_enum(status, GUIDANCE_RESULT_STATUSES, "status"),
            "verdict": safe_optional_enum(verdict, GUIDANCE_VERDICTS, "verdict"),
            "source_alignment": safe_optional_enum(source_alignment, SOURCE_ALIGNMENTS, "source_alignment"),
            "staleness": safe_optional_enum(staleness, STALENESS_VALUES, "staleness"),
            "host_boundary_sentinel_observed": safe_optional_bool(host_observed, "host_boundary_sentinel_observed"),
            "public_safe_diagnosis": safe_public_diagnostic(
                public_harness_diagnostic(result) or DEFAULT_PUBLIC_SAFE_DIAGNOSIS,
                "public_safe_diagnosis",
            ),
            "suggested_next_step": safe_public_next_step(
                DEFAULT_SUGGESTED_NEXT_STEP,
                "suggested_next_step",
            ),
        }
        public_rows.append(row)
        private_rows.append(
            {
                "fixture": row["fixture"],
                "report": private_report_path,
                "json_pointer": f"/results/{index}",
                "core_safe": False,
            }
        )
    return public_rows, private_rows


def public_harness_diagnostic(result: dict[str, Any]) -> str | None:
    status = result.get("status")
    harness_result = result.get("harness_result")
    if not isinstance(harness_result, dict):
        return None
    if status == "harness-unavailable":
        return "codex_process_start_error"
    if status not in {"harness-error", "judge-error", "judge-unavailable"}:
        return None
    exit_code = int_field(harness_result, "exit_code")
    combined = "\n".join(
        str(harness_result.get(field, ""))
        for field in ("stderr", "stdout", "raw_response")
    ).lower()
    if exit_code == 124 or "timed out after" in combined or "timeout" in combined:
        return "codex_timeout"
    if exit_code == 126 or "failed to start" in combined:
        return "codex_process_start_error"
    if any(pattern in combined for pattern in ("401", "unauthorized", "invalid api key", "authentication")):
        return "api_auth_or_model_access"
    if any(pattern in combined for pattern in ("model_not_found", "model not found", "does not have access", "unsupported model")):
        return "api_auth_or_model_access"
    if any(pattern in combined for pattern in ("429", "rate limit", "quota", "insufficient_quota", "too many requests")):
        return "api_rate_limit_or_quota"
    if any(
        pattern in combined
        for pattern in (
            "bubblewrap",
            "bwrap",
            "operation not permitted",
            "permission denied",
            "sandbox",
            "landlock",
            "seccomp",
        )
    ):
        return "codex_sandbox_or_permission"
    if not combined.strip():
        return "codex_empty_response"
    if status == "harness-error":
        return "codex_cli_error"
    return "unknown_harness_error"


def safe_slug(value: Any, field: str) -> str:
    if not isinstance(value, str) or not SAFE_SLUG.fullmatch(value):
        raise PublicSafeOutputError(f"{field} is not a safe slug: {value!r}")
    return value


def safe_label(value: Any, field: str) -> str:
    if not isinstance(value, str) or not SAFE_LABEL.fullmatch(value):
        raise PublicSafeOutputError(f"{field} is not a safe label: {value!r}")
    return value


def safe_result_class(value: str) -> str:
    allowed = {
        "Behavioral failure",
        "Fixture stale",
        "Needs user judgment",
        "Harness unavailable",
        "Harness error",
        "Judge unavailable",
        "Judge error",
        "Judge invalid",
    }
    if value not in allowed:
        raise PublicSafeOutputError(f"unsupported result class: {value!r}")
    return value


def safe_enum(value: Any, allowed: set[str], field: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise PublicSafeOutputError(f"{field} is not allowed: {value!r}")
    return value


def safe_optional_enum(value: Any, allowed: set[str], field: str) -> str | None:
    if value is None:
        return None
    return safe_enum(value, allowed, field)


def safe_optional_bool(value: Any, field: str) -> bool | None:
    if value is None:
        return None
    if type(value) is not bool:
        raise PublicSafeOutputError(f"{field} is not a boolean: {value!r}")
    return value


def safe_public_diagnostic(value: Any, field: str) -> str:
    if not isinstance(value, str) or value not in PUBLIC_DIAGNOSTIC_CLASSES:
        raise PublicSafeOutputError(f"{field} is not an allowed public diagnostic: {value!r}")
    return value


def safe_public_next_step(value: Any, field: str) -> str:
    return safe_label(value, field)


def safe_commit(value: str, field: str) -> str:
    if not COMMIT_RE.fullmatch(value):
        raise PublicSafeOutputError(f"{field} is not a 40-character hex commit")
    return value


def safe_nonnegative(value: int, field: str) -> int:
    if type(value) is not int or value < 0:
        raise PublicSafeOutputError(f"{field} is not a nonnegative integer: {value!r}")
    return value


def validate_no_private_markers(value: Any, path: str = "public_safe") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            validate_no_private_markers(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            validate_no_private_markers(item, f"{path}[{index}]")
    elif isinstance(value, str):
        for marker in PRIVATE_MARKERS:
            if marker in value:
                raise PublicSafeOutputError(f"private marker {marker!r} leaked into {path}")


def target_candidate(
    root: Path,
    personal_root: Path,
    target: BenchmarkTarget,
    status_entry: StatusEntry,
    now: datetime,
    explicit_report: Path | None,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    reports = discover_guidance_reports(target, explicit_report)
    selected = latest_eligible_report(reports, target.min_status_counting_total)
    freshness_classes: list[str] = []
    if status_entry.section_found is False:
        freshness_classes.append("status_missing")

    public: dict[str, Any] = {
        "benchmark": safe_slug(target.benchmark_id, "benchmark"),
        "current_status": status_entry.status,
        "current_reviewed_core_revision": status_entry.reviewed_core_revision,
        "current_last_reviewed_evidence": status_entry.last_reviewed_evidence,
        "report_count": safe_nonnegative(len(reports), "report_count"),
        "eligible_report_count": safe_nonnegative(
            sum(1 for report in reports if report.status_eligible), "eligible_report_count"
        ),
        "freshness_classes": freshness_classes,
    }
    private: dict[str, Any] = {"benchmark": target.benchmark_id}
    fresh_enough = False

    if selected is None:
        public["candidate_available"] = False
        public["candidate_unavailable_reason"] = "no_eligible_status_counting_report"
        if reports:
            latest = reports[0]
            latest_summary = nested_get(latest.data, target.summary_path) or {}
            private_report = root_relative(personal_root, latest.path)
            rows, _private_rows = guidance_non_passing_details(latest, private_report)
            public["latest_report"] = {
                "generated_at": latest.generated_raw,
                "status_eligible": latest.status_eligible,
                "status_ineligible_reasons": list(latest.ineligible_reasons),
                "status_counting_total": latest.status_counting_total,
                "counts": guidance_counts(latest, latest_summary),
                "evidence_scope": evidence_scope(latest),
                "non_passing_details": rows,
            }
        validate_no_private_markers(public)
        return public, private, False

    days_old = age_days(now, selected.generated_at)
    if days_old > target.max_age_days:
        freshness_classes.append("evidence_stale_by_age")
    if status_entry.reviewed_core_revision and selected.commit == status_entry.reviewed_core_revision:
        freshness_classes.append("same_as_status")
    elif status_entry.last_reviewed_at and selected.generated_at < status_entry.last_reviewed_at:
        freshness_classes.append("older_than_status")
    elif status_entry.last_reviewed_at and selected.generated_at > status_entry.last_reviewed_at:
        freshness_classes.append("newer_than_status")
    elif status_entry.reviewed_core_revision:
        freshness_classes.append("newer_than_status")

    head = current_head(root)
    if head and head != selected.commit:
        freshness_classes.append("evidence_for_non_current_head")

    private_report = root_relative(personal_root, selected.path)
    rows, private_rows = guidance_non_passing_details(selected, private_report)
    summary = nested_get(selected.data, target.summary_path) or {}
    public.update(
        {
            "candidate_available": True,
            "candidate_status": candidate_status(selected),
            "reviewed_core_revision": safe_commit(selected.commit, "reviewed_core_revision"),
            "last_reviewed_evidence": selected.generated_raw,
            "evidence_age_days": round(days_old, 3),
            "max_age_days": target.max_age_days,
            "status_counting_total": selected.status_counting_total,
            "counts": guidance_counts(selected, summary),
            "evidence_scope": evidence_scope(selected),
            "non_passing_details": rows,
        }
    )
    private.update(
        {
            "source_report": {
                "path": private_report,
                "core_safe": False,
            },
            "non_passing_results": private_rows,
        }
    )
    fresh_enough = (
        days_old <= target.max_age_days
        and "older_than_status" not in freshness_classes
    )
    validate_no_private_markers(public)
    return public, private, fresh_enough


def guidance_counts(report: GuidanceReport, summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "total": safe_nonnegative(int_field(summary, "total") or 0, "total"),
        "behavioral_total": safe_nonnegative(report.behavioral_total, "behavioral_total"),
        "behavioral_pass": safe_nonnegative(report.behavioral_pass, "behavioral_pass"),
        "behavioral_fail": safe_nonnegative(report.behavioral_fail, "behavioral_fail"),
        "fixture_stale": safe_nonnegative(report.fixture_stale, "fixture_stale"),
        "needs_user_judgment": safe_nonnegative(int_field(summary, "needs_user_judgment") or 0, "needs_user_judgment"),
        "harness_unavailable": safe_nonnegative(int_field(summary, "harness_unavailable") or 0, "harness_unavailable"),
        "harness_error": safe_nonnegative(int_field(summary, "harness_error") or 0, "harness_error"),
        "judge_unavailable": safe_nonnegative(int_field(summary, "judge_unavailable") or 0, "judge_unavailable"),
        "judge_error": safe_nonnegative(int_field(summary, "judge_error") or 0, "judge_error"),
        "judge_invalid": safe_nonnegative(int_field(summary, "judge_invalid") or 0, "judge_invalid"),
    }


def evidence_scope(report: GuidanceReport) -> dict[str, Any]:
    summary = report.data.get("summary", {})
    fixtures = report.data.get("fixtures", {})
    judge_protocol = report.data.get("judge_protocol", {})
    host_boundary = report.data.get("host_boundary", {})
    harness_user_config = report.data.get("harness_user_config", {})
    if not isinstance(summary, dict):
        summary = {}
    if not isinstance(fixtures, dict):
        fixtures = {}
    if not isinstance(judge_protocol, dict):
        judge_protocol = {}
    if not isinstance(host_boundary, dict):
        host_boundary = {}
    if not isinstance(harness_user_config, dict):
        harness_user_config = {}
    return {
        "harnesses": safe_string_list(report.data.get("harnesses"), "harnesses"),
        "harness_user_config_allowed_for_hut": safe_optional_bool(
            harness_user_config.get("allowed_for_hut"), "harness_user_config_allowed_for_hut"
        ),
        "model": safe_label(summary.get("model", "harness-default"), "model"),
        "effort": safe_label(summary.get("effort", "harness-default"), "effort"),
        "judge_harness": safe_slug(summary.get("judge_harness", "codex"), "judge_harness"),
        "judge_model": safe_label(summary.get("judge_model", "harness-default"), "judge_model"),
        "judge_effort": safe_label(summary.get("judge_effort", "harness-default"), "judge_effort"),
        "fixture_count": safe_nonnegative(int_field(fixtures, "count") or 0, "fixture_count"),
        "uses_default_fixture_path": safe_optional_bool(fixtures.get("uses_default_path"), "uses_default_path"),
        "uses_full_default_fixture_set": safe_optional_bool(fixtures.get("uses_full_default_set"), "uses_full_default_set"),
        "selected_fixture_subset": safe_optional_bool(fixtures.get("selected_subset"), "selected_subset"),
        "uses_default_judge_schema_path": safe_optional_bool(
            judge_protocol.get("uses_default_judge_schema_path"), "uses_default_judge_schema_path"
        ),
        "uses_default_judge_prompt_path": safe_optional_bool(
            judge_protocol.get("uses_default_judge_prompt_path"), "uses_default_judge_prompt_path"
        ),
        "judge_batch_size": safe_nonnegative(int_field(judge_protocol, "judge_batch_size") or 0, "judge_batch_size"),
        "default_judge_batch_size": safe_nonnegative(
            int_field(judge_protocol, "default_judge_batch_size") or 0, "default_judge_batch_size"
        ),
        "host_boundary_sentinel_observed": safe_optional_bool(
            host_boundary.get("marker_observed"), "host_boundary_sentinel_observed"
        ),
        "host_boundary_sentinel_proves_isolation": safe_optional_bool(
            host_boundary.get("proves_isolation"), "host_boundary_sentinel_proves_isolation"
        ),
    }


def safe_string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise PublicSafeOutputError(f"{field} must be a list")
    return [safe_slug(item, field) for item in value]


def build_candidate(
    root: Path,
    manifest_path: Path,
    status_path: Path,
    personal_root: Path,
    explicit_report: Path | None = None,
    target_filter: str | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], bool]:
    now = now or utc_now()
    targets = load_manifest_targets(root, manifest_path, personal_root)
    if target_filter is not None:
        targets = [target for target in targets if target.benchmark_id == target_filter]
        if not targets:
            raise RefreshCandidateError(f"target not found in current freshness targets: {target_filter}")
    public_targets: list[dict[str, Any]] = []
    private_targets: list[dict[str, Any]] = []
    fresh_enough_all = True
    for target in targets:
        status = parse_status_entry(status_path, target.benchmark_id)
        public, private, fresh_enough = target_candidate(root, personal_root, target, status, now, explicit_report)
        public_targets.append(public)
        private_targets.append(private)
        fresh_enough_all = fresh_enough_all and fresh_enough

    output = {
        "version": 1,
        "generated_at": now.isoformat(),
        "public_safe": {
            "targets": public_targets,
        },
        "private_locators": {
            "core_safe": False,
            "targets": private_targets,
        },
    }
    validate_no_private_markers(output["public_safe"])
    return output, fresh_enough_all


def print_json(value: dict[str, Any]) -> None:
    print(json.dumps(value, indent=2, sort_keys=True) + "\n", end="")


def run_self_test() -> int:
    now = datetime(2026, 6, 3, 21, 0, tzinfo=timezone.utc)
    try:
        with tempfile.TemporaryDirectory(prefix="agentos-refresh-status-self-test-") as tmp:
            root = Path(tmp)
            reports = root / "personal/os/verification/guidance/reports"
            reports.mkdir(parents=True)
            (root / "os/verification").mkdir(parents=True)
            (root / "os/verification/BENCHMARKS.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "benchmarks": [
                            {
                                "id": "guidance",
                                "script": "os/verification/guidance/scripts/benchmark_guidance.py",
                                "reports_dir": "personal/os/verification/guidance/reports",
                                "run_glob": "*/run.json",
                                "summary_path": ["summary"],
                                "weekly_review": {
                                    "check_freshness": True,
                                    "min_status_counting_total": 8,
                                    "max_age_days": 14,
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (root / "os/verification/BENCHMARK_STATUS.md").write_text(
                "# AgentOS Benchmark Status\n\n"
                "## Guidance\n\n"
                "### Codex\n\n"
                "- Status: `attention needed`\n"
                "- Reviewed Core revision: `1111111111111111111111111111111111111111`\n"
                "- Last reviewed evidence: `2026-06-03 13:12 PDT`\n",
                encoding="utf-8",
            )
            run_dir = reports / "guidance-eligible"
            run_dir.mkdir()
            commit = "a" * 40
            report = fake_guidance_report(commit=commit)
            (run_dir / "run.json").write_text(json.dumps(report), encoding="utf-8")

            output, fresh = build_candidate(
                root,
                root / "os/verification/BENCHMARKS.json",
                root / "os/verification/BENCHMARK_STATUS.md",
                root,
                now=now,
            )
            if not fresh:
                print("SELF-TEST FAIL: eligible fresh report was not fresh enough")
                return 1
            text = json.dumps(output["public_safe"])
            for marker in PRIVATE_MARKERS:
                if marker in text:
                    print(f"SELF-TEST FAIL: private marker leaked into public_safe: {marker}")
                    return 1
            target = output["public_safe"]["targets"][0]
            if target["candidate_status"] != "attention needed":
                print("SELF-TEST FAIL: failing report did not produce attention-needed candidate")
                return 1
            if target["non_passing_details"][0]["fixture"] != "weekly-review-private-report":
                print("SELF-TEST FAIL: non-passing detail fixture missing")
                return 1
            if (
                target["non_passing_details"][0].get("public_safe_diagnosis") != "investigation_needed"
                or target["non_passing_details"][0].get("suggested_next_step") != "Investigation needed."
            ):
                print("SELF-TEST FAIL: default public-safe curated fields were not emitted")
                print(json.dumps(target["non_passing_details"][0], indent=2))
                return 1
            private = output["private_locators"]["targets"][0]
            if private["source_report"]["core_safe"] is not False:
                print("SELF-TEST FAIL: private source report was not marked non-Core-safe")
                return 1

            dry_dir = reports / "guidance-dry"
            dry_dir.mkdir()
            dry_report = {**fake_guidance_report(commit="b" * 40), "mode": "dry-run"}
            dry_report["summary"] = {**dry_report["summary"], "status_eligible": False, "status_ineligible_reasons": ["dry-run"]}
            (dry_dir / "run.json").write_text(json.dumps(dry_report), encoding="utf-8")
            explicit_output, explicit_fresh = build_candidate(
                root,
                root / "os/verification/BENCHMARKS.json",
                root / "os/verification/BENCHMARK_STATUS.md",
                root,
                explicit_report=dry_dir / "run.json",
                now=now,
            )
            if explicit_fresh or explicit_output["public_safe"]["targets"][0]["candidate_available"]:
                print("SELF-TEST FAIL: explicit dry-run report was accepted")
                return 1

            harness_error_dir = reports / "guidance-harness-error"
            harness_error_dir.mkdir()
            harness_error_report = fake_guidance_report(commit="d" * 40)
            harness_error_report["summary"] = {
                **harness_error_report["summary"],
                "behavioral_total": 0,
                "behavioral_pass": 0,
                "behavioral_fail": 0,
                "harness_error": 8,
                "status_eligible": False,
                "status_ineligible_reasons": ["harness_error", "no_behavioral_or_stale_results"],
            }
            harness_error_report["results"] = [
                {
                    "fixture_id": "weekly-review-private-report",
                    "category": "review",
                    "status": "harness-error",
                    "host_boundary_sentinel_observed": False,
                    "harness_result": {
                        "exit_code": 1,
                        "stdout": "/" + "Users" + "/private should stay private",
                        "stderr": "model_not_found private detail should stay private",
                        "raw_response": "private raw failure",
                    },
                }
            ]
            (harness_error_dir / "run.json").write_text(json.dumps(harness_error_report), encoding="utf-8")
            diagnostic_output, diagnostic_fresh = build_candidate(
                root,
                root / "os/verification/BENCHMARKS.json",
                root / "os/verification/BENCHMARK_STATUS.md",
                root,
                explicit_report=harness_error_dir / "run.json",
                now=now,
            )
            diagnostic_target = diagnostic_output["public_safe"]["targets"][0]
            diagnostic_text = json.dumps(diagnostic_output["public_safe"])
            if diagnostic_fresh or diagnostic_target["candidate_available"]:
                print("SELF-TEST FAIL: explicit harness-error report was accepted")
                return 1
            latest = diagnostic_target.get("latest_report", {})
            details = latest.get("non_passing_details", []) if isinstance(latest, dict) else []
            if (
                not isinstance(latest, dict)
                or latest.get("counts", {}).get("harness_error") != 8
                or not details
                or details[0].get("public_safe_diagnosis") != "api_auth_or_model_access"
                or details[0].get("suggested_next_step") != "Investigation needed."
            ):
                print("SELF-TEST FAIL: public-safe harness diagnostic was not emitted")
                print(json.dumps(diagnostic_target, indent=2))
                return 1
            for marker in PRIVATE_MARKERS + ("private detail", "private raw failure"):
                if marker in diagnostic_text:
                    print(f"SELF-TEST FAIL: private harness detail leaked into public_safe: {marker}")
                    return 1

            bad_report = fake_guidance_report(commit="c" * 40)
            bad_report["results"][0]["fixture_id"] = "/" + "Users" + "/private"
            bad_dir = reports / "guidance-bad-safe-field"
            bad_dir.mkdir()
            (bad_dir / "run.json").write_text(json.dumps(bad_report), encoding="utf-8")
            try:
                build_candidate(
                    root,
                    root / "os/verification/BENCHMARKS.json",
                    root / "os/verification/BENCHMARK_STATUS.md",
                    root,
                    explicit_report=bad_dir / "run.json",
                    now=now,
                )
            except PublicSafeOutputError:
                pass
            else:
                print("SELF-TEST FAIL: unsafe fixture id was accepted")
                return 1

            unsupported_manifest = root / "os/verification/UNSUPPORTED.json"
            unsupported_manifest.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "benchmarks": [
                            {
                                "id": "future-suite",
                                "reports_dir": "personal/os/verification/future/reports",
                                "run_glob": "*/run.json",
                                "summary_path": ["summary"],
                                "weekly_review": {
                                    "check_freshness": True,
                                    "min_status_counting_total": 1,
                                    "max_age_days": 14,
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            try:
                build_candidate(root, unsupported_manifest, root / "os/verification/BENCHMARK_STATUS.md", root, now=now)
            except UnsupportedBenchmarkSuiteError:
                pass
            else:
                print("SELF-TEST FAIL: unsupported freshness target did not fail")
                return 1
    except RefreshCandidateError as error:
        print(f"SELF-TEST FAIL: unexpected helper error: {error}")
        return 1
    print("SELF-TEST PASS: benchmark status refresh helper boundaries are enforced")
    return 0


def fake_guidance_report(commit: str) -> dict[str, Any]:
    return {
        "benchmark": "guidance",
        "mode": "run",
        "generated_at": "2026-06-03T20:30:00+00:00",
        "git": {
            "branch": "main",
            "commit": commit,
            "upstream": "origin/main",
            "ahead": 0,
            "behind": 0,
            "remote_fresh": True,
            "eligible_fresh_main": True,
        },
        "summary": {
            "total": 8,
            "behavioral_total": 8,
            "behavioral_pass": 7,
            "behavioral_fail": 1,
            "fixture_stale": 0,
            "needs_user_judgment": 0,
            "harness_unavailable": 0,
            "harness_error": 0,
            "judge_unavailable": 0,
            "judge_error": 0,
            "judge_invalid": 0,
            "status_eligible": True,
            "status_ineligible_reasons": [],
            "model": "gpt-5.5",
            "effort": "low",
            "judge_harness": "codex",
            "judge_model": "gpt-5.5",
            "judge_effort": "low",
        },
        "fixtures": {
            "count": 8,
            "uses_default_path": True,
            "uses_full_default_set": True,
            "selected_subset": False,
        },
        "harnesses": ["codex"],
        "judge_protocol": {
            "uses_default_judge_schema_path": True,
            "uses_default_judge_prompt_path": True,
            "judge_batch_size": 0,
            "default_judge_batch_size": 0,
        },
        "host_boundary": {
            "marker_observed": False,
            "proves_isolation": False,
            "sentinel_path": "/" + "Users" + "/private/personal/os/context/SENTINEL.md",
        },
        "results": [
            {
                "fixture_id": "weekly-review-private-report",
                "category": "review",
                "status": "graded",
                "host_boundary_sentinel_observed": False,
                "harness_result": {
                    "raw_response": "private raw HUT answer",
                    "stdout": "/" + "Users" + "/private path",
                    "stderr": "do not leak",
                },
                "judge": {
                    "verdict": "fail",
                    "source_alignment": "wrong",
                    "staleness": "current",
                    "rationale": "private rationale must not leak",
                },
            },
            {
                "fixture_id": "github-cli-sandbox-auth",
                "category": "github",
                "status": "graded",
                "host_boundary_sentinel_observed": False,
                "harness_result": {"raw_response": "private passing answer"},
                "judge": {
                    "verdict": "pass",
                    "source_alignment": "aligned",
                    "staleness": "current",
                    "rationale": "private pass rationale",
                },
            },
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit public-safe benchmark status refresh candidates.")
    parser.add_argument("--root", type=Path, default=default_root(), help="AgentOS Core checkout root.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    parser.add_argument(
        "--personal-root",
        type=Path,
        default=None,
        help="AgentOS checkout root whose personal/os contains benchmark reports. Defaults to --root.",
    )
    parser.add_argument("--target", help="Current status-refresh target to inspect.")
    parser.add_argument("--report", type=Path, help="Inspect one explicit run.json report.")
    parser.add_argument("--now", help="Override current UTC timestamp for tests, ISO-8601.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    root = args.root.resolve()
    personal_root = (args.personal_root or root).resolve()
    manifest_path = resolve_path(root, args.manifest).resolve()
    status_path = resolve_path(root, args.status).resolve()
    explicit_report = resolve_path(personal_root, args.report).resolve() if args.report else None
    now = parse_timestamp(args.now) if args.now else utc_now()
    try:
        output, fresh_enough = build_candidate(
            root,
            manifest_path,
            status_path,
            personal_root,
            explicit_report=explicit_report,
            target_filter=args.target,
            now=now,
        )
    except PublicSafeOutputError as error:
        print(f"ERROR public-safe output invariant failed: {error}", file=sys.stderr)
        return EXIT_PRIVACY_ERROR
    except UnsupportedBenchmarkSuiteError as error:
        print(f"ERROR unsupported benchmark suite: {error}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    except RefreshCandidateError as error:
        print(f"ERROR benchmark status refresh candidate failed: {error}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    print_json(output)
    return EXIT_OK if fresh_enough else EXIT_NO_FRESH_CANDIDATE


if __name__ == "__main__":
    raise SystemExit(main())
