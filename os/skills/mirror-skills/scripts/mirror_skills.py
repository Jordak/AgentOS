#!/usr/bin/env python3
"""Audit and optionally sync current-machine mirrors for AgentOS skills."""

from __future__ import annotations

import argparse
import json
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
    source_error: str | None = None


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
        manifest_path = path / "os/skills/MANIFEST.md"
        try:
            manifest_path.lstat()
        except FileNotFoundError:
            continue
        except OSError:
            continue
        if source_path_problem(path, manifest_path, "file") is None:
            return path
    raise SystemExit("Could not find AgentOS root containing os/skills/MANIFEST.md")


def extract_field(section: str, field_name: str) -> str | None:
    pattern = re.compile(FIELD_RE_TEMPLATE.format(field=re.escape(field_name)), re.MULTILINE)
    match = pattern.search(section)
    if not match:
        return None
    value = match.group(1).strip().rstrip(".")
    code_span = re.search(r"`([^`]+)`", value)
    return code_span.group(1) if code_span else value


def source_path_problem(boundary_root: Path, source_path: Path, expected_kind: str) -> str | None:
    try:
        rel = source_path.relative_to(boundary_root)
    except ValueError:
        return f"source path is outside boundary root: {source_path}"

    try:
        root_stat = boundary_root.lstat()
    except FileNotFoundError:
        return None
    except OSError as error:
        return f".: {error.__class__.__name__}: {error}"
    if stat.S_ISLNK(root_stat.st_mode):
        return f".: symbolic link is not allowed: {boundary_root}"
    if not stat.S_ISDIR(root_stat.st_mode):
        return f".: not a directory: {boundary_root}"

    current = boundary_root
    parts = rel.parts
    for index, part in enumerate(parts):
        current = current / part
        is_final = index == len(parts) - 1
        try:
            current_stat = current.lstat()
        except FileNotFoundError:
            return None
        except OSError as error:
            return f"{current.relative_to(boundary_root).as_posix()}: {error.__class__.__name__}: {error}"
        if stat.S_ISLNK(current_stat.st_mode):
            return f"{current.relative_to(boundary_root).as_posix()}: symbolic link is not allowed"
        if is_final:
            if expected_kind == "file" and not stat.S_ISREG(current_stat.st_mode):
                return f"{rel.as_posix()}: not a regular file"
            if expected_kind == "directory" and not stat.S_ISDIR(current_stat.st_mode):
                return f"{rel.as_posix()}: not a directory"
        elif not stat.S_ISDIR(current_stat.st_mode):
            return f"{current.relative_to(boundary_root).as_posix()}: not a directory"
    return None


def personal_overlay_boundary_root(personal_overlay_root: Path) -> Path:
    if personal_overlay_root.name == "os" and personal_overlay_root.parent.name == "personal":
        return personal_overlay_root.parent.parent
    return personal_overlay_root.parent


def core_source_problem(agentos_root: Path, skill_name: str, canonical_source: str, source_path: Path) -> str | None:
    source = Path(canonical_source)
    if source.is_absolute():
        return "Canonical source must be root-relative, not absolute."
    if ".." in source.parts:
        return "Canonical source must not contain parent-directory traversal."
    if len(source.parts) < 3 or source.parts[0] != "os" or source.parts[1] != "skills":
        return "Canonical source must be under os/skills/."
    if source.parts[2] != skill_name:
        return f"Canonical source must stay under os/skills/{skill_name}/."
    return source_path_problem(agentos_root, source_path, "file")


def parse_manifest(agentos_root: Path) -> list[SkillEntry]:
    manifest_path = agentos_root / "os/skills/MANIFEST.md"
    manifest_problem = source_path_problem(agentos_root, manifest_path, "file")
    if manifest_problem:
        raise SystemExit(f"Skills manifest could not be inspected: {manifest_problem}")
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
        source_error = core_source_problem(agentos_root, name, canonical_source, source_path)
        entries.append(
            SkillEntry(
                name=name,
                source_kind="core",
                canonical_source=canonical_source,
                source_path=source_path,
                source_root=source_root,
                mirror_dir=Path(),
                source_error=source_error,
            )
        )

    return entries


