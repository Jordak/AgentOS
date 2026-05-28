#!/usr/bin/env python3
"""Build a sanitized public AgentOS export from the current working tree."""

from __future__ import annotations

import argparse
import importlib.util
import io
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

PATH_RESOLUTION_PACKAGE = "path_resolution"
SUPPORTED_EXPECTED_KINDS = {None, "file", "directory"}


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


def _bootstrap_lexical_absolute(path: Path) -> Path:
    """Make a path absolute without resolving symbolic links."""
    expanded = path.expanduser()
    if not expanded.is_absolute():
        expanded = Path.cwd() / expanded
    return Path(os.path.abspath(expanded))


def _bootstrap_final_path_problem(path: Path, expected_kind: str | None = None, allow_missing: bool = True) -> str | None:
    expected_kind_problem = _bootstrap_expected_kind_problem(expected_kind)
    if expected_kind_problem:
        return expected_kind_problem
    absolute = _bootstrap_lexical_absolute(path)
    try:
        path_stat = absolute.lstat()
    except FileNotFoundError:
        if allow_missing:
            return None
        return "path is missing"
    except OSError as error:
        return f"{error.__class__.__name__}: {error}"

    if stat.S_ISLNK(path_stat.st_mode):
        return "symbolic link is not allowed"
    if expected_kind == "directory" and not stat.S_ISDIR(path_stat.st_mode):
        return "not a directory"
    if expected_kind == "file" and not stat.S_ISREG(path_stat.st_mode):
        return "not a regular file"
    return None


def _bootstrap_no_follow_path_problem(
    path: Path,
    expected_kind: str | None,
    allow_missing: bool,
    boundary: Path,
) -> str | None:
    expected_kind_problem = _bootstrap_expected_kind_problem(expected_kind)
    if expected_kind_problem:
        return f"{path} ({expected_kind_problem})"
    boundary_absolute = _bootstrap_lexical_absolute(boundary)
    boundary_problem = _bootstrap_final_path_problem(boundary_absolute, expected_kind="directory", allow_missing=False)
    if boundary_problem:
        return f"{boundary_absolute} ({boundary_problem})"

    if ".." in path.expanduser().parts:
        return f"{path} (parent-directory segments are not allowed)"

    absolute = _bootstrap_lexical_absolute(path)
    try:
        relative = absolute.relative_to(boundary_absolute)
    except ValueError:
        return f"{absolute} (path is outside the managed root: {boundary_absolute})"

    current = boundary_absolute
    if not relative.parts:
        final_problem = _bootstrap_final_path_problem(current, expected_kind=expected_kind, allow_missing=allow_missing)
        return f"{current} ({final_problem})" if final_problem else None

    for index, part in enumerate(relative.parts):
        current = current / part
        is_final = index == len(relative.parts) - 1
        try:
            path_stat = current.lstat()
        except FileNotFoundError:
            if allow_missing:
                return None
            return f"{current} (path component is missing)"
        except OSError as error:
            return f"{current} ({error.__class__.__name__}: {error})"

        if stat.S_ISLNK(path_stat.st_mode):
            return f"{current} (symbolic link is not allowed)"
        if not is_final and not stat.S_ISDIR(path_stat.st_mode):
            return f"{current} (path component is not a directory)"
        if is_final and expected_kind == "directory" and not stat.S_ISDIR(path_stat.st_mode):
            return f"{current} (not a directory)"
        if is_final and expected_kind == "file" and not stat.S_ISREG(path_stat.st_mode):
            return f"{current} (not a regular file)"
    return None


def _bootstrap_expected_kind_problem(expected_kind: object) -> str | None:
    try:
        supported = expected_kind in SUPPORTED_EXPECTED_KINDS
    except TypeError:
        supported = False
    if not supported:
        return "expected_kind must be None, 'file', or 'directory'"
    return None


def current_script_root() -> Path:
    return _bootstrap_lexical_absolute(Path(__file__).parent.parent)


def _bootstrap_path_resolution_package_problem(root: Path) -> str | None:
    package_dir = root / "scripts" / PATH_RESOLUTION_PACKAGE
    package_problem = _bootstrap_no_follow_path_problem(
        package_dir,
        expected_kind="directory",
        allow_missing=False,
        boundary=root,
    )
    if package_problem:
        return package_problem

    try:
        module_paths = sorted(package_dir.glob("*.py"))
    except OSError as error:
        return f"{package_dir} ({error.__class__.__name__}: {error})"
    if not module_paths:
        return f"{package_dir} (package contains no Python modules)"

    for module_path in module_paths:
        module_problem = _bootstrap_no_follow_path_problem(
            module_path,
            expected_kind="file",
            allow_missing=False,
            boundary=root,
        )
        if module_problem:
            return module_problem
    return None


