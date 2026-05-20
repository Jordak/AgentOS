#!/usr/bin/env python3
"""Check whether saved harness benchmark runs are fresh enough for Weekly Review."""

from __future__ import annotations

import argparse
import json
import sys
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
    min_behavioral_total: int
    max_age_days: int


@dataclass(frozen=True)
class RunRecord:
    path: Path
    generated_at: datetime
    total: int
    behavioral_total: int
    behavioral_pass: int
    behavioral_fail: int
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
    total = int(summary.get("total", 0) or 0)
    harness_unavailable = int(
        summary.get("harness_unavailable", inferred_harness_unavailable(data, summary_path)) or 0
    )
    behavioral_total = int(summary.get("behavioral_total", total - harness_unavailable) or 0)
    behavioral_pass_default = summary.get("overall_pass", 0) if behavioral_total else 0
    behavioral_fail_default = summary.get("overall_fail", 0) if behavioral_total else 0
    behavioral_pass = int(summary.get("behavioral_pass", behavioral_pass_default) or 0)
    behavioral_fail = int(summary.get("behavioral_fail", behavioral_fail_default) or 0)
    return RunRecord(
        path=path,
        generated_at=parse_timestamp(generated),
        total=total,
        behavioral_total=behavioral_total,
        behavioral_pass=behavioral_pass,
        behavioral_fail=behavioral_fail,
        harness_unavailable=harness_unavailable,
    )


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
    if int(result.get("exit_code", 0) or 0) == 0:
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


def latest_behavioral(records: list[RunRecord], min_behavioral_total: int) -> RunRecord | None:
    for record in records:
        if record.behavioral_total >= min_behavioral_total:
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
        min_behavioral_total = weekly_review.get("min_behavioral_total")
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
        if not positive_int(min_behavioral_total):
            raise ValueError(f"{benchmark_id}.weekly_review.min_behavioral_total must be a positive integer")
        if not positive_int(max_age_days):
            raise ValueError(f"{benchmark_id}.weekly_review.max_age_days must be a positive integer")

        targets.append(
            BenchmarkTarget(
                name=benchmark_id,
                reports_dir=resolve_root_path(root, Path(reports_dir)),
                run_glob=run_glob,
                summary_path=tuple(summary_path),
                min_behavioral_total=min_behavioral_total,
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
    latest_behavior = latest_behavioral(records, target.min_behavioral_total)
    latest_path = relative_path(root, latest.path.parent)
    print(
        f"INFO  {target.name}: latest report {latest.generated_at.isoformat()} "
        f"behavioral={latest.behavioral_pass}/{latest.behavioral_total} "
        f"unavailable={latest.harness_unavailable}/{latest.total} path={latest_path}"
    )

    if latest_behavior is None:
        print(
            f"WARN  {target.name}: no saved behavioral harness run found "
            f"with at least {target.min_behavioral_total} cases"
        )
        return 1

    days = age_days(now, latest_behavior.generated_at)
    behavior_path = relative_path(root, latest_behavior.path.parent)
    status = "OK" if days <= target.max_age_days else "WARN"
    print(
        f"{status:<5} {target.name}: latest full behavioral harness run "
        f"{latest_behavior.generated_at.isoformat()} ({days:.1f} days old) "
        f"behavioral={latest_behavior.behavioral_pass}/{latest_behavior.behavioral_total} "
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
    print("SELF-TEST PASS: missing reports trigger freshness warning")
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
