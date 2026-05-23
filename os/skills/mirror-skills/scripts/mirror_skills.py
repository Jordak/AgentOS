#!/usr/bin/env python3
"""Audit and optionally sync current-machine mirrors for AgentOS skills."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


SKILL_HEADING_RE = re.compile(r"^### `([^`]+)`\s*$", re.MULTILINE)
FIELD_RE_TEMPLATE = r"^- {field}:\s*(.*)$"
IGNORED_NAMES = {".DS_Store", "__pycache__"}


@dataclass
class SkillEntry:
    name: str
    source_kind: str
    canonical_source: str
    source_path: Path
    source_root: Path
    mirror_dir: Path


@dataclass
class MirrorResult:
    name: str
    source_kind: str
    status: str
    canonical_source: str
    mirror_path: str
    missing_files: list[str]
    changed_files: list[str]
    extra_files: list[str]
    notes: list[str]


def find_agentos_root(start: Path) -> Path:
    for path in [start, *start.parents]:
        if (path / "os/skills/MANIFEST.md").exists():
            return path
    raise SystemExit("Could not find AgentOS root containing os/skills/MANIFEST.md")


def lexical_absolute(path: Path) -> Path:
    """Make a path absolute without resolving symbolic links."""
    expanded = path.expanduser()
    if not expanded.is_absolute():
        expanded = Path.cwd() / expanded
    return Path(os.path.abspath(expanded))


def path_component_problems(path: Path, expected_kind: str | None, allow_missing: bool) -> list[str]:
    absolute = lexical_absolute(path)
    if not absolute.is_absolute():
        return [f"{path} (path is not absolute after normalization)"]

    current = Path(absolute.anchor)
    parts = absolute.parts[1:]
    for index, part in enumerate(parts):
        current = current / part
        is_final = index == len(parts) - 1
        try:
            path_stat = current.lstat()
        except FileNotFoundError:
            if allow_missing:
                return []
            return [f"{current} (path component is missing)"]
        except OSError as error:
            return [f"{current} ({error.__class__.__name__}: {error})"]

        if stat.S_ISLNK(path_stat.st_mode):
            return [f"{current} (symbolic link is not allowed)"]
        if not is_final and not stat.S_ISDIR(path_stat.st_mode):
            return [f"{current} (path component is not a directory)"]
        if is_final and expected_kind == "directory" and not stat.S_ISDIR(path_stat.st_mode):
            return [f"{current} (not a directory)"]
        if is_final and expected_kind == "file" and not stat.S_ISREG(path_stat.st_mode):
            return [f"{current} (not a regular file)"]
    return []


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

        source_path = agentos_root / canonical_source
        source_root = source_path.parent if source_path.name == "SKILL.md" else source_path
        entries.append(
            SkillEntry(
                name=name,
                source_kind="core",
                canonical_source=canonical_source,
                source_path=source_path,
                source_root=source_root,
                mirror_dir=Path(),
            )
        )

    return entries


def discover_personal_overlay_entries(agentos_root: Path) -> tuple[list[SkillEntry], list[str]]:
    personal_skills_root = agentos_root / "personal/os/skills"
    problems = path_component_problems(personal_skills_root, expected_kind="directory", allow_missing=True)
    if problems:
        return [], problems
    try:
        personal_stat = personal_skills_root.lstat()
    except FileNotFoundError:
        return [], []
    except OSError as error:
        return [], [f"{personal_skills_root} ({error.__class__.__name__}: {error})"]
    if not stat.S_ISDIR(personal_stat.st_mode):
        return [], [f"{personal_skills_root} (not a directory)"]

    entries: list[SkillEntry] = []
    for skill_file in sorted(personal_skills_root.glob("*/SKILL.md")):
        skill_dir = skill_file.parent
        name = skill_dir.name
        canonical_source = skill_file.relative_to(agentos_root).as_posix()
        entries.append(
            SkillEntry(
                name=name,
                source_kind="personal-overlay",
                canonical_source=canonical_source,
                source_path=skill_file,
                source_root=skill_dir,
                mirror_dir=Path(),
            )
        )

    return entries, []


def should_ignore(path: Path) -> bool:
    return any(part in IGNORED_NAMES or part.endswith(".pyc") for part in path.parts)


def file_map(root: Path) -> tuple[dict[str, Path], list[str]]:
    files: dict[str, Path] = {}
    problems: list[str] = []
    component_problems = path_component_problems(root, expected_kind=None, allow_missing=True)
    if component_problems:
        return files, component_problems
    try:
        root_stat = root.lstat()
    except FileNotFoundError:
        return files, problems
    except OSError as error:
        return files, [f". ({error.__class__.__name__}: {error})"]
    if stat.S_ISLNK(root_stat.st_mode):
        return files, [f". (symbolic link is not allowed: {root})"]
    if stat.S_ISREG(root_stat.st_mode):
        return {"SKILL.md": root}, problems
    if not stat.S_ISDIR(root_stat.st_mode):
        return files, [f". (not a regular file or directory: {root})"]

    for path in root.rglob("*"):
        rel_path = path.relative_to(root)
        if should_ignore(rel_path):
            continue
        rel = rel_path.as_posix()
        try:
            path_stat = path.lstat()
        except OSError as error:
            problems.append(f"{rel} ({error.__class__.__name__}: {error})")
            continue
        if stat.S_ISLNK(path_stat.st_mode):
            problems.append(f"{rel} (symbolic link is not allowed)")
        elif stat.S_ISDIR(path_stat.st_mode):
            continue
        elif stat.S_ISREG(path_stat.st_mode):
            files[rel] = path
        else:
            problems.append(f"{rel} (not a regular file or directory)")
    return files, problems


def file_read_problem(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError as error:
        return str(error)
    size = path.stat().st_size
    if size != len(data):
        return f"stat size is {size} bytes but read returned {len(data)} bytes"
    return None


def unreadable_files(files: dict[str, Path]) -> list[str]:
    problems = []
    for rel, path in sorted(files.items()):
        problem = file_read_problem(path)
        if problem:
            problems.append(f"{rel} ({problem})")
    return problems


def existing_path_kind_problem(path: Path, expected_kind: str) -> str | None:
    try:
        path_stat = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as error:
        return f"{error.__class__.__name__}: {error}"
    if stat.S_ISLNK(path_stat.st_mode):
        return "symbolic link is not allowed"
    if expected_kind == "directory" and not stat.S_ISDIR(path_stat.st_mode):
        return "not a directory"
    if expected_kind == "file" and not stat.S_ISREG(path_stat.st_mode):
        return "not a regular file"
    return None


def mirror_path_kind_problems(mirror_dir: Path, canonical_files: dict[str, Path]) -> list[str]:
    component_problems = path_component_problems(mirror_dir, expected_kind="directory", allow_missing=True)
    if component_problems:
        return component_problems
    try:
        mirror_root_stat = mirror_dir.lstat()
    except FileNotFoundError:
        return []
    except OSError as error:
        return [f". ({error.__class__.__name__}: {error})"]
    if stat.S_ISLNK(mirror_root_stat.st_mode):
        return [f". (symbolic link is not allowed: {mirror_dir})"]
    if not stat.S_ISDIR(mirror_root_stat.st_mode):
        return [f". (not a directory: {mirror_dir})"]

    problems: list[str] = []
    for rel in sorted(canonical_files):
        current = mirror_dir
        parts = Path(rel).parts
        for part in parts[:-1]:
            current = current / part
            problem = existing_path_kind_problem(current, "directory")
            if problem:
                problems.append(f"{rel} ({current.relative_to(mirror_dir).as_posix()}: {problem})")
                break
            if not current.exists():
                break
        else:
            destination = mirror_dir / rel
            problem = existing_path_kind_problem(destination, "file")
            if problem:
                problems.append(f"{rel} ({rel}: {problem})")
    return problems


def compare_entry(entry: SkillEntry) -> MirrorResult:
    notes: list[str] = []
    try:
        source_stat = entry.source_path.lstat()
    except FileNotFoundError:
        return MirrorResult(
            name=entry.name,
            source_kind=entry.source_kind,
            status="source-missing",
            canonical_source=entry.canonical_source,
            mirror_path=str(entry.mirror_dir),
            missing_files=[],
            changed_files=[],
            extra_files=[],
            notes=[f"canonical source does not exist: {entry.source_path}"],
        )
    except OSError as error:
        return MirrorResult(
            name=entry.name,
            source_kind=entry.source_kind,
            status="source-unreadable",
            canonical_source=entry.canonical_source,
            mirror_path=str(entry.mirror_dir),
            missing_files=[],
            changed_files=[],
            extra_files=[],
            notes=[f"{error.__class__.__name__}: {error}"],
        )
    if stat.S_ISLNK(source_stat.st_mode):
        return MirrorResult(
            name=entry.name,
            source_kind=entry.source_kind,
            status="source-unreadable",
            canonical_source=entry.canonical_source,
            mirror_path=str(entry.mirror_dir),
            missing_files=[],
            changed_files=[],
            extra_files=[],
            notes=[f"canonical source is a symbolic link: {entry.source_path}"],
        )

    canonical_files, source_problems = file_map(entry.source_root)
    mirror_files, mirror_problems = file_map(entry.mirror_dir)
    source_unreadable = [*source_problems, *unreadable_files(canonical_files)]
    if source_unreadable:
        return MirrorResult(
            name=entry.name,
            source_kind=entry.source_kind,
            status="source-unreadable",
            canonical_source=entry.canonical_source,
            mirror_path=str(entry.mirror_dir),
            missing_files=sorted(set(canonical_files) - set(mirror_files)),
            changed_files=[],
            extra_files=sorted(set(mirror_files) - set(canonical_files)),
            notes=source_unreadable,
        )
    mirror_unreadable = [
        *mirror_problems,
        *mirror_path_kind_problems(entry.mirror_dir, canonical_files),
        *unreadable_files(mirror_files),
    ]
    if mirror_unreadable:
        return MirrorResult(
            name=entry.name,
            source_kind=entry.source_kind,
            status="mirror-unreadable",
            canonical_source=entry.canonical_source,
            mirror_path=str(entry.mirror_dir),
            missing_files=[],
            changed_files=[],
            extra_files=[],
            notes=mirror_unreadable,
        )

    missing = sorted(set(canonical_files) - set(mirror_files))
    extra = sorted(set(mirror_files) - set(canonical_files))
    changed = sorted(
        rel
        for rel in set(canonical_files) & set(mirror_files)
        if canonical_files[rel].read_bytes() != mirror_files[rel].read_bytes()
    )

    if not entry.mirror_dir.exists():
        status = "missing"
    elif missing or changed:
        status = "stale"
    elif extra:
        status = "extra-files"
        notes.append("mirror contains files not present in canonical source")
    else:
        status = "in-sync"

    return MirrorResult(
        name=entry.name,
        source_kind=entry.source_kind,
        status=status,
        canonical_source=entry.canonical_source,
        mirror_path=str(entry.mirror_dir),
        missing_files=missing,
        changed_files=changed,
        extra_files=extra,
        notes=notes,
    )


def sync_entry(entry: SkillEntry, prune_extra: bool) -> None:
    try:
        source_stat = entry.source_path.lstat()
    except OSError:
        return
    if stat.S_ISLNK(source_stat.st_mode):
        return

    canonical_files, source_problems = file_map(entry.source_root)
    if source_problems:
        return
    _mirror_files, mirror_problems = file_map(entry.mirror_dir)
    if mirror_problems:
        return
    if mirror_path_kind_problems(entry.mirror_dir, canonical_files):
        return
    entry.mirror_dir.mkdir(parents=True, exist_ok=True)

    for rel, source in canonical_files.items():
        if file_read_problem(source):
            continue
        destination = entry.mirror_dir / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists() or source.read_bytes() != destination.read_bytes():
            shutil.copy2(source, destination)

    if prune_extra:
        mirror_files, mirror_problems = file_map(entry.mirror_dir)
        if mirror_problems:
            return
        for rel in sorted(set(mirror_files) - set(canonical_files), reverse=True):
            mirror_files[rel].unlink()
        remove_empty_dirs(entry.mirror_dir)


def remove_empty_dirs(root: Path) -> None:
    for path in sorted((p for p in root.rglob("*") if p.is_dir()), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass


def select_entries(
    core_entries: list[SkillEntry],
    personal_entries: list[SkillEntry],
    requested_names: list[str],
) -> list[SkillEntry]:
    core_names = {entry.name for entry in core_entries}
    personal_names = {entry.name for entry in personal_entries}

    if not requested_names:
        duplicates = sorted(personal_names & core_names)
        if duplicates:
            duplicate_list = ", ".join(duplicates)
            raise SystemExit(
                "Personal Overlay skill name collides with a Core skill: "
                f"{duplicate_list}. Use a unique private skill name, or put private "
                "inputs for a Core skill under personal/os/skills/<skill-name>/CONFIG.md."
            )
        return [*core_entries, *personal_entries]

    requested = list(dict.fromkeys(requested_names))
    available = core_names | personal_names
    missing = [name for name in requested if name not in available]
    if missing:
        missing_list = ", ".join(missing)
        available_list = ", ".join(sorted(available))
        raise SystemExit(
            "Requested skill is not canonical in the selected scope: "
            f"{missing_list}. Available canonical skills: {available_list}"
        )

    duplicates = sorted(set(requested) & core_names & personal_names)
    if duplicates:
        duplicate_list = ", ".join(duplicates)
        raise SystemExit(
            "Requested skill collides between Core and Personal Overlay: "
            f"{duplicate_list}. Use a unique private skill name, or put private "
            "inputs for a Core skill under personal/os/skills/<skill-name>/CONFIG.md."
        )

    requested_set = set(requested)
    return [entry for entry in [*core_entries, *personal_entries] if entry.name in requested_set]


def print_table(results: list[MirrorResult]) -> None:
    status_width = max(12, *(len(result.status) for result in results))
    skill_width = max(24, *(len(result.name) for result in results))
    source_width = max(16, *(len(result.source_kind) for result in results))
    print(f"{'status':<{status_width}}  {'skill':<{skill_width}}  {'source':<{source_width}}  mirror")
    print(f"{'-' * status_width}  {'-' * skill_width}  {'-' * source_width}  ------")
    for result in results:
        print(
            f"{result.status:<{status_width}}  "
            f"{result.name:<{skill_width}}  "
            f"{result.source_kind:<{source_width}}  "
            f"{result.mirror_path}"
        )
        for label, values in [
            ("missing", result.missing_files),
            ("changed", result.changed_files),
            ("extra", result.extra_files),
            ("note", result.notes),
        ]:
            if values:
                preview = ", ".join(values[:5])
                suffix = "" if len(values) <= 5 else f" (+{len(values) - 5} more)"
                print(f"              {label}: {preview}{suffix}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agentos-root",
        type=Path,
        default=None,
        help=(
            "AgentOS root containing os/skills/MANIFEST.md. Defaults to discovery from cwd. "
            "When including Personal Overlay skills from a feature worktree, pass the primary "
            "AgentOS checkout root or use --core-only."
        ),
    )
    parser.add_argument(
        "--mirror-root",
        type=Path,
        default=Path.home() / ".agents/skills",
        help="Current-machine skill mirror root. Default: the user's .agents/skills directory.",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Create missing mirrors and copy changed canonical files.",
    )
    parser.add_argument(
        "--core-only",
        action="store_true",
        help="Mirror only Core skills from os/skills/MANIFEST.md, not Personal Overlay skills.",
    )
    parser.add_argument(
        "--skill",
        action="append",
        default=[],
        help="Limit audit or sync to one canonical skill. May be repeated.",
    )
    parser.add_argument(
        "--prune-extra",
        action="store_true",
        help="Delete mirror files that are not present in canonical sources.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON results.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    agentos_root = lexical_absolute(args.agentos_root) if args.agentos_root else find_agentos_root(lexical_absolute(Path.cwd()))
    mirror_root = lexical_absolute(args.mirror_root)
    root_problems = path_component_problems(agentos_root, expected_kind="directory", allow_missing=False)
    if root_problems:
        raise SystemExit("Unsafe AgentOS root: " + "; ".join(root_problems))

    core_entries = parse_manifest(agentos_root)
    personal_entries: list[SkillEntry] = []
    preflight_results: list[MirrorResult] = []
    if not args.core_only:
        personal_entries, personal_problems = discover_personal_overlay_entries(agentos_root)
        if personal_problems:
            preflight_results.append(
                MirrorResult(
                    name="personal-overlay",
                    source_kind="personal-overlay",
                    status="source-unreadable",
                    canonical_source="personal/os/skills",
                    mirror_path=str(mirror_root),
                    missing_files=[],
                    changed_files=[],
                    extra_files=[],
                    notes=personal_problems,
                )
            )
    entries = select_entries(core_entries, personal_entries, args.skill)
    if not entries and not preflight_results:
        raise SystemExit("No mirrorable Core or Personal Overlay skills found.")

    entries = [
        SkillEntry(
            name=entry.name,
            source_kind=entry.source_kind,
            canonical_source=entry.canonical_source,
            source_path=entry.source_path,
            source_root=entry.source_root,
            mirror_dir=mirror_root / entry.name,
        )
        for entry in entries
    ]

    if args.sync and not preflight_results:
        for entry in entries:
            sync_entry(entry, prune_extra=args.prune_extra)

    results = [*preflight_results, *[compare_entry(entry) for entry in entries]]

    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        print_table(results)

    bad_statuses = {
        "source-missing",
        "source-unreadable",
        "mirror-unreadable",
        "missing",
        "stale",
        "extra-files",
    }
    return 1 if any(result.status in bad_statuses for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
