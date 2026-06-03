"""Managed-path structural checks for AgentOS validation."""

from __future__ import annotations

from .common import *


class ManagedSymlinkValidator(ValidatorDelegate):
    def check_managed_symlinks(self) -> None:
        check = "managed symlink policy"
        if check in self.checked:
            return

        root_problem = self.root_path_problem()
        if root_problem:
            self.add_error(check, self.root, f"AgentOS validation root is unsafe: {root_problem}")
            self.checked.append(check)
            return

        os_dir = self.root / "os"
        if not os_dir.exists() and not os_dir.is_symlink():
            self.add_error(check, os_dir, "AgentOS Core directory is missing")
            self.checked.append(check)
            return

        for entry in sorted(self.root.iterdir()):
            if self.should_skip_managed_symlink_scan(entry):
                continue
            self.check_managed_symlink_tree(entry, check)

        self.checked.append(check)

    def should_skip_managed_symlink_scan(self, path: Path) -> bool:
        try:
            rel = path.relative_to(self.root)
        except ValueError:
            return False
        if not rel.parts:
            return False
        if rel.parts[0] in {".git", "personal"}:
            return True
        if any(part in PUBLIC_EXPORT_EXCLUDED_DIRS for part in rel.parts):
            return True
        return False

    def check_managed_symlink_tree(self, root: Path, check: str) -> None:
        message = "AgentOS-managed paths outside personal/ must not contain symbolic links"
        pending = [root]
        while pending:
            path = pending.pop()
            if self.should_skip_managed_symlink_scan(path):
                continue
            if path.is_symlink():
                self.add_error(check, path, message)
                continue
            if not path.is_dir():
                continue
            try:
                pending.extend(reversed(sorted(path.iterdir())))
            except OSError as error:
                self.add_error(check, path, f"{error.__class__.__name__}: {error}")


def run_self_test(harness) -> None:
    root = harness.root / "managed_fixture"
    (root / "os").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "target.txt").write_text("target\n", encoding="utf-8")
    (root / "docs/linked.raw").symlink_to("../target.txt")
    validator = harness.validator(root)
    validator.check_managed_symlinks()

    ignored_root = harness.root / "managed_ignored_fixture"
    (ignored_root / "os").mkdir(parents=True)
    (ignored_root / ".gitignore").write_text("output/\nlocal-artifacts/\n", encoding="utf-8")
    ignored_output = ignored_root / "output/private-link.md"
    ignored_output.parent.mkdir()
    ignored_output.symlink_to("../target.txt")
    subprocess.run(
        ["git", "-C", str(ignored_root), "init"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    ignored_validator = harness.validator(ignored_root)
    ignored_validator.check_managed_symlinks()

    managed_os_symlink_root = harness.root / "managed_os_symlink_fixture"
    real_os = managed_os_symlink_root / "real-os"
    (real_os / "verification/source-routing").mkdir(parents=True)
    (real_os / "verification/source-routing/fixtures.json").write_text("{not json\n", encoding="utf-8")
    (real_os / "verification/BENCHMARKS.json").write_text("{not json\n", encoding="utf-8")
    (managed_os_symlink_root / "os").symlink_to("real-os")
    managed_os_validator = harness.validator(managed_os_symlink_root)
    managed_os_validator.run_structural_checks()

    symlinked_root_target = harness.root / "managed_symlinked_root_target"
    (symlinked_root_target / "os").mkdir(parents=True)
    symlinked_root = harness.root / "managed_symlinked_root"
    symlinked_root.symlink_to(symlinked_root_target, target_is_directory=True)
    symlinked_root_validator = harness.validator(symlinked_root)
    symlinked_root_validator.run_structural_checks()

    harness.expect(
        "managed rejects non-personal symlinks",
        any(
            error.path == "docs/linked.raw"
            and "AgentOS-managed paths outside personal/ must not contain symbolic links" in error.message
            for error in validator.errors
        ),
    )
    harness.expect(
        "managed skips ignored artifact symlinks",
        not any("output/private-link.md" in error.path for error in ignored_validator.errors),
    )
    harness.expect(
        "managed os symlink stops later structural reads",
        any(
            error.check == "managed symlink policy"
            and error.path == "os"
            and "symbolic links" in error.message
            for error in managed_os_validator.errors
        )
        and not any(error.check != "managed symlink policy" for error in managed_os_validator.errors),
    )
    harness.expect(
        "managed rejects symlinked validation root",
        any(
            error.check == "managed symlink policy"
            and error.path == "."
            and "AgentOS validation root is unsafe" in error.message
            and "symbolic link is not allowed" in error.message
            for error in symlinked_root_validator.errors
        ),
    )
    harness.record(validator, ignored_validator, managed_os_validator, symlinked_root_validator)
