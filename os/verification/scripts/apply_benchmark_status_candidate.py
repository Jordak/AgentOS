#!/usr/bin/env python3
"""Apply public-safe benchmark refresh candidates to BENCHMARK_STATUS.md."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_STATUS = Path("os/verification/BENCHMARK_STATUS.md")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
STATUS_LABELS = {"passing", "attention needed", "not run", "unknown"}
WRITABLE_STATUS_LABELS = {"passing", "attention needed"}
STATUS_BLOCKER_RESULTS = (
    ("behavioral_fail", "Behavioral failure"),
    ("fixture_stale", "Fixture stale"),
    ("needs_user_judgment", "Needs user judgment"),
    ("harness_unavailable", "Harness unavailable"),
    ("harness_error", "Harness error"),
    ("judge_unavailable", "Judge unavailable"),
    ("judge_error", "Judge error"),
    ("judge_invalid", "Judge invalid"),
)
PRIVATE_MARKERS = (
    "/" + "Users" + "/",
    "\\Users\\",
    "personal/os/",
    "private_locators",
    "source_report",
    "raw_response",
    "harness_result",
    "stdout",
    "stderr",
    "rationale",
)


class StatusApplyError(ValueError):
    """Raised when a public-safe candidate cannot be applied."""


def default_root() -> Path:
    return Path(__file__).resolve().parents[3]


def resolve_path(root: Path, path: Path) -> Path:
    expanded = path.expanduser()
    if expanded.is_absolute():
        return expanded
    return root / expanded


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise StatusApplyError(f"candidate not found: {path}") from error
    except json.JSONDecodeError as error:
        raise StatusApplyError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(value, dict):
        raise StatusApplyError("expected top-level JSON object")
    return value


def public_targets(helper_output: dict[str, Any]) -> list[dict[str, Any]]:
    public_safe = helper_output.get("public_safe")
    if not isinstance(public_safe, dict):
        raise StatusApplyError("missing public_safe object")
    targets = public_safe.get("targets")
    if not isinstance(targets, list):
        raise StatusApplyError("public_safe.targets must be a list")
    parsed: list[dict[str, Any]] = []
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            raise StatusApplyError(f"public_safe.targets[{index}] must be an object")
        parsed.append(target)
    return parsed


def require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise StatusApplyError(f"{field} must be a non-empty string")
    return value


def optional_text(value: Any, default: str = "unknown") -> str:
    if value is None:
        return default
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float, str)):
        text = str(value)
        return text if text else default
    return default


def require_int(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise StatusApplyError(f"{field} must be a nonnegative integer")
    return value


def require_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise StatusApplyError(f"{field} must be a boolean")
    return value


def require_commit(value: Any, field: str) -> str:
    text = require_text(value, field)
    if not COMMIT_RE.fullmatch(text):
        raise StatusApplyError(f"{field} must be a 40-character lowercase hex commit")
    return text


def require_status(value: Any, field: str) -> str:
    text = require_text(value, field)
    if text not in STATUS_LABELS:
        raise StatusApplyError(f"{field} has unsupported status: {text}")
    return text


def require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StatusApplyError(f"{field} must be an object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise StatusApplyError(f"{field} must be a list")
    return value


def require_bool_value(value: Any, field: str, expected: bool) -> None:
    actual = require_bool(value, field)
    if actual is not expected:
        expected_text = "true" if expected else "false"
        raise StatusApplyError(f"{field} must be {expected_text}")


def markdown_cell(value: Any) -> str:
    text = optional_text(value, "n/a")
    return text.replace("|", "\\|").replace("\n", " ")


def title_text(value: str) -> str:
    return value.replace("-", " ").title()


def harness_label(scope: dict[str, Any]) -> str:
    harnesses = scope.get("harnesses")
    if isinstance(harnesses, list) and harnesses:
        return ", ".join(title_text(str(item)) for item in harnesses)
    return title_text(optional_text(scope.get("judge_harness"), "unknown"))


def evidence_scope_text(target: dict[str, Any]) -> str:
    scope = require_mapping(target.get("evidence_scope"), "evidence_scope")
    fixture_count = require_int(scope.get("fixture_count"), "evidence_scope.fixture_count")
    model = require_text(scope.get("model"), "evidence_scope.model")
    effort = require_text(scope.get("effort"), "evidence_scope.effort")
    judge_model = require_text(scope.get("judge_model"), "evidence_scope.judge_model")
    judge_effort = require_text(scope.get("judge_effort"), "evidence_scope.judge_effort")
    hut_config = scope.get("harness_user_config_allowed_for_hut")
    hut_config_text = ""
    if hut_config is True:
        hut_config_text = "HUT user config allowed; "
    elif hut_config is False:
        hut_config_text = "HUT user config disabled; "
    return (
        f"guidance {harness_label(scope)} harness; {hut_config_text}"
        f"{fixture_count} default guidance fixtures; {model} {effort}; judge {judge_model} {judge_effort}"
    )


def nonzero_count_parts(counts: dict[str, Any]) -> list[str]:
    fields = [
        ("behavioral_fail", "behavioral failures"),
        ("fixture_stale", "fixture-stale cases"),
        ("needs_user_judgment", "needs-user-judgment cases"),
        ("harness_unavailable", "harness-unavailable cases"),
        ("harness_error", "harness-error cases"),
        ("judge_unavailable", "judge-unavailable cases"),
        ("judge_error", "judge-error cases"),
        ("judge_invalid", "judge-invalid cases"),
    ]
    parts = []
    for field, label in fields:
        value = require_int(counts.get(field, 0), f"counts.{field}")
        if value:
            parts.append(f"{value} {label}")
    return parts


def status_blocker_count(counts: dict[str, Any]) -> int:
    return sum(
        require_int(counts.get(field, 0), f"counts.{field}")
        for field, _result in STATUS_BLOCKER_RESULTS
    )


def validate_non_passing_detail_coverage(counts: dict[str, Any], rows: list[Any]) -> None:
    expected_results = {result for _field, result in STATUS_BLOCKER_RESULTS}
    actual_by_result = {result: 0 for result in expected_results}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise StatusApplyError("non_passing_details rows must be objects")
        result = require_text(row.get("result"), f"non_passing_details[{index}].result")
        if result not in actual_by_result:
            raise StatusApplyError(f"non_passing_details[{index}].result has unsupported result: {result}")
        actual_by_result[result] += 1
    for field, result in STATUS_BLOCKER_RESULTS:
        expected = require_int(counts.get(field, 0), f"counts.{field}")
        actual = actual_by_result[result]
        if actual != expected:
            raise StatusApplyError(
                f"non_passing_details must contain {expected} {result} row(s); found {actual}"
            )


def validate_counts_for_write(target: dict[str, Any]) -> None:
    status = require_status(target.get("candidate_status"), "candidate_status")
    if status not in WRITABLE_STATUS_LABELS:
        raise StatusApplyError(f"candidate_status is not writable: {status}")
    counts = require_mapping(target.get("counts"), "counts")
    behavioral_total = require_int(counts.get("behavioral_total", 0), "counts.behavioral_total")
    behavioral_pass = require_int(counts.get("behavioral_pass", 0), "counts.behavioral_pass")
    behavioral_fail = require_int(counts.get("behavioral_fail", 0), "counts.behavioral_fail")
    fixture_stale = require_int(counts.get("fixture_stale", 0), "counts.fixture_stale")
    if behavioral_pass + behavioral_fail != behavioral_total:
        raise StatusApplyError("behavioral_pass + behavioral_fail must equal behavioral_total")
    status_counting_total = require_int(target.get("status_counting_total"), "status_counting_total")
    if status_counting_total != behavioral_total + fixture_stale:
        raise StatusApplyError("status_counting_total must equal behavioral_total + fixture_stale")
    details = require_list(target.get("non_passing_details", []), "non_passing_details")
    blockers = status_blocker_count(counts)
    if status == "passing":
        if blockers:
            raise StatusApplyError("passing candidates must not contain status-counting blockers")
        if details:
            raise StatusApplyError("passing candidates must not contain non-passing details")
    elif status == "attention needed" and blockers == 0 and not details:
        raise StatusApplyError("attention-needed candidates must contain a blocker count or non-passing details")
    elif status == "attention needed":
        validate_non_passing_detail_coverage(counts, details)


def validate_scope_for_write(target: dict[str, Any]) -> None:
    scope = require_mapping(target.get("evidence_scope"), "evidence_scope")
    require_bool_value(scope.get("uses_default_fixture_path"), "evidence_scope.uses_default_fixture_path", True)
    require_bool_value(scope.get("uses_full_default_fixture_set"), "evidence_scope.uses_full_default_fixture_set", True)
    require_bool_value(scope.get("selected_fixture_subset"), "evidence_scope.selected_fixture_subset", False)
    require_bool_value(
        scope.get("uses_default_judge_schema_path"),
        "evidence_scope.uses_default_judge_schema_path",
        True,
    )
    require_bool_value(
        scope.get("uses_default_judge_prompt_path"),
        "evidence_scope.uses_default_judge_prompt_path",
        True,
    )
    require_bool_value(
        scope.get("host_boundary_sentinel_observed"),
        "evidence_scope.host_boundary_sentinel_observed",
        False,
    )
    judge_batch_size = require_int(scope.get("judge_batch_size"), "evidence_scope.judge_batch_size")
    default_judge_batch_size = require_int(
        scope.get("default_judge_batch_size"),
        "evidence_scope.default_judge_batch_size",
    )
    if judge_batch_size != default_judge_batch_size:
        raise StatusApplyError("evidence_scope.judge_batch_size must equal default_judge_batch_size")


def validate_target_for_write(target: dict[str, Any]) -> None:
    validate_counts_for_write(target)
    validate_scope_for_write(target)


def summary_text(target: dict[str, Any]) -> str:
    counts = require_mapping(target.get("counts"), "counts")
    behavioral_total = require_int(counts.get("behavioral_total", 0), "counts.behavioral_total")
    behavioral_pass = require_int(counts.get("behavioral_pass", 0), "counts.behavioral_pass")
    status = require_status(target.get("candidate_status"), "candidate_status")
    if status == "passing":
        return (
            f"Codex produced judged responses for all {behavioral_total} default Guidance scenarios "
            f"and passed {behavioral_pass} behavioral checks. No status-counting behavioral failures "
            "or fixture-stale cases were reported."
        )
    parts = nonzero_count_parts(counts)
    if not parts:
        parts = ["a non-passing status signal"]
    return (
        f"Codex produced judged responses for {behavioral_total} default Guidance scenarios and passed "
        f"{behavioral_pass} behavioral checks. Status-counting results include {', '.join(parts)}. "
        "The non-passing details below provide public-safe result classes for investigation."
    )


def caveats_text(target: dict[str, Any]) -> str:
    counts = require_mapping(target.get("counts"), "counts")
    scope = require_mapping(target.get("evidence_scope"), "evidence_scope")
    zero_fields = [
        ("fixture_stale", "fixture-stale cases"),
        ("needs_user_judgment", "needs-user-judgment cases"),
        ("harness_unavailable", "harness-unavailable cases"),
        ("harness_error", "harness-error cases"),
        ("judge_unavailable", "judge-unavailable cases"),
        ("judge_error", "judge-error cases"),
        ("judge_invalid", "judge-invalid cases"),
    ]
    no_reported = [
        label
        for field, label in zero_fields
        if require_int(counts.get(field, 0), f"counts.{field}") == 0
    ]
    sentinel = scope.get("host_boundary_sentinel_observed")
    if sentinel is False:
        sentinel_text = (
            "The host-boundary sentinel was not observed, which satisfies the contamination tripwire "
            "for this status run but does not prove full host filesystem isolation."
        )
    elif sentinel is True:
        sentinel_text = "The host-boundary sentinel was observed; treat this evidence as requiring attention."
    else:
        sentinel_text = "The host-boundary sentinel observation state was not reported."
    no_reported_text = f"No {', '.join(no_reported)} were reported. " if no_reported else ""
    return (
        f"{no_reported_text}{sentinel_text} This status uses a full default, status-eligible run from "
        "clean remote-fresh `main`; diagnostic non-default fixture or judge-protocol runs remain useful "
        "for investigation but are not status evidence."
    )


def diagnosis_for(row: dict[str, Any]) -> str:
    return require_text(
        row.get("public_safe_diagnosis"),
        "non_passing_details.public_safe_diagnosis",
    )


def next_step_for(row: dict[str, Any]) -> str:
    return require_text(
        row.get("suggested_next_step"),
        "non_passing_details.suggested_next_step",
    )


def render_non_passing_details(rows: list[Any]) -> list[str]:
    if not rows:
        return []
    lines = [
        "",
        "#### Non-Passing Details",
        "",
        "| Fixture | Category | Result | Public-safe diagnosis | Suggested next step |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        if not isinstance(row, dict):
            raise StatusApplyError("non_passing_details rows must be objects")
        fixture = require_text(row.get("fixture"), "non_passing_details.fixture")
        category = require_text(row.get("category"), "non_passing_details.category")
        result = require_text(row.get("result"), "non_passing_details.result")
        lines.append(
            "| `{fixture}` | {category} | {result} | {diagnosis} | {next_step} |".format(
                fixture=markdown_cell(fixture),
                category=markdown_cell(category),
                result=markdown_cell(result),
                diagnosis=markdown_cell(diagnosis_for(row)),
                next_step=markdown_cell(next_step_for(row)),
            )
        )
    return lines


def render_guidance_codex_section(target: dict[str, Any]) -> str:
    if require_text(target.get("benchmark"), "benchmark") != "guidance":
        raise StatusApplyError("only the guidance benchmark target is supported")
    if require_bool(target.get("candidate_available"), "candidate_available") is not True:
        raise StatusApplyError("candidate is not available")
    validate_target_for_write(target)
    status = require_status(target.get("candidate_status"), "candidate_status")
    revision = require_commit(target.get("reviewed_core_revision"), "reviewed_core_revision")
    evidence = require_text(target.get("last_reviewed_evidence"), "last_reviewed_evidence")
    lines = [
        "### Codex",
        "",
        f"- Status: `{status}`",
        f"- Reviewed Core revision: `{revision}`",
        f"- Last reviewed evidence: `{evidence}`",
        f"- Evidence scope: `{evidence_scope_text(target)}`",
        f"- Summary: {summary_text(target)}",
        f"- Caveats: {caveats_text(target)}",
    ]
    rows = require_list(target.get("non_passing_details", []), "non_passing_details")
    lines.extend(render_non_passing_details(rows))
    return "\n".join(lines).rstrip() + "\n"


def replace_guidance_codex(status_text: str, replacement: str) -> str:
    guidance_match = re.search(r"(?m)^## Guidance\s*$", status_text)
    if not guidance_match:
        raise StatusApplyError("BENCHMARK_STATUS.md is missing ## Guidance")
    section_start = guidance_match.end()
    next_benchmark = re.search(r"(?m)^## ", status_text[section_start:])
    guidance_end = section_start + next_benchmark.start() if next_benchmark else len(status_text)
    guidance_section = status_text[section_start:guidance_end]
    codex_match = re.search(r"(?m)^### Codex\s*$", guidance_section)
    if not codex_match:
        raise StatusApplyError("BENCHMARK_STATUS.md is missing ### Codex under ## Guidance")
    codex_start = section_start + codex_match.start()
    after_codex_start = section_start + codex_match.end()
    next_harness = re.search(r"(?m)^### ", status_text[after_codex_start:guidance_end])
    codex_end = after_codex_start + next_harness.start() if next_harness else guidance_end
    before = status_text[:codex_start].rstrip() + "\n\n"
    after = status_text[codex_end:].lstrip("\n")
    return before + replacement.rstrip() + "\n" + ("\n" + after if after else "")


def validate_no_private_markers(text: str) -> None:
    for marker in PRIVATE_MARKERS:
        if marker in text:
            raise StatusApplyError(f"private marker leaked into status output: {marker}")


def single_public_target(helper_output: dict[str, Any]) -> dict[str, Any]:
    targets = public_targets(helper_output)
    if len(targets) != 1:
        raise StatusApplyError("expected exactly one public-safe benchmark target")
    return targets[0]


def validate_expected_revision(target: dict[str, Any], expected_revision: str | None) -> None:
    if expected_revision is None:
        return
    expected = require_commit(expected_revision, "expected_revision")
    reviewed = require_commit(target.get("reviewed_core_revision"), "reviewed_core_revision")
    if reviewed != expected:
        raise StatusApplyError(
            "candidate reviewed_core_revision does not match writer checkout: "
            f"{reviewed} != {expected}"
        )


def apply_candidate(
    helper_output: dict[str, Any],
    status_text: str,
    expected_revision: str | None = None,
) -> str:
    target = single_public_target(helper_output)
    validate_expected_revision(target, expected_revision)
    replacement = render_guidance_codex_section(target)
    validate_no_private_markers(replacement)
    updated = replace_guidance_codex(status_text, replacement)
    return updated


def write_status_from_candidate(input_path: Path, status_path: Path, expected_revision: str | None = None) -> bool:
    helper_output = read_json(input_path)
    original = status_path.read_text(encoding="utf-8")
    updated = apply_candidate(helper_output, original, expected_revision=expected_revision)
    if updated == original:
        return False
    status_path.write_text(updated, encoding="utf-8")
    return True


def fake_status() -> str:
    return (
        "# AgentOS Benchmark Status\n\n"
        "Status: Core benchmark snapshot v1.\n\n"
        "Raw reports, stdout, stderr, and personal/os/ paths are examples of non-Core evidence.\n\n"
        "## Guidance\n\n"
        "### Codex\n\n"
        "- Status: `attention needed`\n"
        "- Reviewed Core revision: `1111111111111111111111111111111111111111`\n"
        "- Last reviewed evidence: `2026-06-03 13:12 PDT`\n"
        "- Evidence scope: `old scope`\n"
        "- Summary: Old failing summary.\n"
        "- Caveats: Old caveats.\n\n"
        "#### Non-Passing Details\n\n"
        "| Fixture | Category | Result | Public-safe diagnosis | Suggested next step |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| `old-fixture` | old | Behavioral failure | old | old |\n"
    )


def fake_target(status: str = "passing", details: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    behavioral_fail = 0 if status == "passing" else 1
    return {
        "benchmark": "guidance",
        "candidate_available": True,
        "candidate_status": status,
        "reviewed_core_revision": "a" * 40,
        "last_reviewed_evidence": "2026-06-05T14:35:42.577146+00:00",
        "status_counting_total": 15,
        "counts": {
            "total": 15,
            "behavioral_total": 15,
            "behavioral_pass": 15 - behavioral_fail,
            "behavioral_fail": behavioral_fail,
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
            "harness_user_config_allowed_for_hut": True,
            "model": "gpt-5.5",
            "effort": "low",
            "judge_harness": "codex",
            "judge_model": "gpt-5.5",
            "judge_effort": "low",
            "fixture_count": 15,
            "uses_default_fixture_path": True,
            "uses_full_default_fixture_set": True,
            "selected_fixture_subset": False,
            "uses_default_judge_schema_path": True,
            "uses_default_judge_prompt_path": True,
            "judge_batch_size": 0,
            "default_judge_batch_size": 0,
            "host_boundary_sentinel_observed": False,
            "host_boundary_sentinel_proves_isolation": False,
        },
        "non_passing_details": details or [],
    }


def fake_candidate(target: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": 1,
        "generated_at": "2026-06-05T14:36:00+00:00",
        "public_safe": {"targets": [target]},
        "private_locators": {
            "core_safe": False,
            "targets": [
                {
                    "benchmark": "guidance",
                    "source_report": {
                        "path": "/" + "Users" + "/private/personal/os/verification/guidance/reports/run.json",
                        "core_safe": False,
                    },
                }
            ],
        },
    }


def run_self_test() -> int:
    try:
        passing = apply_candidate(fake_candidate(fake_target()), fake_status())
        expected_fragments = [
            "- Status: `passing`",
            "- Reviewed Core revision: `" + "a" * 40 + "`",
            "- Last reviewed evidence: `2026-06-05T14:35:42.577146+00:00`",
            "HUT user config allowed",
            "passed 15 behavioral checks",
        ]
        missing = [fragment for fragment in expected_fragments if fragment not in passing]
        if missing:
            print("SELF-TEST FAIL: passing update fragments missing")
            print(json.dumps(missing, indent=2))
            return 1
        if "old-fixture" in passing or "#### Non-Passing Details" in passing:
            print("SELF-TEST FAIL: stale non-passing details were not removed")
            return 1
        locator_forbidden = ["/" + "Users" + "/private", "private_locators", "source_report"]
        for marker in locator_forbidden:
            if marker in passing:
                print(f"SELF-TEST FAIL: private locator marker leaked from ignored locators: {marker}")
                return 1
        try:
            apply_candidate(fake_candidate(fake_target()), fake_status(), expected_revision="b" * 40)
        except StatusApplyError:
            pass
        else:
            print("SELF-TEST FAIL: mismatched expected revision was accepted")
            return 1

        detail = {
            "fixture": "weekly-review-private-report",
            "category": "Review / Personal Overlay",
            "result": "Behavioral failure",
            "status": "graded",
            "verdict": "fail",
            "source_alignment": "wrong",
            "staleness": "current",
            "host_boundary_sentinel_observed": False,
            "public_safe_diagnosis": (
                "Behavioral failure reported with status `graded`, verdict `fail`, source alignment `wrong`, "
                "staleness `current`, and host-boundary sentinel observed `no`."
            ),
            "suggested_next_step": (
                "Review the fixture expectation and Guidance source for this scenario, then rerun the status benchmark."
            ),
        }
        failing = apply_candidate(fake_candidate(fake_target("attention needed", [detail])), fake_status())
        failing_fragments = [
            "- Status: `attention needed`",
            "#### Non-Passing Details",
            "`weekly-review-private-report`",
            "Behavioral failure reported with status `graded`",
            "Review the fixture expectation",
        ]
        missing_failing = [fragment for fragment in failing_fragments if fragment not in failing]
        if missing_failing:
            print("SELF-TEST FAIL: non-passing update fragments missing")
            print(json.dumps(missing_failing, indent=2))
            return 1

        unavailable = fake_target()
        unavailable["candidate_available"] = False
        malformed_cases = [
            {},
            {"public_safe": {}},
            {"public_safe": {"targets": []}},
            {"public_safe": {"targets": [None]}},
            fake_candidate(unavailable),
        ]
        bad_count_total = fake_target()
        bad_count_total["counts"]["behavioral_pass"] = 14
        malformed_cases.append(fake_candidate(bad_count_total))

        bad_status_counting_total = fake_target()
        bad_status_counting_total["status_counting_total"] = 14
        malformed_cases.append(fake_candidate(bad_status_counting_total))

        passing_with_details = fake_target(
            details=[
                {
                    "fixture": "weekly-review-private-report",
                    "category": "Review",
                    "result": "Behavioral failure",
                }
            ]
        )
        malformed_cases.append(fake_candidate(passing_with_details))

        attention_without_signal = fake_target("attention needed")
        attention_without_signal["counts"]["behavioral_pass"] = 15
        attention_without_signal["counts"]["behavioral_fail"] = 0
        malformed_cases.append(fake_candidate(attention_without_signal))

        attention_without_details = fake_target("attention needed")
        malformed_cases.append(fake_candidate(attention_without_details))

        attention_wrong_detail_class = fake_target(
            "attention needed",
            [
                {
                    "fixture": "weekly-review-private-report",
                    "category": "Review",
                    "result": "Fixture stale",
                }
            ],
        )
        malformed_cases.append(fake_candidate(attention_wrong_detail_class))

        noncanonical_scope = fake_target()
        noncanonical_scope["evidence_scope"]["selected_fixture_subset"] = True
        malformed_cases.append(fake_candidate(noncanonical_scope))

        nondefault_judge_batch = fake_target()
        nondefault_judge_batch["evidence_scope"]["judge_batch_size"] = 1
        malformed_cases.append(fake_candidate(nondefault_judge_batch))

        for case in malformed_cases:
            try:
                apply_candidate(case, fake_status())
            except StatusApplyError:
                pass
            else:
                print("SELF-TEST FAIL: malformed or unavailable candidate was accepted")
                print(json.dumps(case, indent=2))
                return 1

        with tempfile.TemporaryDirectory(prefix="agentos-apply-status-self-test-") as tmp:
            root = Path(tmp)
            status_path = root / "BENCHMARK_STATUS.md"
            candidate_path = root / "candidate.json"
            status_path.write_text(fake_status(), encoding="utf-8")
            candidate_path.write_text(json.dumps(fake_candidate(fake_target())), encoding="utf-8")
            if not write_status_from_candidate(candidate_path, status_path, expected_revision="a" * 40):
                print("SELF-TEST FAIL: file apply did not report a change")
                return 1
            if write_status_from_candidate(candidate_path, status_path, expected_revision="a" * 40):
                print("SELF-TEST FAIL: idempotent file apply reported a second change")
                return 1
    except StatusApplyError as error:
        print(f"SELF-TEST FAIL: unexpected status apply error: {error}")
        return 1
    print("SELF-TEST PASS: benchmark status applicator boundaries are enforced")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply public-safe benchmark refresh candidates to BENCHMARK_STATUS.md.")
    parser.add_argument("input", type=Path, nargs="?", help="JSON output from refresh_benchmark_status.py.")
    parser.add_argument("--root", type=Path, default=default_root(), help="AgentOS checkout root.")
    parser.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    parser.add_argument(
        "--expected-revision",
        help="Reject candidates whose reviewed_core_revision does not match this checkout revision.",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()
    if args.input is None:
        print("ERROR input path is required unless --self-test is used", file=sys.stderr)
        return 2
    root = args.root.resolve()
    input_path = resolve_path(root, args.input).resolve()
    status_path = resolve_path(root, args.status).resolve()
    try:
        changed = write_status_from_candidate(input_path, status_path, expected_revision=args.expected_revision)
    except (OSError, StatusApplyError) as error:
        print(f"ERROR benchmark status apply failed: {error}", file=sys.stderr)
        return 2
    print(f"benchmark_status_changed={'true' if changed else 'false'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
