#!/usr/bin/env python3
"""Check whether saved harness benchmark runs are fresh enough for Weekly Review."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path("os/verification/BENCHMARKS.json")

HARNESS_UNAVAILABLE_PATTERNS = (
    "is not installed",
    "failed to initialize in-process app-server client",
    "failed to initialize state runtime",
    "attempt to write a readonly database",
    "Error finding codex home",
    "CODEX_HOME points to",
)


@dataclass(frozen=True)
class BenchmarkTarget:
    name: str
    reports_dir: Path
    run_glob: str
    summary_path: tuple[str, ...]
    min_status_counting_total: int
    max_age_days: int


@dataclass(frozen=True)
class RunRecord:
    path: Path
    generated_at: datetime
    total: int
    behavioral_total: int
    behavioral_pass: int
    behavioral_fail: int
    fixture_stale: int
    status_counting_total: int
    harness_unavailable: int


def default_root() -> Path:
    return Path(__file__).resolve().parents[3]


def resolve_root_path(root: Path, raw_path: Path) -> Path:
    expanded = raw_path.expanduser()
    if expanded.is_absolute():
        return expanded
    return root / expanded


def parse_timestamp(raw: str) -> datetime:
    value = raw.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def nested_get(value: dict[str, Any], path: tuple[str, ...]) -> dict[str, Any] | None:
    current: Any = value
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current if isinstance(current, dict) else None


def load_run(path: Path, summary_path: tuple[str, ...]) -> RunRecord | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    generated = data.get("generated_at")
    if not isinstance(generated, str):
        return None
    summary = nested_get(data, summary_path)
    if summary is None:
        return None
    if not report_is_status_eligible(data, summary):
        return None
    total = summary_int(summary, "total", 0)
    harness_unavailable = summary_int(
        summary,
        "harness_unavailable",
        inferred_harness_unavailable(data, summary_path),
    )
    if total is None or harness_unavailable is None:
        return None
    behavioral_total = summary_int(summary, "behavioral_total", total - harness_unavailable)
    if behavioral_total is None:
        return None
    behavioral_pass_default = summary.get("overall_pass", 0) if behavioral_total else 0
    behavioral_fail_default = summary.get("overall_fail", 0) if behavioral_total else 0
    behavioral_pass = summary_int(summary, "behavioral_pass", behavioral_pass_default)
    behavioral_fail = summary_int(summary, "behavioral_fail", behavioral_fail_default)
    fixture_stale = summary_int(summary, "fixture_stale", 0)
    if behavioral_pass is None or behavioral_fail is None or fixture_stale is None:
        return None
    status_counting_total = behavioral_total + fixture_stale
    try:
        generated_at = parse_timestamp(generated)
    except ValueError:
        return None
    return RunRecord(
        path=path,
        generated_at=generated_at,
        total=total,
        behavioral_total=behavioral_total,
        behavioral_pass=behavioral_pass,
        behavioral_fail=behavioral_fail,
        fixture_stale=fixture_stale,
        status_counting_total=status_counting_total,
        harness_unavailable=harness_unavailable,
    )


def summary_int(summary: dict[str, Any], field: str, default: Any) -> int | None:
    value = summary.get(field, default)
    if value is None:
        value = default
    if type(value) is bool:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def report_is_status_eligible(data: dict[str, Any], summary: dict[str, Any]) -> bool:
    if summary.get("status_eligible") is not True:
        return False
    if data.get("mode") not in (None, "run"):
        return False
    git_state = data.get("git")
    return isinstance(git_state, dict) and git_state.get("eligible_fresh_main") is True


def inferred_harness_unavailable(data: dict[str, Any], summary_path: tuple[str, ...]) -> int:
    results: Any
    if summary_path == ("harness", "summary"):
        results = data.get("harness", {}).get("results", [])
    else:
        results = data.get("results", [])
    if not isinstance(results, list):
        return 0
    return sum(1 for item in results if isinstance(item, dict) and result_is_harness_unavailable(item))


def result_is_harness_unavailable(result: dict[str, Any]) -> bool:
    exit_code = summary_int(result, "exit_code", 0)
    if exit_code is None or exit_code == 0:
        return False
    combined = "\n".join([
        str(result.get("stderr", "")),
        str(result.get("stdout", "")),
        str(result.get("raw_response", "")),
    ])
    return any(pattern in combined for pattern in HARNESS_UNAVAILABLE_PATTERNS)


def run_records(target: BenchmarkTarget) -> list[RunRecord]:
    records: list[RunRecord] = []
    if not target.reports_dir.exists():
        return records
    for path in sorted(target.reports_dir.glob(target.run_glob)):
        record = load_run(path, target.summary_path)
        if record is not None and record.total > 0:
            records.append(record)
    return sorted(records, key=lambda item: item.generated_at, reverse=True)


def latest_status_counting(records: list[RunRecord], min_status_counting_total: int) -> RunRecord | None:
    for record in records:
        if record.status_counting_total >= min_status_counting_total:
            return record
    return None


def age_days(now: datetime, generated_at: datetime) -> float:
    return (now - generated_at).total_seconds() / 86400


def relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def load_targets_from_manifest(
    root: Path,
    manifest_path: Path,
    max_age_days_override: int | None = None,
) -> list[BenchmarkTarget]:
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"manifest not found: {relative_path(root, manifest_path)}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"manifest is invalid JSON: {error}") from error

    benchmarks = data.get("benchmarks")
    if not isinstance(benchmarks, list) or not benchmarks:
        raise ValueError("manifest must contain a non-empty benchmarks list")

    targets: list[BenchmarkTarget] = []
    for index, benchmark in enumerate(benchmarks, start=1):
        label = f"benchmarks[{index}]"
        if not isinstance(benchmark, dict):
            raise ValueError(f"{label} must be an object")

        weekly_review = benchmark.get("weekly_review", {})
        if not isinstance(weekly_review, dict):
            raise ValueError(f"{label}.weekly_review must be an object")
        if weekly_review.get("check_freshness") is not True:
            continue

        benchmark_id = benchmark.get("id")
        reports_dir = benchmark.get("reports_dir")
        run_glob = benchmark.get("run_glob")
        summary_path = benchmark.get("summary_path")
        min_status_counting_total = weekly_review.get("min_status_counting_total")
        max_age_days = (
            max_age_days_override
            if max_age_days_override is not None
            else weekly_review.get("max_age_days")
        )

        if not isinstance(benchmark_id, str) or not benchmark_id:
            raise ValueError(f"{label}.id must be a non-empty string")
        if not isinstance(reports_dir, str) or not reports_dir:
            raise ValueError(f"{benchmark_id}.reports_dir must be a non-empty string")
        if not isinstance(run_glob, str) or not run_glob:
            raise ValueError(f"{benchmark_id}.run_glob must be a non-empty string")
        if not isinstance(summary_path, list) or not summary_path:
            raise ValueError(f"{benchmark_id}.summary_path must be a non-empty string list")
        if not all(isinstance(part, str) and part for part in summary_path):
            raise ValueError(f"{benchmark_id}.summary_path must contain only non-empty strings")
        if not positive_int(min_status_counting_total):
            raise ValueError(f"{benchmark_id}.weekly_review.min_status_counting_total must be a positive integer")
        if not positive_int(max_age_days):
            raise ValueError(f"{benchmark_id}.weekly_review.max_age_days must be a positive integer")

        targets.append(
            BenchmarkTarget(
                name=benchmark_id,
                reports_dir=resolve_root_path(root, Path(reports_dir)),
                run_glob=run_glob,
                summary_path=tuple(summary_path),
                min_status_counting_total=min_status_counting_total,
                max_age_days=max_age_days,
            )
        )

    if not targets:
        raise ValueError("manifest does not define any weekly freshness targets")
    return targets


def check_target(root: Path, target: BenchmarkTarget, now: datetime) -> int:
    records = run_records(target)
    if not records:
        print(f"WARN  {target.name}: no saved harness benchmark reports found")
        return 1

    latest = records[0]
    latest_status = latest_status_counting(records, target.min_status_counting_total)
    latest_path = relative_path(root, latest.path.parent)
    print(
        f"INFO  {target.name}: latest report {latest.generated_at.isoformat()} "
        f"behavioral={latest.behavioral_pass}/{latest.behavioral_total} "
        f"fixture_stale={latest.fixture_stale} "
        f"status_counting={latest.status_counting_total} "
        f"unavailable={latest.harness_unavailable}/{latest.total} path={latest_path}"
    )

    if latest_status is None:
        print(
            f"WARN  {target.name}: no saved status-counting harness run found "
            f"with at least {target.min_status_counting_total} cases"
        )
        return 1

    days = age_days(now, latest_status.generated_at)
    behavior_path = relative_path(root, latest_status.path.parent)
    status = "OK" if days <= target.max_age_days else "WARN"
    print(
        f"{status:<5} {target.name}: latest full status-counting harness run "
        f"{latest_status.generated_at.isoformat()} ({days:.1f} days old) "
        f"behavioral={latest_status.behavioral_pass}/{latest_status.behavioral_total} "
        f"fixture_stale={latest_status.fixture_stale} "
        f"status_counting={latest_status.status_counting_total} "
        f"path={behavior_path}"
    )
    return 0 if days <= target.max_age_days else 1


def run_self_test(root: Path) -> int:
    target = BenchmarkTarget("self-test", root / "missing", "*/run.json", ("summary",), 8, 14)
    now = datetime(2026, 5, 17, tzinfo=timezone.utc)
    result = check_target(root, target, now)
    if result == 0:
        print("SELF-TEST FAIL: missing reports were accepted")
        return 1
    with tempfile.TemporaryDirectory(prefix="agentos-benchmark-freshness-") as tmp:
        tmp_root = Path(tmp)
        reports_dir = tmp_root / "reports"
        run_dir = reports_dir / "run"
        run_dir.mkdir(parents=True)
        (run_dir / "run.json").write_text(
            json.dumps(
                {
                    "generated_at": now.isoformat(),
                    "mode": "run",
                    "git": {"eligible_fresh_main": True},
                    "summary": {
                        "total": 8,
                        "behavioral_total": 8,
                        "behavioral_pass": 8,
                        "behavioral_fail": 0,
                        "status_eligible": False,
                    },
                }
            ),
            encoding="utf-8",
        )
        ineligible_target = BenchmarkTarget("ineligible", reports_dir, "*/run.json", ("summary",), 8, 14)
        if run_records(ineligible_target):
            print("SELF-TEST FAIL: status-ineligible reports were accepted as freshness records")
            return 1
        missing_eligibility_dir = reports_dir / "missing-eligibility"
        missing_eligibility_dir.mkdir()
        (missing_eligibility_dir / "run.json").write_text(
            json.dumps(
                {
                    "generated_at": now.isoformat(),
                    "mode": "run",
                    "git": {"eligible_fresh_main": True},
                    "summary": {
                        "total": 8,
                        "behavioral_total": 8,
                        "behavioral_pass": 8,
                        "behavioral_fail": 0,
                    },
                }
            ),
            encoding="utf-8",
        )
        missing_git_dir = reports_dir / "missing-git"
        missing_git_dir.mkdir()
        (missing_git_dir / "run.json").write_text(
            json.dumps(
                {
                    "generated_at": now.isoformat(),
                    "mode": "run",
                    "summary": {
                        "total": 8,
                        "behavioral_total": 8,
                        "behavioral_pass": 8,
                        "behavioral_fail": 0,
                        "status_eligible": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        stale_git_dir = reports_dir / "stale-git"
        stale_git_dir.mkdir()
        (stale_git_dir / "run.json").write_text(
            json.dumps(
                {
                    "generated_at": now.isoformat(),
                    "mode": "run",
                    "git": {"eligible_fresh_main": False},
                    "summary": {
                        "total": 8,
                        "behavioral_total": 8,
                        "behavioral_pass": 8,
                        "behavioral_fail": 0,
                        "status_eligible": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        dry_run_dir = reports_dir / "dry-run"
        dry_run_dir.mkdir()
        (dry_run_dir / "run.json").write_text(
            json.dumps(
                {
                    "generated_at": now.isoformat(),
                    "mode": "dry-run",
                    "git": {"eligible_fresh_main": True},
                    "summary": {
                        "total": 8,
                        "behavioral_total": 8,
                        "behavioral_pass": 8,
                        "behavioral_fail": 0,
                        "status_eligible": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        malformed_timestamp_dir = reports_dir / "malformed-timestamp"
        malformed_timestamp_dir.mkdir()
        (malformed_timestamp_dir / "run.json").write_text(
            json.dumps(
                {
                    "generated_at": "not a timestamp",
                    "mode": "run",
                    "git": {"eligible_fresh_main": True},
                    "summary": {
                        "total": 8,
                        "behavioral_total": 8,
                        "behavioral_pass": 8,
                        "behavioral_fail": 0,
                        "status_eligible": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        malformed_counts_dir = reports_dir / "malformed-counts"
        malformed_counts_dir.mkdir()
        (malformed_counts_dir / "run.json").write_text(
            json.dumps(
                {
                    "generated_at": now.isoformat(),
                    "mode": "run",
                    "git": {"eligible_fresh_main": True},
                    "summary": {
                        "total": 8,
                        "behavioral_total": 8,
                        "behavioral_pass": "eight",
                        "behavioral_fail": 0,
                        "status_eligible": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        negative_counts_dir = reports_dir / "negative-counts"
        negative_counts_dir.mkdir()
        (negative_counts_dir / "run.json").write_text(
            json.dumps(
                {
                    "generated_at": now.isoformat(),
                    "mode": "run",
                    "git": {"eligible_fresh_main": True},
                    "summary": {
                        "total": 8,
                        "behavioral_total": -1,
                        "behavioral_pass": 0,
                        "behavioral_fail": 0,
                        "status_eligible": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        stale_dir = reports_dir / "stale"
        stale_dir.mkdir()
        (stale_dir / "run.json").write_text(
            json.dumps(
                {
                    "generated_at": now.isoformat(),
                    "mode": "run",
                    "git": {"eligible_fresh_main": True},
                    "summary": {
                        "total": 10,
                        "behavioral_total": 8,
                        "behavioral_pass": 8,
                        "behavioral_fail": 0,
                        "fixture_stale": 2,
                        "status_eligible": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        stale_heavy_dir = reports_dir / "stale-heavy"
        stale_heavy_dir.mkdir()
        (stale_heavy_dir / "run.json").write_text(
            json.dumps(
                {
                    "generated_at": now.isoformat(),
                    "mode": "run",
                    "git": {"eligible_fresh_main": True},
                    "summary": {
                        "total": 12,
                        "behavioral_total": 7,
                        "behavioral_pass": 7,
                        "behavioral_fail": 0,
                        "fixture_stale": 5,
                        "status_eligible": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        stale_records = run_records(BenchmarkTarget("stale", reports_dir, "*/run.json", ("summary",), 8, 14))
        if not any(record.path.parent.name == "stale" and record.fixture_stale == 2 for record in stale_records):
            print("SELF-TEST FAIL: fixture_stale count was not preserved in freshness records")
            return 1
        accepted_paths = {record.path.parent.name for record in stale_records}
        if accepted_paths != {"stale", "stale-heavy"}:
            print("SELF-TEST FAIL: ineligible or malformed reports were accepted")
            print(json.dumps(sorted(accepted_paths), indent=2))
            return 1
        if "stale-heavy" not in {
            record.path.parent.name
            for record in stale_records
            if record.status_counting_total >= 8
        }:
            print("SELF-TEST FAIL: fixture_stale did not count toward freshness threshold")
            return 1

        inflated_legacy_dir = reports_dir / "inflated-legacy-total"
        inflated_legacy_dir.mkdir()
        (inflated_legacy_dir / "run.json").write_text(
            json.dumps(
                {
                    "generated_at": now.isoformat(),
                    "mode": "run",
                    "git": {"eligible_fresh_main": True},
                    "summary": {
                        "total": 1,
                        "behavioral_total": 0,
                        "behavioral_pass": 0,
                        "behavioral_fail": 0,
                        "fixture_stale": 0,
                        "status_counting_total": 8,
                        "status_eligible": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        inflated_record = load_run(inflated_legacy_dir / "run.json", ("summary",))
        if inflated_record is None or inflated_record.status_counting_total != 0:
            print("SELF-TEST FAIL: freshness checker did not recalculate legacy status_counting_total")
            return 1

        manifest_path = tmp_root / "BENCHMARKS.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "benchmarks": [
                        {
                            "id": "legacy",
                            "script": "os/verification/legacy.py",
                            "reports_dir": "missing-legacy",
                            "run_glob": "*/run.json",
                            "summary_path": ["summary"],
                            "weekly_review": {"check_freshness": False},
                        },
                        {
                            "id": "guidance-eval",
                            "script": "os/verification/guidance-eval.py",
                            "reports_dir": "reports",
                            "run_glob": "*/run.json",
                            "summary_path": ["summary"],
                            "weekly_review": {
                                "check_freshness": True,
                                "min_status_counting_total": 8,
                                "max_age_days": 14,
                            },
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        manifest_targets = load_targets_from_manifest(tmp_root, manifest_path)
        if [target.name for target in manifest_targets] != ["guidance-eval"]:
            print("SELF-TEST FAIL: check_freshness=false manifest entries were not skipped")
            print(json.dumps([target.name for target in manifest_targets], indent=2))
            return 1
    print("SELF-TEST PASS: missing, status-ineligible, stale-metadata, fixture-stale, and manifest-skip reports are handled")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check saved AgentOS harness benchmark freshness.")
    parser.add_argument("--root", type=Path, default=default_root())
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--max-age-days", type=int, default=None, help="Override manifest max-age-days.")
    parser.add_argument("--now", help="Override current UTC timestamp for tests, ISO-8601.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if args.max_age_days is not None and args.max_age_days <= 0:
        parser.error("--max-age-days must be a positive integer")
    if args.self_test:
        return run_self_test(root)

    now = parse_timestamp(args.now) if args.now else datetime.now(timezone.utc)
    manifest_path = resolve_root_path(root, args.manifest).resolve()
    try:
        targets = load_targets_from_manifest(root, manifest_path, args.max_age_days)
    except ValueError as error:
        print(f"ERROR benchmark freshness manifest invalid: {error}", file=sys.stderr)
        return 2

    failures = [
        check_target(root, target, now)
        for target in targets
    ]
    return 1 if any(failures) else 0


if __name__ == "__main__":
    raise SystemExit(main())
