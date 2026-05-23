"""Run and grade AgentOS retrieval questions against real agent harnesses.

The deterministic grader does not try to judge prose quality. It checks only
local, inspectable evidence: structured response shape, cited canonical paths,
whitespace-normalized evidence quotes, and avoidance of eval answer keys.
"""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CONFIDENCE_VALUES = {"low", "medium", "high"}
KNOWN_HARNESSES = ("codex", "claude")
DEFAULT_DISALLOWED_EXACT_PATHS = (
    "os/verification/BENCHMARK_STATUS.md",
    "os/verification/retrieval/questions.json",
)
TARGETED_DISALLOWED_EXACT_PATH_EXCEPTIONS = (
    "os/verification/BENCHMARK_STATUS.md",
)
DEFAULT_DISALLOWED_PATH_PREFIXES = (
    "os/verification/retrieval/reports/",
    "os/verification/playbook-activation/reports/",
    "personal/",
)
DEFAULT_DISALLOWED_PATHS = DEFAULT_DISALLOWED_EXACT_PATHS + DEFAULT_DISALLOWED_PATH_PREFIXES
LINE_SUFFIX_RE = re.compile(r":\d+(?::\d+)?$")
MARKDOWN_LINK_RE = re.compile(r"^\[[^\]]+\]\(([^)]+)\)$")
WHITESPACE_RE = re.compile(r"\s+")
CODEX_MODEL_RE = re.compile(r"(?im)^model:\s*(.+?)\s*$")
CODEX_EFFORT_RE = re.compile(r"(?im)^reasoning effort:\s*(.+?)\s*$")
CONFIG_EFFORT_RE = re.compile(r"\bmodel_reasoning_effort\s*=\s*(.+?)\s*$")
HARNESS_UNAVAILABLE_PATTERNS = (
    "is not installed",
    "failed to initialize in-process app-server client",
    "failed to initialize state runtime",
    "attempt to write a readonly database",
    "Error finding codex home",
    "CODEX_HOME points to",
)


@dataclass(frozen=True)
class HarnessResult:
    harness: str
    question_id: str
    response: dict[str, Any] | None
    raw_response: str
    command: list[str]
    exit_code: int
    stderr: str
    version: str


def default_root() -> Path:
    return Path(__file__).resolve().parents[4]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_questions(path: Path, selected_ids: set[str] | None = None) -> list[dict[str, Any]]:
    questions = read_json(path)
    if selected_ids is None:
        return questions
    return [question for question in questions if question.get("id") in selected_ids]


def disallowed_paths_for_question(question: dict[str, Any]) -> tuple[str, ...]:
    expected_paths = set(question.get("expected_paths", []))
    allowed_exact_paths = expected_paths & set(TARGETED_DISALLOWED_EXACT_PATH_EXCEPTIONS)
    return tuple(path for path in DEFAULT_DISALLOWED_PATHS if path not in allowed_exact_paths)


def disallowed_path_prompt_rules(disallowed_paths: tuple[str, ...] = DEFAULT_DISALLOWED_PATHS) -> str:
    lines = []
    for path in disallowed_paths:
        if path.endswith("/"):
            lines.append(f"- Do not cite files under {path}.")
        else:
            lines.append(f"- Do not cite {path}.")
    return "\n".join(lines)


def build_prompt(question: dict[str, Any]) -> str:
    return f"""You are being evaluated on AgentOS local source discovery.

Answer the user's AgentOS lookup question using only local repository files.
Return exactly one JSON object matching the provided schema. Do not wrap it in
Markdown fences and do not include commentary outside the JSON object.

Rules:
- Cite canonical AgentOS Markdown files, not eval fixtures or previous result reports.
{disallowed_path_prompt_rules(disallowed_paths_for_question(question))}
- Include at least one short quote from each file you rely on.
- Evidence quotes must copy the file's words exactly, except whitespace may
  differ. Do not quote inferred section labels, summaries, or path
  descriptions. If quoting a heading, copy the heading exactly as written.
- If you are unsure, say so in notes while still citing the best local evidence.

Question id: {question["id"]}
Question: {question["question"]}
"""


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
    schema_path: Path,
    prompt: str,
    output_path: Path,
    model: str | None = None,
    effort: str | None = None,
) -> list[str]:
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
        "--output-schema",
        str(schema_path),
        "--output-last-message",
        str(output_path),
    ]
    if model:
        command.extend(["--model", model])
    if effort:
        command.extend(["--config", f"model_reasoning_effort={json.dumps(effort)}"])
    command.append(prompt)
    return command


