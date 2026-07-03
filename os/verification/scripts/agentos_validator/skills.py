"""Skill manifest and skill frontmatter checks for AgentOS validation."""

from __future__ import annotations

from .common import *


class SkillValidator(ValidatorDelegate):
    def check_skills_manifest_consistency(self) -> None:
        check = "skills manifest consistency"
        manifest_path = self.root / "os/skills/MANIFEST.md"
        manifest = self.read_text(manifest_path, check)
        if not manifest:
            return

        self.check_skill_manifest_headings(manifest, manifest_path, check)
        entry_sections = self.skill_manifest_entry_sections(manifest)
        entries: dict[str, str] = {}
        seen_entry_names: set[str] = set()
        for skill_name, section, line_no in entry_sections:
            if skill_name in seen_entry_names:
                self.add_error(
                    check,
                    f"{self.display_path(manifest_path)}:{line_no}",
                    f"duplicate manifest entry for exported skill {skill_name!r}",
                )
                continue
            seen_entry_names.add(skill_name)
            entries[skill_name] = section
        self.check_skill_manifest_summary_count(manifest, manifest_path, len(entries), check)

        for forbidden in [
            "- Installed mirror:",
            "- Mirror state:",
            "Installed harness mirrors tracked",
            "Mirror state checked",
        ]:
            if forbidden in manifest:
                self.add_error(
                    check,
                    manifest_path,
                    f"manifest records legacy machine-local installed-skill state: {forbidden}",
                )

        for skill_name, section in sorted(entries.items()):
            fields = {
                "Canonical source": self.extract_field(section, "Canonical source"),
                "Export group": self.extract_field(section, "Export group"),
                "Export status": self.extract_field(section, "Export status"),
                "Summary": self.extract_field(section, "Summary"),
            }
            canonical = fields["Canonical source"]

            for field_name in REQUIRED_SKILL_MANIFEST_FIELDS:
                if self.skill_manifest_field_count(section, field_name) > 1:
                    self.add_error(
                        check,
                        manifest_path,
                        f"{skill_name}: duplicate {field_name}",
                    )

            for field_name, value in fields.items():
                if not value:
                    self.add_error(check, manifest_path, f"{skill_name}: missing {field_name}")
                elif field_name != "Canonical source":
                    self.check_skill_manifest_field_value(skill_name, field_name, value, manifest_path, check)

            self.check_skill_manifest_export_semantics(skill_name, fields, manifest_path, check)

            if canonical:
                canonical_path = self.managed_relative_path(
                    canonical,
                    check,
                    manifest_path,
                    f"{skill_name}: Canonical source",
                )
                if not canonical_path:
                    continue
                if canonical_path.name != "SKILL.md":
                    self.add_error(
                        check,
                        manifest_path,
                        f"{skill_name}: exported canonical source must be a SKILL.md file: {canonical}",
                    )
                source_problem = self.no_follow_path_problem(
                    canonical_path,
                    expected_kind="file",
                    allow_missing=False,
                )
                if source_problem:
                    self.add_error(
                        check,
                        manifest_path,
                        f"{skill_name}: canonical source is missing or unsafe: {canonical} ({source_problem})",
                    )
                else:
                    frontmatter = self.parse_skill_frontmatter(
                        canonical_path,
                        self.read_text(canonical_path, check),
                        check,
                    )
                    if frontmatter and frontmatter.get("name") != skill_name:
                        self.add_error(
                            check,
                            canonical_path,
                            f"exported skill frontmatter.name must match manifest entry {skill_name!r}",
                        )

        self.checked.append(check)

    def check_skill_manifest_summary_count(
        self,
        manifest: str,
        manifest_path: Path,
        expected_count: int,
        check: str,
    ) -> None:
        match = re.search(r"^- Exported Core skills:\s*(\d+)\.\s*$", manifest, re.MULTILINE)
        if not match:
            self.add_error(check, manifest_path, "missing exported Core skills summary count")
            return
        actual_count = int(match.group(1))
        if actual_count != expected_count:
            self.add_error(
                check,
                manifest_path,
                f"exported Core skills summary count is {actual_count}, expected {expected_count}",
            )

    def check_skill_manifest_headings(self, manifest: str, manifest_path: Path, check: str) -> None:
        for match in re.finditer(r"^###\s+(.+?)\s*$", manifest, re.MULTILINE):
            line = match.group(0)
            if SKILL_HEADING_RE.fullmatch(line):
                continue
            self.add_error(
                check,
                f"{self.display_path(manifest_path)}:{self.line_number_for_offset(manifest, match.start())}",
                "manifest skill heading must use exact shape: ### `skill-name`",
            )

    def line_number_for_offset(self, text: str, offset: int) -> int:
        return text.count("\n", 0, offset) + 1

    def skill_manifest_entry_sections(self, manifest: str) -> list[tuple[str, str, int]]:
        matches = list(SKILL_HEADING_RE.finditer(manifest))
        entries: list[tuple[str, str, int]] = []
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(manifest)
            entries.append(
                (match.group(1), manifest[start:end], self.line_number_for_offset(manifest, match.start()))
            )
        return entries

    def skill_manifest_entries(self, manifest: str) -> dict[str, str]:
        entries: dict[str, str] = {}
        for skill_name, section, _line_no in self.skill_manifest_entry_sections(manifest):
            entries[skill_name] = section
        return entries

    def skill_manifest_field_count(self, section: str, field_name: str) -> int:
        pattern = re.compile(rf"^- {re.escape(field_name)}:\s*.*$", re.MULTILINE)
        return len(pattern.findall(section))

    def check_skill_manifest_field_value(
        self,
        skill_name: str,
        field_name: str,
        value: str,
        manifest_path: Path,
        check: str,
    ) -> None:
        normalized = self.normalize_skill_manifest_value(value)
        if normalized in PLACEHOLDER_SKILL_MANIFEST_VALUES:
            self.add_error(check, manifest_path, f"{skill_name}: {field_name} uses placeholder value {value!r}")

    def check_skill_manifest_export_semantics(
        self,
        skill_name: str,
        fields: dict[str, str | None],
        manifest_path: Path,
        check: str,
    ) -> None:
        export_status = fields.get("Export status")
        if export_status:
            normalized_status = self.normalize_skill_manifest_value(export_status)
            if normalized_status not in ALLOWED_SKILL_EXPORT_STATUSES:
                allowed = ", ".join(sorted(ALLOWED_SKILL_EXPORT_STATUSES))
                self.add_error(
                    check,
                    manifest_path,
                    f"{skill_name}: Export status must be one of {allowed}; got {export_status!r}",
                )

    def normalize_skill_manifest_value(self, value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().strip(".").lower())

    def skill_manifest_mutability_level(self, value: str) -> str:
        normalized = self.normalize_skill_manifest_value(value)
        for level in sorted(ALLOWED_SKILL_MUTABILITY_LEVELS, key=len, reverse=True):
            if normalized == level or normalized.startswith((f"{level}:", f"{level};", f"{level}.", f"{level} ")):
                return level
        return normalized.split(":", maxsplit=1)[0].split(";", maxsplit=1)[0].strip()

    def discover_skill_files(self) -> dict[str, Path]:
        skills_dir = self.root / "os/skills"
        skills: dict[str, Path] = {}
        for path in skills_dir.glob("*.md"):
            if path.name in {"MANIFEST.md", "ORCHESTRATION_LOOPS.md", "README.md", "SKILL_CONTRACT.md"}:
                continue
            if path.name.endswith(".template.md"):
                continue
            skills[path.stem] = path
        for path in skills_dir.glob("*/SKILL.md"):
            skills[path.parent.name] = path
        return skills

    def check_skill_frontmatter(self) -> None:
        check = "skill frontmatter"
        for skill_name, path in sorted(self.discover_skill_files().items()):
            text = self.read_text(path, check)
            if not text:
                continue
            frontmatter = self.parse_skill_frontmatter(path, text, check)
            if frontmatter is None:
                continue

            name = frontmatter.get("name")
            if name is None:
                self.add_error(check, path, "frontmatter.name is required")
            elif name != skill_name:
                self.add_error(
                    check,
                    path,
                    f"frontmatter.name must match canonical skill identifier {skill_name!r}; got {name!r}",
                )

            description = frontmatter.get("description")
            if description is None:
                self.add_error(check, path, "frontmatter.description is required")
            elif not description.strip():
                self.add_error(check, path, "frontmatter.description must be a non-empty string")

        self.checked.append(check)

    def parse_skill_frontmatter(self, path: Path, text: str, check: str) -> dict[str, str] | None:
        """Parse the documented AgentOS skill-frontmatter subset.

        This intentionally is not a YAML parser. Core skill frontmatter supports
        only a leading `---` block containing one-line scalar `key: value` pairs.
        Unsupported YAML features fail closed so the validator stays portable and
        does not grow into an ad hoc partial YAML implementation.
        """
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            self.add_error(check, path, "frontmatter block is required at the start of the file")
            return None

        end_index: int | None = None
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                end_index = index
                break
        if end_index is None:
            self.add_error(check, path, "frontmatter closing delimiter is required")
            return None

        fields: dict[str, str] = {}
        for offset, raw_line in enumerate(lines[1:end_index], start=2):
            line = raw_line.strip()
            if not line or ":" not in line:
                self.add_error(
                    check,
                    f"{self.display_path(path)}:{offset}",
                    "frontmatter uses unsupported syntax; expected one-line 'field: value'",
                )
                continue

            raw_key, _, raw_value = line.partition(":")
            key = raw_key.strip()
            value = raw_value.strip()
            field = f"frontmatter.{key or '<missing>'}"
            if not SKILL_FRONTMATTER_KEY_RE.fullmatch(key):
                self.add_error(
                    check,
                    f"{self.display_path(path)}:{offset}",
                    f"{field} has unsupported field name syntax",
                )
                continue
            if key in fields:
                self.add_error(check, f"{self.display_path(path)}:{offset}", f"frontmatter.{key} is duplicated")
                continue
            if not value:
                fields[key] = ""
                continue
            if value in {"|", ">", "|-", ">-", "|+", ">+"} or value.startswith(("- ", "[", "{")):
                self.add_error(
                    check,
                    f"{self.display_path(path)}:{offset}",
                    f"frontmatter.{key} must be a one-line scalar string",
                )
                fields[key] = value
                continue

            parsed_value = self.parse_skill_frontmatter_scalar(path, offset, key, value, check)
            if parsed_value is not None:
                fields[key] = parsed_value
            else:
                fields[key] = value

        return fields

    def parse_skill_frontmatter_scalar(
        self,
        path: Path,
        line_no: int,
        key: str,
        value: str,
        check: str,
    ) -> str | None:
        if value[0] in {"'", '"'}:
            quote = value[0]
            if len(value) < 2 or value[-1] != quote:
                self.add_error(
                    check,
                    f"{self.display_path(path)}:{line_no}",
                    f"frontmatter.{key} quoted string is not closed",
                )
                return None
            return value[1:-1]

        if value[-1] in {"'", '"'}:
            self.add_error(
                check,
                f"{self.display_path(path)}:{line_no}",
                f"frontmatter.{key} quoted string is not opened",
            )
            return None
        if ": " in value:
            self.add_error(
                check,
                f"{self.display_path(path)}:{line_no}",
                f"frontmatter.{key} contains an unquoted colon; quote the scalar string",
            )
            return None
        return value

    def extract_field(self, section: str, field_name: str) -> str | None:
        pattern = re.compile(rf"^- {re.escape(field_name)}:\s*(.*)$", re.MULTILINE)
        match = pattern.search(section)
        if not match:
            return None
        value = match.group(1).strip()
        code_span = re.fullmatch(r"`([^`]+)`\.?", value)
        if code_span:
            return code_span.group(1)
        return value.rstrip(".").strip()

    def managed_relative_path(self, raw_path: str, check: str, source: Path, label: str) -> Path | None:
        path = Path(raw_path)
        if path.is_absolute():
            self.add_error(check, source, f"{label} must be root-relative, not absolute: {raw_path}")
            return None
        if raw_path.startswith("~"):
            self.add_error(check, source, f"{label} must be root-relative, not home-relative: {raw_path}")
            return None
        if ".." in path.parts:
            self.add_error(check, source, f"{label} must not contain parent-directory segments: {raw_path}")
            return None
        return self.root / path

    def check_full_skill_contract(self, skill_name: str, path: Path, check: str) -> None:
        text = self.read_text(path, check)
        required_needles = [
            "Inputs:",
            "Output artifact:",
            "Mutability:",
            "Tools and connectors:",
            "Safety:",
            "Verification",
        ]
        for needle in required_needles:
            self.require_contains(text, needle, check, path, f"{skill_name} full contract field {needle}")
        if "Workflow Phases" not in text and "Phases:" not in text:
            self.add_error(check, path, f"{skill_name}: full contract missing workflow phases")
        if "Quality Bar" not in text and "Quality" not in text:
            self.add_error(check, path, f"{skill_name}: full contract missing quality bar")
        if "File Conventions" not in text and "Filing" not in text:
            self.add_error(check, path, f"{skill_name}: full contract missing filing rules")


