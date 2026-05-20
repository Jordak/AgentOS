#!/usr/bin/env python3
"""Build a sanitized public AgentOS export from the current working tree."""

from __future__ import annotations

import argparse
import io
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from agentos_publication_rules import (
    PUBLIC_EXPORT_EXCLUDED_DIRS as EXCLUDED_DIRS,
    PUBLIC_EXPORT_ROOT_DIRS as ROOT_DIRS,
    PUBLIC_EXPORT_ROOT_FILES as ROOT_FILES,
    gitkeep_file_reason,
    is_personal_overlay_skeleton_path,
    personal_overlay_skeleton_file_reason,
    publication_path_reason,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export publishable AgentOS Core with Personal Overlay skeleton.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="AgentOS repository root. Defaults to the repository containing this script.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory. Defaults to a new temporary directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete the output directory first if it already exists.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Do not run public-export validation after copying.",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Export the staged Git index instead of working-tree file contents.",
    )
    return parser.parse_args()


def is_git_ignored(root: Path, rel: Path) -> bool:
    if not (root / ".git").exists():
        return False
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "-q", "--", rel.as_posix()],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return result.returncode == 0


def should_copy_file(root: Path, path: Path) -> bool:
    rel = path.relative_to(root)
    if is_git_ignored(root, rel):
        return False
    if any(part in EXCLUDED_DIRS for part in rel.parts):
        return False
    if rel.name == ".gitkeep" and gitkeep_file_reason(path) is not None:
        return False
    if rel.parts[0] == "personal":
        return (
            is_personal_overlay_skeleton_path(rel)
            and personal_overlay_skeleton_file_reason(path) is None
        )
    if len(rel.parts) == 1:
        return rel.as_posix() in ROOT_FILES
    if publication_path_reason(rel):
        return False
    return rel.parts[0] in ROOT_DIRS


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True


def looks_like_export_dir(path: Path) -> bool:
    name = path.name.lower()
    return "agentos" in name and any(
        term in name for term in ["export", "publication", "candidate", "public"]
    )


def output_safety_errors(root: Path, output: Path) -> list[str]:
    errors: list[str] = []
    filesystem_root = Path(output.anchor).resolve()
    home = Path.home().resolve()

    if output == filesystem_root:
        errors.append("output may not be the filesystem root")
    if output == home:
        errors.append("output may not be the current user's home directory")
    if output == root:
        errors.append("output may not be the AgentOS repository root")
    elif is_relative_to(output, root):
        errors.append("output may not be inside the AgentOS repository root")
    if output in root.parents:
        errors.append("output may not be an ancestor of the AgentOS repository root")
    if not looks_like_export_dir(output):
        errors.append("output directory name must look like a dedicated AgentOS export directory")

    return errors


def path_sample(paths: list[str]) -> str:
    sample = ", ".join(paths[:12])
    if len(paths) > 12:
        sample += f", ... ({len(paths)} total)"
    return sample


def git_visible_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"could not enumerate git-visible files: {result.stderr.strip()}")

    files: list[Path] = []
    symlinks: list[str] = []
    missing: list[str] = []
    non_files: list[str] = []
    for raw_path in result.stdout.split("\0"):
        if not raw_path:
            continue
        path = root / raw_path
        rel_text = Path(raw_path).as_posix()
        if path.is_symlink():
            symlinks.append(rel_text)
            continue
        if not path.exists():
            missing.append(rel_text)
            continue
        if not path.is_file():
            non_files.append(rel_text)
            continue
        files.append(path)

    errors: list[str] = []
    if symlinks:
        errors.append(f"Git-visible symlinks are not allowed in public export: {path_sample(symlinks)}")
    if missing:
        errors.append(
            "Git-visible files are missing from the working tree; stage deletions before export: "
            f"{path_sample(missing)}"
        )
    if non_files:
        errors.append(f"Git-visible paths must be regular files: {path_sample(non_files)}")
    if errors:
        raise RuntimeError("; ".join(errors))

    return sorted(files)


