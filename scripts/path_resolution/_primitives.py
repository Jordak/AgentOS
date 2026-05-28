"""Private path primitives for AgentOS path-resolution modules.

This module is implementation, not a caller interface. Public callers should
depend on policy-shaped modules such as ``path_resolution.managed``.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PathProblem:
    path: Path
    reason: str

    def with_path(self) -> str:
        return f"{self.path} ({self.reason})"


def lexical_absolute(path: Path, cwd: Path | None = None) -> Path:
    expanded = path.expanduser()
    if not expanded.is_absolute():
        expanded = (cwd or Path.cwd()) / expanded
    return Path(os.path.abspath(expanded))


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True


def path_kind_problem(
    path: Path,
    expected_kind: str | None = None,
    allow_missing: bool = True,
    cwd: Path | None = None,
) -> PathProblem | None:
    absolute = lexical_absolute(path, cwd=cwd)
    try:
        path_stat = absolute.lstat()
    except FileNotFoundError:
        if allow_missing:
            return None
        return PathProblem(absolute, "path is missing")
    except OSError as error:
        return PathProblem(absolute, f"{error.__class__.__name__}: {error}")

    if stat.S_ISLNK(path_stat.st_mode):
        return PathProblem(absolute, "symbolic link is not allowed")
    if expected_kind == "directory" and not stat.S_ISDIR(path_stat.st_mode):
        return PathProblem(absolute, "not a directory")
    if expected_kind == "file" and not stat.S_ISREG(path_stat.st_mode):
        return PathProblem(absolute, "not a regular file")
    return None


def no_follow_path_problem(
    root: Path,
    path: Path,
    expected_kind: str | None,
    allow_missing: bool,
    cwd: Path | None = None,
    root_label: str = "managed root",
) -> PathProblem | None:
    root_absolute = lexical_absolute(root, cwd=cwd)
    root_problem = path_kind_problem(
        root_absolute,
        expected_kind="directory",
        allow_missing=False,
        cwd=cwd,
    )
    if root_problem:
        return root_problem

    raw_path = path.expanduser()
    if ".." in raw_path.parts:
        candidate = raw_path if raw_path.is_absolute() else root_absolute / raw_path
        return PathProblem(candidate, "parent-directory segments are not allowed")

    candidate = path if path.is_absolute() else root_absolute / path
    absolute = lexical_absolute(candidate, cwd=cwd)
    try:
        relative = absolute.relative_to(root_absolute)
    except ValueError:
        return PathProblem(absolute, f"path is outside the {root_label}: {root_absolute}")

    if not relative.parts:
        return path_kind_problem(
            root_absolute,
            expected_kind=expected_kind,
            allow_missing=allow_missing,
            cwd=cwd,
        )

    current = root_absolute
    for index, part in enumerate(relative.parts):
        current = current / part
        is_final = index == len(relative.parts) - 1
        try:
            path_stat = current.lstat()
        except FileNotFoundError:
            if allow_missing:
                return None
            return PathProblem(current, "path component is missing")
        except OSError as error:
            return PathProblem(current, f"{error.__class__.__name__}: {error}")

        if stat.S_ISLNK(path_stat.st_mode):
            return PathProblem(current, "symbolic link is not allowed")
        if not is_final and not stat.S_ISDIR(path_stat.st_mode):
            return PathProblem(current, "path component is not a directory")
        if is_final and expected_kind == "directory" and not stat.S_ISDIR(path_stat.st_mode):
            return PathProblem(current, "not a directory")
        if is_final and expected_kind == "file" and not stat.S_ISREG(path_stat.st_mode):
            return PathProblem(current, "not a regular file")
    return None
