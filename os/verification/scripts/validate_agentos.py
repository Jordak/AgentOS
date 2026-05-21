#!/usr/bin/env python3
"""Deterministic local validators for AgentOS maintenance.

The checks in this script intentionally avoid network calls and connector reads.
They inspect local Markdown files, local path existence, and portable AgentOS
metadata. Machine-local skill mirrors are checked by the mirror-skills
skill instead of this portable validator.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

PUBLICATION_RULES_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(PUBLICATION_RULES_DIR) not in sys.path:
    sys.path.insert(0, str(PUBLICATION_RULES_DIR))

from agentos_publication_rules import (  # noqa: E402
    GENERATED_OUTPUT_PARTS,
    PERSONAL_OVERLAY_SKELETON_FILES,
    PUBLIC_EXPORT_EXCLUDED_DIRS,
    PUBLIC_EXPORT_ROOT_DIRS,
    PUBLIC_EXPORT_ROOT_FILES,
    gitkeep_file_reason,
    is_personal_overlay_skeleton_path,
    personal_overlay_skeleton_file_reason,
    publication_path_reason,
)


CODE_SPAN_RE = re.compile(r"`([^`]+)`")
SKILL_HEADING_RE = re.compile(r"^### `([^`]+)`\s*$", re.MULTILINE)
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


@dataclass
class Finding:
    check: str
    path: str
    message: str

    def format(self) -> str:
        return f"[{self.check}] {self.path}: {self.message}"


class AgentOSValidator:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.private_marker_patterns = [*PRIVATE_MARKER_PATTERNS, *self.load_private_marker_patterns(self.root)]
        self.errors: list[Finding] = []
        self.warnings: list[Finding] = []
        self.checked: list[str] = []

    def run(self) -> int:
        self.run_structural_checks()
        self.run_publication_precheck_checks()
        return self.report()

    def run_structural_only(self) -> int:
        self.run_structural_checks()
        return self.report()

    def run_structural_checks(self) -> None:
        self.check_markdown_path_portability()
        self.check_source_map_path_health()
        self.check_skill_frontmatter_parseability()
        self.check_skills_manifest_consistency()
        self.check_agent_contract_completeness()
        self.check_automation_registry_completeness()
        self.check_resolver_reachability()
        self.check_retrieval_eval_fixtures()
        self.check_benchmark_manifest()

    def run_publication_precheck(self) -> int:
        self.run_publication_precheck_checks()
        return self.report()

    def run_publication_precheck_checks(self) -> None:
        self.check_git_publication_source_set()
        self.check_private_overlay_files_are_ignored()
        self.check_personal_overlay_ignore_rules()
        self.check_personal_overlay_tracking(allow_private_files=True)
        self.check_core_private_markers()
        self.check_secret_like_tokens()
        self.checked.append("publication precheck")

    def run_public_export_validation(self, export_root: Path) -> int:
        self.root = export_root.resolve()
        self.check_no_git_directory()
        self.check_public_export_allowlist()
        self.check_personal_overlay_ignore_file_rules()
        self.check_personal_overlay_tracking(allow_private_files=False)
        self.check_core_private_markers()
        self.check_secret_like_tokens()
        self.check_no_private_generated_outputs()
        self.checked.append("public export validation")
        return self.report()

    def add_error(self, check: str, path: Path | str, message: str) -> None:
        self.errors.append(Finding(check, self.display_path(path), self.redact_private_markers(message)))

    def add_warning(self, check: str, path: Path | str, message: str) -> None:
        self.warnings.append(Finding(check, self.display_path(path), self.redact_private_markers(message)))

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

    def load_private_marker_patterns(self, root: Path) -> list[PrivateMarker]:
        marker_file = root / "personal/os/verification/privacy-markers.txt"
        if not marker_file.exists():
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

    def check_markdown_path_portability(self) -> None:
        check = "markdown path portability"
        root_agents = self.root / "AGENTS.md"
        root_agents_text = self.read_text(root_agents, check)
        if root_agents_text:
            self.require_contains(
                root_agents_text,
                "Unless otherwise stated, local file paths in AgentOS Markdown are relative to",
                check,
                root_agents,
                "root-relative path convention",
            )

        root_literal = str(self.root)
        for path in sorted(self.root.rglob("*.md")):
            if path.is_symlink() or ".git" in path.parts:
                continue
            text = self.read_text(path, check)
            for line_no, line in enumerate(text.splitlines(), start=1):
                if root_literal in line:
                    self.add_error(
                        check,
                        f"{self.display_path(path)}:{line_no}",
                        "hardcodes the AgentOS checkout path; use a root-relative AgentOS path",
                    )
                if "../" in line:
                    self.add_error(
                        check,
                        f"{self.display_path(path)}:{line_no}",
                        "uses a parent-relative AgentOS path; use a root-relative path",
                    )

        self.checked.append(check)

    def iter_content_scan_files(self) -> list[Path]:
        return sorted(
            path
            for path in self.root.rglob("*")
            if self.is_regular_file(path)
            and ".git" not in path.parts
        )

    def check_no_git_directory(self) -> None:
        check = "no git history"
        if (self.root / ".git").exists():
            self.add_error(check, self.root / ".git", "public export must not contain git history")
        self.checked.append(check)

    def check_public_export_allowlist(self) -> None:
        check = "public export allowlist"
        for path in sorted(self.root.rglob("*")):
            rel = path.relative_to(self.root)
            if path.is_dir() and not path.is_symlink():
                continue
            if path.is_symlink():
                self.add_error(check, rel.as_posix(), "public export contains a symbolic link")
                continue
            if not path.is_file():
                continue
            if any(part in PUBLIC_EXPORT_EXCLUDED_DIRS for part in rel.parts):
                self.add_error(check, path, "public export contains an excluded path")
                continue
            if len(rel.parts) == 1:
                if rel.as_posix() not in PUBLIC_EXPORT_ROOT_FILES:
                    self.add_error(check, path, "root file is not allowlisted for public export")
                continue
            if rel.parts[0] not in PUBLIC_EXPORT_ROOT_DIRS:
                self.add_error(check, path, "top-level directory is not allowlisted for public export")
                continue
            if rel.name == ".gitkeep":
                reason = gitkeep_file_reason(path)
                if reason:
                    self.add_error(check, path, reason)
                    continue
            reason = publication_path_reason(rel)
            if reason:
                self.add_error(check, path, reason)

        self.checked.append(check)

    def check_git_publication_source_set(self) -> None:
        check = "git publication source set"
        if not (self.root / ".git").exists():
            self.add_error(check, self.root / ".git", "publication precheck requires a git working tree")
            self.checked.append(check)
            return

        result = self.run_git(["ls-files", "-z"])
        if result.returncode != 0:
            self.add_error(check, self.root, f"could not list tracked files: {result.stderr.strip()}")
            self.checked.append(check)
            return

        missing_tracked: list[str] = []
        for raw_path in result.stdout.split("\0"):
            if not raw_path:
                continue
            rel = Path(raw_path)
            path = self.root / rel
            rel_text = rel.as_posix()
            if path.is_symlink():
                self.add_error(
                    check,
                    rel_text,
                    "tracked file is a symbolic link; public export rejects Git-visible symlinks",
                )
                continue
            if not path.exists():
                missing_tracked.append(rel_text)
                continue
            self.check_publishable_path(check, rel, tracked=True)

        untracked = self.git_paths(["ls-files", "--others", "--exclude-standard"])
        for rel in untracked:
            path = self.root / rel
            if path.is_symlink():
                self.add_error(
                    check,
                    rel.as_posix(),
                    "untracked unignored file is a symbolic link; public export rejects Git-visible symlinks",
                )
                continue
            self.check_publishable_path(check, rel, tracked=False)

        if missing_tracked:
            sample = ", ".join(missing_tracked[:8])
            if len(missing_tracked) > 8:
                sample += f", ... ({len(missing_tracked)} total)"
            self.add_error(
                check,
                self.root,
                f"tracked files are deleted in the working tree; stage deletions before a publication commit: {sample}",
            )

        self.checked.append(check)

    def check_publishable_path(self, check: str, rel: Path, tracked: bool) -> None:
        rel_text = rel.as_posix()
        label = "tracked file" if tracked else "untracked unignored file"
        if any(part in PUBLIC_EXPORT_EXCLUDED_DIRS for part in rel.parts):
            self.add_error(check, rel_text, f"{label} is in an excluded path")
            return
        if rel.parts[0] == "personal":
            if not is_personal_overlay_skeleton_path(rel):
                self.add_error(
                    check,
                    rel_text,
                    f"{label} under personal/ must be an allowlisted public-safe skeleton .gitkeep",
                )
                return
            reason = personal_overlay_skeleton_file_reason(self.root / rel)
            if reason:
                self.add_error(check, rel_text, f"{label} {reason}")
            return
        if len(rel.parts) == 1:
            if rel_text not in PUBLIC_EXPORT_ROOT_FILES:
                self.add_error(check, rel_text, f"{label} is not an allowlisted root file")
            return
        if rel.parts[0] not in PUBLIC_EXPORT_ROOT_DIRS:
            self.add_error(check, rel_text, f"{label} is not under an allowlisted top-level directory")
            return
        if rel.name == ".gitkeep":
            reason = gitkeep_file_reason(self.root / rel)
            if reason:
                self.add_error(check, rel_text, f"{label} {reason}")
                return
        reason = publication_path_reason(rel)
        if reason:
            self.add_error(check, rel_text, f"{label} {reason}")
            return

    def check_private_overlay_files_are_ignored(self) -> None:
        check = "private overlay ignore coverage"
        personal = self.root / "personal"
        if not personal.exists():
            self.add_error(check, personal, "personal overlay skeleton is missing")
            self.checked.append(check)
            return

        checked_private_files = 0
        for path in sorted(p for p in personal.rglob("*") if self.is_file_or_symlink(p)):
            rel_path = path.relative_to(self.root)
            if path.name == ".gitkeep" and is_personal_overlay_skeleton_path(rel_path):
                continue
            checked_private_files += 1
            rel = rel_path.as_posix()
            tracked = self.run_git(["ls-files", "--error-unmatch", "--", rel])
            if tracked.returncode == 0:
                self.add_error(check, rel, "private overlay file is tracked by git")
                continue
            ignored = self.run_git(["check-ignore", "-q", "--", rel])
            if ignored.returncode != 0:
                self.add_error(check, rel, "private overlay file is not covered by .gitignore")

        self.checked.append(f"{check} ({checked_private_files} private file(s) checked)")

    def check_personal_overlay_ignore_rules(self) -> None:
        check = "personal overlay ignore rules"
        if not (self.root / ".git").exists():
            self.add_error(check, self.root / ".git", "personal overlay ignore rules require a git working tree")
            self.checked.append(check)
            return

        private_probe = Path("personal/os/agents/private-client/.gitkeep")
        if self.run_git(["check-ignore", "--no-index", "-q", "--", private_probe.as_posix()]).returncode != 0:
            self.add_error(
                check,
                private_probe.as_posix(),
                "private-specific .gitkeep paths must remain ignored; only public-safe skeleton .gitkeep paths may be unignored",
            )

        for rel_text in sorted(PERSONAL_OVERLAY_SKELETON_FILES):
            if self.run_git(["check-ignore", "--no-index", "-q", "--", rel_text]).returncode == 0:
                self.add_error(
                    check,
                    rel_text,
                    "public-safe Personal Overlay skeleton .gitkeep path must be unignored",
                )

        self.checked.append(check)

    def check_personal_overlay_ignore_file_rules(self) -> None:
        check = "personal overlay ignore file"
        gitignore = self.root / ".gitignore"
        text = self.read_text(gitignore, check)
        if not text:
            self.checked.append(check)
            return

        lines = {line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")}
        required_rules = {"personal/**/*", "!personal/**/"}
        required_rules.update(f"!{rel_text}" for rel_text in PERSONAL_OVERLAY_SKELETON_FILES)

        for rule in sorted(required_rules):
            if rule not in lines:
                self.add_error(check, gitignore, f"missing required Personal Overlay ignore rule: {rule}")

        allowed_unignore_rules = {"!personal/**/"}
        allowed_unignore_rules.update(f"!{rel_text}" for rel_text in PERSONAL_OVERLAY_SKELETON_FILES)
        for rule in sorted(line for line in lines if line.startswith("!personal/")):
            if rule not in allowed_unignore_rules:
                self.add_error(
                    check,
                    gitignore,
                    f"unexpected Personal Overlay unignore rule: {rule}",
                )

        if "!personal/**/.gitkeep" in lines:
            self.add_error(
                check,
                gitignore,
                "broad Personal Overlay .gitkeep unignore is not allowed; only public-safe skeleton .gitkeep paths may be unignored",
            )

        self.checked.append(check)

    def check_personal_overlay_tracking(self, allow_private_files: bool) -> None:
        check = "personal overlay skeleton"
        personal = self.root / "personal"
        if not personal.exists():
            self.add_error(check, personal, "personal overlay skeleton is missing")
            self.checked.append(check)
            return
        for rel_text in sorted(PERSONAL_OVERLAY_SKELETON_FILES):
            skeleton_path = self.root / rel_text
            if not skeleton_path.exists():
                self.add_error(check, rel_text, "required Personal Overlay skeleton .gitkeep is missing")
                continue
            reason = personal_overlay_skeleton_file_reason(skeleton_path)
            if reason:
                self.add_error(check, skeleton_path, reason)
            if allow_private_files and (self.root / ".git").exists():
                tracked = self.run_git(["ls-files", "--error-unmatch", "--", rel_text])
                if tracked.returncode != 0:
                    self.add_error(check, rel_text, "Personal Overlay skeleton .gitkeep must be tracked by git")
        for path in sorted(p for p in personal.rglob("*") if self.is_file_or_symlink(p)):
            rel_text = path.relative_to(self.root).as_posix()
            if path.name == ".gitkeep":
                rel_path = path.relative_to(self.root)
                if not is_personal_overlay_skeleton_path(rel_path):
                    if allow_private_files and self.is_git_ignored(rel_path):
                        continue
                    self.add_error(
                        check,
                        path,
                        "personal overlay .gitkeep path is not in the public-safe skeleton allowlist",
                    )
                    continue
                continue
            if allow_private_files:
                continue
            self.add_error(check, path, "public export may contain only .gitkeep files under personal/")
        self.checked.append(check)

    def is_git_ignored(self, rel: Path) -> bool:
        if not (self.root / ".git").exists():
            return False
        return self.run_git(["check-ignore", "-q", "--", rel.as_posix()]).returncode == 0

    def should_skip_publication_privacy_scan(
        self, path: Path, scan_personal_gitkeep_paths: bool = False
    ) -> bool:
        rel = path.relative_to(self.root)
        if any(part in PUBLIC_EXPORT_EXCLUDED_DIRS for part in rel.parts):
            return True
        if rel.parts[0] == "personal":
            return not (scan_personal_gitkeep_paths and path.name == ".gitkeep")
        return self.is_git_ignored(rel)

    def should_validate_agent_dir(self, agent_dir: Path) -> bool:
        if (agent_dir / "JOB.md").exists() or (agent_dir / "AGENTS.md").exists():
            return True
        for path in sorted(p for p in agent_dir.rglob("*") if self.is_file_or_symlink(p)):
            rel = path.relative_to(self.root)
            if not self.is_git_ignored(rel):
                return True
        return False

    def check_core_private_markers(self) -> None:
        check = "private marker scan"
        for path in sorted(p for p in self.root.rglob("*") if self.is_file_or_symlink(p) and ".git" not in p.parts):
            if self.should_skip_publication_privacy_scan(path, scan_personal_gitkeep_paths=True):
                continue
            rel = path.relative_to(self.root)
            rel_text = rel.as_posix()
            for marker in self.private_marker_patterns:
                if self.private_marker_match(marker, rel_text):
                    self.add_error(
                        check,
                        self.redact_private_markers(rel_text),
                        f"private marker matched path with {marker.label}",
                    )
                    break

        for path in self.iter_content_scan_files():
            if self.should_skip_publication_privacy_scan(path):
                continue
            text = self.read_text(path, check)
            for line_no, line in enumerate(text.splitlines(), start=1):
                for marker in self.private_marker_patterns:
                    if self.private_marker_match(marker, line):
                        self.add_error(
                            check,
                            f"{self.redact_private_markers(self.display_path(path))}:{line_no}",
                            f"private marker matched {marker.label}",
                        )
                        break
        self.checked.append(check)

    def check_no_private_generated_outputs(self) -> None:
        check = "private generated outputs"
        for path in self.root.rglob("*"):
            if not self.is_file_or_symlink(path) or ".git" in path.parts:
                continue
            rel = path.relative_to(self.root)
            if rel.parts[0] == "personal":
                continue
            if any(part in GENERATED_OUTPUT_PARTS for part in rel.parts):
                if "example" in path.name.lower() or ".template." in path.name:
                    continue
                self.add_error(
                    check,
                    path,
                    "generated outputs belong in personal/os/ unless sanitized as examples or templates",
                )
        self.checked.append(check)

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

    def check_source_map_path_health(self) -> None:
        check = "source-map path health"
        source_map = self.root / "os/context/SOURCE_MAP.md"
        text = self.read_text(source_map, check)
        if not text:
            return

        for span in CODE_SPAN_RE.findall(text):
            candidate = span.strip()
            if "://" in candidate:
                continue
            if candidate.startswith(("/", "~")):
                path = Path(candidate).expanduser()
            elif candidate.startswith("os/") or candidate in {"AGENTS.md", "CLAUDE.md", "README.md"}:
                path = self.resolve_path(candidate)
            else:
                continue
            if not path.exists():
                self.add_error(
                    check,
                    source_map,
                    f"listed local path does not exist: {candidate}",
                )

        for line_no, line in enumerate(text.splitlines(), start=1):
            if "TODO" in line:
                self.add_warning(
                    check,
                    f"{self.display_path(source_map)}:{line_no}",
                    "source map contains TODO; confirm it remains intentional",
                )

        self.checked.append(check)

    def check_secret_like_tokens(self) -> None:
        check = "secret-like token scan"
        for path in self.iter_content_scan_files():
            if self.should_skip_publication_privacy_scan(path):
                continue
            text = self.read_text(path, check)
            for line_no, line in enumerate(text.splitlines(), start=1):
                for label, pattern in SECRET_LIKE_PATTERNS:
                    if pattern.search(line):
                        self.add_error(
                            check,
                            f"{self.display_path(path)}:{line_no}",
                            f"found {label}",
                        )
                        break

        self.checked.append(check)

    def check_skills_manifest_consistency(self) -> None:
        check = "skills manifest consistency"
        manifest_path = self.root / "os/skills/MANIFEST.md"
        manifest = self.read_text(manifest_path, check)
        if not manifest:
            return

        entries = self.skill_manifest_entries(manifest)
        expected = self.discover_canonical_skills()

        for forbidden in [
            "- Installed mirror:",
            "- Mirror state:",
            "Installed harness mirrors tracked",
            "Mirror state checked",
        ]:
            if forbidden in manifest:
                self.add_error(
                    check,
                    manifest_path,
                    f"manifest records machine-local mirror state: {forbidden}",
                )

        for skill_name, source_path in sorted(expected.items()):
            if skill_name not in entries:
                self.add_error(
                    check,
                    manifest_path,
                    f"canonical skill {skill_name!r} is missing from manifest",
                )

        for skill_name, section in sorted(entries.items()):
            canonical = self.extract_field(section, "Canonical source")
            contract = self.extract_field(section, "Contract status")

            for field_name, value in {
                "Canonical source": canonical,
                "Contract status": contract,
                "Mutability": self.extract_field(section, "Mutability"),
                "Tools and connectors": self.extract_field(section, "Tools and connectors"),
                "Output artifact": self.extract_field(section, "Output artifact"),
                "Filing rule": self.extract_field(section, "Filing rule"),
                "Safety posture": self.extract_field(section, "Safety posture"),
                "Verification coverage": self.extract_field(section, "Verification coverage"),
                "Upgrade notes": self.extract_field(section, "Upgrade notes"),
            }.items():
                if not value:
                    self.add_error(check, manifest_path, f"{skill_name}: missing {field_name}")

            if canonical:
                canonical_path = self.resolve_path(canonical)
                if not canonical_path.exists():
                    self.add_error(
                        check,
                        manifest_path,
                        f"{skill_name}: canonical source does not exist: {canonical}",
                    )
                elif contract == "full":
                    self.check_full_skill_contract(skill_name, canonical_path, check)

        self.checked.append(check)

    def check_skill_frontmatter_parseability(self) -> None:
        check = "skill frontmatter parseability"
        for skill_name, path in sorted(self.discover_canonical_skills().items()):
            text = self.read_text(path, check)
            if not text:
                continue
            lines = text.splitlines()
            if not lines or lines[0] != "---":
                self.add_error(check, path, f"{skill_name}: missing YAML frontmatter delimiter")
                continue
            try:
                end_index = lines[1:].index("---") + 1
            except ValueError:
                self.add_error(check, path, f"{skill_name}: missing closing YAML frontmatter delimiter")
                continue

            fields: dict[str, str] = {}
            for line_no, line in enumerate(lines[1:end_index], start=2):
                if not line.strip():
                    continue
                match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
                if not match:
                    self.add_error(
                        check,
                        f"{self.display_path(path)}:{line_no}",
                        f"{skill_name}: frontmatter line must be simple key: value",
                    )
                    continue
                key, value = match.groups()
                value = value.strip()
                fields[key] = value
                if not value:
                    self.add_error(
                        check,
                        f"{self.display_path(path)}:{line_no}",
                        f"{skill_name}: frontmatter field {key!r} is empty",
                    )
                    continue
                if value[0] in {"'", '"'}:
                    if len(value) < 2 or value[-1] != value[0]:
                        self.add_error(
                            check,
                            f"{self.display_path(path)}:{line_no}",
                            f"{skill_name}: quoted frontmatter field {key!r} is not closed",
                        )
                    continue
                if re.search(r":\s", value):
                    self.add_error(
                        check,
                        f"{self.display_path(path)}:{line_no}",
                        f"{skill_name}: plain frontmatter field {key!r} contains ': '; quote the value",
                    )

            for field_name in ["name", "description"]:
                if field_name not in fields:
                    self.add_error(check, path, f"{skill_name}: missing frontmatter field {field_name!r}")

        self.checked.append(check)

    def skill_manifest_entries(self, manifest: str) -> dict[str, str]:
        matches = list(SKILL_HEADING_RE.finditer(manifest))
        entries: dict[str, str] = {}
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(manifest)
            entries[match.group(1)] = manifest[start:end]
        return entries

    def discover_canonical_skills(self) -> dict[str, Path]:
        skills_dir = self.root / "os/skills"
        skills: dict[str, Path] = {}
        for path in skills_dir.glob("*.md"):
            if path.name in {"MANIFEST.md", "README.md", "SKILL_CONTRACT.md"}:
                continue
            skills[path.stem] = path
        for path in skills_dir.glob("*/SKILL.md"):
            skills[path.parent.name] = path
        return skills

    def extract_field(self, section: str, field_name: str) -> str | None:
        pattern = re.compile(rf"^- {re.escape(field_name)}:\s*(.*)$", re.MULTILINE)
        match = pattern.search(section)
        if not match:
            return None
        value = match.group(1).strip()
        code_span = CODE_SPAN_RE.search(value)
        if code_span:
            return code_span.group(1)
        return value.rstrip(".").strip()

    def resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path).expanduser()
        if path.is_absolute():
            return path
        return self.root / path

    def check_full_skill_contract(self, skill_name: str, path: Path, check: str) -> None:
        text = self.read_text(path, check)
        required_needles = [
            "Inputs:",
            "Output artifact:",
            "Mutability:",
            "Tools and connectors:",
            "Safety:",
            "Verification",
        ]
        for needle in required_needles:
            self.require_contains(text, needle, check, path, f"{skill_name} full contract field {needle}")
        if "Workflow Phases" not in text and "Phases:" not in text:
            self.add_error(check, path, f"{skill_name}: full contract missing workflow phases")
        if "Quality Bar" not in text and "Quality" not in text:
            self.add_error(check, path, f"{skill_name}: full contract missing quality bar")
        if "File Conventions" not in text and "Filing" not in text:
            self.add_error(check, path, f"{skill_name}: full contract missing filing rules")

    def check_agent_contract_completeness(self) -> None:
        check = "agent contract completeness"
        agents_dir = self.root / "os/agents"
        if not agents_dir.exists():
            self.add_error(check, agents_dir, "agents directory is missing")
            return

        for agent_dir in sorted(path for path in agents_dir.iterdir() if path.is_dir()):
            if not self.should_validate_agent_dir(agent_dir):
                continue
            job = agent_dir / "JOB.md"
            instructions = agent_dir / "AGENTS.md"
            job_text = self.read_text(job, check)
            instructions_text = self.read_text(instructions, check)
            combined = f"{job_text}\n{instructions_text}"

            for section in ["## Job", "## Inputs", "## Outputs", "## Cadence"]:
                self.require_contains(job_text, section, check, job, section)

            if not any(token in combined for token in ["## Boundaries", "## Safety", "## Source Discipline"]):
                self.add_error(
                    check,
                    agent_dir,
                    "missing boundaries, safety, or source-discipline guidance",
                )
            if not any(token in combined for token in ["## Verification", "## Verification Checklist", "## Quality Bar", "## Success Criteria"]):
                self.add_error(
                    check,
                    agent_dir,
                    "missing verification, quality, or success criteria guidance",
                )

        self.checked.append(check)

    def check_automation_registry_completeness(self) -> None:
        check = "automation registry completeness"
        registry_path = self.root / "os/automations/AUTOMATIONS.md"
        registry = self.read_text(registry_path, check)
        if not registry:
            return

        active = self.extract_between_headers(registry, "## Active Automations", "## Retired / Completed One-Offs")
        active_sections = self.section_map(active, level="###")
        if not active_sections and "No active Core automations." not in active:
            self.add_error(check, registry_path, "no active automation sections found")
        for name, section in active_sections.items():
            for label in [
                "Automation id:",
                "Status:",
                "Kind:",
                "Trigger:",
                "Schedule rule:",
                "Workspace:",
                "Execution environment:",
                "Model:",
                "Invocation prompt:",
                "Inputs:",
                "Output:",
                "Verification:",
            ]:
                if label not in section:
                    self.add_error(check, registry_path, f"active automation {name!r} missing {label}")
            definition = self.field_following_code_span(section, "Current Codex definition:")
            if definition and not self.resolve_machine_local_path(definition).exists():
                self.add_error(
                    check,
                    registry_path,
                    f"active automation {name!r} definition path does not exist: {definition}",
                )

        candidates = self.extract_between_headers(registry, "## Candidate Automations", "## Automation Creation Checklist")
        for name, section in self.section_map(candidates, level="###").items():
            for label in ["Purpose:", "Suggested trigger:", "Suggested output:", "Activation standard:"]:
                if label not in section:
                    self.add_error(check, registry_path, f"candidate automation {name!r} missing {label}")

        checklist = self.extract_between_headers(registry, "## Automation Creation Checklist", "## Automation Spec Template")
        for item in ["output location", "verification checklist", "external sends", "workspace path", "source map"]:
            if item not in checklist:
                self.add_error(check, registry_path, f"automation creation checklist missing {item!r}")

        self.checked.append(check)

    def extract_between_headers(self, text: str, start_header: str, end_header: str) -> str:
        start = text.find(start_header)
        if start == -1:
            return ""
        end = text.find(end_header, start + len(start_header))
        if end == -1:
            return text[start:]
        return text[start:end]

    def section_map(self, text: str, level: str) -> dict[str, str]:
        pattern = re.compile(rf"^{re.escape(level)}\s+(.+?)\s*$", re.MULTILINE)
        matches = list(pattern.finditer(text))
        sections: dict[str, str] = {}
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            sections[match.group(1)] = text[start:end]
        return sections

    def field_following_code_span(self, section: str, label: str) -> str | None:
        label_index = section.find(label)
        if label_index == -1:
            return None
        match = CODE_SPAN_RE.search(section, label_index)
        return match.group(1) if match else None

    def resolve_machine_local_path(self, path_text: str) -> Path:
        """Resolve documented machine-local path tokens while keeping docs portable."""
        if path_text.startswith("$CODEX_HOME/"):
            codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
            return codex_home / path_text.removeprefix("$CODEX_HOME/")
        return Path(os.path.expandvars(path_text)).expanduser()

    def check_resolver_reachability(self) -> None:
        check = "resolver reachability"
        resolver = self.root / "os/RESOLVER.md"
        resolver_text = self.read_text(resolver, check)
        if not resolver_text:
            return

        root_agents = self.read_text(self.root / "AGENTS.md", check)
        index = self.read_text(self.root / "os/INDEX.md", check)
        playbook = self.read_text(self.root / "os/playbook/AGENTOS_PLAYBOOK.md", check)
        self.require_contains(root_agents, "os/RESOLVER.md", check, self.root / "AGENTS.md")
        self.require_contains(index, "RESOLVER.md", check, self.root / "os/INDEX.md")
        self.require_contains(playbook, "os/RESOLVER.md", check, self.root / "os/playbook/AGENTOS_PLAYBOOK.md")

        for path in [
            self.root / "os/context/README.md",
            self.root / "os/memory/README.md",
            self.root / "os/skills/README.md",
            self.root / "os/agents/README.md",
        ]:
            if not path.exists():
                self.add_error(check, path, "directory resolver is missing")

        for span in CODE_SPAN_RE.findall(resolver_text):
            candidate = span.strip()
            if "://" in candidate:
                continue
            if not self.looks_like_local_reference(candidate):
                continue
            if candidate.startswith("personal/os/"):
                continue
            if not self.reference_exists(candidate):
                self.add_error(check, resolver, f"referenced path is not reachable: {candidate}")

        self.checked.append(check)

    def check_retrieval_eval_fixtures(self) -> None:
        check = "retrieval eval fixtures"
        fixture_path = self.root / "os/verification/retrieval/fixtures.json"
        raw = self.read_text(fixture_path, check)
        if not raw:
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            self.add_error(check, fixture_path, f"invalid JSON: {error}")
            return

        fixtures = data.get("fixtures")
        if not isinstance(fixtures, list) or not fixtures:
            self.add_error(check, fixture_path, "fixtures must be a non-empty list")
            return

        required_categories = {
            "current-awareness brief",
            "portfolio gap scan",
            "morning brief",
            "weekly review",
            "skill update",
            "skillify workflow",
            "github issue breakdown",
            "mapped-project handoff",
            "safety-sensitive external action",
        }
        seen_categories: set[str] = set()

        resolver_text = self.read_text(self.root / "os/RESOLVER.md", check)
        source_map_text = self.read_text(self.root / "os/context/SOURCE_MAP.md", check)

        for fixture in fixtures:
            if not isinstance(fixture, dict):
                self.add_error(check, fixture_path, "fixture entries must be objects")
                continue
            fixture_id = fixture.get("id")
            prompt = fixture.get("prompt")
            category = fixture.get("category")
            expected = fixture.get("expected", {})
            evidence = fixture.get("evidence", [])
            if not fixture_id:
                self.add_error(check, fixture_path, "fixture missing id")
                continue
            if not prompt:
                self.add_error(check, fixture_path, f"{fixture_id}: missing prompt")
            if category:
                seen_categories.add(category)
            if not isinstance(expected, dict) or not expected:
                self.add_error(check, fixture_path, f"{fixture_id}: missing expected route")
                continue
            if not isinstance(evidence, list) or not evidence:
                self.add_error(check, fixture_path, f"{fixture_id}: missing evidence list")

            self.check_expected_route(check, fixture_path, fixture_id, expected, resolver_text, source_map_text)
            self.check_fixture_evidence(check, fixture_path, fixture_id, expected, evidence)

        missing_categories = sorted(required_categories - seen_categories)
        if missing_categories:
            self.add_error(
                check,
                fixture_path,
                f"missing required fixture categories: {', '.join(missing_categories)}",
            )

        self.checked.append(check)

    def check_benchmark_manifest(self) -> None:
        check = "benchmark manifest completeness"
        manifest_path = self.root / "os/verification/BENCHMARKS.json"
        raw = self.read_text(manifest_path, check)
        if not raw:
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            self.add_error(check, manifest_path, f"invalid JSON: {error}")
            self.checked.append(check)
            return

        if type(data.get("version")) is not int or data.get("version") < 1:
            self.add_error(check, manifest_path, "version must be a positive integer")

        benchmarks = data.get("benchmarks")
        if not isinstance(benchmarks, list) or not benchmarks:
            self.add_error(check, manifest_path, "benchmarks must be a non-empty list")
            self.checked.append(check)
            return

        seen_ids: set[str] = set()
        seen_scripts: set[str] = set()
        manifest_scripts: set[str] = set()

        for index, benchmark in enumerate(benchmarks, start=1):
            label = f"benchmarks[{index}]"
            if not isinstance(benchmark, dict):
                self.add_error(check, manifest_path, f"{label} must be an object")
                continue

            benchmark_id = benchmark.get("id")
            if not isinstance(benchmark_id, str) or not benchmark_id:
                self.add_error(check, manifest_path, f"{label}.id must be a non-empty string")
                benchmark_id = label
            elif benchmark_id in seen_ids:
                self.add_error(check, manifest_path, f"duplicate benchmark id: {benchmark_id}")
            else:
                seen_ids.add(benchmark_id)

            script = self.validate_manifest_path_field(check, manifest_path, benchmark_id, benchmark, "script")
            reports_dir = self.validate_manifest_path_field(
                check,
                manifest_path,
                benchmark_id,
                benchmark,
                "reports_dir",
            )
            run_glob = benchmark.get("run_glob")
            if not isinstance(run_glob, str) or not run_glob:
                self.add_error(check, manifest_path, f"{benchmark_id}: run_glob must be a non-empty string")
            elif Path(run_glob).is_absolute() or ".." in Path(run_glob).parts:
                self.add_error(check, manifest_path, f"{benchmark_id}: run_glob must be relative to reports_dir")

            summary_path = benchmark.get("summary_path")
            if not isinstance(summary_path, list) or not summary_path:
                self.add_error(check, manifest_path, f"{benchmark_id}: summary_path must be a non-empty list")
            elif not all(isinstance(part, str) and part for part in summary_path):
                self.add_error(
                    check,
                    manifest_path,
                    f"{benchmark_id}: summary_path must contain only non-empty strings",
                )

            weekly_review = benchmark.get("weekly_review")
            if not isinstance(weekly_review, dict):
                self.add_error(check, manifest_path, f"{benchmark_id}: weekly_review must be an object")
            else:
                check_freshness = weekly_review.get("check_freshness")
                if not isinstance(check_freshness, bool):
                    self.add_error(
                        check,
                        manifest_path,
                        f"{benchmark_id}: weekly_review.check_freshness must be true or false",
                    )
                elif check_freshness:
                    for field in ["min_behavioral_total", "max_age_days"]:
                        value = weekly_review.get(field)
                        if type(value) is not int or value <= 0:
                            self.add_error(
                                check,
                                manifest_path,
                                f"{benchmark_id}: weekly_review.{field} must be a positive integer",
                            )

            if script:
                manifest_scripts.add(script)
                if script in seen_scripts:
                    self.add_error(check, manifest_path, f"{benchmark_id}: duplicate script path: {script}")
                else:
                    seen_scripts.add(script)
                if not self.resolve_path(script).is_file():
                    self.add_error(check, manifest_path, f"{benchmark_id}: script does not exist: {script}")
            if reports_dir and not self.resolve_path(reports_dir).is_dir():
                self.add_error(
                    check,
                    manifest_path,
                    f"{benchmark_id}: reports_dir does not exist or is not a directory: {reports_dir}",
                )

        discovered_scripts = {
            path.relative_to(self.root).as_posix()
            for path in self.root.glob("os/verification/**/scripts/benchmark_*.py")
        }
        for script in sorted(discovered_scripts - manifest_scripts):
            self.add_error(check, manifest_path, f"benchmark script missing from manifest: {script}")

        self.checked.append(check)

    def validate_manifest_path_field(
        self,
        check: str,
        manifest_path: Path,
        benchmark_id: str,
        benchmark: dict,
        field_name: str,
    ) -> str | None:
        value = benchmark.get(field_name)
        if not isinstance(value, str) or not value:
            self.add_error(check, manifest_path, f"{benchmark_id}: {field_name} must be a non-empty string")
            return None
        path = Path(value)
        if path.is_absolute() or value.startswith("~") or ".." in path.parts:
            self.add_error(check, manifest_path, f"{benchmark_id}: {field_name} must be root-relative")
            return None
        return value

    def check_expected_route(
        self,
        check: str,
        fixture_path: Path,
        fixture_id: str,
        expected: dict,
        resolver_text: str,
        source_map_text: str,
    ) -> None:
        skill = expected.get("skill")
        if skill:
            skill_file = self.skill_file_for(skill)
            if not skill_file.exists():
                self.add_error(check, fixture_path, f"{fixture_id}: expected skill not found: {skill}")

        if expected.get("resolver_role") == "tie-breakers-only":
            for needle in ["If a harness exposes a matching skill", "tie-breakers"]:
                if needle not in resolver_text:
                    self.add_error(
                        check,
                        fixture_path,
                        f"{fixture_id}: resolver missing harness/tie-breaker policy: {needle}",
                    )

        agent = expected.get("agent")
        if agent:
            agent_dir = self.root / "os/agents" / agent
            for filename in ["JOB.md", "AGENTS.md"]:
                if not (agent_dir / filename).exists():
                    self.add_error(
                        check,
                        fixture_path,
                        f"{fixture_id}: expected agent file missing: os/agents/{agent}/{filename}",
                    )

        playbook = expected.get("playbook")
        if playbook and not self.resolve_path(playbook).exists():
            self.add_error(check, fixture_path, f"{fixture_id}: expected playbook missing: {playbook}")

        filing_path = expected.get("filing_path")
        if filing_path and not self.reference_exists(filing_path):
            self.add_error(check, fixture_path, f"{fixture_id}: filing path is not reachable: {filing_path}")

        handoff_destination = expected.get("handoff_destination")
        if handoff_destination and not self.reference_exists(handoff_destination):
            self.add_error(
                check,
                fixture_path,
                f"{fixture_id}: handoff destination is not reachable: {handoff_destination}",
            )

        safety_path = expected.get("safety_path")
        if safety_path and not self.resolve_path(safety_path).exists():
            self.add_error(check, fixture_path, f"{fixture_id}: safety path is missing: {safety_path}")

        source_map_entry = expected.get("source_map_entry")
        if source_map_entry and source_map_entry not in source_map_text:
            self.add_error(
                check,
                fixture_path,
                f"{fixture_id}: source map does not contain entry {source_map_entry!r}",
            )

        if expected.get("ask_before_external_action"):
            for needle in ["Pause and ask the user before", "sending email", "posting publicly"]:
                if needle not in resolver_text:
                    self.add_error(
                        check,
                        fixture_path,
                        f"{fixture_id}: resolver missing approval-pause evidence: {needle}",
                    )

    def skill_file_for(self, skill_name: str) -> Path:
        directory_skill = self.root / "os/skills" / skill_name / "SKILL.md"
        if directory_skill.exists():
            return directory_skill
        return self.root / "os/skills" / f"{skill_name}.md"

    def check_fixture_evidence(
        self,
        check: str,
        fixture_path: Path,
        fixture_id: str,
        expected: dict,
        evidence: list,
    ) -> None:
        for item in evidence:
            if not isinstance(item, dict):
                self.add_error(check, fixture_path, f"{fixture_id}: evidence entries must be objects")
                continue
            raw_path = item.get("path")
            contains = item.get("contains", [])
            if not raw_path:
                self.add_error(check, fixture_path, f"{fixture_id}: evidence missing path")
                continue
            if raw_path == "os/skills/MANIFEST.md" and expected.get("skill"):
                self.add_error(
                    check,
                    fixture_path,
                    f"{fixture_id}: manifest may not be used as routing evidence for a skill",
                )
            path = self.resolve_path(raw_path)
            text = self.read_text(path, check)
            for needle in contains:
                if needle not in text:
                    self.add_error(
                        check,
                        path,
                        f"{fixture_id}: evidence missing required text {needle!r}",
                    )

    def looks_like_local_reference(self, candidate: str) -> bool:
        if candidate.startswith("$"):
            return False
        return candidate.endswith((".md", "/")) or "/" in candidate

    def reference_exists(self, candidate: str) -> bool:
        path = Path(candidate).expanduser()
        if path.is_absolute():
            return path.exists()
        return (self.root / candidate).exists() or (self.root / "os" / candidate).exists()


def run_self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="agentos-validator-") as tmp:
        root = Path(tmp).resolve()
        root_agents = root / "AGENTS.md"
        root_agents.write_text(
            "# AgentOS\n\n"
            "Unless otherwise stated, local file paths in AgentOS Markdown are relative to the AgentOS repository root.\n",
            encoding="utf-8",
        )
        portability_fixture = root / "os/playbook/PORTABILITY.md"
        portability_fixture.parent.mkdir(parents=True)
        portability_fixture.write_text(
            f"# Fixture\n\nBad internal path: `{root}/os/INDEX.md`\n\nBad parent path: `../INDEX.md`\n",
            encoding="utf-8",
        )
        source_map = root / "os/context/SOURCE_MAP.md"
        source_map.parent.mkdir(parents=True)
        missing = root / "definitely-missing"
        private_home_path = "/" + "Users" + "/example-user/PrivateProject/file.md"
        private_spaced_home_path = "/" + "Users" + "/example-user/Private Project/file.md"
        private_punctuated_home_path = "/" + "Users" + "/example-user/Client (O'Brien)/tail-segment.md"
        private_linux_home_path = "/" + "home" + "/example-user/PrivateProject/file.md"
        private_tmp_path = "/" + "tmp" + "/agentos-private/run.json"
        private_macos_tmp_path = "/" + "private" + "/" + "var" + "/folders/aa/private-cache/run.json"
        drive_link = "https://drive.google.com/" + "file/d/private-id/view"
        calendar_id = "othercalendar" + "@group.calendar.google.com"
        source_map.write_text(
            "# Source Map\n\n"
            "- Local directory: `" + str(missing) + "`\n"
            "- Private local directory: `" + private_home_path + "`\n"
            "- Private local directory with spaces: `" + private_spaced_home_path + "`\n"
            "- Private local directory with punctuation: `" + private_punctuated_home_path + "`\n"
            "- Private Linux local directory: `" + private_linux_home_path + "`\n"
            "- Private temp directory: `" + private_tmp_path + "`\n"
            "- Private macOS temp directory: `" + private_macos_tmp_path + "`\n",
            encoding="utf-8",
        )
        listed_script = root / "os/verification/listed/scripts/benchmark_listed.py"
        listed_script.parent.mkdir(parents=True)
        listed_script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        listed_reports = root / "os/verification/listed/reports"
        listed_reports.mkdir()
        unlisted_script = root / "os/verification/unlisted/scripts/benchmark_unlisted.py"
        unlisted_script.parent.mkdir(parents=True)
        unlisted_script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        benchmark_manifest = root / "os/verification/BENCHMARKS.json"
        benchmark_manifest.write_text(
            json.dumps(
                {
                    "version": 1,
                    "benchmarks": [
                        {
                            "id": "listed",
                            "script": "os/verification/listed/scripts/benchmark_listed.py",
                            "reports_dir": "os/verification/listed/reports",
                            "run_glob": "*/run.json",
                            "summary_path": ["summary"],
                            "weekly_review": {
                                "check_freshness": False,
                            },
                        }
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        bad_skill = root / "os/skills/bad-frontmatter/SKILL.md"
        bad_skill.parent.mkdir(parents=True)
        bad_skill.write_text(
            "---\n"
            "name: bad-frontmatter\n"
            "description: Bad example: contains an unquoted colon-space\n"
            "---\n"
            "\n"
            "# Bad Frontmatter\n",
            encoding="utf-8",
        )
        (root / ".git").mkdir()
        (root / ".gitignore").write_text(
            "/" + "Users" + "/private-client/cache\n!personal/**/*.md\n",
            encoding="utf-8",
        )
        private_csv = root / "docs/private.csv"
        private_csv.parent.mkdir()
        private_csv.write_text("/" + "Users" + "/private-csv/cache\n", encoding="utf-8")
        local_path_variants = root / "docs/local-path-variants.md"
        backslash = chr(92)
        local_path_variants.write_text(
            "\n".join(
                [
                    "/" + "home" + "/private-linux-user/project/file.md",
                    "/" + "tmp" + "/private-temp-artifact/run.json",
                    "/" + "private" + "/" + "tmp" + "/private-macos-temp-artifact/run.json",
                    "/" + "var" + "/" + "tmp" + "/private-var-temp-artifact/run.json",
                    "/" + "private" + "/" + "var" + "/folders/aa/private-cache/run.json",
                    "C:" + backslash + "Users" + backslash + "PrivateWindowsUser" + backslash + "AgentOS" + backslash + "secret.txt",
                    "C:" + "/" + "Users/PrivateWindowsUser/AppData/Local/Temp/secret.txt",
                    backslash * 2 + "private-host" + backslash + "private-share" + backslash + "client" + backslash + "secret.txt",
                    "$" + "HOME/private-project/file.md",
                    "${" + "TMPDIR}/private-project/run.json",
                    "%" + "USERPROFILE%" + backslash + "Documents" + backslash + "private-project" + backslash + "file.md",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        marker_file = root / "personal/os/verification/privacy-markers.txt"
        marker_file.parent.mkdir(parents=True)
        marker_file.write_text("sensitive-client-name\n", encoding="utf-8")
        marker_variant = root / "docs/marker-variant.md"
        marker_variant.write_text("sensitive_client_name\n", encoding="utf-8")
        marker_path_variant = root / "docs/sensitive_client_name.md"
        marker_path_variant.write_text("sanitized content\n", encoding="utf-8")
        marker_root_path_variant = root / "sensitive_client_name.txt"
        marker_root_path_variant.write_text("not allowlisted but path should be redacted\n", encoding="utf-8")
        (root / "unexpected.txt").write_text("not allowlisted\n", encoding="utf-8")
        public_workflow = root / ".github/workflows/agentos-validation.yml"
        public_workflow.parent.mkdir(parents=True)
        public_workflow.write_text("name: fixture\n", encoding="utf-8")
        disallowed_github_metadata = root / ".github/dependabot.yml"
        disallowed_github_metadata.write_text("version: 2\n", encoding="utf-8")
        (root / "os/linked.raw").symlink_to("../unexpected.txt")
        nonempty_core_gitkeep = root / "os/memory/weekly-review/.gitkeep"
        nonempty_core_gitkeep.parent.mkdir(parents=True)
        nonempty_core_gitkeep.write_text("not empty\n", encoding="utf-8")
        disallowed_skeleton = root / "personal/os/agents/private-client/.gitkeep"
        disallowed_skeleton.parent.mkdir(parents=True)
        disallowed_skeleton.write_text("", encoding="utf-8")
        nonempty_skeleton = root / "personal/os/context/.gitkeep"
        nonempty_skeleton.parent.mkdir(parents=True, exist_ok=True)
        nonempty_skeleton.write_text("not empty\n", encoding="utf-8")
        (root / "personal/bad.md").symlink_to("private-project/secret.md")

        validator = AgentOSValidator(root)
        validator.check_markdown_path_portability()
        validator.check_source_map_path_health()
        validator.check_skill_frontmatter_parseability()
        validator.check_benchmark_manifest()
        validator.check_no_git_directory()
        validator.check_public_export_allowlist()
        validator.check_personal_overlay_ignore_file_rules()
        validator.check_personal_overlay_tracking(allow_private_files=False)
        validator.check_core_private_markers()
        validator.add_error(
            "redaction fixture",
            "docs/redaction.md",
            "drive link " + drive_link + " and calendar " + calendar_id,
        )
        expected_messages = [
            "hardcodes the AgentOS checkout path",
            "uses a parent-relative AgentOS path",
            "listed local path does not exist",
            "plain frontmatter field 'description' contains ': '; quote the value",
            "benchmark script missing from manifest",
            "public export must not contain git history",
            "private marker matched",
            "missing required Personal Overlay ignore rule",
            "unexpected Personal Overlay unignore rule",
            "root file is not allowlisted for public export",
            "GitHub metadata outside the public-safe CI workflow allowlist",
            "public export contains a symbolic link",
            "publishable .gitkeep must be empty",
            "personal overlay .gitkeep path is not in the public-safe skeleton allowlist",
            "personal overlay skeleton .gitkeep must be empty",
        ]
        ignored_root = root / "_ignored_artifacts_fixture"
        ignored_root.mkdir()
        (ignored_root / "os").mkdir()
        (ignored_root / ".gitignore").write_text(
            ".DS_Store\noutput/\nlocal-artifacts/\n",
            encoding="utf-8",
        )
        ignored_output = ignored_root / "output/private.txt"
        ignored_output.parent.mkdir()
        ignored_output.write_text(
            "/" + "Users" + "/private\n" + "sk-" + "fakeignoredfixture1234567890\n",
            encoding="utf-8",
        )
        ignored_local_artifact = ignored_root / "local-artifacts/private.txt"
        ignored_local_artifact.parent.mkdir()
        ignored_local_artifact.write_text(
            "/" + "Users" + "/private\n" + "sk-" + "fakeignoredfixture1234567890\n",
            encoding="utf-8",
        )
        ignored_agent_dir = ignored_root / "os/agents/ignored-agent"
        ignored_agent_dir.mkdir(parents=True)
        (ignored_agent_dir / ".DS_Store").write_text("ignored local artifact\n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(ignored_root), "init"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        ignored_validator = AgentOSValidator(ignored_root)
        ignored_validator.check_core_private_markers()
        ignored_validator.check_secret_like_tokens()
        ignored_validator.check_agent_contract_completeness()
        ignored_artifacts_clean = not any(
            "output/private.txt" in error.path or "local-artifacts/private.txt" in error.path
            for error in ignored_validator.errors
        )
        ignored_agent_clean = not any(
            "os/agents/ignored-agent" in error.path for error in ignored_validator.errors
        )

        broad_gitkeep_root = root / "_broad_gitkeep_ignore_fixture"
        broad_gitkeep_root.mkdir()
        (broad_gitkeep_root / ".gitignore").write_text(
            "personal/**/*\n!personal/**/\n!personal/**/.gitkeep\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "-C", str(broad_gitkeep_root), "init"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        broad_gitkeep_validator = AgentOSValidator(broad_gitkeep_root)
        broad_gitkeep_validator.check_personal_overlay_ignore_rules()
        broad_gitkeep_unignore_rejected = any(
            error.path == "personal/os/agents/private-client/.gitkeep"
            and "private-specific .gitkeep paths must remain ignored" in error.message
            for error in broad_gitkeep_validator.errors
        )

        symlink_diagnostic_safe = any(
            error.path == "personal/bad.md" and "public export may contain only .gitkeep" in error.message
            for error in validator.errors
        ) and not any(
            "personal/private-project/secret.md" in error.path
            for error in validator.errors
        )
        csv_private_marker_rejected = any(
            error.path == "docs/private.csv:1" and "private marker matched" in error.message
            for error in validator.errors
        )
        local_path_variants_rejected = sum(
            1
            for error in validator.errors
            if error.path.startswith("docs/local-path-variants.md:")
            and "private marker matched" in error.message
        ) == 11
        configured_marker_variant_rejected = any(
            error.path == "docs/marker-variant.md:1"
            and "configured private marker #1" in error.message
            for error in validator.errors
        )
        configured_marker_path_variant_rejected = any(
            error.path == "docs/[private-marker].md"
            and "configured private marker #1" in error.message
            for error in validator.errors
        )
        configured_marker_non_marker_path_redacted = any(
            error.path == "[private-marker].txt"
            and "root file is not allowlisted" in error.message
            for error in validator.errors
        )
        configured_marker_redacted = not any(
            sensitive in error.format()
            for sensitive in [
                "sensitive-client-name",
                "sensitive_client_name",
                "sensitive client name",
            ]
            for error in validator.errors
        )
        built_in_marker_redacted = not any(
            sensitive in error.format()
            for sensitive in [
                "example-user",
                "PrivateProject",
                "Project/file.md",
                "tail-segment.md",
                "private-linux-user",
                "private-temp-artifact",
                "private-macos-temp-artifact",
                "private-var-temp-artifact",
                "PrivateWindowsUser",
                "private-host",
                "private-share",
                "private-project",
                "private-id",
                "othercalendar",
            ]
            for error in validator.errors
        )
        missing_skeleton_rejected = any(
            error.path == "personal/os/skills/.gitkeep"
            and "required Personal Overlay skeleton .gitkeep is missing" in error.message
            for error in validator.errors
        )

        symlink_root = root / "_publication_symlink_fixture"
        (symlink_root / "os/context").mkdir(parents=True)
        (symlink_root / "os/agents/current-awareness-agent").mkdir(parents=True)
        (symlink_root / "os/reports").mkdir()
        (symlink_root / "personal").mkdir()
        (symlink_root / ".gitignore").write_text("personal/**\n", encoding="utf-8")
        (symlink_root / "os/INDEX.md").write_text("safe\n", encoding="utf-8")
        (symlink_root / "os/context/CAREER.md").write_text("private-looking filename with sanitized content\n", encoding="utf-8")
        (symlink_root / "os/agents/current-awareness-agent/JOB.md").write_text(
            "live agent fixture with sanitized content\n",
            encoding="utf-8",
        )
        nested_live_core = symlink_root / "os/context/private-client/NOTES.md"
        nested_live_core.parent.mkdir()
        nested_live_core.write_text("nested high-risk Core file with sanitized content\n", encoding="utf-8")
        core_gitkeep = symlink_root / "os/memory/weekly-review/.gitkeep"
        core_gitkeep.parent.mkdir(parents=True)
        core_gitkeep.write_text("not empty\n", encoding="utf-8")
        (symlink_root / "os/reports/private.md").write_text("generated output with sanitized content\n", encoding="utf-8")
        core_report_gitkeep = symlink_root / "os/verification/retrieval/reports/.gitkeep"
        core_report_gitkeep.parent.mkdir(parents=True)
        core_report_gitkeep.write_text("", encoding="utf-8")
        (symlink_root / "personal/binary.md").write_bytes(b"\xff\xfeprivate")
        (symlink_root / "os/linked.md").symlink_to("../personal/binary.md")
        subprocess.run(
            ["git", "-C", str(symlink_root), "init"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        subprocess.run(
            ["git", "-C", str(symlink_root), "add", ".gitignore", "os/INDEX.md", "os/linked.md"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        symlink_validator = AgentOSValidator(symlink_root)
        symlink_validator.run_publication_precheck_checks()
        symlink_rejected_cleanly = any(
            error.path == "os/linked.md" and "tracked file is a symbolic link" in error.message
            for error in symlink_validator.errors
        ) and not any(
            error.check in {"private marker scan", "secret-like token scan"}
            for error in symlink_validator.errors
        )
        live_core_file_rejected = any(
            error.path == "os/context/CAREER.md" and "live personal context file" in error.message
            for error in symlink_validator.errors
        )
        live_agent_path_rejected = any(
            error.path == "os/agents/current-awareness-agent/JOB.md"
            and "live personal agents file" in error.message
            for error in symlink_validator.errors
        )
        generated_output_rejected = any(
            error.path == "os/reports/private.md" and "generated output" in error.message
            for error in symlink_validator.errors
        )
        nested_live_core_rejected = any(
            error.path == "os/context/private-client/NOTES.md"
            and "nested high-risk Core path" in error.message
            for error in symlink_validator.errors
        )
        core_gitkeep_rejected = any(
            error.path == "os/memory/weekly-review/.gitkeep"
            and "publishable .gitkeep must be empty" in error.message
            for error in symlink_validator.errors
        )
        core_report_gitkeep_rejected = any(
            error.path == "os/verification/retrieval/reports/.gitkeep"
            and "generated output" in error.message
            for error in symlink_validator.errors
        )
        default_validator = AgentOSValidator(symlink_root)
        default_validator.run_structural_checks()
        default_validator.run_publication_precheck_checks()
        default_catches_publication_precheck = any(
            error.path == "os/agents/current-awareness-agent/JOB.md"
            and "live personal agents file" in error.message
            for error in default_validator.errors
        ) and any(
            error.path == "os/reports/private.md" and "generated output" in error.message
            for error in default_validator.errors
        )

        matched = (
            all(
                any(message in error.message for error in validator.errors)
                for message in expected_messages
            )
            and ignored_artifacts_clean
            and ignored_agent_clean
            and broad_gitkeep_unignore_rejected
            and symlink_diagnostic_safe
            and csv_private_marker_rejected
            and local_path_variants_rejected
            and configured_marker_variant_rejected
            and configured_marker_path_variant_rejected
            and configured_marker_non_marker_path_redacted
            and configured_marker_redacted
            and built_in_marker_redacted
            and missing_skeleton_rejected
            and symlink_rejected_cleanly
            and live_core_file_rejected
            and live_agent_path_rejected
            and generated_output_rejected
            and nested_live_core_rejected
            and core_gitkeep_rejected
            and core_report_gitkeep_rejected
            and default_catches_publication_precheck
        )
        if matched:
            print("SELF-TEST PASS: structural and publication/privacy fixtures were caught.")
            for error in validator.errors:
                print(f"EXPECTED {error.format()}")
            for error in symlink_validator.errors:
                print(f"EXPECTED {error.format()}")
            for error in broad_gitkeep_validator.errors:
                print(f"EXPECTED {error.format()}")
            return 0

        print("SELF-TEST FAIL: expected structural and publication/privacy fixtures were not caught.")
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic AgentOS maintenance validators.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="AgentOS repository root. Defaults to the repository containing os/.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run a safe temporary fixture that demonstrates a failing invariant.",
    )
    parser.add_argument(
        "--publication-precheck",
        action="store_true",
        help="Run publication precheck against the mixed local working tree.",
    )
    parser.add_argument(
        "--structural-only",
        action="store_true",
        help="Run only structural AgentOS checks, without publication/privacy precheck checks.",
    )
    parser.add_argument(
        "--public-export",
        type=Path,
        help="Run public-export validation against the given generated export directory.",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    if not (args.root / "os").exists():
        print(f"AgentOS validation failed: root does not contain os/: {args.root}", file=sys.stderr)
        return 2

    validator = AgentOSValidator(args.root)
    if args.public_export:
        export_root = args.public_export.resolve()
        if not (export_root / "os").exists():
            print(f"AgentOS validation failed: export root does not contain os/: {export_root}", file=sys.stderr)
            return 2
        return validator.run_public_export_validation(export_root)
    if args.publication_precheck:
        return validator.run_publication_precheck()
    if args.structural_only:
        return validator.run_structural_only()

    return validator.run()


if __name__ == "__main__":
    raise SystemExit(main())