def discover_personal_overlay_entries(agentos_root: Path, personal_overlay_root: Path | None = None) -> list[SkillEntry]:
    personal_skills_root = (personal_overlay_root or (agentos_root / "personal/os")) / "skills"
    boundary_root = personal_overlay_boundary_root(personal_skills_root.parent)
    try:
        personal_skills_root.lstat()
    except FileNotFoundError:
        return []
    except OSError:
        return []
    if source_path_problem(boundary_root, personal_skills_root, "directory"):
        return []

    entries: list[SkillEntry] = []
    for skill_dir in sorted(personal_skills_root.iterdir()):
        try:
            skill_dir_stat = skill_dir.lstat()
        except OSError:
            continue
        if stat.S_ISLNK(skill_dir_stat.st_mode) or not stat.S_ISDIR(skill_dir_stat.st_mode):
            continue
        skill_file = skill_dir / "SKILL.md"
        try:
            skill_file.lstat()
        except FileNotFoundError:
            continue
        except OSError as error:
            source_error = f"{skill_file.relative_to(boundary_root).as_posix()}: {error.__class__.__name__}: {error}"
        else:
            source_error = source_path_problem(boundary_root, skill_file, "file")
        name = skill_dir.name
        try:
            canonical_source = skill_file.relative_to(agentos_root).as_posix()
        except ValueError:
            canonical_source = str(skill_file)
        entries.append(
            SkillEntry(
                name=name,
                source_kind="personal-overlay",
                canonical_source=canonical_source,
                source_path=skill_file,
                source_root=skill_dir,
                mirror_dir=Path(),
                source_error=source_error,
            )
        )

    return entries


def personal_overlay_root_problem(personal_overlay_root: Path) -> str | None:
    return source_path_problem(
        personal_overlay_boundary_root(personal_overlay_root),
        personal_overlay_root,
        "directory",
    )


def personal_overlay_skills_root_problem(personal_skills_root: Path) -> str | None:
    boundary_root = personal_overlay_boundary_root(personal_skills_root.parent)
    root_problem = source_path_problem(boundary_root, personal_skills_root, "directory")
    if root_problem:
        return root_problem
    try:
        children = list(personal_skills_root.iterdir())
    except FileNotFoundError:
        return None
    except OSError as error:
        return f"{error.__class__.__name__}: {error}"
    for child in children:
        try:
            child_stat = child.lstat()
        except OSError as error:
            return f"{error.__class__.__name__}: {error}"
        if stat.S_ISLNK(child_stat.st_mode):
            return f"{child.relative_to(boundary_root).as_posix()}: symbolic link is not allowed"
        if not stat.S_ISDIR(child_stat.st_mode):
            continue
        skill_problem = source_path_problem(boundary_root, child / "SKILL.md", "file")
        if skill_problem:
            return skill_problem
    return None


def personal_overlay_discovery_error_result(
    agentos_root: Path,
    mirror_root: Path,
    personal_skills_root: Path,
    problem: str,
) -> MirrorResult:
    try:
        canonical_source = personal_skills_root.relative_to(agentos_root).as_posix()
    except ValueError:
        canonical_source = str(personal_skills_root)
    return MirrorResult(
        name="personal-overlay-skills",
        source_kind="personal-overlay",
        status="source-unreadable",
        canonical_source=canonical_source,
        mirror_path=str(mirror_root / "personal-overlay-skills"),
        missing_files=[],
        changed_files=[],
        extra_files=[],
        notes=[f"Personal Overlay skills root could not be inspected: {problem}"],
    )


def should_ignore(path: Path) -> bool:
    return any(part in IGNORED_NAMES or part.endswith(".pyc") for part in path.parts)