def snapshot_visible_files(root: Path) -> list[Path]:
    files: list[Path] = []
    symlinks: list[str] = []
    non_files: list[str] = []
    for path in sorted(root.rglob("*")):
        rel_text = path.relative_to(root).as_posix()
        if path.is_dir() and not path.is_symlink():
            continue
        if path.is_symlink():
            symlinks.append(rel_text)
            continue
        if not path.is_file():
            non_files.append(rel_text)
            continue
        files.append(path)

    errors: list[str] = []
    if symlinks:
        errors.append(f"Git-visible symlinks are not allowed in public export: {path_sample(symlinks)}")
    if non_files:
        errors.append(f"Git-visible paths must be regular files: {path_sample(non_files)}")
    if errors:
        raise RuntimeError("; ".join(errors))

    return files


def materialize_staged_tree(root: Path) -> Path:
    if not (root / ".git").exists():
        raise RuntimeError("--staged requires a Git working tree")

    tree = subprocess.run(
        ["git", "-C", str(root), "write-tree"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if tree.returncode != 0:
        raise RuntimeError(f"could not write staged tree: {tree.stderr.strip()}")

    archive = subprocess.run(
        ["git", "-C", str(root), "archive", "--format=tar", tree.stdout.strip()],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if archive.returncode != 0:
        raise RuntimeError(f"could not archive staged tree: {archive.stderr.decode(errors='replace').strip()}")

    snapshot = Path(tempfile.mkdtemp(prefix="agentos-staged-tree-")).resolve()
    with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as tar:
        tar.extractall(snapshot)
    return snapshot


def publishable_sources(root: Path, *, git_source_set: bool = True) -> list[Path]:
    sources = git_visible_files(root) if git_source_set else snapshot_visible_files(root)
    refused = [
        source.relative_to(root).as_posix()
        for source in sources
        if not should_copy_file(root, source)
    ]
    if refused:
        raise RuntimeError(
            "Git-visible files are outside the publishable export allowlist; "
            f"run the publication precheck for details: {path_sample(refused)}"
        )
    return sources


def run_publication_precheck(root: Path) -> int:
    validator = Path(__file__).resolve().parents[1] / "os/verification/scripts/validate_agentos.py"
    result = subprocess.run(
        [sys.executable, str(validator), "--root", str(root), "--publication-precheck"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(result.stdout, end="")
    return result.returncode


def copy_public_tree(root: Path, output: Path, sources: list[Path]) -> None:
    for source in sources:
        rel = source.relative_to(root)
        target = output / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def run_validation(root: Path, output: Path, validator_root: Path | None = None) -> int:
    validator_source = validator_root or root
    validator = validator_source / "os/verification/scripts/validate_agentos.py"
    result = subprocess.run(
        [sys.executable, str(validator), "--root", str(root), "--public-export", str(output)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(result.stdout, end="")
    return result.returncode


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not (root / "os").is_dir():
        print(f"error: root does not contain os/: {root}", file=sys.stderr)
        return 2

    staged_snapshot: Path | None = None
    try:
        source_root = root
        git_source_set = True
        if args.staged:
            staged_snapshot = materialize_staged_tree(root)
            source_root = staged_snapshot
            git_source_set = False
            precheck_status = run_validation(root, source_root, validator_root=source_root)
        else:
            precheck_status = run_publication_precheck(root)
        if precheck_status != 0:
            return precheck_status

        sources = publishable_sources(source_root, git_source_set=git_source_set)

        if args.output:
            output = args.output.resolve()
            safety_errors = output_safety_errors(root, output)
            if safety_errors:
                print(f"error: unsafe output directory: {output}", file=sys.stderr)
                for error in safety_errors:
                    print(f"  - {error}", file=sys.stderr)
                return 2
            if output.exists():
                if not args.force:
                    print(f"error: output already exists; pass --force to replace it: {output}", file=sys.stderr)
                    return 2
                shutil.rmtree(output)
            output.mkdir(parents=True)
        else:
            output = Path(tempfile.mkdtemp(prefix="agentos-export-")).resolve()

        copy_public_tree(source_root, output, sources)
        print(f"Exported public AgentOS tree to {output}")

        if args.skip_validation:
            return 0
        validator_root = output if args.staged else root
        return run_validation(root, output, validator_root=validator_root)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    finally:
        if staged_snapshot is not None:
            shutil.rmtree(staged_snapshot, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
