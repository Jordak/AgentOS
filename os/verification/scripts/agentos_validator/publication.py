"""Publication, Personal Overlay, and privacy checks for AgentOS validation."""

from __future__ import annotations

from .common import *
from .common import _bootstrap_lexical_absolute


class PublicationValidator(ValidatorDelegate):
    def run_publication_precheck_checks(self) -> None:
        self.context.managed_symlinks.check_managed_symlinks()
        if self.has_errors_for("managed symlink policy"):
            return
        self.check_git_publication_source_set()
        self.check_private_overlay_files_are_ignored()
        self.check_personal_overlay_ignore_rules()
        self.check_personal_overlay_tracking(allow_private_files=True)
        self.check_core_private_markers()
        self.check_secret_like_tokens()
        self.checked.append("publication precheck")

    def run_public_export_validation_checks(self, export_root: Path) -> None:
        self.context.root = _bootstrap_lexical_absolute(export_root)
        root_problem = self.root_path_problem()
        if root_problem:
            self.add_error("public export allowlist", self.root, f"public export root is unsafe: {root_problem}")
            self.checked.append("public export allowlist")
            self.checked.append("public export validation")
            return
        self.check_no_git_directory()
        self.check_public_export_required_support_files()
        self.check_public_export_allowlist()
        self.check_personal_overlay_ignore_file_rules()
        self.check_personal_overlay_tracking(allow_private_files=False)
        self.check_core_private_markers()
        self.check_secret_like_tokens()
        self.check_no_private_generated_outputs()
        self.checked.append("public export validation")

    def check_no_git_directory(self) -> None:
        check = "no git history"
        if (self.root / ".git").exists():
            self.add_error(check, self.root / ".git", "public export must not contain git history")
        self.checked.append(check)

    def check_public_export_required_support_files(self) -> None:
        check = "public export required support"
        for rel in PUBLIC_EXPORT_REQUIRED_SUPPORT_FILES:
            path = self.root / rel
            problem = self.no_follow_path_problem(
                path,
                expected_kind="file",
                allow_missing=False,
            )
            if problem:
                self.add_error(check, path, f"required support file is missing or unsafe: {problem}")
        self.checked.append(check)

    def check_public_export_allowlist(self) -> None:
        check = "public export allowlist"
        for path in sorted(self.root.rglob("*")):
            rel = path.relative_to(self.root)
            if path.is_dir() and not path.is_symlink():
                continue
            if path.is_symlink():
                self.add_error(check, rel.as_posix(), "public export contains a symbolic link")
                continue
            if not path.is_file():
                continue
            if any(part in PUBLIC_EXPORT_EXCLUDED_DIRS for part in rel.parts):
                self.add_error(check, path, "public export contains an excluded path")
                continue
            if len(rel.parts) == 1:
                if rel.as_posix() not in PUBLIC_EXPORT_ROOT_FILES:
                    self.add_error(check, path, "root file is not allowlisted for public export")
                continue
            if rel.parts[0] not in PUBLIC_EXPORT_ROOT_DIRS:
                self.add_error(check, path, "top-level directory is not allowlisted for public export")
                continue
            if rel.name == ".gitkeep":
                reason = gitkeep_file_reason(path)
                if reason:
                    self.add_error(check, path, reason)
                    continue
            reason = publication_path_reason(rel)
            if reason:
                self.add_error(check, path, reason)

        self.checked.append(check)

    def check_git_publication_source_set(self) -> None:
        check = "git publication source set"
        if not (self.root / ".git").exists():
            self.add_error(check, self.root / ".git", "publication precheck requires a git working tree")
            self.checked.append(check)
            return

        result = self.run_git(["ls-files", "-z"])
        if result.returncode != 0:
            self.add_error(check, self.root, f"could not list tracked files: {result.stderr.strip()}")
            self.checked.append(check)
            return

        missing_tracked: list[str] = []
        for raw_path in result.stdout.split("\0"):
            if not raw_path:
                continue
            rel = Path(raw_path)
            path = self.root / rel
            rel_text = rel.as_posix()
            if path.is_symlink():
                self.add_error(
                    check,
                    rel_text,
                    "tracked file is a symbolic link; public export rejects Git-visible symlinks",
                )
                continue
            if not path.exists():
                missing_tracked.append(rel_text)
                continue
            self.check_publishable_path(check, rel, tracked=True)

        untracked = self.git_paths(["ls-files", "--others", "--exclude-standard"])
        for rel in untracked:
            path = self.root / rel
            if path.is_symlink():
                self.add_error(
                    check,
                    rel.as_posix(),
                    "untracked unignored file is a symbolic link; public export rejects Git-visible symlinks",
                )
                continue
            self.check_publishable_path(check, rel, tracked=False)

        if missing_tracked:
            sample = ", ".join(missing_tracked[:8])
            if len(missing_tracked) > 8:
                sample += f", ... ({len(missing_tracked)} total)"
            self.add_error(
                check,
                self.root,
                f"tracked files are deleted in the working tree; stage deletions before a publication commit: {sample}",
            )

        self.checked.append(check)

    def check_publishable_path(self, check: str, rel: Path, tracked: bool) -> None:
        rel_text = rel.as_posix()
        label = "tracked file" if tracked else "untracked unignored file"
        if any(part in PUBLIC_EXPORT_EXCLUDED_DIRS for part in rel.parts):
            self.add_error(check, rel_text, f"{label} is in an excluded path")
            return
        if rel.parts[0] == "personal":
            if not is_personal_overlay_skeleton_path(rel):
                self.add_error(
                    check,
                    rel_text,
                    f"{label} under personal/ must be an allowlisted public-safe skeleton .gitkeep",
                )
                return
            reason = personal_overlay_skeleton_file_reason(self.root / rel)
            if reason:
                self.add_error(check, rel_text, f"{label} {reason}")
            return
        if len(rel.parts) == 1:
            if rel_text not in PUBLIC_EXPORT_ROOT_FILES:
                self.add_error(check, rel_text, f"{label} is not an allowlisted root file")
            return
        if rel.parts[0] not in PUBLIC_EXPORT_ROOT_DIRS:
            self.add_error(check, rel_text, f"{label} is not under an allowlisted top-level directory")
            return
        if rel.name == ".gitkeep":
            reason = gitkeep_file_reason(self.root / rel)
            if reason:
                self.add_error(check, rel_text, f"{label} {reason}")
                return
        reason = publication_path_reason(rel)
        if reason:
            self.add_error(check, rel_text, f"{label} {reason}")
            return

    def check_private_overlay_files_are_ignored(self) -> None:
        check = "private overlay ignore coverage"
        personal = self.root / "personal"
        personal_problem = self.personal_overlay_root_problem(personal)
        if personal_problem:
            self.add_error(check, personal, personal_problem)
            self.checked.append(check)
            return

        checked_private_files = 0
        for path in self.iter_personal_overlay_files(personal, check):
            rel_path = path.relative_to(self.root)
            if path.name == ".gitkeep" and is_personal_overlay_skeleton_path(rel_path):
                continue
            checked_private_files += 1
            rel = rel_path.as_posix()
            tracked = self.run_git(["ls-files", "--error-unmatch", "--", rel])
            if tracked.returncode == 0:
                self.add_error(check, rel, "private overlay file is tracked by git")
                continue
            ignored = self.run_git(["check-ignore", "-q", "--", rel])
            if ignored.returncode != 0:
                self.add_error(check, rel, "private overlay file is not covered by .gitignore")

        self.checked.append(f"{check} ({checked_private_files} private file(s) checked)")

    def check_personal_overlay_ignore_rules(self) -> None:
        check = "personal overlay ignore rules"
        if not (self.root / ".git").exists():
            self.add_error(check, self.root / ".git", "personal overlay ignore rules require a git working tree")
            self.checked.append(check)
            return

        private_probe = Path("personal/os/agents/private-client/.gitkeep")
        if self.run_git(["check-ignore", "--no-index", "-q", "--", private_probe.as_posix()]).returncode != 0:
            self.add_error(
                check,
                private_probe.as_posix(),
                "private-specific .gitkeep paths must remain ignored; only public-safe skeleton .gitkeep paths may be unignored",
            )

        for rel_text in sorted(PERSONAL_OVERLAY_SKELETON_FILES):
            if self.run_git(["check-ignore", "--no-index", "-q", "--", rel_text]).returncode == 0:
                self.add_error(
                    check,
                    rel_text,
                    "public-safe Personal Overlay skeleton .gitkeep path must be unignored",
                )

        self.checked.append(check)

    def check_personal_overlay_ignore_file_rules(self) -> None:
        check = "personal overlay ignore file"
        gitignore = self.root / ".gitignore"
        text = self.read_text(gitignore, check)
        if not text:
            self.checked.append(check)
            return

        lines = {line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")}
        required_rules = {"personal/**/*", "!personal/**/"}
        required_rules.update(f"!{rel_text}" for rel_text in PERSONAL_OVERLAY_SKELETON_FILES)

        for rule in sorted(required_rules):
            if rule not in lines:
                self.add_error(check, gitignore, f"missing required Personal Overlay ignore rule: {rule}")

        allowed_unignore_rules = {"!personal/**/"}
        allowed_unignore_rules.update(f"!{rel_text}" for rel_text in PERSONAL_OVERLAY_SKELETON_FILES)
        for rule in sorted(line for line in lines if line.startswith("!personal/")):
            if rule not in allowed_unignore_rules:
                self.add_error(
                    check,
                    gitignore,
                    f"unexpected Personal Overlay unignore rule: {rule}",
                )

        if "!personal/**/.gitkeep" in lines:
            self.add_error(
                check,
                gitignore,
                "broad Personal Overlay .gitkeep unignore is not allowed; only public-safe skeleton .gitkeep paths may be unignored",
            )

        self.checked.append(check)

    def check_personal_overlay_tracking(self, allow_private_files: bool) -> None:
        check = "personal overlay skeleton"
        personal = self.root / "personal"
        personal_problem = self.personal_overlay_root_problem(personal)
        if personal_problem:
            self.add_error(check, personal, personal_problem)
            self.checked.append(check)
            return
        for rel_text in sorted(PERSONAL_OVERLAY_SKELETON_FILES):
            skeleton_path = self.root / rel_text
            skeleton_problem = self.no_follow_path_problem(skeleton_path)
            if skeleton_problem:
                self.add_error(check, rel_text, skeleton_problem)
                continue
            if not skeleton_path.exists():
                self.add_error(check, rel_text, "required Personal Overlay skeleton .gitkeep is missing")
                continue
            reason = personal_overlay_skeleton_file_reason(skeleton_path)
            if reason:
                self.add_error(check, skeleton_path, reason)
            if allow_private_files and (self.root / ".git").exists():
                tracked = self.run_git(["ls-files", "--error-unmatch", "--", rel_text])
                if tracked.returncode != 0:
                    self.add_error(check, rel_text, "Personal Overlay skeleton .gitkeep must be tracked by git")
        for path in self.iter_personal_overlay_files(personal, check):
            rel_text = path.relative_to(self.root).as_posix()
            if path.name == ".gitkeep":
                rel_path = path.relative_to(self.root)
                if not is_personal_overlay_skeleton_path(rel_path):
                    if allow_private_files and self.is_git_ignored(rel_path):
                        continue
                    self.add_error(
                        check,
                        path,
                        "personal overlay .gitkeep path is not in the public-safe skeleton allowlist",
                    )
                    continue
                continue
            if allow_private_files:
                continue
            self.add_error(check, path, "public export may contain only .gitkeep files under personal/")
        self.checked.append(check)

    def should_skip_publication_privacy_scan(
        self, path: Path, scan_personal_gitkeep_paths: bool = False
    ) -> bool:
        rel = path.relative_to(self.root)
        if any(part in PUBLIC_EXPORT_EXCLUDED_DIRS for part in rel.parts):
            return True
        if rel.parts[0] == "personal":
            return not (scan_personal_gitkeep_paths and path.name == ".gitkeep")
        return self.is_git_ignored(rel)

    def check_core_private_markers(self) -> None:
        check = "private marker scan"
        for path in sorted(p for p in self.root.rglob("*") if self.is_file_or_symlink(p) and ".git" not in p.parts):
            if self.should_skip_publication_privacy_scan(path, scan_personal_gitkeep_paths=True):
                continue
            rel = path.relative_to(self.root)
            rel_text = rel.as_posix()
            for marker in self.private_marker_patterns:
                if self.private_marker_match(marker, rel_text):
                    self.add_error(
                        check,
                        self.redact_private_markers(rel_text),
                        f"private marker matched path with {marker.label}",
                    )
                    break

        for path in self.iter_content_scan_files():
            if self.should_skip_publication_privacy_scan(path):
                continue
            text = self.read_text(path, check)
            for line_no, line in enumerate(text.splitlines(), start=1):
                for marker in self.private_marker_patterns:
                    if self.private_marker_match(marker, line):
                        self.add_error(
                            check,
                            f"{self.redact_private_markers(self.display_path(path))}:{line_no}",
                            f"private marker matched {marker.label}",
                        )
                        break
        self.checked.append(check)

    def check_no_private_generated_outputs(self) -> None:
        check = "private generated outputs"
        for path in self.root.rglob("*"):
            if not self.is_file_or_symlink(path) or ".git" in path.parts:
                continue
            rel = path.relative_to(self.root)
            if rel.parts[0] == "personal":
                continue
            if any(part in GENERATED_OUTPUT_PARTS for part in rel.parts):
                if "example" in path.name.lower() or ".template." in path.name:
                    continue
                self.add_error(
                    check,
                    path,
                    "generated outputs belong in personal/os/ unless sanitized as examples or templates",
                )
        self.checked.append(check)

    def check_secret_like_tokens(self) -> None:
        check = "secret-like token scan"
        for path in self.iter_content_scan_files():
            if self.should_skip_publication_privacy_scan(path):
                continue
            text = self.read_text(path, check)
            for line_no, line in enumerate(text.splitlines(), start=1):
                for label, pattern in SECRET_LIKE_PATTERNS:
                    if pattern.search(line):
                        self.add_error(
                            check,
                            f"{self.display_path(path)}:{line_no}",
                            f"found {label}",
                        )
                        break

        self.checked.append(check)


def run_self_test(harness) -> None:
    root = harness.root / "publication_fixture"
    (root / "os").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / ".github").mkdir()
    (root / ".gitignore").write_text(
        "/" + "Users" + "/private-client/cache\n!personal/**/*.md\n",
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "-C", str(root), "init"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    (root / "docs/private.csv").write_text("/" + "Users" + "/private-csv/cache\n", encoding="utf-8")
    (root / "docs/token.txt").write_text("sk-" + "fakepublicationfixture1234567890\n", encoding="utf-8")
    local_path_variants = root / "docs/local-path-variants.md"
    backslash = chr(92)
    local_path_variants.write_text(
        "\n".join(
            [
                "/" + "home" + "/private-linux-user/project/file.md",
                "/" + "tmp" + "/private-temp-artifact/run.json",
                "C:" + backslash + "Users" + backslash + "PrivateWindowsUser" + backslash + "secret.txt",
                backslash * 2 + "private-host" + backslash + "private-share" + backslash + "secret.txt",
                "$" + "HOME/private-project/file.md",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    marker_file = root / "personal/os/verification/privacy-markers.txt"
    marker_file.parent.mkdir(parents=True)
    marker_file.write_text("sensitive-client-name\n", encoding="utf-8")
    (root / "docs/sensitive_client_name.md").write_text("sanitized content\n", encoding="utf-8")
    (root / "unexpected.txt").write_text("not allowlisted\n", encoding="utf-8")
    (root / ".github/dependabot.yml").write_text("version: 2\n", encoding="utf-8")
    (root / "docs/linked.raw").symlink_to("../unexpected.txt")
    core_gitkeep = root / "os/memory/weekly-review/.gitkeep"
    core_gitkeep.parent.mkdir(parents=True)
    core_gitkeep.write_text("not empty\n", encoding="utf-8")
    disallowed_skeleton = root / "personal/os/agents/private-client/.gitkeep"
    disallowed_skeleton.parent.mkdir(parents=True)
    disallowed_skeleton.write_text("", encoding="utf-8")
    nonempty_skeleton = root / "personal/os/context/.gitkeep"
    nonempty_skeleton.parent.mkdir(parents=True, exist_ok=True)
    nonempty_skeleton.write_text("not empty\n", encoding="utf-8")
    (root / "personal/os/private.md").write_text("ignored-private\n", encoding="utf-8")

    validator = harness.validator(root)
    validator.check_no_git_directory()
    validator.check_public_export_allowlist()
    validator.check_private_overlay_files_are_ignored()
    validator.check_personal_overlay_ignore_rules()
    validator.check_personal_overlay_ignore_file_rules()
    validator.check_personal_overlay_tracking(allow_private_files=False)
    validator.check_core_private_markers()
    validator.check_secret_like_tokens()

    symlink_root = harness.root / "publication_precheck_fixture"
    (symlink_root / "os/context").mkdir(parents=True)
    (symlink_root / "os/agents/current-awareness-agent").mkdir(parents=True)
    (symlink_root / "os/reports").mkdir()
    (symlink_root / "personal").mkdir()
    (symlink_root / ".gitignore").write_text("personal/**\n", encoding="utf-8")
    (symlink_root / "os/INDEX.md").write_text("safe\n", encoding="utf-8")
    (symlink_root / "os/context/CAREER.md").write_text("private-looking filename with sanitized content\n", encoding="utf-8")
    (symlink_root / "os/agents/current-awareness-agent/JOB.md").write_text(
        "live agent fixture with sanitized content\n",
        encoding="utf-8",
    )
    nested_live_core = symlink_root / "os/context/private-client/NOTES.md"
    nested_live_core.parent.mkdir()
    nested_live_core.write_text("nested high-risk Core file with sanitized content\n", encoding="utf-8")
    (symlink_root / "os/reports/private.md").write_text("generated output with sanitized content\n", encoding="utf-8")
    core_report_gitkeep = symlink_root / "os/verification/reports/.gitkeep"
    core_report_gitkeep.parent.mkdir(parents=True)
    core_report_gitkeep.write_text("", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(symlink_root), "init"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    publication_validator = harness.validator(symlink_root)
    publication_validator.run_publication_precheck_checks()

    personal_symlink_root = harness.root / "publication_personal_symlink_fixture"
    (personal_symlink_root / "real-personal").mkdir(parents=True)
    (personal_symlink_root / "personal").symlink_to("real-personal")
    personal_root_validator = harness.validator(personal_symlink_root)
    personal_root_validator.check_private_overlay_files_are_ignored()

    nested_personal_symlink_root = harness.root / "publication_personal_nested_symlink_fixture"
    (nested_personal_symlink_root / "personal/os/skills").mkdir(parents=True)
    (nested_personal_symlink_root / "outside").mkdir()
    (nested_personal_symlink_root / ".gitignore").write_text("personal/**/*\n!personal/**/\n", encoding="utf-8")
    (nested_personal_symlink_root / "personal/os/skills/linkdir").symlink_to("../../../outside")
    subprocess.run(
        ["git", "-C", str(nested_personal_symlink_root), "init"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    nested_personal_validator = harness.validator(nested_personal_symlink_root)
    nested_personal_validator.check_private_overlay_files_are_ignored()
    nested_personal_validator.check_personal_overlay_tracking(allow_private_files=True)

    symlinked_export_target = harness.root / "publication_symlinked_export_target"
    (symlinked_export_target / "os").mkdir(parents=True)
    symlinked_export_root = harness.root / "publication_symlinked_export"
    symlinked_export_root.symlink_to(symlinked_export_target, target_is_directory=True)
    public_export_root_validator = harness.validator(root)
    public_export_root_validator.run_public_export_validation_checks(symlinked_export_root)

    missing_support_export_root = harness.root / "publication_missing_support_export"
    missing_support_export_root.mkdir()
    missing_support_validator = harness.validator(root)
    missing_support_validator.run_public_export_validation_checks(missing_support_export_root)

    harness.expect(
        "publication catches public export allowlist problems",
        any("public export must not contain git history" in error.message for error in validator.errors)
        and any("root file is not allowlisted" in error.message for error in validator.errors)
        and any("GitHub metadata outside the public-safe CI workflow allowlist" in error.message for error in validator.errors)
        and any("public export contains a symbolic link" in error.message for error in validator.errors),
    )
    harness.expect(
        "publication catches Personal Overlay rule problems",
        any("private overlay file is not covered by .gitignore" in error.message for error in validator.errors)
        and any("private-specific .gitkeep paths must remain ignored" in error.message for error in validator.errors)
        and any("unexpected Personal Overlay unignore rule" in error.message for error in validator.errors)
        and any("personal overlay .gitkeep path is not in the public-safe skeleton allowlist" in error.message for error in validator.errors),
    )
    harness.expect(
        "publication catches privacy and secret markers",
        any("private marker matched" in error.message for error in validator.errors)
        and any("found OpenAI-style secret key" in error.message for error in validator.errors),
    )
    harness.expect(
        "publication precheck catches live Core and generated output paths",
        any(error.path == "os/context/CAREER.md" and "live personal context file" in error.message for error in publication_validator.errors)
        and any(error.path == "os/agents/current-awareness-agent/JOB.md" and "live personal agents file" in error.message for error in publication_validator.errors)
        and any(error.path == "os/reports/private.md" and "generated output" in error.message for error in publication_validator.errors)
        and any(error.path == "os/context/private-client/NOTES.md" and "nested high-risk Core path" in error.message for error in publication_validator.errors)
        and any(error.path == "os/verification/reports/.gitkeep" and "generated output" in error.message for error in publication_validator.errors),
    )
    harness.expect(
        "publication rejects personal root symlink but allows ignored nested personal symlink",
        any(
            error.check == "private overlay ignore coverage"
            and error.path == "personal"
            and "must not be a symbolic link" in error.message
            for error in personal_root_validator.errors
        )
        and not any(
            error.path == "personal/os/skills/linkdir"
            and "must not be a symbolic link" in error.message
            for error in nested_personal_validator.errors
        ),
    )
    harness.expect(
        "publication rejects unsafe public export roots and missing support files",
        any(
            error.check == "public export allowlist"
            and error.path == "."
            and "public export root is unsafe" in error.message
            for error in public_export_root_validator.errors
        )
        and any(
            error.check == "public export required support"
            and error.path == "scripts/path_resolution/managed.py"
            and "required support file is missing or unsafe" in error.message
            for error in missing_support_validator.errors
        ),
    )
    harness.record(
        validator,
        publication_validator,
        personal_root_validator,
        nested_personal_validator,
        public_export_root_validator,
        missing_support_validator,
    )
