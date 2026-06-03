#!/usr/bin/env python3
"""Deterministic local validators for AgentOS maintenance.

The checks in this script intentionally avoid network calls and connector reads.
They inspect local Markdown files, local path existence, and portable AgentOS
metadata. Machine-local Core skill exposure is checked by the expose-skills
skill instead of this portable validator.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

PATH_RESOLUTION_PACKAGE = "path_resolution"
PUBLIC_EXPORT_REQUIRED_SUPPORT_FILES = tuple(
    Path(rel)
    for rel in [
        "os/verification/scripts/validate_agentos.py",
        "os/verification/scripts/agentos_validator/__init__.py",
        "os/verification/scripts/agentos_validator/common.py",
        "os/verification/scripts/agentos_validator/managed.py",
        "os/verification/scripts/agentos_validator/publication.py",
        "os/verification/scripts/agentos_validator/self_test.py",
        "os/verification/scripts/agentos_validator/skills.py",
        "os/verification/scripts/agentos_validator/structural.py",
        "scripts/agentos_publication_rules.py",
        "scripts/path_resolution/__init__.py",
        "scripts/path_resolution/_primitives.py",
        "scripts/path_resolution/bootstrap.py",
        "scripts/path_resolution/managed.py",
    ]
)


def _loader_lexical_absolute(path: Path) -> Path:
    """Make a path absolute without resolving symbolic links."""
    expanded = path.expanduser()
    if not expanded.is_absolute():
        expanded = Path.cwd() / expanded
    return Path(os.path.abspath(expanded))


def _loader_file_problem(root: Path, path: Path) -> str | None:
    root_absolute = _loader_lexical_absolute(root)
    try:
        root_stat = root_absolute.lstat()
    except FileNotFoundError:
        return f"{root_absolute} (path is missing)"
    except OSError as error:
        return f"{root_absolute} ({error.__class__.__name__}: {error})"
    if stat.S_ISLNK(root_stat.st_mode):
        return f"{root_absolute} (symbolic link is not allowed)"
    if not stat.S_ISDIR(root_stat.st_mode):
        return f"{root_absolute} (not a directory)"

    absolute = _loader_lexical_absolute(path)
    try:
        relative = absolute.relative_to(root_absolute)
    except ValueError:
        return f"{absolute} (path is outside the managed root: {root_absolute})"

    current = root_absolute
    for index, part in enumerate(relative.parts):
        current = current / part
        is_final = index == len(relative.parts) - 1
        try:
            path_stat = current.lstat()
        except FileNotFoundError:
            return f"{current} (path component is missing)"
        except OSError as error:
            return f"{current} ({error.__class__.__name__}: {error})"
        if stat.S_ISLNK(path_stat.st_mode):
            return f"{current} (symbolic link is not allowed)"
        if is_final:
            if not stat.S_ISREG(path_stat.st_mode):
                return f"{current} (not a regular file)"
        elif not stat.S_ISDIR(path_stat.st_mode):
            return f"{current} (path component is not a directory)"
    return None


def load_path_resolution_bootstrap(root: Path):
    package_dir = root / "scripts" / PATH_RESOLUTION_PACKAGE
    bootstrap_path = package_dir / "bootstrap.py"
    bootstrap_problem = _loader_file_problem(root, bootstrap_path)
    if bootstrap_problem:
        raise RuntimeError(f"unsafe path-resolution bootstrap module: {bootstrap_problem}")

    spec = importlib.util.spec_from_file_location("_agentos_checked_path_resolution_bootstrap", bootstrap_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load path-resolution bootstrap module: {bootstrap_path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise RuntimeError(f"could not load path-resolution bootstrap module: {bootstrap_path}: {error}") from error
    return module


_ROOT_FOR_BOOTSTRAP = _loader_lexical_absolute(Path(__file__).parents[4])


try:
    _PATH_RESOLUTION_BOOTSTRAP = load_path_resolution_bootstrap(_ROOT_FOR_BOOTSTRAP)
    _MANAGED_PATHS = _PATH_RESOLUTION_BOOTSTRAP.load_checked_managed_paths(_ROOT_FOR_BOOTSTRAP)
except RuntimeError as error:
    print(f"AgentOS validation failed: {error}", file=sys.stderr)
    raise SystemExit(2)
_bootstrap_lexical_absolute = _PATH_RESOLUTION_BOOTSTRAP.lexical_absolute
_bootstrap_final_path_problem = _PATH_RESOLUTION_BOOTSTRAP.path_kind_problem
managed_path_problem_text = _MANAGED_PATHS.managed_path_problem_text


def load_publication_rules() -> None:
    global GENERATED_OUTPUT_PARTS
    global PERSONAL_OVERLAY_SKELETON_FILES
    global PUBLIC_EXPORT_EXCLUDED_DIRS
    global PUBLIC_EXPORT_ROOT_DIRS
    global PUBLIC_EXPORT_ROOT_FILES
    global gitkeep_file_reason
    global is_personal_overlay_skeleton_path
    global personal_overlay_skeleton_file_reason
    global publication_path_reason

    root = _bootstrap_lexical_absolute(Path(__file__).parents[4])
    rules_path = root / "scripts/agentos_publication_rules.py"
    rules_problem = managed_path_problem_text(
        root,
        rules_path,
        expected_kind="file",
        allow_missing=False,
    )
    if rules_problem:
        raise RuntimeError(f"unsafe publication rules script: {rules_problem}")

    spec = importlib.util.spec_from_file_location("agentos_publication_rules_checked", rules_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load publication rules script: {rules_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    GENERATED_OUTPUT_PARTS = module.GENERATED_OUTPUT_PARTS
    PERSONAL_OVERLAY_SKELETON_FILES = module.PERSONAL_OVERLAY_SKELETON_FILES
    PUBLIC_EXPORT_EXCLUDED_DIRS = module.PUBLIC_EXPORT_EXCLUDED_DIRS
    PUBLIC_EXPORT_ROOT_DIRS = module.PUBLIC_EXPORT_ROOT_DIRS
    PUBLIC_EXPORT_ROOT_FILES = module.PUBLIC_EXPORT_ROOT_FILES
    gitkeep_file_reason = module.gitkeep_file_reason
    is_personal_overlay_skeleton_path = module.is_personal_overlay_skeleton_path
    personal_overlay_skeleton_file_reason = module.personal_overlay_skeleton_file_reason
    publication_path_reason = module.publication_path_reason


try:
    load_publication_rules()
except RuntimeError as error:
    print(f"AgentOS validation failed: {error}", file=sys.stderr)
    raise SystemExit(2)


CODE_SPAN_RE = re.compile(r"`([^`]+)`")
SKILL_HEADING_RE = re.compile(r"^### `([^`]+)`\s*$", re.MULTILINE)
SKILL_FRONTMATTER_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
REQUIRED_SKILL_MANIFEST_FIELDS = (
    "Canonical source",
    "Contract status",
    "Mutability",
    "Tools and connectors",
    "Output artifact",
    "Filing rule",
    "Safety posture",
    "Verification coverage",
    "Upgrade notes",
)
ALLOWED_SKILL_CONTRACT_STATUSES = {"full", "partial", "needs-upgrade", "thin-adapter"}
ALLOWED_SKILL_MUTABILITY_LEVELS = {
    "read-only",
    "local-write",
    "connector-write",
    "external-write",
    "mixed",
}
PLACEHOLDER_SKILL_MANIFEST_VALUES = {"none", "n/a", "na", "tbd", "todo", "unknown", "safe"}
MUTATING_SKILL_APPROVAL_TERMS = (
    "ask",
    "approval",
    "approve",
    "approved",
    "authorization",
    "authorize",
    "explicit",
    "permitted",
    "permission",
    "requested",
    "user asks",
    "dry run",
)
PRIVATE_LOCAL_PATH_RE = r"[^\n`]+"
PRIVATE_TOKEN_RE = r"[^\s`'\"<>)\]}]+"
POSIX_ROOT = "/"
WINDOWS_SEGMENT_RE = r"[A-Za-z0-9._$ -]+"
PRIVATE_LOCAL_PATH_PATTERNS = [
    ("macOS home absolute path", re.compile(POSIX_ROOT + "Users" + POSIX_ROOT + PRIVATE_LOCAL_PATH_RE, re.IGNORECASE)),
    ("Linux home absolute path", re.compile(POSIX_ROOT + "home" + POSIX_ROOT + PRIVATE_LOCAL_PATH_RE, re.IGNORECASE)),
    (
        "POSIX temp absolute path",
        re.compile(POSIX_ROOT + r"(?:private/)?" + "tmp" + POSIX_ROOT + PRIVATE_LOCAL_PATH_RE, re.IGNORECASE),
    ),
    (
        "POSIX var temp absolute path",
        re.compile(
            POSIX_ROOT
            + r"(?:private/)?"
            + "var"
            + POSIX_ROOT
            + r"(?:tmp|folders)"
            + POSIX_ROOT
            + PRIVATE_LOCAL_PATH_RE,
            re.IGNORECASE,
        ),
    ),
    (
        "Windows user absolute path",
        re.compile(r"\b[A-Za-z]:[\\/]+Users[\\/]+" + PRIVATE_LOCAL_PATH_RE, re.IGNORECASE),
    ),
    (
        "Windows UNC path",
        re.compile(
            r"(?<!\\)\\\\"
            + r"(?![nrt][\\/])"
            + WINDOWS_SEGMENT_RE
            + r"[\\/]+"
            + WINDOWS_SEGMENT_RE
            + r"(?:[\\/]+[^`'\"<>\n]+)?",
            re.IGNORECASE,
        ),
    ),
    (
        "shell home or temp path",
        re.compile(
            r"(?:~|\$(?:HOME|USERPROFILE|TMPDIR|TEMP|TMP)|\$\{(?:HOME|USERPROFILE|TMPDIR|TEMP|TMP)\}|"
            r"%(?:USERPROFILE|TEMP|TMP)%)(?:[\\/][^`'\"<>\n]+)+",
            re.IGNORECASE,
        ),
    ),
]


@dataclass(frozen=True)
class PrivateMarker:
    label: str
    pattern: re.Pattern[str]


PRIVATE_MARKER_PATTERNS = [
    *[PrivateMarker(label, pattern) for label, pattern in PRIVATE_LOCAL_PATH_PATTERNS],
    PrivateMarker(
        "email address",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", re.IGNORECASE),
    ),
    PrivateMarker("family account identifier", re.compile(r"family\d{6,}", re.IGNORECASE)),
    PrivateMarker("Google Drive URL", re.compile(r"https://drive\.google\.com/" + PRIVATE_TOKEN_RE, re.IGNORECASE)),
    PrivateMarker(
        "Google Calendar group ID",
        re.compile(r"\b[A-Za-z0-9._%+-]+@group\.calendar\.google\.com\b", re.IGNORECASE),
    ),
]
SECRET_LIKE_PATTERNS = [
    ("private key block", re.compile(r"-----BEGIN (?:RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("OpenAI-style secret key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{20,}\b")),
]
GENERIC_LOCAL_TOOL_PATH_RE = re.compile(
    r"^(?:~|\$HOME|\$\{HOME\})[\\/](?:\.agents[\\/]skills|\.codex[\\/]automations)(?:[\\/].*)?$"
)
BENCHMARK_REQUIRED_HELP_FLAGS = (
    "--help",
    "--self-test",
    "--save-report",
    "--no-save-report",
    "--check-remote-main",
)
BENCHMARK_HARNESS_HELP_FLAGS = (
    "--harness",
    "--dry-run",
    "--no-dry-run",
    "--model",
    "--effort",
)


@dataclass
class Finding:
    check: str
    path: str
    message: str

    def format(self) -> str:
        return f"[{self.check}] {self.path}: {self.message}"

class ValidatorDelegate:
    def __init__(self, context: Any) -> None:
        self.context = context

    def __getattr__(self, name: str) -> Any:
        return getattr(self.context, name)


class AgentOSValidatorBase:
    def __init__(self, root: Path) -> None:
        self.root = _bootstrap_lexical_absolute(root)
        self.errors: list[Finding] = []
        self.warnings: list[Finding] = []
        self.checked: list[str] = []
        self.private_marker_patterns = [*PRIVATE_MARKER_PATTERNS]
        if not self.root_path_problem():
            self.private_marker_patterns.extend(self.load_private_marker_patterns())

    def add_error(self, check: str, path: Path | str, message: str) -> None:
        self.errors.append(Finding(check, self.display_path(path), self.redact_private_markers(message)))

    def add_warning(self, check: str, path: Path | str, message: str) -> None:
        self.warnings.append(Finding(check, self.display_path(path), self.redact_private_markers(message)))

    def has_errors_for(self, check: str) -> bool:
        return any(error.check == check for error in self.errors)

    def root_path_problem(self) -> str | None:
        return _bootstrap_final_path_problem(self.root, expected_kind="directory", allow_missing=False)

    def display_path(self, path: Path | str) -> str:
        if isinstance(path, Path):
            try:
                path_text = path.relative_to(self.root).as_posix()
            except ValueError:
                path_text = str(path)
        else:
            path_text = path
        return self.redact_private_markers(path_text)

    def redact_private_markers(self, text: str) -> str:
        redacted = text
        for marker in self.private_marker_patterns:
            redacted = marker.pattern.sub("[private-marker]", redacted)
        return redacted

    def private_marker_match(self, marker: PrivateMarker, text: str) -> re.Match[str] | None:
        for match in marker.pattern.finditer(text):
            if marker.label == "shell home or temp path" and GENERIC_LOCAL_TOOL_PATH_RE.match(match.group(0)):
                continue
            return match
        return None

    def is_regular_file(self, path: Path) -> bool:
        return not path.is_symlink() and path.is_file()

    def is_file_or_symlink(self, path: Path) -> bool:
        return path.is_symlink() or path.is_file()

    def read_text(self, path: Path, check: str) -> str:
        if path.is_symlink():
            self.add_error(
                check,
                path,
                "expected a regular text file, found symbolic link",
            )
            return ""
        if not path.exists():
            self.add_error(check, path, "required file is missing")
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            self.add_error(check, path, f"file is not valid UTF-8 text: {error.reason}")
            return ""

    def run_git(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def git_paths(self, args: list[str]) -> list[Path]:
        result = self.run_git([*args, "-z"])
        if result.returncode != 0:
            return []
        paths: list[Path] = []
        for raw_path in result.stdout.split("\0"):
            if raw_path:
                paths.append(Path(raw_path))
        return paths

    def no_follow_path_problem(
        self,
        path: Path,
        expected_kind: str | None = None,
        allow_missing: bool = True,
    ) -> str | None:
        problem = _MANAGED_PATHS.managed_path_problem(
            self.root,
            path,
            expected_kind=expected_kind,
            allow_missing=allow_missing,
            root_label="AgentOS root",
        )
        if problem and problem.reason.startswith("path is outside the AgentOS root:"):
            return "path is outside the AgentOS root"
        return problem.reason if problem else None

    def personal_overlay_root_problem(self, personal: Path) -> str | None:
        try:
            personal_stat = personal.lstat()
        except FileNotFoundError:
            return "personal overlay skeleton is missing"
        except OSError as error:
            return f"{error.__class__.__name__}: {error}"
        if stat.S_ISLNK(personal_stat.st_mode):
            return "Personal Overlay path used by validator must not be a symbolic link"
        if not personal.is_dir():
            return "personal overlay skeleton is not a directory"
        return None

    def iter_personal_overlay_files(self, personal: Path, check: str) -> list[Path]:
        files: list[Path] = []
        for path in sorted(personal.rglob("*")):
            try:
                path_stat = path.lstat()
            except OSError as error:
                self.add_error(check, path, f"{error.__class__.__name__}: {error}")
                continue
            if stat.S_ISLNK(path_stat.st_mode) or stat.S_ISREG(path_stat.st_mode):
                files.append(path)
        return files

    def load_private_marker_patterns(self) -> list[PrivateMarker]:
        check = "private marker config"
        marker_file = self.root / "personal/os/verification/privacy-markers.txt"
        marker_problem = self.no_follow_path_problem(marker_file, expected_kind="file", allow_missing=True)
        if marker_problem:
            self.add_error(check, marker_file, marker_problem)
            return []
        try:
            marker_file_stat = marker_file.lstat()
        except FileNotFoundError:
            return []
        except OSError as error:
            self.add_error(check, marker_file, f"{error.__class__.__name__}: {error}")
            return []
        if not stat.S_ISREG(marker_file_stat.st_mode):
            self.add_error(check, marker_file, "not a regular file")
            return []
        patterns: list[PrivateMarker] = []
        marker_index = 0
        for line in marker_file.read_text(encoding="utf-8").splitlines():
            marker = line.strip()
            if not marker or marker.startswith("#"):
                continue
            marker_index += 1
            marker_parts = [part for part in re.split(r"[\s_-]+", marker) if part]
            marker_pattern = (
                r"[\s_-]+".join(re.escape(part) for part in marker_parts)
                if len(marker_parts) > 1
                else re.escape(marker)
            )
            patterns.append(
                PrivateMarker(
                    f"configured private marker #{marker_index}",
                    re.compile(marker_pattern, re.IGNORECASE),
                )
            )
        return patterns

    def require_contains(
        self, text: str, needle: str, check: str, path: Path, label: str | None = None
    ) -> None:
        if needle not in text:
            self.add_error(check, path, f"missing {label or needle!r}")

    def resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path).expanduser()
        if path.is_absolute():
            return path
        return self.root / path

    def iter_content_scan_files(self) -> list[Path]:
        return sorted(
            path
            for path in self.root.rglob("*")
            if self.is_regular_file(path)
            and ".git" not in path.parts
        )

    def is_git_ignored(self, rel: Path) -> bool:
        if not (self.root / ".git").exists():
            return False
        return self.run_git(["check-ignore", "-q", "--", rel.as_posix()]).returncode == 0

    def report(self) -> int:
        if self.errors:
            print(f"AgentOS validation failed: {len(self.errors)} error(s).")
            for finding in self.errors:
                print(f"ERROR {finding.format()}")
            for finding in self.warnings:
                print(f"WARN  {finding.format()}")
            return 1

        print("AgentOS validation passed.")
        for check in self.checked:
            print(f"OK    {check}")
        for finding in self.warnings:
            print(f"WARN  {finding.format()}")
        return 0


def run_self_test(harness) -> None:
    root = harness.root / "common_fixture"
    (root / "os").mkdir(parents=True)
    marker_file = root / "personal/os/verification/privacy-markers.txt"
    marker_file.parent.mkdir(parents=True)
    marker_file.write_text("sensitive-client-name\n", encoding="utf-8")

    validator = harness.validator(root)
    drive_link = "https://drive.google.com/" + "file/d/private-id/view"
    calendar_id = "othercalendar" + "@group.calendar.google.com"
    validator.add_error(
        "redaction fixture",
        "docs/sensitive_client_name.md",
        "marker sensitive-client-name, drive " + drive_link + ", calendar " + calendar_id,
    )
    marker_symlink_root = harness.root / "common_marker_symlink_fixture"
    (marker_symlink_root / "os").mkdir(parents=True)
    marker_symlink_file = marker_symlink_root / "personal/os/verification/privacy-markers.txt"
    marker_symlink_file.parent.mkdir(parents=True)
    marker_target = marker_symlink_root / "marker-target.txt"
    marker_target.write_text("symlink-only-marker\n", encoding="utf-8")
    marker_symlink_file.symlink_to("../../../marker-target.txt")
    marker_symlink_validator = harness.validator(marker_symlink_root)

    harness.expect(
        "common redacts configured and built-in private markers",
        all("[private-marker]" in error.format() for error in validator.errors)
        and not any(
            sensitive in error.format()
            for sensitive in ["sensitive-client-name", "sensitive_client_name", "private-id", "othercalendar"]
            for error in validator.errors
        ),
    )
    harness.expect(
        "common rejects symlinked private marker config",
        any(
            error.check == "private marker config"
            and error.path == "personal/os/verification/privacy-markers.txt"
            and "symbolic link is not allowed" in error.message
            for error in marker_symlink_validator.errors
        )
        and not any(
            marker.label.startswith("configured private marker")
            for marker in marker_symlink_validator.private_marker_patterns
        ),
    )
    harness.record(validator, marker_symlink_validator)
