#!/usr/bin/env python3
"""Classify Codex CI preflight results without exposing raw model-call logs."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any


PUBLIC_DIAGNOSTIC_CLASSES = {
    "codex_preflight_ok",
    "api_auth_or_model_access",
    "api_rate_limit_or_quota",
    "codex_sandbox_or_permission",
    "codex_timeout",
    "codex_empty_response",
    "codex_process_start_error",
    "codex_cli_error",
}

PRIVATE_MARKERS = (
    "/" + "Users" + "/",
    "\\Users\\",
    "personal/os/",
    "raw_response",
    "stdout",
    "stderr",
    "sk-",
)


class PreflightClassificationError(ValueError):
    """Raised when a preflight result cannot be classified safely."""


def read_limited(path: Path | None, limit: int = 20000) -> str:
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except FileNotFoundError:
        return ""


def classify(exit_code: int, combined: str) -> str:
    normalized = combined.lower()
    if exit_code == 0:
        return "codex_preflight_ok"
    if exit_code == 124 or "timed out after" in normalized or "timeout" in normalized:
        return "codex_timeout"
    if exit_code == 126 or exit_code == 127 or "not found" in normalized or "failed to start" in normalized:
        return "codex_process_start_error"
    if any(pattern in normalized for pattern in ("401", "unauthorized", "invalid api key", "authentication")):
        return "api_auth_or_model_access"
    if any(pattern in normalized for pattern in ("model_not_found", "model not found", "does not have access", "unsupported model")):
        return "api_auth_or_model_access"
    if any(pattern in normalized for pattern in ("429", "rate limit", "quota", "insufficient_quota", "too many requests")):
        return "api_rate_limit_or_quota"
    if any(
        pattern in normalized
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
    if not normalized.strip():
        return "codex_empty_response"
    return "codex_cli_error"


def response_status(exit_code: int, raw_response: str) -> str:
    if exit_code != 0:
        return "not_checked"
    return "ok" if raw_response.strip() == "OK" else "unexpected"


def public_output(exit_code: int, diagnosis: str, raw_response: str) -> dict[str, Any]:
    if diagnosis not in PUBLIC_DIAGNOSTIC_CLASSES:
        raise PreflightClassificationError(f"unsupported public diagnosis: {diagnosis}")
    return {
        "exit_code": exit_code,
        "public_safe_diagnosis": diagnosis,
        "response_status": response_status(exit_code, raw_response),
    }


def assert_public_safe(value: dict[str, Any]) -> None:
    encoded = json.dumps(value, sort_keys=True)
    for marker in PRIVATE_MARKERS:
        if marker in encoded:
            raise PreflightClassificationError(f"public output contains private marker: {marker}")


def write_github_outputs(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"preflight_status={value['exit_code']}\n")
        handle.write(f"preflight_diagnosis={value['public_safe_diagnosis']}\n")
        handle.write(f"preflight_response_status={value['response_status']}\n")


def run_self_test() -> int:
    cases = [
        (0, "OK", "codex_preflight_ok", "ok"),
        (1, "401 unauthorized", "api_auth_or_model_access", "not_checked"),
        (1, "model_not_found: gpt-x", "api_auth_or_model_access", "not_checked"),
        (1, "insufficient_quota", "api_rate_limit_or_quota", "not_checked"),
        (124, "", "codex_timeout", "not_checked"),
        (127, "codex: not found", "codex_process_start_error", "not_checked"),
        (1, "bubblewrap permission denied", "codex_sandbox_or_permission", "not_checked"),
        (1, "", "codex_empty_response", "not_checked"),
        (1, "unexpected cli failure", "codex_cli_error", "not_checked"),
    ]
    for exit_code, combined, expected_diagnosis, expected_response in cases:
        diagnosis = classify(exit_code, combined)
        raw_response = "OK" if exit_code == 0 else ""
        value = public_output(exit_code, diagnosis, raw_response)
        assert_public_safe(value)
        if value["public_safe_diagnosis"] != expected_diagnosis:
            print(f"SELF-TEST FAIL: expected {expected_diagnosis}, got {value}", file=sys.stderr)
            return 1
        if value["response_status"] != expected_response:
            print(f"SELF-TEST FAIL: expected response {expected_response}, got {value}", file=sys.stderr)
            return 1

    with tempfile.TemporaryDirectory(prefix="agentos-codex-preflight-") as tmp:
        output_path = Path(tmp) / "github-output.txt"
        write_github_outputs(
            output_path,
            {
                "exit_code": 1,
                "public_safe_diagnosis": "api_auth_or_model_access",
                "response_status": "not_checked",
            },
        )
        rendered = output_path.read_text(encoding="utf-8")
        if "preflight_diagnosis=api_auth_or_model_access" not in rendered:
            print("SELF-TEST FAIL: missing GitHub output diagnosis", file=sys.stderr)
            return 1
    print("SELF-TEST PASS: Codex preflight classifier")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exit-code", type=int, help="Exit code from the Codex preflight command.")
    parser.add_argument("--stdout", type=Path, help="Captured Codex preflight stdout.")
    parser.add_argument("--stderr", type=Path, help="Captured Codex preflight stderr.")
    parser.add_argument("--raw-response", type=Path, help="Captured final Codex preflight message.")
    parser.add_argument("--github-output", type=Path, help="Append GitHub Action outputs to this file.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in self-tests.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        return run_self_test()
    if args.exit_code is None:
        raise PreflightClassificationError("--exit-code is required unless --self-test is used")

    stdout = read_limited(args.stdout)
    stderr = read_limited(args.stderr)
    raw_response = read_limited(args.raw_response)
    diagnosis = classify(args.exit_code, "\n".join((stderr, stdout, raw_response)))
    value = public_output(args.exit_code, diagnosis, raw_response)
    assert_public_safe(value)
    if args.github_output is not None:
        write_github_outputs(args.github_output, value)
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PreflightClassificationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