# Bootstrap stays local so this script can inspect the path-resolution package before executing it.
def load_managed_paths():
    root = current_script_root()
    package_problem = _bootstrap_path_resolution_package_problem(root)
    if package_problem:
        raise RuntimeError(f"unsafe path-resolution package: {package_problem}")

    package_dir = root / "scripts" / PATH_RESOLUTION_PACKAGE
    package_init = package_dir / "__init__.py"
    managed_path = package_dir / "managed.py"
    checked_package_name = "_agentos_checked_path_resolution"
    for module_name in [
        f"{checked_package_name}.managed",
        f"{checked_package_name}._primitives",
        checked_package_name,
    ]:
        sys.modules.pop(module_name, None)

    package_spec = importlib.util.spec_from_file_location(
        checked_package_name,
        package_init,
        submodule_search_locations=[str(package_dir)],
    )
    if package_spec is None or package_spec.loader is None:
        raise RuntimeError(f"could not load path-resolution package: {package_init}")
    package_module = importlib.util.module_from_spec(package_spec)
    sys.modules[checked_package_name] = package_module
    package_spec.loader.exec_module(package_module)

    managed_spec = importlib.util.spec_from_file_location(
        f"{checked_package_name}.managed",
        managed_path,
    )
    if managed_spec is None or managed_spec.loader is None:
        raise RuntimeError(f"could not load managed paths module: {managed_path}")
    managed_module = importlib.util.module_from_spec(managed_spec)
    sys.modules[managed_spec.name] = managed_module
    managed_spec.loader.exec_module(managed_module)
    return managed_module


try:
    _MANAGED_PATHS = load_managed_paths()
except RuntimeError as error:
    print(f"AgentOS export failed: {error}", file=sys.stderr)
    raise SystemExit(2)
managed_path_problem_text = _MANAGED_PATHS.managed_path_problem_text


_PUBLICATION_RULES_LOADED = False


def load_publication_rules() -> None:
    global EXCLUDED_DIRS
    global ROOT_DIRS
    global ROOT_FILES
    global gitkeep_file_reason
    global is_personal_overlay_skeleton_path
    global personal_overlay_skeleton_file_reason
    global publication_path_reason
    global _PUBLICATION_RULES_LOADED

    if _PUBLICATION_RULES_LOADED:
        return

    root = current_script_root()
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

    EXCLUDED_DIRS = module.PUBLIC_EXPORT_EXCLUDED_DIRS
    ROOT_DIRS = module.PUBLIC_EXPORT_ROOT_DIRS
    ROOT_FILES = module.PUBLIC_EXPORT_ROOT_FILES
    gitkeep_file_reason = module.gitkeep_file_reason
    is_personal_overlay_skeleton_path = module.is_personal_overlay_skeleton_path
    personal_overlay_skeleton_file_reason = module.personal_overlay_skeleton_file_reason
    publication_path_reason = module.publication_path_reason
    _PUBLICATION_RULES_LOADED = True


def looks_like_export_dir(path: Path) -> bool:
    name = path.name.lower()
    return "agentos" in name and any(
        term in name for term in ["export", "publication", "candidate", "public"]
    )


def output_safety_errors(root: Path, output: Path) -> list[str]:
    errors: list[str] = []
    resolved_root = root.resolve()
    resolved_output = output.resolve(strict=False)
    filesystem_root = Path(resolved_output.anchor).resolve()
    home = Path.home().resolve()

    if resolved_output == filesystem_root:
        errors.append("output may not be the filesystem root")
    if resolved_output == home:
        errors.append("output may not be the current user's home directory")
    if resolved_output == resolved_root:
        errors.append("output may not be the AgentOS repository root")
    elif is_relative_to(resolved_output, resolved_root):
        errors.append("output may not be inside the AgentOS repository root")
    if resolved_output in resolved_root.parents:
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


def current_validator_script() -> Path:
    root = current_script_root()
    validator = root / "os/verification/scripts/validate_agentos.py"
    validator_problem = managed_path_problem_text(
        root,
        validator,
        expected_kind="file",
        allow_missing=False,
    )
    if validator_problem:
        raise RuntimeError(f"unsafe validator script: {validator_problem}")
    return validator


def run_publication_precheck(root: Path) -> int:
    validator = current_validator_script()
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


def run_validation(root: Path, output: Path) -> int:
    validator = current_validator_script()
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
    root = _bootstrap_lexical_absolute(args.root)
    root_problem = _bootstrap_final_path_problem(root, expected_kind="directory", allow_missing=False)
    if root_problem:
        print(f"error: unsafe AgentOS root: {root} ({root_problem})", file=sys.stderr)
        return 2
    if not (root / "os").is_dir():
        print(f"error: root does not contain os/: {root}", file=sys.stderr)
        return 2
    try:
        load_publication_rules()
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    staged_snapshot: Path | None = None
    try:
        source_root = root
        git_source_set = True
        sources: list[Path] | None = None
        if args.staged:
            staged_snapshot = materialize_staged_tree(root)
            source_root = staged_snapshot
            git_source_set = False
            sources = publishable_sources(source_root, git_source_set=git_source_set)
            precheck_status = run_validation(root, source_root)
        else:
            precheck_status = run_publication_precheck(root)
        if precheck_status != 0:
            return precheck_status

        if sources is None:
            sources = publishable_sources(source_root, git_source_set=git_source_set)

        if args.output:
            output = _bootstrap_lexical_absolute(args.output)
            output_problem = _bootstrap_final_path_problem(output, expected_kind="directory", allow_missing=True)
            if output_problem:
                print(f"error: unsafe output directory: {output} ({output_problem})", file=sys.stderr)
                return 2
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
        return run_validation(root, output)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    finally:
        if staged_snapshot is not None:
            shutil.rmtree(staged_snapshot, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
