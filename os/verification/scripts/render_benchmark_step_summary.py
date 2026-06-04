#!/usr/bin/env python3
"""Render public-safe benchmark refresh output for GitHub step summaries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class SummaryRenderError(ValueError):
    """Raised when refresh helper output cannot be rendered safely."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SummaryRenderError(f"input not found: {path}") from error
    except json.JSONDecodeError as error:
        raise SummaryRenderError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(value, dict):
        raise SummaryRenderError("expected top-level JSON object")
    return value


def as_bool_text(value: Any) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def as_text(value: Any, default: str = "unknown") -> str:
    if value is None:
        return default
    if isinstance(value, bool):
        return as_bool_text(value)
    if isinstance(value, (int, float, str)):
        text = str(value)
        return text if text else default
    return default


def comma_list(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "none"
    return ", ".join(as_text(item) for item in value)


def short_commit(value: Any) -> str:
    text = as_text(value)
    if len(text) == 40 and all(char in "0123456789abcdefABCDEF" for char in text):
        return text[:12]
    return text


def get_public_safe(helper_output: dict[str, Any]) -> dict[str, Any]:
    public_safe = helper_output.get("public_safe")
    if not isinstance(public_safe, dict):
        raise SummaryRenderError("missing public_safe object")
    targets = public_safe.get("targets")
    if not isinstance(targets, list):
        raise SummaryRenderError("public_safe.targets must be a list")
    return public_safe


def render_counts(counts: dict[str, Any]) -> list[str]:
    return [
        "",
        "| Count | Value |",
        "| --- | ---: |",
        f"| Total | {as_text(counts.get('total'), '0')} |",
        f"| Behavioral pass | {as_text(counts.get('behavioral_pass'), '0')} |",
        f"| Behavioral fail | {as_text(counts.get('behavioral_fail'), '0')} |",
        f"| Fixture stale | {as_text(counts.get('fixture_stale'), '0')} |",
        f"| Needs user judgment | {as_text(counts.get('needs_user_judgment'), '0')} |",
        f"| Harness unavailable | {as_text(counts.get('harness_unavailable'), '0')} |",
        f"| Harness error | {as_text(counts.get('harness_error'), '0')} |",
        f"| Judge unavailable | {as_text(counts.get('judge_unavailable'), '0')} |",
        f"| Judge error | {as_text(counts.get('judge_error'), '0')} |",
        f"| Judge invalid | {as_text(counts.get('judge_invalid'), '0')} |",
    ]


def render_scope(scope: dict[str, Any]) -> list[str]:
    return [
        "",
        "#### Evidence Scope",
        "",
        f"- Harnesses: `{comma_list(scope.get('harnesses'))}`",
        f"- HUT user config: `{as_bool_text(scope.get('harness_user_config_allowed_for_hut'))}`",
        f"- Model: `{as_text(scope.get('model'))}`",
        f"- Effort: `{as_text(scope.get('effort'))}`",
        f"- Judge harness: `{as_text(scope.get('judge_harness'))}`",
        f"- Judge model: `{as_text(scope.get('judge_model'))}`",
        f"- Judge effort: `{as_text(scope.get('judge_effort'))}`",
        f"- Fixture count: `{as_text(scope.get('fixture_count'))}`",
        f"- Default fixture path: `{as_bool_text(scope.get('uses_default_fixture_path'))}`",
        f"- Full default fixture set: `{as_bool_text(scope.get('uses_full_default_fixture_set'))}`",
        f"- Selected fixture subset: `{as_bool_text(scope.get('selected_fixture_subset'))}`",
        f"- Default judge schema: `{as_bool_text(scope.get('uses_default_judge_schema_path'))}`",
        f"- Default judge prompt: `{as_bool_text(scope.get('uses_default_judge_prompt_path'))}`",
        f"- Judge batch size: `{as_text(scope.get('judge_batch_size'))}`",
        f"- Host-boundary sentinel observed: `{as_bool_text(scope.get('host_boundary_sentinel_observed'))}`",
        f"- Host-boundary sentinel proves isolation: `{as_bool_text(scope.get('host_boundary_sentinel_proves_isolation'))}`",
    ]


def render_non_passing(rows: list[Any]) -> list[str]:
    if not rows:
        return []
    lines = [
        "",
        "#### Non-Passing Structured Details",
        "",
        "| Fixture | Category | Result | Status | Public diagnosis | Verdict | Source alignment | Staleness | Sentinel observed |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        if not isinstance(row, dict):
            continue
        lines.append(
            "| {fixture} | {category} | {result} | {status} | {diagnosis} | {verdict} | {source} | {staleness} | {sentinel} |".format(
                fixture=f"`{as_text(row.get('fixture'))}`",
                category=as_text(row.get("category")),
                result=as_text(row.get("result")),
                status=as_text(row.get("status")),
                diagnosis=as_text(row.get("public_safe_diagnosis"), "n/a"),
                verdict=as_text(row.get("verdict"), "n/a"),
                source=as_text(row.get("source_alignment"), "n/a"),
                staleness=as_text(row.get("staleness"), "n/a"),
                sentinel=as_bool_text(row.get("host_boundary_sentinel_observed")),
            )
        )
    return lines


def render_target(target: dict[str, Any]) -> list[str]:
    benchmark = as_text(target.get("benchmark"))
    lines = [
        f"### {benchmark}",
        "",
        f"- Candidate available: `{as_bool_text(target.get('candidate_available'))}`",
        f"- Current status: `{as_text(target.get('current_status'))}`",
        f"- Current reviewed revision: `{short_commit(target.get('current_reviewed_core_revision'))}`",
        f"- Current last reviewed evidence: `{as_text(target.get('current_last_reviewed_evidence'))}`",
        f"- Report count inspected: `{as_text(target.get('report_count'), '0')}`",
        f"- Eligible report count: `{as_text(target.get('eligible_report_count'), '0')}`",
        f"- Freshness classes: `{comma_list(target.get('freshness_classes'))}`",
    ]
    if target.get("candidate_available") is not True:
        lines.append(f"- Candidate unavailable reason: `{as_text(target.get('candidate_unavailable_reason'))}`")
        latest = target.get("latest_report")
        if isinstance(latest, dict):
            lines.extend(
                [
                    f"- Latest report generated: `{as_text(latest.get('generated_at'))}`",
                    f"- Latest report status eligible: `{as_bool_text(latest.get('status_eligible'))}`",
                    f"- Latest report ineligible reasons: `{comma_list(latest.get('status_ineligible_reasons'))}`",
                    f"- Latest report status-counting total: `{as_text(latest.get('status_counting_total'))}`",
                ]
            )
            counts = latest.get("counts")
            if isinstance(counts, dict):
                lines.extend(render_counts(counts))
            scope = latest.get("evidence_scope")
            if isinstance(scope, dict):
                lines.extend(render_scope(scope))
            details = latest.get("non_passing_details")
            if isinstance(details, list):
                lines.extend(render_non_passing(details))
        return lines

    lines.extend(
        [
            f"- Candidate status: `{as_text(target.get('candidate_status'))}`",
            f"- Candidate reviewed revision: `{short_commit(target.get('reviewed_core_revision'))}`",
            f"- Candidate evidence timestamp: `{as_text(target.get('last_reviewed_evidence'))}`",
            f"- Evidence age days: `{as_text(target.get('evidence_age_days'))}`",
            f"- Max age days: `{as_text(target.get('max_age_days'))}`",
            f"- Status-counting total: `{as_text(target.get('status_counting_total'))}`",
        ]
    )
    counts = target.get("counts")
    if isinstance(counts, dict):
        lines.extend(render_counts(counts))
    scope = target.get("evidence_scope")
    if isinstance(scope, dict):
        lines.extend(render_scope(scope))
    details = target.get("non_passing_details")
    if isinstance(details, list):
        lines.extend(render_non_passing(details))
    return lines


def render_summary(helper_output: dict[str, Any]) -> str:
    public_safe = get_public_safe(helper_output)
    targets = public_safe["targets"]
    lines = [
        "## Guidance Benchmark Trial",
        "",
        "Public-safe summary generated from `refresh-benchmark-status` candidate facts.",
        "",
    ]
    if not targets:
        lines.append("No current benchmark status-refresh targets were reported.")
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            raise SummaryRenderError(f"public_safe.targets[{index}] must be an object")
        if index:
            lines.append("")
        lines.extend(render_target(target))
    return "\n".join(lines).rstrip() + "\n"


def run_self_test() -> int:
    private_path = "/" + "Users" + "/private/personal/os/verification/guidance/reports/raw/run.json"
    helper_output = {
        "version": 1,
        "generated_at": "2026-06-04T20:00:00+00:00",
        "public_safe": {
            "targets": [
                {
                    "benchmark": "guidance",
                    "current_status": "attention needed",
                    "current_reviewed_core_revision": "1" * 40,
                    "current_last_reviewed_evidence": "2026-06-03 13:12 PDT",
                    "report_count": 1,
                    "eligible_report_count": 1,
                    "freshness_classes": ["newer_than_status"],
                    "candidate_available": True,
                    "candidate_status": "attention needed",
                    "reviewed_core_revision": "a" * 40,
                    "last_reviewed_evidence": "2026-06-04T20:00:00+00:00",
                    "evidence_age_days": 0.1,
                    "max_age_days": 14,
                    "status_counting_total": 8,
                    "counts": {
                        "total": 8,
                        "behavioral_pass": 7,
                        "behavioral_fail": 1,
                        "fixture_stale": 0,
                        "needs_user_judgment": 0,
                        "harness_unavailable": 0,
                        "harness_error": 0,
                        "judge_unavailable": 0,
                        "judge_error": 0,
                        "judge_invalid": 0,
                    },
                    "evidence_scope": {
                        "harnesses": ["codex"],
                        "model": "gpt-5.5",
                        "effort": "low",
                        "judge_harness": "codex",
                        "judge_model": "gpt-5.5",
                        "judge_effort": "low",
                        "fixture_count": 8,
                        "uses_default_fixture_path": True,
                        "uses_full_default_fixture_set": True,
                        "selected_fixture_subset": False,
                        "uses_default_judge_schema_path": True,
                        "uses_default_judge_prompt_path": True,
                        "judge_batch_size": 0,
                        "host_boundary_sentinel_observed": False,
                        "host_boundary_sentinel_proves_isolation": False,
                    },
                    "non_passing_details": [
                        {
                            "fixture": "weekly-review-private-report",
                            "category": "review",
                            "result": "Behavioral failure",
                            "status": "graded",
                            "public_safe_diagnosis": "n/a",
                            "verdict": "fail",
                            "source_alignment": "wrong",
                            "staleness": "current",
                            "host_boundary_sentinel_observed": False,
                        }
                    ],
                }
            ]
        },
        "private_locators": {
            "core_safe": False,
            "targets": [
                {
                    "benchmark": "guidance",
                    "source_report": {
                        "path": private_path,
                        "core_safe": False,
                    },
                }
            ],
        },
    }
    rendered = render_summary(helper_output)
    expected_fragments = [
        "## Guidance Benchmark Trial",
        "### guidance",
        "Candidate available: `yes`",
        "Candidate status: `attention needed`",
        "| Behavioral pass | 7 |",
        "Public diagnosis",
        "`weekly-review-private-report`",
        "Host-boundary sentinel observed: `no`",
    ]
    missing = [fragment for fragment in expected_fragments if fragment not in rendered]
    if missing:
        print("SELF-TEST FAIL: expected summary fragments missing")
        print(json.dumps(missing, indent=2))
        return 1
    forbidden = ["private_locators", private_path, "source_report", "personal/os/verification"]
    leaked = [fragment for fragment in forbidden if fragment in rendered]
    if leaked:
        print("SELF-TEST FAIL: private locator content leaked")
        print(json.dumps(leaked, indent=2))
        return 1
    unavailable = {
        "public_safe": {
            "targets": [
                {
                    "benchmark": "guidance",
                    "candidate_available": False,
                    "candidate_unavailable_reason": "no_eligible_status_counting_report",
                    "current_status": "attention needed",
                    "report_count": 1,
                    "eligible_report_count": 0,
                    "latest_report": {
                        "generated_at": "2026-06-04T21:08:46+00:00",
                        "status_eligible": False,
                        "status_ineligible_reasons": ["harness_error", "no_behavioral_or_stale_results"],
                        "status_counting_total": 0,
                        "counts": {
                            "total": 8,
                            "behavioral_pass": 0,
                            "behavioral_fail": 0,
                            "fixture_stale": 0,
                            "needs_user_judgment": 0,
                            "harness_unavailable": 0,
                            "harness_error": 8,
                            "judge_unavailable": 0,
                            "judge_error": 0,
                            "judge_invalid": 0,
                        },
                        "evidence_scope": {
                            "harnesses": ["codex"],
                            "model": "gpt-5.5",
                            "effort": "low",
                            "judge_harness": "codex",
                            "judge_model": "gpt-5.5",
                            "judge_effort": "low",
                            "fixture_count": 8,
                            "uses_default_fixture_path": True,
                            "uses_full_default_fixture_set": True,
                            "selected_fixture_subset": False,
                            "uses_default_judge_schema_path": True,
                            "uses_default_judge_prompt_path": True,
                            "judge_batch_size": 0,
                            "host_boundary_sentinel_observed": False,
                            "host_boundary_sentinel_proves_isolation": False,
                        },
                        "non_passing_details": [
                            {
                                "fixture": "weekly-review-private-report",
                                "category": "review",
                                "result": "Harness error",
                                "status": "harness-error",
                                "public_safe_diagnosis": "api_auth_or_model_access",
                                "host_boundary_sentinel_observed": False,
                            }
                        ],
                    },
                }
            ]
        }
    }
    unavailable_rendered = render_summary(unavailable)
    unavailable_expected = [
        "Candidate unavailable reason: `no_eligible_status_counting_report`",
        "| Harness error | 8 |",
        "api_auth_or_model_access",
    ]
    missing_unavailable = [fragment for fragment in unavailable_expected if fragment not in unavailable_rendered]
    if missing_unavailable:
        print("SELF-TEST FAIL: unavailable candidate details missing")
        print(json.dumps(missing_unavailable, indent=2))
        return 1
    for bad in ({}, {"public_safe": {}}, {"public_safe": {"targets": [None]}}):
        try:
            render_summary(bad)
        except SummaryRenderError:
            pass
        else:
            print("SELF-TEST FAIL: malformed helper output was accepted")
            print(json.dumps(bad, indent=2))
            return 1
    print("SELF-TEST PASS: benchmark step summary renderer is public-safe")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render public-safe benchmark refresh output for a GitHub step summary.")
    parser.add_argument("input", type=Path, nargs="?", help="JSON output from refresh_benchmark_status.py.")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic renderer self-tests.")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()
    if args.input is None:
        print("ERROR input path is required unless --self-test is used", file=sys.stderr)
        return 2
    try:
        rendered = render_summary(read_json(args.input))
    except SummaryRenderError as error:
        print(f"ERROR benchmark step summary render failed: {error}", file=sys.stderr)
        return 2
    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
