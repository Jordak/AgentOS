#!/usr/bin/env python3
"""Expose AgentOS Core skills with global symlink adapters."""

from __future__ import annotations

import argparse
import errno
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

SKILL_HEADING_RE = re.compile(r"^### `([^`]+)`\s*$", re.MULTILINE)
FIELD_RE_TEMPLATE = r"^- {field}:\s*(.*)$"
SYMLINK_PERMISSION_ERRNOS = {errno.EACCES, errno.EPERM, errno.EROFS}
SYMLINK_PERMISSION_WINERRORS = {5, 1314}
APPLY_SUCCESS_STATUSES = {"already-linked", "created-symlink"}
DRY_RUN_FAILURE_STATUSES = {"blocked", "missing-source"}


@dataclass(frozen=True)
class SkillEntry:
    name: str
    canonical_source: str
    source_path: Path
    source_root: Path


@dataclass(frozen=True)
class ExposureResult:
    status: str
    skill: str
    adapter_path: str
    canonical_source: str
    notes: tuple[str, ...] = ()


def lexical_absolute(path: Path) -> Path:
    expanded = path.expanduser()
    if not expanded.is_absolute():
        expanded = Path.cwd() / expanded
    return Path(os.path.abspath(expanded))


def find_agentos_root(start: Path) -> Path:
    for path in [start, *start.parents]:
        manifest = path / "os/skills/MANIFEST.md"
        if path.is_dir() and manifest.is_file():
            return lexical_absolute(path)
    raise SystemExit("Could not find AgentOS root containing os/skills/MANIFEST.md")


def path_problem(path: Path, expected_kind: str | None, allow_missing: bool) -> str | None:
    if ".." in path.expanduser().parts:
        return "parent-directory segments are not allowed"
    try:
        path_stat = lexical_absolute(path).lstat()
    except FileNotFoundError:
        return None if allow_missing else "path is missing"
    except OSError as error:
        return f"{error.__class__.__name__}: {error}"
    if stat.S_ISLNK(path_stat.st_mode):
        return "symbolic link is not allowed"
    if expected_kind == "directory" and not stat.S_ISDIR(path_stat.st_mode):
        return "not a directory"
    if expected_kind == "file" and not stat.S_ISREG(path_stat.st_mode):
        return "not a regular file"
    return None


def managed_relative_path_problem(raw_path: str) -> str | None:
    path = Path(raw_path)
    if path.is_absolute():
        return "must be root-relative, not absolute"
    if raw_path.startswith("~"):
        return "must be root-relative, not home-relative"
    if ".." in path.parts:
        return "must not contain parent-directory segments"
    return None


def extract_field(section: str, field_name: str) -> str | None:
    pattern = re.compile(FIELD_RE_TEMPLATE.format(field=re.escape(field_name)), re.MULTILINE)
    match = pattern.search(section)
    if not match:
        return None
    value = match.group(1).strip().rstrip(".")
    code_span = re.search(r"`([^`]+)`", value)
    return code_span.group(1) if code_span else value


def parse_manifest(agentos_root: Path) -> list[SkillEntry]:
    manifest_path = agentos_root / "os/skills/MANIFEST.md"
    problem = path_problem(manifest_path, expected_kind="file", allow_missing=False)
    if problem:
        raise SystemExit(f"Unsafe skills manifest: {manifest_path} ({problem})")

    manifest = manifest_path.read_text(encoding="utf-8")
    matches = list(SKILL_HEADING_RE.finditer(manifest))
    entries: list[SkillEntry] = []

    for index, match in enumerate(matches):
        name = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(manifest)
        section = manifest[start:end]
        canonical_source = extract_field(section, "Canonical source")
        if not canonical_source:
            continue
        source_problem = managed_relative_path_problem(canonical_source)
        if source_problem:
            raise SystemExit(f"{name}: unsafe Canonical source {canonical_source!r}: {source_problem}")
        source_path = agentos_root / canonical_source
        source_root = source_path.parent if source_path.name == "SKILL.md" else source_path
        entries.append(
            SkillEntry(
                name=name,
                canonical_source=canonical_source,
                source_path=source_path,
                source_root=source_root,
            )
        )

    return entries


def select_entries(entries: list[SkillEntry], requested_names: list[str]) -> list[SkillEntry]:
    if not requested_names:
        return entries
    requested = list(dict.fromkeys(requested_names))
    by_name = {entry.name: entry for entry in entries}
    missing = [name for name in requested if name not in by_name]
    if missing:
        missing_list = ", ".join(missing)
        available_list = ", ".join(sorted(by_name))
        raise SystemExit(
            "Requested skill is not canonical in the Core manifest: "
            f"{missing_list}. Available Core skills: {available_list}"
        )
    return [by_name[name] for name in requested]


def symlink_permission_denied(error: OSError) -> bool:
    winerror = getattr(error, "winerror", None)
    return error.errno in SYMLINK_PERMISSION_ERRNOS or winerror in SYMLINK_PERMISSION_WINERRORS


def symlink_target(path: Path) -> str:
    try:
        return os.readlink(path)
    except OSError as error:
        return f"<unreadable symlink target: {error.__class__.__name__}: {error}>"


def source_result(entry: SkillEntry, adapter_path: Path) -> ExposureResult | None:
    source_problem = path_problem(entry.source_path, expected_kind="file", allow_missing=False)
    if source_problem:
        return ExposureResult(
            status="missing-source",
            skill=entry.name,
            adapter_path=str(adapter_path),
            canonical_source=entry.canonical_source,
            notes=(f"canonical source is unsafe or missing: {entry.source_path} ({source_problem})",),
        )
    root_problem = path_problem(entry.source_root, expected_kind="directory", allow_missing=False)
    if root_problem:
        return ExposureResult(
            status="missing-source",
            skill=entry.name,
            adapter_path=str(adapter_path),
            canonical_source=entry.canonical_source,
            notes=(f"canonical skill root is unsafe or missing: {entry.source_root} ({root_problem})",),
        )
    return None


