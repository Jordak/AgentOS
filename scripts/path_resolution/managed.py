"""Managed-path safety checks for AgentOS trusted scripts.

This public module owns one narrow policy: a managed path must stay under a
non-symlink declared root, must not traverse symbolic-link components beneath
that root, and must have the expected final kind when the caller asks for one.
Callers still own AgentOS domain policy, status labels, and decisions such as
FAIL versus WARN.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional


ExpectedKind = Optional[Literal["file", "directory"]]


def _load_direct_primitives():
    module_path = Path(__file__).with_name("_primitives.py")
    spec = importlib.util.spec_from_file_location("_agentos_path_resolution_primitives", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load path primitives: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


if __package__ in (None, ""):
    _primitives = _load_direct_primitives()
else:
    from . import _primitives


@dataclass(frozen=True)
class ManagedPathProblem:
    path: Path
    reason: str

    def with_path(self) -> str:
        return f"{self.path} ({self.reason})"


def _managed_problem(problem: _primitives.PathProblem | None) -> ManagedPathProblem | None:
    if problem is None:
        return None
    return ManagedPathProblem(problem.path, problem.reason)


def managed_path_problem(
    root: Path,
    path: Path,
    expected_kind: ExpectedKind,
    allow_missing: bool,
    cwd: Path | None = None,
    root_label: str = "managed root",
) -> ManagedPathProblem | None:
    return _managed_problem(
        _primitives.no_follow_path_problem(
            root,
            path,
            expected_kind=expected_kind,
            allow_missing=allow_missing,
            cwd=cwd,
            root_label=root_label,
        )
    )


def managed_path_problem_text(
    root: Path,
    path: Path,
    expected_kind: ExpectedKind,
    allow_missing: bool,
    cwd: Path | None = None,
    root_label: str = "managed root",
) -> str | None:
    problem = managed_path_problem(
        root,
        path,
        expected_kind=expected_kind,
        allow_missing=allow_missing,
        cwd=cwd,
        root_label=root_label,
    )
    return problem.with_path() if problem else None


def managed_path_problem_list(
    root: Path,
    path: Path,
    expected_kind: ExpectedKind,
    allow_missing: bool,
    cwd: Path | None = None,
    root_label: str = "managed root",
) -> list[str]:
    problem = managed_path_problem(
        root,
        path,
        expected_kind=expected_kind,
        allow_missing=allow_missing,
        cwd=cwd,
        root_label=root_label,
    )
    return [problem.with_path()] if problem else []


def managed_relative_path_problem(raw_path: str) -> str | None:
    path = Path(raw_path)
    if path.is_absolute():
        return "must be root-relative, not absolute"
    if raw_path.startswith("~"):
        return "must be root-relative, not home-relative"
    if ".." in path.parts:
        return "must not contain parent-directory segments"
    return None


def run_self_tests() -> int:
    with tempfile.TemporaryDirectory(prefix="path-resolution-") as tmp:
        root = Path(tmp)
        safe = root / "safe"
        safe.mkdir()
        regular = safe / "file.txt"
        regular.write_text("ok\n", encoding="utf-8")

        missing = managed_path_problem(root, root / "missing.txt", expected_kind="file", allow_missing=False)
        assert missing and missing.reason == "path component is missing", missing

        wrong_kind = managed_path_problem(root, safe, expected_kind="file", allow_missing=False)
        assert wrong_kind and wrong_kind.reason == "not a regular file", wrong_kind

        outside = managed_path_problem(
            root,
            root.parent / "outside.txt",
            expected_kind="file",
            allow_missing=True,
        )
        assert outside and "outside the managed root" in outside.reason, outside

        assert managed_relative_path_problem("/" + "tmp/file") == "must be root-relative, not absolute"
        assert managed_relative_path_problem("~" + "/file") == "must be root-relative, not home-relative"
        assert managed_relative_path_problem("../file") == "must not contain parent-directory segments"
        assert managed_relative_path_problem("os/INDEX.md") is None

        try:
            managed_path_problem(root, regular, expected_kind="dir", allow_missing=False)  # type: ignore[arg-type]
        except ValueError as error:
            assert "expected_kind" in str(error), error
        else:
            raise AssertionError("invalid expected_kind must fail closed")

        parent_segment = managed_path_problem(
            root,
            safe / ".." / "safe" / "file.txt",
            expected_kind="file",
            allow_missing=False,
        )
        assert parent_segment and parent_segment.reason == "parent-directory segments are not allowed", parent_segment

        target = root / "real"
        target.mkdir()
        link = root / "link"
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            print("PASS path_resolution.managed self-tests (symlink checks skipped)")
            return 0

        symlink_problem = managed_path_problem(
            root,
            link / "child",
            expected_kind="file",
            allow_missing=False,
        )
        assert symlink_problem and symlink_problem.path == link, symlink_problem
        assert symlink_problem.reason == "symbolic link is not allowed", symlink_problem

        hidden_symlink_problem = managed_path_problem(
            root,
            link / ".." / "safe" / "file.txt",
            expected_kind="file",
            allow_missing=False,
        )
        assert hidden_symlink_problem, hidden_symlink_problem
        assert hidden_symlink_problem.reason == "parent-directory segments are not allowed", hidden_symlink_problem

    print("PASS path_resolution.managed self-tests")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Managed-path safety checks for AgentOS scripts.")
    parser.add_argument("--self-test", action="store_true", help="Run temporary-directory self-tests and exit.")
    args = parser.parse_args(argv)
    if args.self_test:
        return run_self_tests()
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