def file_map(root: Path) -> tuple[dict[str, Path], list[str]]:
    files: dict[str, Path] = {}
    problems: list[str] = []
    try:
        root_stat = root.lstat()
    except FileNotFoundError:
        return files, problems
    except OSError as error:
        return files, [f". ({error.__class__.__name__}: {error})"]
    if stat.S_ISLNK(root_stat.st_mode):
        return files, [f". (symbolic link is not allowed: {root})"]
    if not stat.S_ISDIR(root_stat.st_mode):
        return files, [f". (not a directory: {root})"]

    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            children = sorted(directory.iterdir())
        except OSError as error:
            rel = directory.relative_to(root).as_posix() if directory != root else "."
            problems.append(f"{rel} ({error.__class__.__name__}: {error})")
            continue
        for path in children:
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
                pending.append(path)
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
    try:
        mirror_root_stat = mirror_dir.lstat()
    except FileNotFoundError:
        return []
    except OSError as error:
        return [f". ({error.__class__.__name__}: {error})"]
    if not stat.S_ISDIR(mirror_root_stat.st_mode):
        return []

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
    if entry.source_error:
        return MirrorResult(
            name=entry.name,
            source_kind=entry.source_kind,
            status="source-unreadable",
            canonical_source=entry.canonical_source,
            mirror_path=str(entry.mirror_dir),
            missing_files=[],
            changed_files=[],
            extra_files=[],
            notes=[entry.source_error],
        )
    try:
        entry.source_path.lstat()
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
    if entry.source_error:
        return
    try:
        entry.source_path.lstat()
    except OSError:
        return

    canonical_files, source_problems = file_map(entry.source_root)
    if source_problems:
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
        help="AgentOS root containing os/skills/MANIFEST.md. Defaults to discovery from cwd.",
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
        "--personal-overlay-root",
        type=Path,
        default=None,
        help="Personal Overlay root to scan for private skills. Default: <agentos-root>/personal/os.",
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

    agentos_root = args.agentos_root.resolve() if args.agentos_root else find_agentos_root(Path.cwd().resolve())
    mirror_root = args.mirror_root.expanduser().resolve()

    core_entries = parse_manifest(agentos_root)
    personal_entries: list[SkillEntry] = []
    discovery_results: list[MirrorResult] = []
    if not args.core_only:
        personal_overlay_root = (
            args.personal_overlay_root.expanduser()
            if args.personal_overlay_root
            else agentos_root / "personal/os"
        )
        personal_skills_root = personal_overlay_root / "skills"
        problem = personal_overlay_root_problem(personal_overlay_root) or personal_overlay_skills_root_problem(
            personal_skills_root
        )
        if problem:
            discovery_results.append(
                personal_overlay_discovery_error_result(
                    agentos_root,
                    mirror_root,
                    personal_skills_root,
                    problem,
                )
            )
        else:
            personal_entries = discover_personal_overlay_entries(agentos_root, personal_overlay_root)
    entries = select_entries(core_entries, personal_entries, args.skill)
    if not entries and not discovery_results:
        raise SystemExit("No mirrorable Core or Personal Overlay skills found.")

    entries = [
        SkillEntry(
            name=entry.name,
            source_kind=entry.source_kind,
            canonical_source=entry.canonical_source,
            source_path=entry.source_path,
            source_root=entry.source_root,
            mirror_dir=mirror_root / entry.name,
            source_error=entry.source_error,
        )
        for entry in entries
    ]

    if args.sync:
        pre_sync_results = list(discovery_results)
        pre_sync_results.extend(compare_entry(entry) for entry in entries)
        blocking_statuses = {"source-missing", "source-unreadable", "mirror-unreadable"}
        if any(result.status in blocking_statuses for result in pre_sync_results):
            if args.json:
                print(json.dumps([asdict(result) for result in pre_sync_results], indent=2))
            else:
                print_table(pre_sync_results)
            return 1

        for entry in entries:
            sync_entry(entry, prune_extra=args.prune_extra)

    results = list(discovery_results)
    results.extend(compare_entry(entry) for entry in entries)

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