def claude_command(
    schema_path: Path,
    prompt: str,
    model: str | None = None,
    effort: str | None = None,
) -> list[str]:
    schema_text = schema_path.read_text(encoding="utf-8")
    command = [
        "claude",
        "-p",
        "--no-session-persistence",
        "--permission-mode",
        "plan",
        "--output-format",
        "json",
        "--json-schema",
        schema_text,
    ]
    if model:
        command.extend(["--model", model])
    if effort:
        command.extend(["--effort", effort])
    command.append(prompt)
    return command


def expand_harnesses(selected: list[str], dry_run: bool) -> list[str]:
    if not selected:
        if dry_run:
            return list(KNOWN_HARNESSES)
        raise ValueError("real harness runs require --harness codex, --harness claude, or --harness all")
    if "all" in selected:
        return list(KNOWN_HARNESSES)

    expanded: list[str] = []
    for harness in selected:
        if harness not in KNOWN_HARNESSES:
            raise ValueError(f"unsupported harness: {harness}")
        if harness not in expanded:
            expanded.append(harness)
    return expanded


def planned_harness_result(
    harness: str,
    root: Path,
    schema_path: Path,
    question: dict[str, Any],
    model: str | None = None,
    effort: str | None = None,
) -> HarnessResult:
    prompt = build_prompt(question)
    output_path = Path("<tmp>") / "last-message.json"
    command = (
        codex_command(root, schema_path, prompt, output_path, model=model, effort=effort)
        if harness == "codex"
        else claude_command(schema_path, prompt, model=model, effort=effort)
    )
    return HarnessResult(
        harness=harness,
        question_id=question["id"],
        response=None,
        raw_response="",
        command=command,
        exit_code=0,
        stderr="dry-run: command not executed",
        version=command_version(harness),
    )


def run_harness(
    harness: str,
    root: Path,
    schema_path: Path,
    question: dict[str, Any],
    timeout_seconds: int,
    model: str | None = None,
    effort: str | None = None,
) -> HarnessResult:
    prompt = build_prompt(question)
    version = command_version(harness)
    if shutil.which(harness) is None:
        return HarnessResult(
            harness=harness,
            question_id=question["id"],
            response=None,
            raw_response="",
            command=[harness],
            exit_code=127,
            stderr=f"{harness} is not installed",
            version=version,
        )

    with tempfile.TemporaryDirectory(prefix=f"agentos-{harness}-retrieval-") as tmp:
        output_path = Path(tmp) / "last-message.json"
        if harness == "codex":
            command = codex_command(root, schema_path, prompt, output_path, model=model, effort=effort)
        elif harness == "claude":
            command = claude_command(schema_path, prompt, model=model, effort=effort)
        else:
            raise ValueError(f"unsupported harness: {harness}")

        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                cwd=root,
                timeout=timeout_seconds,
            )
            raw_response = output_path.read_text(encoding="utf-8") if output_path.exists() else completed.stdout
            response = parse_harness_response(raw_response)
            return HarnessResult(
                harness=harness,
                question_id=question["id"],
                response=response,
                raw_response=raw_response,
                command=command,
                exit_code=completed.returncode,
                stderr=completed.stderr,
                version=version,
            )
        except subprocess.TimeoutExpired as error:
            return HarnessResult(
                harness=harness,
                question_id=question["id"],
                response=None,
                raw_response=error.stdout or "",
                command=command,
                exit_code=124,
                stderr=f"timed out after {timeout_seconds} seconds",
                version=version,
            )


