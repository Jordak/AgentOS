#!/usr/bin/env python3
"""Self-tests for os/skills/expose-skills/scripts/expose_skills.py."""

from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import expose_skills as subject

_case = unittest.TestCase()


def run_self_tests() -> int:
    tests = [
        test_default_apply_creates_missing_symlinks,
        test_existing_copy_is_reported_not_changed_without_replace,
        test_replace_dry_run_does_not_change_same_name_directory,
        test_replace_apply_backs_up_same_name_directory_and_links,
        test_wrong_target_symlink_is_not_replaced,
        test_regular_file_is_blocked_not_replaced,
        test_unrelated_global_skill_is_ignored,
        test_retired_core_adapter_is_reported,
        test_prune_retired_core_adapter_backs_up_before_removal,
        test_scoped_skill_replaces_only_requested_skill,
        test_partial_failure_reports_prior_backup_path,
        test_self_test_rejects_other_options,
    ]
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
            return 1
    print(f"PASS expose_skills self-tests ({len(tests)} tests)")
    return 0


def test_default_apply_creates_missing_symlinks() -> None:
    with tempfile.TemporaryDirectory(prefix="expose-skills-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_agentos(root)
        code, output, _error = run_cli(root, home, "--no-dry-run")
        _case.assertEqual(code, 0)
        _case.assertIn("created-symlink", output)
        assert_symlink_to(home / ".agents/skills/alpha", root / "os/skills/alpha")


def test_existing_copy_is_reported_not_changed_without_replace() -> None:
    with tempfile.TemporaryDirectory(prefix="expose-skills-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_agentos(root)
        alpha = home / ".agents/skills/alpha"
        alpha.mkdir(parents=True)
        (alpha / "custom.txt").write_text("not a byte-identical copy\n", encoding="utf-8")
        code, output, _error = run_cli(root, home, "--no-dry-run")
        _case.assertEqual(code, 1)
        _case.assertIn("existing-copy", output)
        _case.assertTrue(alpha.is_dir() and not alpha.is_symlink())
        _case.assertTrue((alpha / "custom.txt").is_file())


def test_replace_dry_run_does_not_change_same_name_directory() -> None:
    with tempfile.TemporaryDirectory(prefix="expose-skills-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_agentos(root)
        alpha = home / ".agents/skills/alpha"
        alpha.mkdir(parents=True)
        (alpha / "custom.txt").write_text("same name, not byte-identical\n", encoding="utf-8")
        code, output, _error = run_cli(root, home, "--replace-existing-copy")
        _case.assertEqual(code, 0)
        _case.assertIn("would-replace-existing-copy", output)
        _case.assertTrue(alpha.is_dir() and not alpha.is_symlink())
        _case.assertTrue((alpha / "custom.txt").is_file())


def test_replace_apply_backs_up_same_name_directory_and_links() -> None:
    with tempfile.TemporaryDirectory(prefix="expose-skills-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_agentos(root)
        alpha = home / ".agents/skills/alpha"
        alpha.mkdir(parents=True)
        (alpha / "custom.txt").write_text("same name, not byte-identical\n", encoding="utf-8")
        code, output, _error = run_cli(root, home, "--replace-existing-copy", "--no-dry-run")
        _case.assertEqual(code, 0)
        _case.assertIn("replaced-copy-with-symlink", output)
        _case.assertIn("backed up existing directory to:", output)
        assert_symlink_to(alpha, root / "os/skills/alpha")
        backups = list((home / ".agents/skills/.archive/expose-skills").glob("*/alpha/custom.txt"))
        _case.assertEqual(len(backups), 1)
        _case.assertEqual(backups[0].read_text(encoding="utf-8"), "same name, not byte-identical\n")


def test_wrong_target_symlink_is_not_replaced() -> None:
    with tempfile.TemporaryDirectory(prefix="expose-skills-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        outside = Path(tmp) / "outside"
        make_agentos(root)
        outside.mkdir()
        alpha = home / ".agents/skills/alpha"
        alpha.parent.mkdir(parents=True)
        alpha.symlink_to(outside, target_is_directory=True)
        code, output, _error = run_cli(root, home, "--replace-existing-copy", "--no-dry-run")
        _case.assertEqual(code, 1)
        _case.assertIn("wrong-target", output)
        assert_symlink_to(alpha, outside)


def test_regular_file_is_blocked_not_replaced() -> None:
    with tempfile.TemporaryDirectory(prefix="expose-skills-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_agentos(root)
        alpha = home / ".agents/skills/alpha"
        alpha.parent.mkdir(parents=True)
        alpha.write_text("do not replace\n", encoding="utf-8")
        code, output, _error = run_cli(root, home, "--replace-existing-copy", "--no-dry-run")
        _case.assertEqual(code, 1)
        _case.assertIn("blocked", output)
        _case.assertTrue(alpha.is_file())
        _case.assertEqual(alpha.read_text(encoding="utf-8"), "do not replace\n")


def test_unrelated_global_skill_is_ignored() -> None:
    with tempfile.TemporaryDirectory(prefix="expose-skills-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_agentos(root)
        extra = home / ".agents/skills/not-agentos"
        extra.mkdir(parents=True)
        code, output, _error = run_cli(root, home, "--replace-existing-copy")
        _case.assertEqual(code, 0)
        _case.assertNotIn("not-agentos", output)
        _case.assertTrue(extra.is_dir())


def test_retired_core_adapter_is_reported() -> None:
    with tempfile.TemporaryDirectory(prefix="expose-skills-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_agentos(root)
        retired = home / ".agents/skills/github-loop"
        retired.parent.mkdir(parents=True)
        retired.symlink_to(root / "os/skills/github-loop", target_is_directory=True)
        code, output, _error = run_cli(root, home)
        _case.assertEqual(code, 1)
        _case.assertIn("retired-core-export-candidate", output)
        _case.assertIn("github-loop", output)
        _case.assertIn("provenance is not proven", output)
        _case.assertTrue(retired.is_symlink())


def test_prune_retired_core_adapter_backs_up_before_removal() -> None:
    with tempfile.TemporaryDirectory(prefix="expose-skills-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_agentos(root)
        retired = home / ".agents/skills/coordinate-issue-batch"
        retired.mkdir(parents=True)
        (retired / "old.txt").write_text("retired copy\n", encoding="utf-8")

        dry_code, dry_output, _dry_error = run_cli(root, home, "--prune-retired-core-adapters")
        _case.assertEqual(dry_code, 0)
        _case.assertIn("would-prune-retired-core-export-candidate", dry_output)
        _case.assertIn("unproven provenance", dry_output)
        _case.assertTrue((retired / "old.txt").is_file())

        code, output, _error = run_cli(root, home, "--prune-retired-core-adapters", "--no-dry-run")
        _case.assertEqual(code, 0)
        _case.assertIn("pruned-retired-core-export-candidate", output)
        _case.assertFalse(retired.exists())
        backups = list((home / ".agents/skills/.archive/expose-skills").glob("*/coordinate-issue-batch/old.txt"))
        _case.assertEqual(len(backups), 1)
        _case.assertEqual(backups[0].read_text(encoding="utf-8"), "retired copy\n")


def test_scoped_skill_replaces_only_requested_skill() -> None:
    with tempfile.TemporaryDirectory(prefix="expose-skills-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_agentos(root)
        alpha = home / ".agents/skills/alpha"
        beta = home / ".agents/skills/beta"
        alpha.mkdir(parents=True)
        beta.mkdir(parents=True)
        (alpha / "custom.txt").write_text("alpha\n", encoding="utf-8")
        (beta / "custom.txt").write_text("beta\n", encoding="utf-8")
        code, output, _error = run_cli(
            root,
            home,
            "--skill",
            "alpha",
            "--replace-existing-copy",
            "--no-dry-run",
        )
        _case.assertEqual(code, 0)
        _case.assertIn("alpha", output)
        _case.assertNotIn("beta", output)
        assert_symlink_to(alpha, root / "os/skills/alpha")
        _case.assertTrue(beta.is_dir() and not beta.is_symlink())
        _case.assertTrue((beta / "custom.txt").is_file())


def test_partial_failure_reports_prior_backup_path() -> None:
    with tempfile.TemporaryDirectory(prefix="expose-skills-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_agentos(root)
        adapter_root = home / ".agents/skills"
        backup_root = adapter_root / ".archive/expose-skills/run"
        for name in ("alpha", "beta"):
            copied = adapter_root / name
            copied.mkdir(parents=True)
            (copied / "custom.txt").write_text(f"{name}\n", encoding="utf-8")
        entries = subject.select_entries(subject.parse_manifest(root), ["alpha", "beta"])
        original_create_symlink = subject.create_symlink

        def fail_for_beta(entry: subject.SkillEntry, adapter_path: Path) -> None:
            if entry.name == "beta":
                raise SystemExit("forced beta symlink failure")
            original_create_symlink(entry, adapter_path)

        subject.create_symlink = fail_for_beta
        try:
            results = subject.collect_results(
                entries,
                adapter_root,
                apply=True,
                replace_existing_copy=True,
                prune_retired_core_adapters=False,
                backup_root=backup_root,
            )
        finally:
            subject.create_symlink = original_create_symlink

        _case.assertEqual([result.status for result in results], ["replaced-copy-with-symlink", "blocked"])
        _case.assertTrue(any("backed up existing directory to:" in note for note in results[0].notes))
        _case.assertTrue(any("forced beta symlink failure" in note for note in results[1].notes))
        beta_failure_note = " ".join(results[1].notes)
        _case.assertIn("No replacement backup remains because the original directory was restored.", beta_failure_note)
        legacy_backup_phrase = "Existing " + "copy " + "backup"
        _case.assertNotIn(legacy_backup_phrase, beta_failure_note)
        assert_symlink_to(adapter_root / "alpha", root / "os/skills/alpha")
        _case.assertTrue((backup_root / "alpha/custom.txt").is_file())
        _case.assertTrue((adapter_root / "beta/custom.txt").is_file())
        _case.assertFalse((backup_root / "beta").exists())
        _case.assertFalse((adapter_root / "beta").is_symlink())


def test_self_test_rejects_other_options() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = subject.main(["--self-test", "--no-dry-run"])
    _case.assertEqual(code, 2)
    _case.assertIn("cannot be combined", stderr.getvalue())

    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = subject.main(["--agentos-root", ".", "--skill", "alpha", "--prune-retired-core-adapters"])
    _case.assertEqual(code, 2)
    _case.assertIn("cannot be combined", stderr.getvalue())


def make_agentos(root: Path) -> None:
    manifest = root / "os/skills/MANIFEST.md"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        "\n".join(
            [
                "# Skills Manifest",
                "",
                "### `alpha`",
                "",
                "- Canonical source: `os/skills/alpha/SKILL.md`",
                "",
                "### `beta`",
                "",
                "- Canonical source: `os/skills/beta/SKILL.md`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    for name in ("alpha", "beta"):
        skill = root / "os/skills" / name / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(f"---\nname: {name}\n---\n\n# {name}\n", encoding="utf-8")


def run_cli(root: Path, home: Path, *args: str) -> tuple[int, str, str]:
    previous_home = os.environ.get("HOME")
    os.environ["HOME"] = str(home)
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                code = subject.main(["--agentos-root", str(root), *args])
            except SystemExit as exc:
                code = int(exc.code) if isinstance(exc.code, int) else 1
    finally:
        if previous_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = previous_home
    return code, stdout.getvalue(), stderr.getvalue()


def assert_symlink_to(path: Path, target: Path) -> None:
    _case.assertTrue(path.is_symlink(), f"{path} should be a symlink")
    _case.assertTrue(path.samefile(target), f"{path} should point to {target}")
