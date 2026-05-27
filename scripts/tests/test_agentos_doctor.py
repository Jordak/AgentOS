#!/usr/bin/env python3
"""Self-tests for scripts/agentos_doctor.py."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from agentos_doctor import *  # noqa: F403 - self-tests exercise the script's public helpers.


PRIVATE_CONTENT_SENTINEL = "DO_NOT_LEAK_AGENTOS_DOCTOR_SELF_TEST"
_case = unittest.TestCase()


def run_self_tests() -> int:
    tests = [
        test_invalid_home_is_graceful,
        test_required_core_files_pass,
        test_required_core_files_unreadable_fails,
        test_untrusted_home_skips_subprocess_helpers,
        test_helper_parent_symlink_does_not_execute,
        test_personal_overlay_does_not_print_private_contents,
        test_adapter_check_is_read_only_check_only,
        test_adapter_check_uses_audit_root_when_primary_differs,
        test_same_root_adapter_output_omits_write_commands,
        test_split_root_adapter_output_omits_write_commands,
        test_adapter_helper_failure_warns,
        test_mirror_audit_never_syncs,
        test_mirror_audit_passes_primary_personal_root,
        test_mirror_malformed_json_warns,
        test_mirror_valid_json_schema_errors_warn,
        test_mirror_unknown_source_kind_warns_without_echo,
        test_mirror_output_does_not_print_private_metadata,
        test_helper_output_is_bounded,
        test_count_files_ignores_placeholder_noise,
        test_count_files_warns_on_walk_errors,
        test_count_files_warns_on_symlink_root,
        test_automation_locations_report_counts_not_contents,
        test_automation_locations_split_roots,
        test_strict_warn_exit_code,
        test_adapter_home_notation_is_preserved,
    ]
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
            return 1
    print(f"PASS agentos_doctor self-tests ({len(tests)} tests)")
    return 0


def test_invalid_home_is_graceful() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "not-agentos"
        root.mkdir()
        report = run_doctor(
            requested_agentos_home=root,
            requested_primary_agentos_home=None,
            mirror_root=Path(tmp) / "mirrors",
            cwd=root,
            process_home=Path(tmp) / "home",
            env=minimal_env(Path(tmp) / "home"),
            adapter_args=[],
            verbose=False,
        )
        _case.assertTrue(result_named(report, "home structure").status == "FAIL", "invalid home should fail home structure")


def test_required_core_files_pass() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        result = check_required_core_files(root)
        _case.assertTrue(result.status == "PASS", "fake AgentOS should have required files")


def test_required_core_files_unreadable_fails() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        target = root / "AGENTS.md"
        original_mode = target.stat().st_mode
        try:
            target.chmod(0)
            unreadable_for_process = not os.access(target, os.R_OK)
            result = check_required_core_files(root)
        finally:
            target.chmod(original_mode)
        if not unreadable_for_process:
            return
        _case.assertTrue(result.status == "FAIL", "unreadable required files should fail")


def test_untrusted_home_skips_subprocess_helpers() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        target = root / "linked-agents.md"
        target.write_text("# Linked\n", encoding="utf-8")
        (root / "AGENTS.md").unlink()
        (root / "AGENTS.md").symlink_to(target)
        (root / "scripts" / "install_global_agent_instructions.py").write_text(
            "print('SHOULD_NOT_RUN')\n",
            encoding="utf-8",
        )
        report = run_doctor(
            requested_agentos_home=root,
            requested_primary_agentos_home=root,
            mirror_root=Path(tmp) / "mirrors",
            cwd=root,
            process_home=Path(tmp) / "home",
            env=minimal_env(Path(tmp) / "home"),
            adapter_args=[],
            verbose=True,
        )
        rendered = render_report_for_test(report, verbose=True)
        _case.assertTrue(result_named(report, "home structure").status == "WARN", "symlinked home should warn")
        _case.assertTrue(result_named(report, "adapter drift").status == "WARN", "adapter check should be skipped")
        _case.assertTrue("SHOULD_NOT_RUN" not in rendered, "untrusted helper should not execute")


def test_helper_parent_symlink_does_not_execute() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        outside = Path(tmp) / "outside"
        make_fake_agentos(root)
        outside.mkdir()
        (outside / "install_global_agent_instructions.py").write_text(
            "print('SHOULD_NOT_RUN')\n",
            encoding="utf-8",
        )
        (root / "scripts" / "install_global_agent_instructions.py").unlink()
        (root / "scripts").rmdir()
        (root / "scripts").symlink_to(outside, target_is_directory=True)
        report = run_doctor(
            requested_agentos_home=root,
            requested_primary_agentos_home=root,
            mirror_root=Path(tmp) / "mirrors",
            cwd=root,
            process_home=Path(tmp) / "home",
            env=minimal_env(Path(tmp) / "home"),
            adapter_args=[],
            verbose=True,
        )
        rendered = render_report_for_test(report, verbose=True)
        _case.assertTrue(result_named(report, "adapter drift").status == "FAIL", "symlinked helper parent should fail closed")
        _case.assertTrue("parent directory is a symlink" in rendered, "symlinked parent should be reported")
        _case.assertTrue("SHOULD_NOT_RUN" not in rendered, "helper behind symlinked parent should not execute")


def test_personal_overlay_does_not_print_private_contents() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        secret = root / "personal" / "os" / "identity" / "USER.md"
        secret.parent.mkdir(parents=True, exist_ok=True)
        secret.write_text(PRIVATE_CONTENT_SENTINEL, encoding="utf-8")
        report = run_doctor(
            requested_agentos_home=root,
            requested_primary_agentos_home=root,
            mirror_root=Path(tmp) / "mirrors",
            cwd=root,
            process_home=Path(tmp) / "home",
            env=minimal_env(Path(tmp) / "home"),
            adapter_args=[],
            verbose=True,
        )
        rendered = render_report_for_test(report, verbose=True)
        _case.assertTrue(PRIVATE_CONTENT_SENTINEL not in rendered, "private file contents leaked")
        _case.assertTrue("Personal Overlay starters" not in rendered, "doctor should not report starter completeness")
        _case.assertTrue("personal/os/identity/USER.md" not in rendered, "doctor should not parse starter paths from Markdown")


def test_adapter_check_is_read_only_check_only() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        result = check_adapters(root, minimal_env(Path(tmp) / "home"), [], verbose=True)
        joined = "\n".join(result.details + result.recommendations)
        _case.assertTrue(result.status == "PASS", "default fake adapter check should pass")
        _case.assertTrue("--check" in joined, "adapter command must use --check")
        _case.assertTrue("--no-remediation" in joined, "adapter command must request fact-only check output")
        _case.assertTrue("--no-dry-run" not in joined, "doctor must not request adapter writes")


def test_adapter_check_uses_audit_root_when_primary_differs() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        audit_root = Path(tmp) / "audit-AgentOS"
        primary_root = Path(tmp) / "primary-AgentOS"
        make_fake_agentos(audit_root)
        make_fake_agentos(primary_root)
        (audit_root / "scripts" / "install_global_agent_instructions.py").write_text(
            "print('AUDIT_HELPER')\n",
            encoding="utf-8",
        )
        (primary_root / "scripts" / "install_global_agent_instructions.py").write_text(
            "print('PRIMARY_HELPER')\n",
            encoding="utf-8",
        )
        report = run_doctor(
            requested_agentos_home=audit_root,
            requested_primary_agentos_home=primary_root,
            mirror_root=Path(tmp) / "mirrors",
            cwd=audit_root,
            process_home=Path(tmp) / "home",
            env=minimal_env(Path(tmp) / "home"),
            adapter_args=[],
            verbose=True,
        )
        rendered = render_report_for_test(report, verbose=True)
        _case.assertTrue("AUDIT_HELPER" in rendered, "adapter check should use the audited AgentOS root")
        _case.assertTrue("PRIMARY_HELPER" not in rendered, "adapter check should not use the primary overlay root")


def test_same_root_adapter_output_omits_write_commands() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        (root / "scripts" / "install_global_agent_instructions.py").write_text(
            "import sys\n"
            "if '--no-remediation' in sys.argv:\n"
            "    print('Drift detected.')\n"
            "else:\n"
            "    print('Drift detected. Remediation:')\n"
            "    print('python3 scripts/install_global_agent_instructions.py --no-dry-run')\n"
            "    print('run --remove to clean it')\n"
            "sys.exit(1)\n",
            encoding="utf-8",
        )
        report = run_doctor(
            requested_agentos_home=root,
            requested_primary_agentos_home=root,
            mirror_root=Path(tmp) / "mirrors",
            cwd=root,
            process_home=Path(tmp) / "home",
            env=minimal_env(Path(tmp) / "home"),
            adapter_args=[],
            verbose=True,
        )
        rendered = render_report_for_test(report, verbose=True)
        _case.assertTrue("--no-dry-run" not in rendered, "same-root doctor should omit write commands")
        _case.assertTrue("--remove" not in rendered, "same-root doctor should omit removal commands")
        _case.assertTrue("Remediation:" not in rendered, "same-root doctor should omit remediation labels")
        _case.assertTrue("write guidance omitted" not in rendered, "doctor should rely on helper fact-only output")


def test_split_root_adapter_output_omits_write_commands() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        audit_root = Path(tmp) / "audit-AgentOS"
        primary_root = Path(tmp) / "primary-AgentOS"
        make_fake_agentos(audit_root)
        make_fake_agentos(primary_root)
        (audit_root / "scripts" / "install_global_agent_instructions.py").write_text(
            "import sys\n"
            "if '--no-remediation' in sys.argv:\n"
            "    print('Drift detected.')\n"
            "else:\n"
            "    print('Drift detected. Remediation:')\n"
            "    print('python3 scripts/install_global_agent_instructions.py --no-dry-run')\n"
            "    print('run --remove to clean it')\n"
            "sys.exit(1)\n",
            encoding="utf-8",
        )
        report = run_doctor(
            requested_agentos_home=audit_root,
            requested_primary_agentos_home=primary_root,
            mirror_root=Path(tmp) / "mirrors",
            cwd=audit_root,
            process_home=Path(tmp) / "home",
            env=minimal_env(Path(tmp) / "home"),
            adapter_args=[],
            verbose=True,
        )
        rendered = render_report_for_test(report, verbose=True)
        _case.assertTrue("--no-dry-run" not in rendered, "split-root doctor should omit write commands")
        _case.assertTrue("--remove" not in rendered, "split-root doctor should omit removal commands")
        _case.assertTrue("Remediation:" not in rendered, "split-root doctor should omit remediation labels")
        _case.assertTrue("write guidance omitted" not in rendered, "doctor should rely on helper fact-only output")
        _case.assertTrue("Feature-worktree split detected" in rendered, "split-root limitation should be explicit")


def test_adapter_helper_failure_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        installer = root / "scripts" / "install_global_agent_instructions.py"
        installer.write_text(
            "import sys\nprint('adapter drift or helper warning', file=sys.stderr)\nsys.exit(1)\n",
            encoding="utf-8",
        )
        result = check_adapters(root, minimal_env(Path(tmp) / "home"), [], verbose=False)
        joined = "\n".join(result.details + result.recommendations)
        _case.assertTrue(result.status == "WARN", "helper nonzero output should warn for interpretation")
        _case.assertTrue("adapter drift or helper warning" in joined, "stderr should be reported")


def test_mirror_audit_never_syncs() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        result = check_skill_mirrors(root, root, Path(tmp) / "mirrors", minimal_env(Path(tmp) / "home"), verbose=True)
        joined = "\n".join(result.details + result.recommendations)
        _case.assertTrue(result.status == "PASS", "default fake mirror audit should pass")
        _case.assertTrue("--json" in joined, "mirror audit should request JSON")
        _case.assertTrue("--sync" not in joined, "doctor must not sync mirrors")


def test_mirror_audit_passes_primary_personal_root() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        audit_root = Path(tmp) / "audit-AgentOS"
        primary_root = Path(tmp) / "primary-AgentOS"
        make_fake_agentos(audit_root)
        make_fake_agentos(primary_root)
        mirror = audit_root / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py"
        mirror.write_text(
            "import json, sys\n"
            "has_primary = '--personal-agentos-root' in sys.argv and sys.argv[sys.argv.index('--personal-agentos-root') + 1].endswith('primary-AgentOS')\n"
            "results = [{\n"
            "  'name': 'example-skill',\n"
            "  'source_kind': 'core',\n"
            "  'status': 'in-sync',\n"
            "  'canonical_source': 'os/skills/example-skill/SKILL.md',\n"
            "  'mirror_path': 'mirror/example-skill',\n"
            "  'missing_files': [],\n"
            "  'changed_files': [],\n"
            "  'extra_files': [],\n"
            "  'notes': []\n"
            "}]\n"
            "if has_primary:\n"
            "  results.append({\n"
            "    'name': 'private-skill',\n"
            "    'source_kind': 'personal-overlay',\n"
            "    'status': 'in-sync',\n"
            "    'canonical_source': 'personal/os/skills/private-skill/SKILL.md',\n"
            "    'mirror_path': 'mirror/private-skill',\n"
            "    'missing_files': [],\n"
            "    'changed_files': [],\n"
            "    'extra_files': [],\n"
            "    'notes': []\n"
            "  })\n"
            "print(json.dumps(results))\n",
            encoding="utf-8",
        )
        result = check_skill_mirrors(
            audit_root,
            primary_root,
            Path(tmp) / "mirrors",
            minimal_env(Path(tmp) / "home"),
            verbose=True,
            suppress_sync_commands=True,
        )
        joined = "\n".join(result.details + result.recommendations)
        _case.assertTrue("Mirror source kinds: core=1, personal-overlay=1" in joined, "primary Personal Overlay root should be audited")
        _case.assertTrue("--sync" not in joined, "split-root mirror audit should omit sync commands")


def test_mirror_malformed_json_warns() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        mirror = root / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py"
        mirror.write_text("print('not json')\n", encoding="utf-8")
        result = check_skill_mirrors(root, root, Path(tmp) / "mirrors", minimal_env(Path(tmp) / "home"), verbose=False)
        _case.assertTrue(result.status == "WARN", "malformed mirror JSON should warn")
        _case.assertTrue(any("malformed" in detail for detail in result.details), "malformed JSON should be reported")


def test_mirror_valid_json_schema_errors_warn() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        mirror = root / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py"
        mirror.write_text("import json\nprint(json.dumps([{'name': 'partial'}]))\n", encoding="utf-8")
        result = check_skill_mirrors(root, root, Path(tmp) / "mirrors", minimal_env(Path(tmp) / "home"), verbose=False)
        joined = "\n".join(result.details)
        _case.assertTrue(result.status == "WARN", "schema-invalid mirror JSON should warn")
        _case.assertTrue("missing fields" in joined, "schema error should be reported")


def test_mirror_unknown_source_kind_warns_without_echo() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        mirror = root / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py"
        mirror.write_text(
            "import json\n"
            "print(json.dumps([{\n"
            "  'name': 'example-skill',\n"
            "  'source_kind': 'private-client-secret',\n"
            "  'status': 'in-sync',\n"
            "  'canonical_source': 'os/skills/example-skill/SKILL.md',\n"
            "  'mirror_path': 'mirror/example-skill',\n"
            "  'missing_files': [],\n"
            "  'changed_files': [],\n"
            "  'extra_files': [],\n"
            "  'notes': []\n"
            "}]))\n",
            encoding="utf-8",
        )
        result = check_skill_mirrors(root, root, Path(tmp) / "mirrors", minimal_env(Path(tmp) / "home"), verbose=True)
        joined = "\n".join(result.details + result.recommendations)
        _case.assertTrue(result.status == "WARN", "unknown source_kind should warn")
        _case.assertTrue("source_kind was not recognized" in joined, "source_kind schema error should be reported")
        _case.assertTrue("private-client-secret" not in joined, "unknown source_kind value leaked")


def test_mirror_output_does_not_print_private_metadata() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        mirror = root / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py"
        mirror.write_text(
            "import json\n"
            "print(json.dumps([{\n"
            "  'name': 'private-client-skill',\n"
            "  'source_kind': 'personal-overlay',\n"
            "  'status': 'stale',\n"
            "  'canonical_source': 'personal/os/skills/private-client-skill/SKILL.md',\n"
            "  'mirror_path': 'mirror/private-client-skill',\n"
            "  'missing_files': ['secret-plan.md'],\n"
            "  'changed_files': ['client-notes.md'],\n"
            "  'extra_files': [],\n"
            "  'notes': ['private note']\n"
            "}]))\n",
            encoding="utf-8",
        )
        result = check_skill_mirrors(root, root, Path(tmp) / "mirrors", minimal_env(Path(tmp) / "home"), verbose=True)
        joined = "\n".join(result.details + result.recommendations)
        _case.assertTrue(result.status == "WARN", "stale mirror result should warn")
        _case.assertTrue("private-client-skill" not in joined, "mirror skill name leaked")
        _case.assertTrue("secret-plan.md" not in joined, "mirror file name leaked")
        _case.assertTrue("Mirror statuses: stale=1" in joined, "safe aggregate status missing")
        _case.assertTrue("--sync" not in joined, "doctor must not suggest mirror sync commands")


def test_helper_output_is_bounded() -> None:
    long_line = "x" * (OUTPUT_LINE_CHAR_LIMIT + 50)
    lines = format_output("stdout", "\n".join([long_line] * (OUTPUT_LINE_LIMIT + 2)), OUTPUT_LINE_LIMIT, OUTPUT_LINE_CHAR_LIMIT)
    rendered = "\n".join(lines)
    _case.assertTrue(len(lines) == OUTPUT_LINE_LIMIT + 1, "line count should be capped with an omission note")
    _case.assertTrue("char(s) omitted" in rendered, "long line should be capped")


def test_count_files_ignores_placeholder_noise() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        make_fake_agentos(root)
        personal_root = root / "personal" / "os" / "automations"
        (personal_root / "AUTOMATIONS.md").unlink()
        (personal_root / ".gitkeep").write_text("", encoding="utf-8")
        (personal_root / ".DS_Store").write_text("noise", encoding="utf-8")
        count, error = count_files(personal_root)
        _case.assertTrue(error is None, "placeholder-only directory should be readable")
        _case.assertTrue(count == 0, "placeholder/noise files should not count as automation files")


def test_count_files_warns_on_walk_errors() -> None:
    original_walk = os.walk

    def fake_walk(root: Path, topdown: bool = True, onerror=None, followlinks: bool = False):
        yield os.fspath(root), ["blocked"], ["visible.md"]
        if onerror is not None:
            onerror(OSError("blocked"))

    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "automations"
        root.mkdir()
        try:
            os.walk = fake_walk  # type: ignore[assignment]
            count, error = count_files(root)
        finally:
            os.walk = original_walk  # type: ignore[assignment]
        _case.assertTrue(count is None, "walk errors should make counts unknown")
        _case.assertTrue(error is not None and "walk error" in error, "walk error should be reported")


def test_count_files_warns_on_symlink_root() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        target = Path(tmp) / "target"
        target.mkdir()
        (target / "automation.md").write_text("private", encoding="utf-8")
        link = Path(tmp) / "linked-automations"
        link.symlink_to(target, target_is_directory=True)
        count, error = count_files(link)
        _case.assertTrue(count is None, "symlink roots should make counts unknown")
        _case.assertTrue(error == "root is symlink", "symlink root should be reported")


def test_automation_locations_report_counts_not_contents() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        root = Path(tmp) / "AgentOS"
        home = Path(tmp) / "home"
        make_fake_agentos(root)
        note = root / "personal" / "os" / "automations" / "private-note.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text(PRIVATE_CONTENT_SENTINEL, encoding="utf-8")
        codex_auto = home / ".codex" / "automations" / "daily" / "automation.toml"
        codex_auto.parent.mkdir(parents=True, exist_ok=True)
        codex_auto.write_text(PRIVATE_CONTENT_SENTINEL, encoding="utf-8")
        report = run_doctor(
            requested_agentos_home=root,
            requested_primary_agentos_home=root,
            mirror_root=Path(tmp) / "mirrors",
            cwd=root,
            process_home=home,
            env=minimal_env(home),
            adapter_args=[],
            verbose=True,
        )
        rendered = render_report_for_test(report, verbose=True)
        _case.assertTrue(PRIVATE_CONTENT_SENTINEL not in rendered, "automation file contents leaked")
        _case.assertTrue("Personal automation files: 2" in rendered, "personal automation count missing")
        _case.assertTrue("Codex automation TOML files: 1" in rendered, "Codex TOML count missing")


def test_automation_locations_split_roots() -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-doctor-self-test-") as tmp:
        audit_root = Path(tmp) / "audit-AgentOS"
        primary_root = Path(tmp) / "primary-AgentOS"
        make_fake_agentos(audit_root)
        make_fake_agentos(primary_root)
        result = check_automation_locations(
            audit_root,
            primary_root,
            Path(tmp) / "home",
            minimal_env(Path(tmp) / "home"),
        )
        joined = "\n".join(result.details)
        _case.assertTrue(f"Core automation registry: present file ({audit_root / 'os' / 'automations' / 'AUTOMATIONS.md'})" in joined, "Core registry should use audit root")
        _case.assertTrue(f"Personal automation registry: present file ({primary_root / 'personal' / 'os' / 'automations' / 'AUTOMATIONS.md'})" in joined, "Personal registry should use primary root")


def test_strict_warn_exit_code() -> None:
    results = [CheckResult("example", "WARN", "warning")]
    _case.assertTrue(exit_code_for(results, strict=False) == 0, "WARN should exit 0 outside strict mode")
    _case.assertTrue(exit_code_for(results, strict=True) == 1, "WARN should exit 1 in strict mode")


def test_adapter_home_notation_is_preserved() -> None:
    args = argparse.Namespace(all_default_adapters=False, adapter=["<home>", "<home>/AGENTS.md"])
    _case.assertTrue(
        adapter_args(args, Path("/tmp")) == ["--adapter", "<home>", "--adapter", "<home>/AGENTS.md"],
        "<home> notation should pass through",
    )


def make_fake_agentos(root: Path) -> None:
    (root / "os" / "playbook").mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "os" / "skills" / "mirror-skills" / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "os" / "automations").mkdir(parents=True, exist_ok=True)
    (root / "personal" / "os" / "automations").mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (root / "os" / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    (root / "os" / "playbook" / "PERSONAL_OVERLAY.md").write_text("# Personal Overlay\n", encoding="utf-8")
    (root / "os" / "automations" / "AUTOMATIONS.md").write_text("# Automations\n", encoding="utf-8")
    (root / "personal" / "os" / "automations" / "AUTOMATIONS.md").write_text("# Private Automations\n", encoding="utf-8")
    (root / "os" / "playbook" / "GETTING_STARTED.md").write_text(
        "# Getting Started\n\n"
        "## Starter Files\n\n"
        "- `personal/os/identity/USER.md`\n"
        "- `personal/os/context/TOOLS.md`\n",
        encoding="utf-8",
    )
    (root / "scripts" / "install_global_agent_instructions.py").write_text(
        "print('[OK] ok global - managed block current')\n",
        encoding="utf-8",
    )
    (root / "os" / "skills" / "mirror-skills" / "scripts" / "mirror_skills.py").write_text(
        "import json\n"
        "print(json.dumps([{\n"
        "  'name': 'example-skill',\n"
        "  'source_kind': 'core',\n"
        "  'status': 'in-sync',\n"
        "  'canonical_source': 'os/skills/example-skill/SKILL.md',\n"
        "  'mirror_path': 'mirror/example-skill',\n"
        "  'missing_files': [],\n"
        "  'changed_files': [],\n"
        "  'extra_files': [],\n"
        "  'notes': []\n"
        "}]))\n",
        encoding="utf-8",
    )


def minimal_env(home: Path) -> dict[str, str]:
    home.mkdir(parents=True, exist_ok=True)
    env = {
        "HOME": str(home),
        "PATH": os.environ.get("PATH", ""),
    }
    if "SYSTEMROOT" in os.environ:
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    return env


def result_named(report: DoctorReport, name: str) -> CheckResult:
    for result in report.results:
        if result.name == name:
            return result
    raise AssertionError(f"missing result {name!r}")

if __name__ == "__main__":
    raise SystemExit(run_self_tests())
