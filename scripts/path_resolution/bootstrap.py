"""Private checked-import support for AgentOS path-resolution modules.

This module is intentionally not part of the public path-resolution interface.
It exists so trusted scripts that execute before normal package imports are set
up can validate and import ``path_resolution.managed`` without duplicating the
same safety-critical import logic.
"""

from __future__ import annotations

import importlib.util
import os
import stat
import sys
from pathlib import Path


PATH_RESOLUTION_PACKAGE = "path_resolution"
PATH_RESOLUTION_REQUIRED_MODULES = ("__init__.py", "_primitives.py", "managed.py", "bootstrap.py")
SUPPORTED_EXPECTED_KINDS = {None, "file", "directory"}


def lexical_absolute(path: Path) -> Path:
    """Make a path absolute without resolving symbolic links."""
    expanded = path.expanduser()
    if not expanded.is_absolute():
        expanded = Path.cwd() / expanded
    return Path(os.path.abspath(expanded))


def path_kind_problem(
    path: Path,
    expected_kind: str | None = None,
    allow_missing: bool = True,
) -> str | None:
    expected_kind_problem = expected_kind_problem_text(expected_kind)
    if expected_kind_problem:
        return expected_kind_problem
    absolute = lexical_absolute(path)
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


def no_follow_path_problem(
    path: Path,
    expected_kind: str | None,
    allow_missing: bool,
    boundary: Path,
) -> str | None:
    expected_kind_problem = expected_kind_problem_text(expected_kind)
    if expected_kind_problem:
        return f"{path} ({expected_kind_problem})"
    boundary_absolute = lexical_absolute(boundary)
    boundary_problem = path_kind_problem(boundary_absolute, expected_kind="directory", allow_missing=False)
    if boundary_problem:
        return f"{boundary_absolute} ({boundary_problem})"

    if ".." in path.expanduser().parts:
        return f"{path} (parent-directory segments are not allowed)"

    absolute = lexical_absolute(path)
    try:
        relative = absolute.relative_to(boundary_absolute)
    except ValueError:
        return f"{absolute} (path is outside the managed root: {boundary_absolute})"

    current = boundary_absolute
    if not relative.parts:
        final_problem = path_kind_problem(current, expected_kind=expected_kind, allow_missing=allow_missing)
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


def expected_kind_problem_text(expected_kind: object) -> str | None:
    try:
        supported = expected_kind in SUPPORTED_EXPECTED_KINDS
    except TypeError:
        supported = False
    if not supported:
        return "expected_kind must be None, 'file', or 'directory'"
    return None


def path_resolution_package_problem(root: Path) -> str | None:
    package_dir = root / "scripts" / PATH_RESOLUTION_PACKAGE
    package_problem = no_follow_path_problem(
        package_dir,
        expected_kind="directory",
        allow_missing=False,
        boundary=root,
    )
    if package_problem:
        return package_problem

    for module_name in PATH_RESOLUTION_REQUIRED_MODULES:
        module_problem = no_follow_path_problem(
            package_dir / module_name,
            expected_kind="file",
            allow_missing=False,
            boundary=root,
        )
        if module_problem:
            return module_problem

    try:
        module_paths = sorted(package_dir.glob("*.py"))
    except OSError as error:
        return f"{package_dir} ({error.__class__.__name__}: {error})"
    if not module_paths:
        return f"{package_dir} (package contains no Python modules)"

    for module_path in module_paths:
        module_problem = no_follow_path_problem(
            module_path,
            expected_kind="file",
            allow_missing=False,
            boundary=root,
        )
        if module_problem:
            return module_problem
    return None


def load_checked_managed_paths(root: Path, checked_package_name: str = "_agentos_checked_path_resolution"):
    root = lexical_absolute(root)
    package_problem = path_resolution_package_problem(root)
    if package_problem:
        raise RuntimeError(f"unsafe path-resolution package: {package_problem}")

    package_dir = root / "scripts" / PATH_RESOLUTION_PACKAGE
    package_init = package_dir / "__init__.py"
    managed_path = package_dir / "managed.py"
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
    try:
        package_spec.loader.exec_module(package_module)
    except Exception as error:
        raise RuntimeError(f"could not load path-resolution package: {package_init}: {error}") from error

    managed_spec = importlib.util.spec_from_file_location(
        f"{checked_package_name}.managed",
        managed_path,
    )
    if managed_spec is None or managed_spec.loader is None:
        raise RuntimeError(f"could not load managed paths module: {managed_path}")
    managed_module = importlib.util.module_from_spec(managed_spec)
    sys.modules[managed_spec.name] = managed_module
    try:
        managed_spec.loader.exec_module(managed_module)
        getattr(managed_module, "managed_path_problem_text")
    except Exception as error:
        raise RuntimeError(f"could not load managed paths module: {managed_path}: {error}") from error
    return managed_module
