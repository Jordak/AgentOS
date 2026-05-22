#!/usr/bin/env python3
"""Run the AgentOS retrieval benchmark suites from one CLI.

The default command produces a safe full report: the local lexical benchmark is
run for real, and known model harnesses are included as dry-run plans. Real
harness calls require an explicit --no-dry-run plus --harness selection.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shlex
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import harness_eval


WORD_RE = re.compile(r"[a-z0-9]+(?:[._/-][a-z0-9]+)*")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
STOPWORDS = {
    "a",
    "about",
    "and",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "should",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "with",
}
EXCLUDED_MARKDOWN_PATHS = set(harness_eval.DEFAULT_DISALLOWED_EXACT_PATHS)
EXCLUDED_MARKDOWN_PREFIXES = harness_eval.DEFAULT_DISALLOWED_PATH_PREFIXES


@dataclass(frozen=True)
class MarkdownFile:
    path: str
    text: str
    tokens: Counter[str]


@dataclass(frozen=True)
class Section:
    path: str
    heading: str
    text: str
    path_tokens: Counter[str]
    heading_tokens: Counter[str]
    text_tokens: Counter[str]


@dataclass(frozen=True)
class SearchResult:
    path: str
    score: float
    heading: str = ""


def default_root() -> Path:
    return Path(__file__).resolve().parents[4]


def resolve_under_root(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in WORD_RE.findall(text.lower()):
        pieces = [raw, *re.split(r"[._/-]+", raw)]
        for piece in pieces:
            if len(piece) < 2 or piece in STOPWORDS:
                continue
            tokens.append(piece)
    return tokens


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
    value = completed.stdout.strip()
    return value or None


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
    upstream_fresh = ahead == 0 and behind == 0 if ahead is not None and behind is not None else None
    eligible_fresh_main = (
        branch == "main"
        and upstream == "origin/main"
        and worktree_clean is True
        and upstream_fresh is True
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
        "upstream_fresh": upstream_fresh,
        "worktree_clean": worktree_clean,
        "eligible_fresh_main": bool(eligible_fresh_main),
    }


def markdown_files(root: Path, allowed_exact_paths: set[str] | None = None) -> list[Path]:
    allowed_exact_paths = allowed_exact_paths or set()
    root_markdown_files = ("AGENTS.md", "README.md", "DOMAIN.md")
    files = [root / name for name in root_markdown_files if (root / name).exists()]
    for source_dir in ("docs", "os"):
        path = root / source_dir
        if path.exists():
            files.extend(sorted(path.rglob("*.md")))
    return sorted(
        path
        for path in files
        if path.is_file() and should_index_markdown(root, path, allowed_exact_paths)
    )


def should_index_markdown(root: Path, path: Path, allowed_exact_paths: set[str] | None = None) -> bool:
    allowed_exact_paths = allowed_exact_paths or set()
    rel_path = path.relative_to(root).as_posix()
    if rel_path in EXCLUDED_MARKDOWN_PATHS and rel_path not in allowed_exact_paths:
        return False
    return not any(rel_path.startswith(prefix) for prefix in EXCLUDED_MARKDOWN_PREFIXES)


def load_files(root: Path, allowed_exact_paths: set[str] | None = None) -> list[MarkdownFile]:
    docs: list[MarkdownFile] = []
    for path in markdown_files(root, allowed_exact_paths):
        rel_path = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        docs.append(MarkdownFile(rel_path, text, Counter(tokenize(f"{rel_path}\n{text}"))))
    return docs


def allowed_exact_paths_for_question(question: dict[str, Any]) -> set[str]:
    return set(question.get("expected_paths", [])) & EXCLUDED_MARKDOWN_PATHS


def split_sections(doc: MarkdownFile) -> list[Section]:
    sections: list[Section] = []
    heading_stack: list[tuple[int, str]] = []
    current_heading = "document"
    current_lines: list[str] = []

    def flush() -> None:
        if not current_lines:
            return
        heading = " > ".join([heading for _, heading in heading_stack]) or current_heading
        text = "\n".join(current_lines)
        sections.append(
            Section(
                path=doc.path,
                heading=heading,
                text=text,
                path_tokens=Counter(tokenize(doc.path)),
                heading_tokens=Counter(tokenize(heading)),
                text_tokens=Counter(tokenize(text)),
            )
        )

    for line in doc.text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            flush()
            current_lines = [line]
            level = len(match.group(1))
            title = match.group(2).strip()
            heading_stack = [(h_level, h_title) for h_level, h_title in heading_stack if h_level < level]
            heading_stack.append((level, title))
            current_heading = title
        else:
            current_lines.append(line)

    flush()
    return sections


def inverse_document_frequency(counters: Iterable[Counter[str]]) -> dict[str, float]:
    counters = list(counters)
    total = len(counters)
    document_frequency: Counter[str] = Counter()
    for counter in counters:
        document_frequency.update(counter.keys())
    return {
        token: math.log((1 + total) / (1 + frequency)) + 1
        for token, frequency in document_frequency.items()
    }


def score_counter(query: Counter[str], counter: Counter[str], idf: dict[str, float], boost: float = 1.0) -> float:
    score = 0.0
    for token, query_count in query.items():
        score += min(counter.get(token, 0), 5) * query_count * idf.get(token, 1.0) * boost
    return score


def keyword_file_search(docs: list[MarkdownFile], question: str, limit: int) -> list[SearchResult]:
    query = Counter(tokenize(question))
    idf = inverse_document_frequency(doc.tokens for doc in docs)
    scored = [
        SearchResult(doc.path, score_counter(query, doc.tokens, idf))
        for doc in docs
    ]
    return sorted((item for item in scored if item.score > 0), key=lambda item: (-item.score, item.path))[:limit]


def section_index_search(docs: list[MarkdownFile], question: str, limit: int) -> list[SearchResult]:
    query = Counter(tokenize(question))
    sections = [section for doc in docs for section in split_sections(doc)]
    idf = inverse_document_frequency(
        section.path_tokens + section.heading_tokens + section.text_tokens
        for section in sections
    )
    best_by_path: dict[str, SearchResult] = {}
    support_by_path: defaultdict[str, float] = defaultdict(float)

    for section in sections:
        score = (
            score_counter(query, section.path_tokens, idf, boost=3.0)
            + score_counter(query, section.heading_tokens, idf, boost=2.0)
            + score_counter(query, section.text_tokens, idf, boost=1.0)
        )
        if score <= 0:
            continue
        support_by_path[section.path] += score * 0.05
        previous = best_by_path.get(section.path)
        if previous is None or score > previous.score:
            best_by_path[section.path] = SearchResult(section.path, score, section.heading)

    collapsed = [
        SearchResult(path, result.score + support_by_path[path], result.heading)
        for path, result in best_by_path.items()
    ]
    return sorted(collapsed, key=lambda item: (-item.score, item.path))[:limit]


def first_hit_rank(results: list[SearchResult], expected_paths: set[str]) -> int | None:
    for index, result in enumerate(results, start=1):
        if result.path in expected_paths:
            return index
    return None


def search_result_record(result: SearchResult) -> dict[str, Any]:
    return {
        "path": result.path,
        "score": result.score,
        "heading": result.heading,
    }


def render_result_paths(results: list[dict[str, Any]]) -> str:
    rendered: list[str] = []
    for result in results[:3]:
        suffix = f" ({result['heading']})" if result["heading"] else ""
        rendered.append(f"{result['path']}{suffix}")
    return "; ".join(rendered)


def build_local_report(root: Path, questions: list[dict[str, Any]], limit: int) -> dict[str, Any]:
    default_docs = load_files(root)
    docs_by_allowed_paths: dict[tuple[str, ...], list[MarkdownFile]] = {(): default_docs}
    rows: list[dict[str, Any]] = []
    keyword_hits = 0
    section_hits = 0

    for item in questions:
        allowed_key = tuple(sorted(allowed_exact_paths_for_question(item)))
        if allowed_key not in docs_by_allowed_paths:
            docs_by_allowed_paths[allowed_key] = load_files(root, set(allowed_key))
        docs = docs_by_allowed_paths[allowed_key]
        expected = set(item["expected_paths"])
        keyword = keyword_file_search(docs, item["question"], limit)
        section = section_index_search(docs, item["question"], limit)
        keyword_rank = first_hit_rank(keyword, expected)
        section_rank = first_hit_rank(section, expected)
        keyword_hits += 1 if keyword_rank is not None else 0
        section_hits += 1 if section_rank is not None else 0
        rows.append(
            {
                "id": item["id"],
                "category": item["category"],
                "keyword_rank": keyword_rank,
                "section_rank": section_rank,
                "keyword_top": [search_result_record(result) for result in keyword],
                "section_top": [search_result_record(result) for result in section],
            }
        )

    return {
        "docs_indexed": max(len(docs) for docs in docs_by_allowed_paths.values()),
        "questions": len(questions),
        "limit": limit,
        "keyword_hit": keyword_hits,
        "section_hit": section_hits,
        "rows": rows,
    }


def build_harness_report(
    root: Path,
    questions: list[dict[str, Any]],
    schema_path: Path,
    selected_harnesses: list[str],
    dry_run: bool,
    timeout_seconds: int,
    responses_path: Path | None,
    model: str | None,
    effort: str | None,
) -> dict[str, Any]:
    questions_by_id = {question["id"]: question for question in questions}
    if responses_path:
        records = harness_eval.response_records_from_file(responses_path)
        results = [
            harness_eval.result_from_record(record)
            for record in records
            if record["question_id"] in questions_by_id
        ]
        report = harness_eval.report_for_results(root, questions_by_id, results)
        report["mode"] = "responses"
        report["responses_path"] = str(responses_path)
        apply_requested_harness_fallbacks(report, model, effort)
        return report

    harnesses = harness_eval.expand_harnesses(selected_harnesses, dry_run)
    results = harness_eval.collect_harness_results(
        harnesses,
        root,
        schema_path,
        questions,
        dry_run=dry_run,
        timeout_seconds=timeout_seconds,
        model=model,
        effort=effort,
    )
    if not dry_run:
        report = harness_eval.report_for_results(root, questions_by_id, results)
        report["mode"] = "run"
        apply_requested_harness_fallbacks(report, model, effort)
        return report

    return {
        "mode": "dry-run",
        "summary": {
            "total": len(results),
            "harnesses": harnesses,
            "model": model or "harness-default",
            "effort": effort or "harness-default",
        },
        "results": [
            {
                "harness": result.harness,
                "version": result.version,
                "question_id": result.question_id,
                "command": result.command,
            }
            for result in results
        ],
    }


def apply_requested_harness_fallbacks(report: dict[str, Any], model: str | None, effort: str | None) -> None:
    if report["summary"].get("model") == "unknown" and model:
        report["summary"]["model"] = model
    if report["summary"].get("effort") == "unknown" and effort:
        report["summary"]["effort"] = effort


def build_report(
    root: Path,
    suite: str,
    questions: list[dict[str, Any]],
    limit: int,
    schema_path: Path,
    selected_harnesses: list[str],
    dry_run: bool,
    timeout_seconds: int,
    responses_path: Path | None,
    model: str | None,
    effort: str | None,
) -> dict[str, Any]:
    include_local = suite in {"all", "local"}
    include_harness = suite in {"all", "harness"}
    report: dict[str, Any] = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agentos_git": collect_git_state(root),
        "root": str(root),
        "suite": suite,
        "dry_run": dry_run,
        "model": model or "harness-default",
        "effort": effort or "harness-default",
    }
    if include_local:
        report["local"] = build_local_report(root, questions, limit)
    if include_harness:
        harness_report = build_harness_report(
            root,
            questions,
            schema_path,
            selected_harnesses,
            dry_run,
            timeout_seconds,
            responses_path,
            model,
            effort,
        )
        report["harness"] = harness_report
        report["model"] = harness_report["summary"].get("model", report["model"])
        report["effort"] = harness_report["summary"].get("effort", report["effort"])
    return report


def render_markdown(report: dict[str, Any]) -> str:
    harness_dry_run = str(report["dry_run"]).lower() if "harness" in report else "n/a"
    git_state = report.get("agentos_git", {})
    lines = [
        "# AgentOS Retrieval Benchmark",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- AgentOS commit: `{git_state.get('commit', 'unknown')}`",
        f"- AgentOS branch: `{git_state.get('branch', 'unknown')}`",
        f"- Worktree clean: `{str(git_state.get('worktree_clean', 'unknown')).lower()}`",
        f"- Fresh main eligible: `{str(git_state.get('eligible_fresh_main', False)).lower()}`",
        f"- Suite: `{report['suite']}`",
        f"- Harness dry run: `{harness_dry_run}`",
        f"- Harness model: `{report['model']}`",
        f"- Harness effort: `{report['effort']}`",
        "",
    ]
    if "local" in report:
        lines.extend(render_local_markdown(report["local"]))
    if "harness" in report:
        lines.extend(render_harness_markdown(report["harness"]))
    return "\n".join(lines).rstrip() + "\n"


def render_local_markdown(local: dict[str, Any]) -> list[str]:
    lines = [
        "## Local Lexical Benchmark",
        "",
        f"Docs indexed: {local['docs_indexed']} Markdown files",
        f"Questions: {local['questions']}",
        "",
        "| id | category | keyword rank | section-index rank | keyword top 3 | section-index top 3 |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in local["rows"]:
        lines.append(
            "| {id} | {category} | {keyword_rank} | {section_rank} | {keyword_top} | {section_top} |".format(
                id=row["id"],
                category=row["category"],
                keyword_rank=row["keyword_rank"] or "-",
                section_rank=row["section_rank"] or "-",
                keyword_top=render_result_paths(row["keyword_top"]),
                section_top=render_result_paths(row["section_top"]),
            )
        )
    lines.extend(
        [
            "",
            f"Keyword hit@{local['limit']}: {local['keyword_hit']}/{local['questions']}",
            f"Section-index hit@{local['limit']}: {local['section_hit']}/{local['questions']}",
            "",
        ]
    )
    return lines


def render_harness_markdown(harness: dict[str, Any]) -> list[str]:
    mode = harness["mode"]
    if mode == "dry-run":
        return render_harness_dry_run_markdown(harness)
    return render_harness_grade_markdown(harness)


def render_harness_dry_run_markdown(harness: dict[str, Any]) -> list[str]:
    lines = [
        "## Harness Eval Plan",
        "",
        "Mode: dry-run. Commands were planned but not executed.",
        "",
        "| harness | question | version | command shape |",
        "| --- | --- | --- | --- |",
    ]
    for item in harness["results"]:
        lines.append(
            "| {harness} | {question} | {version} | `{command}` |".format(
                harness=item["harness"],
                question=item["question_id"],
                version=one_line(item["version"]),
                command=summarize_command(item["command"]),
            )
        )
    lines.append("")
    return lines


def render_harness_grade_markdown(harness: dict[str, Any]) -> list[str]:
    summary = harness["summary"]
    behavioral_total = summary.get("behavioral_total", summary["total"])
    behavioral_pass = summary.get("behavioral_pass", summary["overall_pass"])
    behavioral_fail = summary.get("behavioral_fail", summary["overall_fail"])
    unavailable = summary.get("harness_unavailable", 0)
    lines = [
        "## Harness Eval Results",
        "",
        f"Mode: {harness['mode']}.",
        f"Overall pass: {summary['overall_pass']}/{summary['total']}",
        f"Behavioral pass: {behavioral_pass}/{behavioral_total}",
        f"Behavioral fail: {behavioral_fail}",
        f"Harness unavailable: {unavailable}/{summary['total']}",
        f"Model: {summary.get('model', 'harness-default')}",
        f"Effort: {summary.get('effort', 'harness-default')}",
        "",
        "| harness | question | status | schema | source | evidence | disallowed | overall |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in harness["results"]:
        status = item.get("status", "graded")
        if status == "harness-unavailable":
            lines.append(
                "| {harness} | {question} | {status}: {reason} | n/a | n/a | n/a | n/a | unavailable |".format(
                    harness=item["harness"],
                    question=item["question_id"],
                    status=status,
                    reason=one_line(item.get("unavailable_reason") or "unknown"),
                )
            )
            continue
        grade = item["grade"]
        lines.append(
            "| {harness} | {question} | {status} | {schema} | {source} | {evidence} | {disallowed} | {overall} |".format(
                harness=item["harness"],
                question=item["question_id"],
                status=status,
                schema=mark(grade["schema_pass"]),
                source=mark(grade["source_pass"]),
                evidence=mark(grade["evidence_pass"]),
                disallowed=mark(grade["disallowed_pass"]),
                overall=mark(grade["overall_pass"]),
            )
        )
    lines.append("")
    return lines


def summarize_command(command: list[str]) -> str:
    summarized: list[str] = []
    for part in command:
        if part.strip().startswith("{") and "$schema" in part:
            summarized.append("<schema-json>")
        elif "\n" in part:
            summarized.append("<prompt>")
        else:
            summarized.append(part)
    return " ".join(shlex.quote(part) for part in summarized)


def one_line(text: str) -> str:
    return " ".join(text.split())


def mark(value: bool) -> str:
    return "yes" if value else "no"


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


def default_report_dir(root: Path, suite: str) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    base = root / "personal/os/verification/retrieval/reports" / f"retrieval-{suite}-{timestamp}"
    if not base.exists():
        return base
    for suffix in range(2, 100):
        candidate = base.with_name(f"{base.name}-{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not allocate unique report directory for {base}")


def report_exit_code(report: dict[str, Any]) -> int:
    harness = report.get("harness")
    if harness and harness["mode"] in {"run", "responses"} and harness["summary"].get("behavioral_fail", harness["summary"]["overall_fail"]):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run AgentOS retrieval benchmark suites.")
    parser.add_argument("--root", type=Path, default=default_root())
    parser.add_argument("--suite", choices=["all", "local", "harness"], default="all")
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path("os/verification/retrieval/questions.json"),
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("os/verification/retrieval/harness_response.schema.json"),
    )
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--harness", action="append", choices=["codex", "claude", "all"], default=[])
    parser.add_argument("--question-id", action="append", dest="question_ids")
    parser.add_argument("--responses", type=Path, help="Grade saved harness response records.")
    parser.add_argument("--output", type=Path, help="Write the combined report to this path.")
    parser.add_argument(
        "--save-report",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Write report.md and run.json to a timestamped directory under personal/os/verification/retrieval/reports/.",
    )
    parser.add_argument(
        "--report-format",
        choices=["md", "json"],
        default="md",
        help="Deprecated for --save-report, which always writes both report.md and run.json. Use --output for a single-file report.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--model", help="Optional model override passed through to selected harnesses.")
    parser.add_argument("--effort", help="Optional reasoning effort override passed through to selected harnesses.")
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Plan harness commands without running them. Harness mode defaults to dry-run; use --no-dry-run to spend model calls.",
    )
    parser.add_argument("--self-test", action="store_true", help="Run the deterministic harness-grader self-test.")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    questions_path = resolve_under_root(root, args.questions)
    schema_path = resolve_under_root(root, args.schema)
    responses_path = resolve_under_root(root, args.responses) if args.responses else None
    output_path = resolve_under_root(root, args.output) if args.output else None
    dry_run = args.dry_run if args.dry_run is not None else True

    if args.self_test:
        return harness_eval.run_self_test(root, questions_path)

    if args.output and args.save_report:
        print("Use either --output or --save-report, not both.", file=sys.stderr)
        return 2

    if args.suite == "local" and args.responses:
        print("--responses requires --suite harness or --suite all", file=sys.stderr)
        return 2

    selected_ids = set(args.question_ids) if args.question_ids else None
    questions = harness_eval.load_questions(questions_path, selected_ids)
    if not questions:
        print("No questions selected.", file=sys.stderr)
        return 2

    try:
        report = build_report(
            root=root,
            suite=args.suite,
            questions=questions,
            limit=args.limit,
            schema_path=schema_path,
            selected_harnesses=args.harness,
            dry_run=dry_run,
            timeout_seconds=args.timeout_seconds,
            responses_path=responses_path,
            model=args.model,
            effort=args.effort,
        )
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    markdown = render_markdown(report)
    print(markdown, end="")
    if args.save_report:
        report_dir = default_report_dir(root, args.suite)
        write_saved_report(report_dir, report, markdown)
        print(f"Report written to {report_dir}", file=sys.stderr)
    if output_path:
        write_report(output_path, report, markdown)
        print(f"Report written to {output_path}", file=sys.stderr)

    return report_exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