def collect_harness_results(
    harnesses: list[str],
    root: Path,
    schema_path: Path,
    questions: list[dict[str, Any]],
    dry_run: bool,
    timeout_seconds: int,
    model: str | None = None,
    effort: str | None = None,
) -> list[HarnessResult]:
    if dry_run:
        return [
            planned_harness_result(harness, root, schema_path, question, model=model, effort=effort)
            for harness in harnesses
            for question in questions
        ]
    return [
        run_harness(harness, root, schema_path, question, timeout_seconds, model=model, effort=effort)
        for harness in harnesses
        for question in questions
    ]


def parse_json_text(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        raise ValueError("empty response")
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    for line in reversed(stripped.splitlines()):
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue

    decoder = json.JSONDecoder()
    for index, char in enumerate(stripped):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(stripped[index:])
            return value
        except json.JSONDecodeError:
            continue
    raise ValueError("response did not contain a JSON object")


def parse_harness_response(text: str) -> dict[str, Any] | None:
    try:
        parsed = parse_json_text(text)
    except ValueError:
        return None
    return coerce_response_object(parsed)


def coerce_response_object(value: Any, depth: int = 0) -> dict[str, Any] | None:
    if depth > 4:
        return None
    if isinstance(value, dict) and looks_like_response(value):
        return value
    if isinstance(value, dict):
        for key in ("result", "response", "final", "message", "content"):
            if key not in value:
                continue
            nested = value[key]
            if isinstance(nested, dict):
                found = coerce_response_object(nested, depth + 1)
                if found:
                    return found
            if isinstance(nested, str):
                try:
                    found = coerce_response_object(parse_json_text(nested), depth + 1)
                except ValueError:
                    found = None
                if found:
                    return found
        if isinstance(value.get("content"), list):
            for item in value["content"]:
                found = coerce_response_object(item, depth + 1)
                if found:
                    return found
    if isinstance(value, list):
        for item in value:
            found = coerce_response_object(item, depth + 1)
            if found:
                return found
    return None


def looks_like_response(value: dict[str, Any]) -> bool:
    return {"answer", "cited_paths", "evidence", "confidence", "notes"}.issubset(value)


def validate_response_shape(response: dict[str, Any] | None) -> list[str]:
    if response is None:
        return ["response is missing or not parseable as the expected JSON object"]

    errors: list[str] = []
    if not isinstance(response.get("answer"), str) or not response["answer"].strip():
        errors.append("answer must be a non-empty string")
    if not isinstance(response.get("cited_paths"), list) or not response["cited_paths"]:
        errors.append("cited_paths must be a non-empty array")
    elif not all(isinstance(path, str) and path.strip() for path in response["cited_paths"]):
        errors.append("all cited_paths entries must be non-empty strings")
    if not isinstance(response.get("evidence"), list) or not response["evidence"]:
        errors.append("evidence must be a non-empty array")
    else:
        for index, item in enumerate(response["evidence"]):
            if not isinstance(item, dict):
                errors.append(f"evidence[{index}] must be an object")
                continue
            for field in ("path", "locator", "quote"):
                if field not in item:
                    errors.append(f"evidence[{index}] missing {field}")
            if not isinstance(item.get("path"), str) or not item.get("path", "").strip():
                errors.append(f"evidence[{index}].path must be a non-empty string")
            if not isinstance(item.get("locator"), str):
                errors.append(f"evidence[{index}].locator must be a string")
            if not isinstance(item.get("quote"), str) or not item.get("quote", "").strip():
                errors.append(f"evidence[{index}].quote must be a non-empty string")
            elif len(item["quote"]) > 280:
                errors.append(f"evidence[{index}].quote must be 280 characters or fewer")
    if response.get("confidence") not in CONFIDENCE_VALUES:
        errors.append("confidence must be low, medium, or high")
    if not isinstance(response.get("notes"), str):
        errors.append("notes must be a string")
    return errors


def clean_path(raw_path: str) -> str:
    match = MARKDOWN_LINK_RE.match(raw_path.strip())
    if match:
        raw_path = match.group(1)
    raw_path = raw_path.strip().strip("`").strip()
    raw_path = raw_path.removeprefix("file://")
    raw_path = raw_path.split("#", 1)[0]
    return LINE_SUFFIX_RE.sub("", raw_path)


def normalize_repo_path(root: Path, raw_path: str) -> tuple[str | None, str | None]:
    cleaned = clean_path(raw_path)
    if not cleaned:
        return None, "empty path"

    candidate = Path(cleaned).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate

    try:
        resolved = candidate.resolve(strict=False)
        rel_path = resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return None, f"path escapes repository: {raw_path}"

    return rel_path, None


def is_disallowed(path: str, disallowed_paths: tuple[str, ...]) -> bool:
    for disallowed in disallowed_paths:
        clean = disallowed.rstrip("/")
        if path == clean or path.startswith(f"{clean}/"):
            return True
    return False


def normalize_evidence_text(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def quote_is_supported(quote: str, file_text: str) -> bool:
    normalized_quote = normalize_evidence_text(quote)
    if not normalized_quote:
        return False
    return normalized_quote in normalize_evidence_text(file_text)


def grade_response(
    root: Path,
    question: dict[str, Any],
    response: dict[str, Any] | None,
    disallowed_paths: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    if disallowed_paths is None:
        disallowed_paths = disallowed_paths_for_question(question)
    shape_errors = validate_response_shape(response)
    cited_paths: list[str] = []
    evidence_paths: list[str] = []
    path_errors: list[str] = []
    quote_errors: list[str] = []
    disallowed_used: list[str] = []

    if response is not None:
        for raw_path in response.get("cited_paths", []):
            rel_path, error = normalize_repo_path(root, raw_path)
            if error:
                path_errors.append(error)
                continue
            if rel_path is None:
                continue
            cited_paths.append(rel_path)
            if not (root / rel_path).exists():
                path_errors.append(f"cited path does not exist: {rel_path}")
            if is_disallowed(rel_path, disallowed_paths):
                disallowed_used.append(rel_path)

        for index, item in enumerate(response.get("evidence", [])):
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                continue
            rel_path, error = normalize_repo_path(root, item["path"])
            if error:
                path_errors.append(f"evidence[{index}]: {error}")
                continue
            if rel_path is None:
                continue
            evidence_paths.append(rel_path)
            if is_disallowed(rel_path, disallowed_paths):
                disallowed_used.append(rel_path)
                continue
            file_path = root / rel_path
            if not file_path.exists():
                path_errors.append(f"evidence path does not exist: {rel_path}")
                continue
            quote = item.get("quote")
            try:
                file_text = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as error:
                path_errors.append(f"evidence[{index}] file is not readable UTF-8 text: {rel_path}: {error}")
                continue
            if isinstance(quote, str) and not quote_is_supported(quote, file_text):
                quote_errors.append(f"evidence[{index}] quote not found in {rel_path}")

    expected_paths = set(question["expected_paths"])
    observed_paths = set(cited_paths) | set(evidence_paths)
    schema_pass = not shape_errors
    path_pass = not path_errors
    source_pass = bool(observed_paths & expected_paths)
    evidence_pass = bool(evidence_paths) and not quote_errors
    disallowed_pass = not disallowed_used
    overall_pass = schema_pass and path_pass and source_pass and evidence_pass and disallowed_pass

    return {
        "question_id": question["id"],
        "category": question["category"],
        "expected_paths": sorted(expected_paths),
        "cited_paths": sorted(set(cited_paths)),
        "evidence_paths": sorted(set(evidence_paths)),
        "schema_pass": schema_pass,
        "path_pass": path_pass,
        "source_pass": source_pass,
        "evidence_pass": evidence_pass,
        "disallowed_pass": disallowed_pass,
        "overall_pass": overall_pass,
        "answer_review": "manual",
        "errors": {
            "shape": shape_errors,
            "paths": path_errors,
            "quotes": quote_errors,
            "disallowed": sorted(set(disallowed_used)),
        },
    }


def response_records_from_file(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        return data["results"]
    raise ValueError("responses file must be a list or an object with a results array")


def result_from_record(record: dict[str, Any]) -> HarnessResult:
    raw_response = record.get("raw_response", "")
    response = record.get("response")
    if response is None and isinstance(raw_response, str):
        response = parse_harness_response(raw_response)
    if response is not None and not isinstance(response, dict):
        response = None
    return HarnessResult(
        harness=record.get("harness", "recorded"),
        question_id=record["question_id"],
        response=response,
        raw_response=raw_response if isinstance(raw_response, str) else "",
        command=record.get("command", []),
        exit_code=int(record.get("exit_code", 0)),
        stderr=record.get("stderr", ""),
        version=record.get("version", "recorded"),
    )


def observed_model(result: HarnessResult) -> str | None:
    if result.harness == "codex":
        parsed = parse_regex_value(CODEX_MODEL_RE, result.stderr)
        if parsed:
            return parsed
    return command_option_value(result.command, "--model")


def observed_effort(result: HarnessResult) -> str | None:
    if result.harness == "codex":
        parsed = parse_regex_value(CODEX_EFFORT_RE, result.stderr)
        if parsed:
            return parsed
    return command_option_value(result.command, "--effort") or command_config_effort(result.command)


def parse_regex_value(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def normalized_command_parts(command: list[str]) -> list[str]:
    parts: list[str] = []
    for part in command:
        if not isinstance(part, str):
            continue
        try:
            split = shlex.split(part)
        except ValueError:
            split = []
        if len(split) == 1:
            parts.append(split[0])
        else:
            parts.append(part)
    return parts


def command_option_value(command: list[str], option: str) -> str | None:
    parts = normalized_command_parts(command)
    for index, part in enumerate(parts[:-1]):
        if part == option:
            value = parts[index + 1].strip()
            return value or None
    return None


def command_config_effort(command: list[str]) -> str | None:
    parts = normalized_command_parts(command)
    for index, part in enumerate(parts[:-1]):
        if part != "--config":
            continue
        match = CONFIG_EFFORT_RE.search(parts[index + 1].strip())
        if not match:
            continue
        raw_value = match.group(1).strip()
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value.strip("'\"")
        if isinstance(value, str) and value:
            return value
    return None


def summarize_observed_field(results: list[dict[str, Any]], field: str) -> str:
    values = sorted({item[field] for item in results if item.get(field)})
    if not values:
        return "unknown"
    if len(values) == 1:
        return values[0]

    by_harness: dict[str, set[str]] = {}
    for item in results:
        value = item.get(field)
        if value:
            by_harness.setdefault(item["harness"], set()).add(value)
    return "; ".join(
        f"{harness}={','.join(sorted(harness_values))}"
        for harness, harness_values in sorted(by_harness.items())
    )


def report_for_results(
    root: Path,
    questions_by_id: dict[str, dict[str, Any]],
    results: list[HarnessResult],
) -> dict[str, Any]:
    graded_results: list[dict[str, Any]] = []
    for result in results:
        question = questions_by_id[result.question_id]
        grade = grade_response(root, question, result.response)
        unavailable_reason = harness_unavailable_reason(result)
        graded_results.append(
            {
                "harness": result.harness,
                "version": result.version,
                "question_id": result.question_id,
                "status": "harness-unavailable" if unavailable_reason else "graded",
                "unavailable_reason": unavailable_reason,
                "model": observed_model(result),
                "effort": observed_effort(result),
                "exit_code": result.exit_code,
                "command": [shlex.quote(part) for part in result.command],
                "stderr": result.stderr,
                "response": result.response,
                "grade": grade,
            }
        )

    total = len(graded_results)
    unavailable = sum(1 for item in graded_results if item["status"] == "harness-unavailable")
    behavioral_results = [item for item in graded_results if item["status"] != "harness-unavailable"]
    passed = sum(1 for item in graded_results if item["grade"]["overall_pass"])
    behavioral_passed = sum(1 for item in behavioral_results if item["grade"]["overall_pass"])
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "summary": {
            "total": total,
            "overall_pass": passed,
            "overall_fail": total - passed,
            "harness_unavailable": unavailable,
            "behavioral_total": len(behavioral_results),
            "behavioral_pass": behavioral_passed,
            "behavioral_fail": len(behavioral_results) - behavioral_passed,
            "model": summarize_observed_field(graded_results, "model"),
            "effort": summarize_observed_field(graded_results, "effort"),
        },
        "results": graded_results,
    }


def harness_unavailable_reason(result: HarnessResult) -> str | None:
    if result.exit_code == 0:
        return None
    combined = f"{result.stderr}\n{result.raw_response}"
    for pattern in HARNESS_UNAVAILABLE_PATTERNS:
        if pattern in combined:
            return pattern
    return None


def print_summary(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print(f"Harness retrieval eval: {summary['overall_pass']}/{summary['total']} overall pass")
    print()
    print("| harness | question | schema | source | evidence | disallowed | overall |")
    print("| --- | --- | ---: | ---: | ---: | ---: | ---: |")
    for item in report["results"]:
        grade = item["grade"]
        print(
            "| {harness} | {question} | {schema} | {source} | {evidence} | {disallowed} | {overall} |".format(
                harness=item["harness"],
                question=item["question_id"],
                schema=mark(grade["schema_pass"]),
                source=mark(grade["source_pass"]),
                evidence=mark(grade["evidence_pass"]),
                disallowed=mark(grade["disallowed_pass"]),
                overall=mark(grade["overall_pass"]),
            )
        )


def mark(value: bool) -> str:
    return "yes" if value else "no"


def run_self_test(root: Path, questions_path: Path) -> int:
    questions = load_questions(questions_path, {"identity-defaults"})
    if not questions:
        print("SELF-TEST FAIL: missing identity-defaults fixture")
        return 1
    question = questions[0]
    source_path = next(path for path in question["expected_paths"] if (root / path).exists())
    source_text = (root / source_path).read_text(encoding="utf-8")
    quote = next(line.strip() for line in source_text.splitlines() if line.strip())
    response = {
        "answer": "Use the cited AgentOS identity file for durable identity context.",
        "cited_paths": [source_path],
        "evidence": [
            {
                "path": source_path,
                "locator": "self-test",
                "quote": quote,
            }
        ],
        "confidence": "high",
        "notes": "Synthetic self-test response.",
    }
    grade = grade_response(root, question, response)
    if not grade["overall_pass"]:
        print("SELF-TEST FAIL: valid structured response was rejected.")
        print(json.dumps(grade, indent=2))
        return 1

    contract_questions = load_questions(questions_path, {"skills-contract"})
    if not contract_questions:
        print("SELF-TEST FAIL: missing skills-contract fixture")
        return 1
    wrapped_response = {
        "answer": "The skill contract points agents to the skills manifest.",
        "cited_paths": ["os/skills/SKILL_CONTRACT.md"],
        "evidence": [
            {
                "path": "os/skills/SKILL_CONTRACT.md",
                "locator": "Contract Adoption",
                "quote": "Existing skills do not need to be fully rewritten in one pass. Use the manifest to classify each skill as:",
            }
        ],
        "confidence": "high",
        "notes": "Synthetic self-test response for hard-wrapped Markdown evidence.",
    }
    wrapped_grade = grade_response(root, contract_questions[0], wrapped_response)
    if not wrapped_grade["overall_pass"]:
        print("SELF-TEST FAIL: whitespace-normalized evidence quote was rejected.")
        print(json.dumps(wrapped_grade, indent=2))
        return 1

    with tempfile.TemporaryDirectory(prefix="agentos-harness-grader-") as tmp:
        synthetic_root = Path(tmp)
        synthetic_source_path = synthetic_root / source_path
        synthetic_source_path.parent.mkdir(parents=True)
        synthetic_source_path.write_text(quote + "\n", encoding="utf-8")
        synthetic_question = {**question, "expected_paths": [source_path]}
        disallowed_evidence_paths = (
            "personal/os/context/SOURCE_MAP.md",
            "personal/os/verification/reports/private.md",
            "personal/os/verification/markdown-audit/private.md",
            "personal/os/agents/current-awareness-agent/briefs/private.md",
        )
        for private_report_path in disallowed_evidence_paths:
            private_report_quote = f"Private evidence from {private_report_path}."
            synthetic_private_report = synthetic_root / private_report_path
            synthetic_private_report.parent.mkdir(parents=True)
            synthetic_private_report.write_text(private_report_quote + "\n", encoding="utf-8")
            contaminated_response = {
                "answer": "Use the public source while avoiding private generated evidence.",
                "cited_paths": [source_path],
                "evidence": [
                    {
                        "path": source_path,
                        "locator": "self-test",
                        "quote": quote,
                    },
                    {
                        "path": private_report_path,
                        "locator": "private report",
                        "quote": private_report_quote,
                    },
                ],
                "confidence": "high",
                "notes": "Synthetic response with disallowed private generated evidence.",
            }
            contaminated_grade = grade_response(synthetic_root, synthetic_question, contaminated_response)
            if contaminated_grade["overall_pass"] or contaminated_grade["disallowed_pass"]:
                print("SELF-TEST FAIL: private/generated evidence path was not rejected.")
                print(json.dumps(contaminated_grade, indent=2))
                return 1
            if private_report_path not in contaminated_grade["errors"]["disallowed"]:
                print("SELF-TEST FAIL: private/generated evidence path was not reported as disallowed.")
                print(json.dumps(contaminated_grade, indent=2))
                return 1
        binary_private_path = "personal/os/context/binary.md"
        synthetic_binary_private = synthetic_root / binary_private_path
        synthetic_binary_private.parent.mkdir(parents=True, exist_ok=True)
        synthetic_binary_private.write_bytes(b"\xff\xfeprivate")
        binary_private_response = {
            "answer": "Use the public source while avoiding private binary evidence.",
            "cited_paths": [source_path],
            "evidence": [
                {
                    "path": source_path,
                    "locator": "self-test",
                    "quote": quote,
                },
                {
                    "path": binary_private_path,
                    "locator": "private binary",
                    "quote": "private",
                },
            ],
            "confidence": "high",
            "notes": "Synthetic response with disallowed non-UTF-8 private evidence.",
        }
        binary_private_grade = grade_response(synthetic_root, synthetic_question, binary_private_response)
        if binary_private_grade["overall_pass"] or binary_private_grade["disallowed_pass"]:
            print("SELF-TEST FAIL: non-UTF-8 private evidence path was not rejected.")
            print(json.dumps(binary_private_grade, indent=2))
            return 1
        if binary_private_path not in binary_private_grade["errors"]["disallowed"]:
            print("SELF-TEST FAIL: non-UTF-8 private evidence path was not reported as disallowed.")
            print(json.dumps(binary_private_grade, indent=2))
            return 1
        binary_core_path = "os/context/binary.md"
        synthetic_binary_core = synthetic_root / binary_core_path
        synthetic_binary_core.parent.mkdir(parents=True, exist_ok=True)
        synthetic_binary_core.write_bytes(b"\xff\xfecore")
        binary_core_response = {
            "answer": "Use readable local source files as evidence.",
            "cited_paths": [source_path],
            "evidence": [
                {
                    "path": source_path,
                    "locator": "self-test",
                    "quote": quote,
                },
                {
                    "path": binary_core_path,
                    "locator": "binary core",
                    "quote": "core",
                },
            ],
            "confidence": "high",
            "notes": "Synthetic response with unreadable UTF-8 evidence.",
        }
        binary_core_grade = grade_response(synthetic_root, synthetic_question, binary_core_response)
        if binary_core_grade["overall_pass"] or binary_core_grade["path_pass"]:
            print("SELF-TEST FAIL: non-UTF-8 evidence path did not fail grading.")
            print(json.dumps(binary_core_grade, indent=2))
            return 1
        if not any("file is not readable UTF-8 text" in error for error in binary_core_grade["errors"]["paths"]):
            print("SELF-TEST FAIL: non-UTF-8 evidence path did not report a path error.")
            print(json.dumps(binary_core_grade, indent=2))
            return 1

        status_path = "os/verification/BENCHMARK_STATUS.md"
        status_quote = "current public-safe benchmark posture"
        synthetic_status = synthetic_root / status_path
        synthetic_status.parent.mkdir(parents=True, exist_ok=True)
        synthetic_status.write_text(status_quote + "\n", encoding="utf-8")
        status_question = {**question, "id": "benchmark-status", "expected_paths": [status_path]}
        status_response = {
            "answer": "Use the benchmark status snapshot.",
            "cited_paths": [status_path],
            "evidence": [
                {
                    "path": status_path,
                    "locator": "self-test",
                    "quote": status_quote,
                }
            ],
            "confidence": "high",
            "notes": "Synthetic benchmark-status exception response.",
        }
        status_grade = grade_response(synthetic_root, status_question, status_response)
        if not status_grade["overall_pass"]:
            print("SELF-TEST FAIL: targeted benchmark status evidence was not allowed.")
            print(json.dumps(status_grade, indent=2))
            return 1

        answer_key_path = "os/verification/retrieval/questions.json"
        answer_key_quote = "answer key"
        synthetic_answer_key = synthetic_root / answer_key_path
        synthetic_answer_key.parent.mkdir(parents=True, exist_ok=True)
        synthetic_answer_key.write_text(answer_key_quote + "\n", encoding="utf-8")
        answer_key_question = {**question, "expected_paths": [answer_key_path]}
        answer_key_response = {
            "answer": "This should not be allowed even when expected.",
            "cited_paths": [answer_key_path],
            "evidence": [
                {
                    "path": answer_key_path,
                    "locator": "self-test",
                    "quote": answer_key_quote,
                }
            ],
            "confidence": "high",
            "notes": "Synthetic answer-key contamination response.",
        }
        answer_key_grade = grade_response(synthetic_root, answer_key_question, answer_key_response)
        if answer_key_grade["overall_pass"] or answer_key_grade["disallowed_pass"]:
            print("SELF-TEST FAIL: retrieval answer key was allowed as targeted evidence.")
            print(json.dumps(answer_key_grade, indent=2))
            return 1

    synthetic_result = HarnessResult(
        harness="codex",
        question_id=question["id"],
        response=response,
        raw_response=json.dumps(response),
        command=["codex", "exec"],
        exit_code=0,
        stderr="model: gpt-test\nreasoning effort: low\n",
        version="codex-test",
    )
    synthetic_report = report_for_results(root, {question["id"]: question}, [synthetic_result])
    if synthetic_report["summary"]["model"] != "gpt-test" or synthetic_report["summary"]["effort"] != "low":
        print("SELF-TEST FAIL: observed harness model and effort were not reported.")
        print(json.dumps(synthetic_report["summary"], indent=2))
        return 1

    unavailable_result = HarnessResult(
        harness="codex",
        question_id=question["id"],
        response=None,
        raw_response="",
        command=["codex", "exec"],
        exit_code=1,
        stderr="Error: failed to initialize in-process app-server client: Operation not permitted (os error 1)",
        version="codex-test",
    )
    unavailable_report = report_for_results(root, {question["id"]: question}, [unavailable_result])
    if unavailable_report["summary"]["harness_unavailable"] != 1 or unavailable_report["summary"]["behavioral_fail"] != 0:
        print("SELF-TEST FAIL: harness startup failure was not separated from behavioral failures.")
        print(json.dumps(unavailable_report["summary"], indent=2))
        return 1

    print("SELF-TEST PASS: valid structured responses were accepted.")
    return 0