def write_fixture_skill(root: Path, skill_name: str, body: str = "# Fixture\n") -> None:
    skill_file = root / "os/skills" / skill_name / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(
        f"---\nname: {skill_name}\ndescription: Fixture skill.\n---\n\n{body}",
        encoding="utf-8",
    )


def run_self_test(harness) -> None:
    canonical_escape_root = harness.root / "skills_canonical_escape_fixture"
    (canonical_escape_root / "os/skills").mkdir(parents=True)
    (canonical_escape_root / "personal").mkdir()
    (canonical_escape_root / "os/skills/MANIFEST.md").write_text(
        "# Skills\n\n"
        "## Summary\n\n"
        "- Exported Core skills: 1.\n\n"
        "## Exported Skills\n\n"
        "### `escape`\n\n"
        "- Canonical source: `/agentos-fixture-outside/SKILL.md`\n"
        "- Export group: fixture.\n"
        "- Export status: exported.\n"
        "- Summary: Fixture export.\n",
        encoding="utf-8",
    )
    canonical_escape_validator = harness.validator(canonical_escape_root)
    canonical_escape_validator.check_skills_manifest_consistency()

    malformed_manifest_root = harness.root / "skills_malformed_manifest_fixture"
    (malformed_manifest_root / "os/skills").mkdir(parents=True)
    for skill_name in ("duplicate", "malformed-heading", "directory-source"):
        write_fixture_skill(malformed_manifest_root, skill_name)
    (malformed_manifest_root / "os/skills/MANIFEST.md").write_text(
        "# Skills\n\n"
        "## Summary\n\n"
        "- Exported Core skills: 4.\n\n"
        "## Exported Skills\n\n"
        "### `duplicate`\n\n"
        "- Canonical source: `os/skills/duplicate/SKILL.md`\n"
        "- Export group: fixture.\n"
        "- Export group: duplicate.\n"
        "- Export status: exported.\n"
        "- Summary: Fixture export.\n\n"
        "### `duplicate`\n\n"
        "- Canonical source: `os/skills/duplicate/SKILL.md`\n"
        "- Export group: fixture.\n"
        "- Export status: exported.\n"
        "- Summary: Fixture export.\n\n"
        "### malformed-heading\n\n"
        "- Canonical source: `os/skills/malformed-heading/SKILL.md`\n"
        "- Export group: fixture.\n"
        "- Export status: exported.\n"
        "- Summary: Fixture export.\n\n"
        "### `directory-source`\n\n"
        "- Canonical source: `os/skills/directory-source`\n"
        "- Export group: fixture.\n"
        "- Export status: exported.\n"
        "- Summary: Fixture export.\n",
        encoding="utf-8",
    )
    malformed_manifest_validator = harness.validator(malformed_manifest_root)
    malformed_manifest_validator.check_skills_manifest_consistency()

    semantic_manifest_root = harness.root / "skills_semantic_manifest_fixture"
    (semantic_manifest_root / "os/skills").mkdir(parents=True)
    for skill_name in ("bad-status", "placeholder", "unlisted-draft"):
        write_fixture_skill(semantic_manifest_root, skill_name)
    (semantic_manifest_root / "os/skills/ORCHESTRATION_LOOPS.md").write_text(
        "# Orchestration Loops\n\nStatus: convention fixture.\n",
        encoding="utf-8",
    )
    (semantic_manifest_root / "os/skills/MANIFEST.md").write_text(
        "# Skills\n\n"
        "## Summary\n\n"
        "- Exported Core skills: 3.\n\n"
        "## Exported Skills\n\n"
        "### `bad-status`\n\n"
        "- Canonical source: `os/skills/bad-status/SKILL.md`\n"
        "- Export group: fixture.\n"
        "- Export status: experimental.\n"
        "- Summary: Fixture export.\n\n"
        "### `placeholder`\n\n"
        "- Canonical source: `os/skills/placeholder/SKILL.md`\n"
        "- Export group: fixture.\n"
        "- Export status: exported.\n"
        "- Summary: none\n",
        encoding="utf-8",
    )
    semantic_manifest_validator = harness.validator(semantic_manifest_root)
    semantic_manifest_validator.check_skills_manifest_consistency()

    frontmatter_root = harness.root / "skills_frontmatter_fixture"
    missing_frontmatter = frontmatter_root / "os/skills/missing-frontmatter/SKILL.md"
    missing_frontmatter.parent.mkdir(parents=True)
    missing_frontmatter.write_text("# Missing Frontmatter\n", encoding="utf-8")
    write_fixture_skill(frontmatter_root, "wrong-name")
    (frontmatter_root / "os/skills/wrong-name/SKILL.md").write_text(
        "---\nname: other-name\ndescription: Present description.\n---\n# Wrong Name\n",
        encoding="utf-8",
    )
    (frontmatter_root / "os/skills/bad-colon").mkdir(parents=True)
    (frontmatter_root / "os/skills/bad-colon/SKILL.md").write_text(
        "---\nname: bad-colon\ndescription: Needs quote: because colon-space is outside the subset.\n---\n# Bad Colon\n",
        encoding="utf-8",
    )
    (frontmatter_root / "os/skills/list-value").mkdir(parents=True)
    (frontmatter_root / "os/skills/list-value/SKILL.md").write_text(
        "---\nname: list-value\ndescription: [unsupported]\n---\n# List Value\n",
        encoding="utf-8",
    )
    (frontmatter_root / "os/skills/empty-description").mkdir(parents=True)
    (frontmatter_root / "os/skills/empty-description/SKILL.md").write_text(
        "---\nname: empty-description\ndescription:\n---\n# Empty Description\n",
        encoding="utf-8",
    )
    (frontmatter_root / "os/skills/PERSONAL_OVERLAY_MANIFEST.template.md").write_text(
        "# Personal Overlay Skills Manifest\n\nStatus: template.\n",
        encoding="utf-8",
    )
    (frontmatter_root / "os/skills/ORCHESTRATION_LOOPS.md").write_text(
        "# Orchestration Loops\n\nStatus: convention fixture.\n",
        encoding="utf-8",
    )
    frontmatter_validator = harness.validator(frontmatter_root)
    frontmatter_validator.check_skill_frontmatter()

    harness.expect(
        "skills rejects absolute canonical source",
        any("Canonical source must be root-relative" in error.message for error in canonical_escape_validator.errors),
    )
    harness.expect(
        "skills rejects malformed manifest headings and duplicates",
        any("manifest skill heading must use exact shape" in error.message for error in malformed_manifest_validator.errors)
        and any("duplicate manifest entry for exported skill 'duplicate'" in error.message for error in malformed_manifest_validator.errors)
        and any("duplicate Export group" in error.message for error in malformed_manifest_validator.errors)
        and any("canonical source is missing or unsafe" in error.message for error in malformed_manifest_validator.errors),
    )
    harness.expect(
        "skills rejects semantic manifest drift",
        any("exported Core skills summary count is 3, expected 2" in error.message for error in semantic_manifest_validator.errors)
        and any("bad-status: Export status must be one of" in error.message for error in semantic_manifest_validator.errors)
        and any("placeholder: Summary uses placeholder value 'none'" in error.message for error in semantic_manifest_validator.errors)
        and not any("unlisted-draft" in error.message and "missing from manifest" in error.message for error in semantic_manifest_validator.errors),
    )
    harness.expect(
        "skills rejects unsupported frontmatter",
        any("frontmatter block is required" in error.message for error in frontmatter_validator.errors)
        and any("frontmatter.name must match canonical skill identifier" in error.message for error in frontmatter_validator.errors)
        and any("frontmatter.description contains an unquoted colon" in error.message for error in frontmatter_validator.errors)
        and any("frontmatter.description must be a one-line scalar string" in error.message for error in frontmatter_validator.errors)
        and any("frontmatter.description must be a non-empty string" in error.message for error in frontmatter_validator.errors)
        and not any(error.path == "os/skills/PERSONAL_OVERLAY_MANIFEST.template.md" for error in frontmatter_validator.errors),
    )
    harness.expect(
        "skills ignores top-level convention docs",
        not any(error.path == "os/skills/ORCHESTRATION_LOOPS.md" for error in semantic_manifest_validator.errors)
        and not any(error.path == "os/skills/ORCHESTRATION_LOOPS.md" for error in frontmatter_validator.errors),
    )
    harness.record(
        canonical_escape_validator,
        malformed_manifest_validator,
        semantic_manifest_validator,
        frontmatter_validator,
    )