def inspect_adapter(entry: SkillEntry, adapter_root: Path, apply: bool) -> ExposureResult:
    adapter_path = adapter_root / entry.name
    source_problem_result = source_result(entry, adapter_path)
    if source_problem_result:
        return source_problem_result

    try:
        adapter_stat = adapter_path.lstat()
    except FileNotFoundError:
        if not apply:
            return ExposureResult("would-create-symlink", entry.name, str(adapter_path), entry.canonical_source)
        create_symlink(entry, adapter_path)
        return ExposureResult("created-symlink", entry.name, str(adapter_path), entry.canonical_source)
    except OSError as error:
        return ExposureResult(
            "blocked",
            entry.name,
            str(adapter_path),
            entry.canonical_source,
            (f"could not inspect adapter: {error.__class__.__name__}: {error}",),
        )

    if stat.S_ISLNK(adapter_stat.st_mode):
        try:
            points_to_source = adapter_path.samefile(entry.source_root)
        except OSError as error:
            return ExposureResult(
                "wrong-target",
                entry.name,
                str(adapter_path),
                entry.canonical_source,
                (
                    f"adapter symlink target cannot be resolved: {symlink_target(adapter_path)}",
                    f"expected canonical source: {entry.source_root}",
                    f"{error.__class__.__name__}: {error}",
                ),
            )
        if points_to_source:
            return ExposureResult("already-linked", entry.name, str(adapter_path), entry.canonical_source)
        return ExposureResult(
            "wrong-target",
            entry.name,
            str(adapter_path),
            entry.canonical_source,
            (
                f"adapter symlink points to: {symlink_target(adapter_path)}",
                f"expected canonical source: {entry.source_root}",
            ),
        )

    if stat.S_ISDIR(adapter_stat.st_mode):
        return ExposureResult(
            "existing-copy",
            entry.name,
            str(adapter_path),
            entry.canonical_source,
            ("non-symlink directory exists; v1 reports it and does not replace it",),
        )

    return ExposureResult(
        "blocked",
        entry.name,
        str(adapter_path),
        entry.canonical_source,
        ("adapter path exists and is not a symlink or directory; v1 does not overwrite it",),
    )


def create_symlink(entry: SkillEntry, adapter_path: Path) -> None:
    root_problem = path_problem(adapter_path.parent, expected_kind="directory", allow_missing=True)
    if root_problem:
        raise SystemExit(f"Unsafe adapter root: {adapter_path.parent} ({root_problem})")
    try:
        adapter_path.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(entry.source_root, adapter_path, target_is_directory=True)
    except OSError as error:
        fix = permission_fix_text()
        if symlink_permission_denied(error):
            raise SystemExit(
                "Permission denied creating skill symlink: "
                f"{adapter_path} -> {entry.source_root}. {fix} "
                f"Original error: {error.__class__.__name__}: {error}"
            )
        raise SystemExit(
            "Could not create skill symlink: "
            f"{adapter_path} -> {entry.source_root}. {fix} "
            f"Original error: {error.__class__.__name__}: {error}"
        )


def permission_fix_text() -> str:
    if os.name == "nt":
        return "Enable Windows Developer Mode or run the shell elevated, then rerun. No junction or copy fallback was used."
    return (
        "Grant write/symlink permission to the global skill root, choose a writable HOME, "
        "or adjust sandbox/filesystem policy, then rerun. No copy fallback was used."
    )


def print_table(results: list[ExposureResult]) -> None:
    status_width = max(12, *(len(result.status) for result in results))
    skill_width = max(24, *(len(result.skill) for result in results))
    print(f"{'status':<{status_width}}  {'skill':<{skill_width}}  adapter")
    print(f"{'-' * status_width}  {'-' * skill_width}  -------")
    for result in results:
        print(f"{result.status:<{status_width}}  {result.skill:<{skill_width}}  {result.adapter_path}")
        if result.canonical_source:
            print(f"              source: {result.canonical_source}")
        for note in result.notes:
            print(f"              note: {note}")


def exit_code(results: list[ExposureResult], apply: bool) -> int:
    if apply:
        return 0 if all(result.status in APPLY_SUCCESS_STATUSES for result in results) else 1
    return 1 if any(result.status in DRY_RUN_FAILURE_STATUSES for result in results) else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agentos-root",
        type=Path,
        default=None,
        help="AgentOS root containing os/skills/MANIFEST.md. Defaults to discovery from cwd.",
    )
    parser.add_argument(
        "--skill",
        action="append",
        default=[],
        help="Limit dry run or apply to one Core skill. May be repeated.",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Apply planned exposure changes by creating missing symlink adapters.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    agentos_root = lexical_absolute(args.agentos_root) if args.agentos_root else find_agentos_root(lexical_absolute(Path.cwd()))
    root_problem = path_problem(agentos_root, expected_kind="directory", allow_missing=False)
    if root_problem:
        raise SystemExit(f"Unsafe AgentOS root: {agentos_root} ({root_problem})")

    adapter_root = Path.home() / ".agents/skills"
    entries = parse_manifest(agentos_root)
    selected_entries = select_entries(entries, args.skill)

    apply = bool(args.no_dry_run)
    results = [inspect_adapter(entry, adapter_root, apply=apply) for entry in selected_entries]

    print_table(results)
    return exit_code(results, apply)


if __name__ == "__main__":
    sys.exit(main())
