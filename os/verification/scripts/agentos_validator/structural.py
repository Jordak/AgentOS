"""Structural, routing, and benchmark checks for AgentOS validation."""

from __future__ import annotations

from .common import *


class StructuralValidator(ValidatorDelegate):
    def run_structural_checks(self) -> None:
        self.context.managed_symlinks.check_managed_symlinks()
        if self.has_errors_for("managed symlink policy"):
            return
        self.check_markdown_path_portability()
        self.check_source_map_path_health()
        self.context.skill_validator.check_skills_manifest_consistency()
        self.context.skill_validator.check_skill_frontmatter()
        self.check_agent_contract_completeness()
        self.check_automation_registry_completeness()
        self.check_resolver_reachability()
        self.check_pr_readiness_tripwire()
        self.check_guidance_benchmark_trial_workflow()
        self.check_source_routing_fixtures()
        self.check_benchmark_manifest()

    def check_markdown_path_portability(self) -> None:
        check = "markdown path portability"
        root_agents = self.root / "AGENTS.md"
        root_agents_text = self.read_text(root_agents, check)
        if root_agents_text:
            self.require_contains(
                root_agents_text,
                "Unless otherwise stated, local file paths in AgentOS Markdown are relative to",
                check,
                root_agents,
                "root-relative path convention",
            )

        root_literal = str(self.root)
        for path in sorted(self.root.rglob("*.md")):
            if path.is_symlink() or ".git" in path.parts:
                continue
            text = self.read_text(path, check)
            for line_no, line in enumerate(text.splitlines(), start=1):
                if root_literal in line:
                    self.add_error(
                        check,
                        f"{self.display_path(path)}:{line_no}",
                        "hardcodes the AgentOS checkout path; use a root-relative AgentOS path",
                    )
                if "../" in line:
                    self.add_error(
                        check,
                        f"{self.display_path(path)}:{line_no}",
                        "uses a parent-relative AgentOS path; use a root-relative path",
                    )

        self.checked.append(check)

    def check_source_map_path_health(self) -> None:
        check = "source-map path health"
        source_map = self.root / "os/context/SOURCE_MAP.md"
        text = self.read_text(source_map, check)
        if not text:
            return

        for span in CODE_SPAN_RE.findall(text):
            candidate = span.strip()
            if "://" in candidate:
                continue
            if candidate.startswith(("/", "~")):
                path = Path(candidate).expanduser()
            elif candidate.startswith("os/") or candidate in {"AGENTS.md", "CLAUDE.md", "README.md"}:
                path = self.resolve_path(candidate)
            else:
                continue
            if not path.exists():
                self.add_error(
                    check,
                    source_map,
                    f"listed local path does not exist: {candidate}",
                )

        for line_no, line in enumerate(text.splitlines(), start=1):
            if "TODO" in line:
                self.add_warning(
                    check,
                    f"{self.display_path(source_map)}:{line_no}",
                    "source map contains TODO; confirm it remains intentional",
                )

        self.checked.append(check)

    def should_validate_agent_dir(self, agent_dir: Path) -> bool:
        if (agent_dir / "JOB.md").exists() or (agent_dir / "AGENTS.md").exists():
            return True
        for path in sorted(p for p in agent_dir.rglob("*") if self.is_file_or_symlink(p)):
            rel = path.relative_to(self.root)
            if not self.is_git_ignored(rel):
                return True
        return False

    def check_agent_contract_completeness(self) -> None:
        check = "agent contract completeness"
        agents_dir = self.root / "os/agents"
        if not agents_dir.exists():
            self.add_error(check, agents_dir, "agents directory is missing")
            return

        for agent_dir in sorted(path for path in agents_dir.iterdir() if path.is_dir()):
            if not self.should_validate_agent_dir(agent_dir):
                continue
            job = agent_dir / "JOB.md"
            instructions = agent_dir / "AGENTS.md"
            job_text = self.read_text(job, check)
            instructions_text = self.read_text(instructions, check)
            combined = f"{job_text}\n{instructions_text}"

            for section in ["## Job", "## Inputs", "## Outputs", "## Cadence"]:
                self.require_contains(job_text, section, check, job, section)

            if not any(token in combined for token in ["## Boundaries", "## Safety", "## Source Discipline"]):
                self.add_error(
                    check,
                    agent_dir,
                    "missing boundaries, safety, or source-discipline guidance",
                )
            if not any(token in combined for token in ["## Verification", "## Verification Checklist", "## Quality Bar", "## Success Criteria"]):
                self.add_error(
                    check,
                    agent_dir,
                    "missing verification, quality, or success criteria guidance",
                )

        self.checked.append(check)

    def check_automation_registry_completeness(self) -> None:
        check = "automation registry completeness"
        registry_path = self.root / "os/automations/AUTOMATIONS.md"
        registry = self.read_text(registry_path, check)
        if not registry:
            return

        active = self.extract_between_headers(registry, "## Active Automations", "## Retired / Completed One-Offs")
        active_sections = self.section_map(active, level="###")
        if not active_sections and "No active Core automations." not in active:
            self.add_error(check, registry_path, "no active automation sections found")
        for name, section in active_sections.items():
            for label in [
                "Automation id:",
                "Status:",
                "Kind:",
                "Trigger:",
                "Schedule rule:",
                "Workspace:",
                "Execution environment:",
                "Model:",
                "Invocation prompt:",
                "Inputs:",
                "Output:",
                "Verification:",
            ]:
                if label not in section:
                    self.add_error(check, registry_path, f"active automation {name!r} missing {label}")
            definition = self.field_following_code_span(section, "Current Codex definition:")
            if definition and not self.resolve_machine_local_path(definition).exists():
                self.add_error(
                    check,
                    registry_path,
                    f"active automation {name!r} definition path does not exist: {definition}",
                )

        candidates = self.extract_between_headers(registry, "## Candidate Automations", "## Automation Creation Checklist")
        for name, section in self.section_map(candidates, level="###").items():
            for label in ["Purpose:", "Suggested trigger:", "Suggested output:", "Activation standard:"]:
                if label not in section:
                    self.add_error(check, registry_path, f"candidate automation {name!r} missing {label}")

        checklist = self.extract_between_headers(registry, "## Automation Creation Checklist", "## Automation Spec Template")
        for item in ["output location", "verification checklist", "external sends", "workspace path", "source map"]:
            if item not in checklist:
                self.add_error(check, registry_path, f"automation creation checklist missing {item!r}")

        self.checked.append(check)

    def extract_between_headers(self, text: str, start_header: str, end_header: str) -> str:
        start = text.find(start_header)
        if start == -1:
            return ""
        end = text.find(end_header, start + len(start_header))
        if end == -1:
            return text[start:]
        return text[start:end]

    def section_map(self, text: str, level: str) -> dict[str, str]:
        pattern = re.compile(rf"^{re.escape(level)}\s+(.+?)\s*$", re.MULTILINE)
        matches = list(pattern.finditer(text))
        sections: dict[str, str] = {}
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            sections[match.group(1)] = text[start:end]
        return sections

    def field_following_code_span(self, section: str, label: str) -> str | None:
        label_index = section.find(label)
        if label_index == -1:
            return None
        match = CODE_SPAN_RE.search(section, label_index)
        return match.group(1) if match else None

    def resolve_machine_local_path(self, path_text: str) -> Path:
        """Resolve documented machine-local path tokens while keeping docs portable."""
        if path_text.startswith("$CODEX_HOME/"):
            codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
            return codex_home / path_text.removeprefix("$CODEX_HOME/")
        return Path(os.path.expandvars(path_text)).expanduser()

    def check_resolver_reachability(self) -> None:
        check = "resolver reachability"
        resolver = self.root / "os/RESOLVER.md"
        resolver_text = self.read_text(resolver, check)
        if not resolver_text:
            return

        root_agents = self.read_text(self.root / "AGENTS.md", check)
        index = self.read_text(self.root / "os/INDEX.md", check)
        playbook = self.read_text(self.root / "os/playbook/AGENTOS_PLAYBOOK.md", check)
        self.require_contains(root_agents, "os/RESOLVER.md", check, self.root / "AGENTS.md")
        self.require_contains(index, "RESOLVER.md", check, self.root / "os/INDEX.md")
        self.require_contains(playbook, "os/RESOLVER.md", check, self.root / "os/playbook/AGENTOS_PLAYBOOK.md")

        for path in [
            self.root / "os/context/README.md",
            self.root / "os/memory/README.md",
            self.root / "os/skills/README.md",
            self.root / "os/agents/README.md",
        ]:
            if not path.exists():
                self.add_error(check, path, "directory resolver is missing")

        for span in CODE_SPAN_RE.findall(resolver_text):
            candidate = span.strip()
            if "://" in candidate:
                continue
            if not self.looks_like_local_reference(candidate):
                continue
            if candidate.startswith("personal/os/"):
                continue
            if not self.reference_exists(candidate):
                self.add_error(check, resolver, f"referenced path is not reachable: {candidate}")

        self.checked.append(check)

    def check_pr_readiness_tripwire(self) -> None:
        check = "PR readiness tripwire"
        template_path = self.root / ".github/pull_request_template.md"
        workflow_path = self.root / ".github/workflows/agentos-validation.yml"
        template = self.read_text(template_path, check)
        workflow = self.read_text(workflow_path, check)

        if template:
            for needle in [
                "Readiness evidence:",
                "Readiness verdict:",
                "GitHub issue",
                "Ready to Implement",
                "Gate Skipped",
                "os/playbook/IMPLEMENT_FEATURES.md",
            ]:
                self.require_contains(template, needle, check, template_path)

        if workflow:
            for needle in [
                "Check PR design readiness fields",
                "Readiness evidence:",
                "Readiness verdict:",
                "Ready to Implement",
                "Gate Skipped",
            ]:
                self.require_contains(workflow, needle, check, workflow_path)

        self.checked.append(check)

    def workflow_top_level_block(self, workflow: str, key: str) -> str | None:
        match = re.search(rf"(?m)^{re.escape(key)}:\s*$", workflow)
        if not match:
            return None
        start = match.end()
        next_match = re.search(r"(?m)^[A-Za-z_][A-Za-z0-9_-]*:\s*$", workflow[start:])
        end = start + next_match.start() if next_match else len(workflow)
        return workflow[start:end]

    def workflow_job_block(self, workflow: str, job_name: str) -> str | None:
        jobs = self.workflow_top_level_block(workflow, "jobs")
        if jobs is None:
            return None
        match = re.search(rf"(?m)^  {re.escape(job_name)}:\s*$", jobs)
        if not match:
            return None
        start = match.end()
        next_match = re.search(r"(?m)^  [A-Za-z0-9_-]+:\s*$", jobs[start:])
        end = start + next_match.start() if next_match else len(jobs)
        return jobs[start:end]

    def check_guidance_benchmark_trial_workflow(self) -> None:
        check = "Guidance benchmark workflow contract"
        workflow_path = self.root / ".github/workflows/guidance-benchmark-trial.yml"
        workflow = self.read_text(workflow_path, check)
        if not workflow:
            return

        for needle, label in [
            ("workflow_dispatch:", "manual dispatch trigger"),
            ("if: github.ref_name == 'main'", "main-branch job guard"),
            ("environment: guidance-benchmark-trial", "protected environment"),
            ("contents: read", "read-only default contents permission"),
            (
                "openai/codex-action@a26d2d4d8b78a694338b8e3715c3630254340b2c",
                "pinned Codex action",
            ),
            ("--harness codex", "single codex harness"),
            ("--model gpt-5.5", "single benchmark model"),
            ("--effort low", "single benchmark effort"),
            ("--judge-harness codex", "single judge harness"),
            ("--judge-model gpt-5.5", "single judge model"),
            ("--judge-effort low", "single judge effort"),
            ("--quiet", "quiet benchmark mode"),
            ('--output "$GUIDANCE_RUN_JSON"', "workflow-owned benchmark output path"),
            ("status-pr:", "status pull request job"),
            ("apply_benchmark_status_candidate.py", "status applicator"),
            ("--expected-revision", "applicator revision guard"),
            ("secrets.AGENTOS_STATUS_PR_TOKEN", "dedicated status PR token"),
            ("gh pr create", "generated status pull request"),
        ]:
            self.require_contains(workflow, needle, check, workflow_path, label)

        if re.search(r"(?m)^\s+(push|pull_request|schedule):\s*$", workflow):
            self.add_error(check, workflow_path, "must stay manual-only; do not add push, pull_request, or schedule triggers")
        if re.search(r"(?m)^\s+inputs:\s*$", workflow):
            self.add_error(check, workflow_path, "must not define custom workflow_dispatch inputs")

        top_permissions = self.workflow_top_level_block(workflow, "permissions")
        if top_permissions is None:
            self.add_error(check, workflow_path, "must define top-level read-only permissions")
        else:
            if "  contents: read" not in top_permissions:
                self.add_error(check, workflow_path, "top-level permissions must include contents: read")
            if re.search(r"(?m)^  (contents|pull-requests|issues): write\s*$", top_permissions):
                self.add_error(check, workflow_path, "top-level permissions must not grant write access")

        guidance_job = self.workflow_job_block(workflow, "guidance")
        if guidance_job is None:
            self.add_error(check, workflow_path, "guidance job is missing")
        else:
            for needle, label in [
                ("environment: guidance-benchmark-trial", "guidance protected environment"),
                ("permissions:", "guidance job permissions"),
                ("contents: read", "guidance read-only contents permission"),
            ]:
                if needle not in guidance_job:
                    self.add_error(check, workflow_path, f"guidance job missing {label}")
            if re.search(r"(?m)^\s+(contents|pull-requests|issues): write\s*$", guidance_job):
                self.add_error(check, workflow_path, "guidance job must not grant write permissions")

        status_pr_job = self.workflow_job_block(workflow, "status-pr")
        if status_pr_job is None:
            self.add_error(check, workflow_path, "status-pr job is missing")
        else:
            for needle, label in [
                ("needs: guidance", "guidance dependency"),
                ("environment: guidance-benchmark-trial", "status-pr protected environment"),
                ("permissions:", "status-pr job permissions"),
                ("contents: read", "status-pr read-only contents permission"),
                ("secrets.AGENTOS_STATUS_PR_TOKEN", "dedicated status PR token"),
                ("STATUS_PR_TOKEN", "status PR token environment"),
                ("github.ref_name == 'main'", "main guard"),
                ("needs.guidance.outputs.refresh_status == '0'", "refresh success guard"),
                ("needs.guidance.outputs.public_refresh_candidate != ''", "nonempty public candidate guard"),
            ]:
                if needle not in status_pr_job:
                    self.add_error(check, workflow_path, f"status-pr job missing {label}")
            if re.search(r"(?m)^\s+(contents|pull-requests|issues): write\s*$", status_pr_job):
                self.add_error(check, workflow_path, "status-pr job must keep repository GITHUB_TOKEN read-only")

        for forbidden, message in [
            ("actions/upload-artifact", "must not upload benchmark artifacts"),
            ("--harness all", "must not allow all harnesses in the v1 workflow"),
            ("HEAD:refs/heads/main", "must not push generated status updates directly to main"),
            ("issues: write", "must not grant issue write permission"),
        ]:
            if forbidden in workflow:
                self.add_error(check, workflow_path, message)

        if re.search(r"(?m)^\s+(contents|pull-requests|issues): write\s*$", workflow):
            self.add_error(check, workflow_path, "must keep repository GITHUB_TOKEN permissions read-only")

        self.checked.append(check)

    def check_source_routing_fixtures(self) -> None:
        check = "source routing fixtures"
        fixture_path = self.root / "os/verification/source-routing/fixtures.json"
        raw = self.read_text(fixture_path, check)
        if not raw:
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            self.add_error(check, fixture_path, f"invalid JSON: {error}")
            return

        fixtures = data.get("fixtures")
        if not isinstance(fixtures, list) or not fixtures:
            self.add_error(check, fixture_path, "fixtures must be a non-empty list")
            return

        required_categories = {
            "current-awareness brief",
            "portfolio gap scan",
            "morning brief",
            "weekly review",
            "skill update",
            "skillify workflow",
            "github issue breakdown",
            "mapped-project handoff",
            "safety-sensitive external action",
        }
        seen_categories: set[str] = set()

        resolver_text = self.read_text(self.root / "os/RESOLVER.md", check)
        source_map_text = self.read_text(self.root / "os/context/SOURCE_MAP.md", check)

        for fixture in fixtures:
            if not isinstance(fixture, dict):
                self.add_error(check, fixture_path, "fixture entries must be objects")
                continue
            fixture_id = fixture.get("id")
            prompt = fixture.get("prompt")
            category = fixture.get("category")
            expected = fixture.get("expected", {})
            evidence = fixture.get("evidence", [])
            if not fixture_id:
                self.add_error(check, fixture_path, "fixture missing id")
                continue
            if not prompt:
                self.add_error(check, fixture_path, f"{fixture_id}: missing prompt")
            if category:
                seen_categories.add(category)
            if not isinstance(expected, dict) or not expected:
                self.add_error(check, fixture_path, f"{fixture_id}: missing expected route")
                continue
            if not isinstance(evidence, list) or not evidence:
                self.add_error(check, fixture_path, f"{fixture_id}: missing evidence list")

            self.check_expected_route(check, fixture_path, fixture_id, expected, resolver_text, source_map_text)
            self.check_fixture_evidence(check, fixture_path, fixture_id, expected, evidence)

        missing_categories = sorted(required_categories - seen_categories)
        if missing_categories:
            self.add_error(
                check,
                fixture_path,
                f"missing required fixture categories: {', '.join(missing_categories)}",
            )

        self.checked.append(check)

    def check_benchmark_manifest(self) -> None:
        check = "benchmark manifest completeness"
        manifest_path = self.root / "os/verification/BENCHMARKS.json"
        raw = self.read_text(manifest_path, check)
        if not raw:
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            self.add_error(check, manifest_path, f"invalid JSON: {error}")
            self.checked.append(check)
            return

        if type(data.get("version")) is not int or data.get("version") < 1:
            self.add_error(check, manifest_path, "version must be a positive integer")

        benchmarks = data.get("benchmarks")
        if not isinstance(benchmarks, list) or not benchmarks:
            self.add_error(check, manifest_path, "benchmarks must be a non-empty list")
            self.checked.append(check)
            return

        seen_ids: set[str] = set()
        seen_scripts: set[str] = set()
        manifest_scripts: set[str] = set()

        for index, benchmark in enumerate(benchmarks, start=1):
            label = f"benchmarks[{index}]"
            if not isinstance(benchmark, dict):
                self.add_error(check, manifest_path, f"{label} must be an object")
                continue

            benchmark_id = benchmark.get("id")
            if not isinstance(benchmark_id, str) or not benchmark_id:
                self.add_error(check, manifest_path, f"{label}.id must be a non-empty string")
                benchmark_id = label
            elif benchmark_id in seen_ids:
                self.add_error(check, manifest_path, f"duplicate benchmark id: {benchmark_id}")
            else:
                seen_ids.add(benchmark_id)

            script = self.validate_manifest_path_field(check, manifest_path, benchmark_id, benchmark, "script")
            reports_dir = self.validate_manifest_path_field(
                check,
                manifest_path,
                benchmark_id,
                benchmark,
                "reports_dir",
            )
            run_glob = benchmark.get("run_glob")
            if not isinstance(run_glob, str) or not run_glob:
                self.add_error(check, manifest_path, f"{benchmark_id}: run_glob must be a non-empty string")
            elif Path(run_glob).is_absolute() or ".." in Path(run_glob).parts:
                self.add_error(check, manifest_path, f"{benchmark_id}: run_glob must be relative to reports_dir")

            summary_path = benchmark.get("summary_path")
            if not isinstance(summary_path, list) or not summary_path:
                self.add_error(check, manifest_path, f"{benchmark_id}: summary_path must be a non-empty list")
            elif not all(isinstance(part, str) and part for part in summary_path):
                self.add_error(
                    check,
                    manifest_path,
                    f"{benchmark_id}: summary_path must contain only non-empty strings",
                )

            weekly_review = benchmark.get("weekly_review")
            if not isinstance(weekly_review, dict):
                self.add_error(check, manifest_path, f"{benchmark_id}: weekly_review must be an object")
            else:
                check_freshness = weekly_review.get("check_freshness")
                if not isinstance(check_freshness, bool):
                    self.add_error(
                        check,
                        manifest_path,
                        f"{benchmark_id}: weekly_review.check_freshness must be true or false",
                    )
                elif check_freshness:
                    for field in ["min_status_counting_total", "max_age_days"]:
                        value = weekly_review.get(field)
                        if type(value) is not int or value <= 0:
                            self.add_error(
                                check,
                                manifest_path,
                                f"{benchmark_id}: weekly_review.{field} must be a positive integer",
                            )

            if script:
                manifest_scripts.add(script)
                if script in seen_scripts:
                    self.add_error(check, manifest_path, f"{benchmark_id}: duplicate script path: {script}")
                else:
                    seen_scripts.add(script)
                script_path = self.resolve_path(script)
                if not script_path.is_file():
                    self.add_error(check, manifest_path, f"{benchmark_id}: script does not exist: {script}")
                else:
                    self.check_benchmark_cli_contract(check, manifest_path, benchmark_id, script_path)
            if reports_dir and not self.resolve_path(reports_dir).is_dir():
                self.add_error(
                    check,
                    manifest_path,
                    f"{benchmark_id}: reports_dir does not exist or is not a directory: {reports_dir}",
                )

        discovered_scripts = {
            path.relative_to(self.root).as_posix()
            for path in self.root.glob("os/verification/**/scripts/benchmark_*.py")
        }
        for script in sorted(discovered_scripts - manifest_scripts):
            self.add_error(check, manifest_path, f"benchmark script missing from manifest: {script}")

        self.checked.append(check)

    def check_benchmark_cli_contract(
        self,
        check: str,
        manifest_path: Path,
        benchmark_id: str,
        script_path: Path,
    ) -> None:
        help_result = self.run_benchmark_contract_command(script_path, ["--help"], timeout_seconds=30)
        if help_result is None:
            self.add_error(check, manifest_path, f"{benchmark_id}: benchmark script --help could not run")
            return
        if help_result.returncode != 0:
            detail = self.command_failure_detail(help_result)
            self.add_error(check, manifest_path, f"{benchmark_id}: benchmark script --help failed{detail}")
            return

        help_text = "\n".join([help_result.stdout, help_result.stderr])
        missing_flags = [flag for flag in BENCHMARK_REQUIRED_HELP_FLAGS if flag not in help_text]
        if "--harness" in help_text:
            missing_flags.extend(flag for flag in BENCHMARK_HARNESS_HELP_FLAGS if flag not in help_text)
        if missing_flags:
            flags = ", ".join(sorted(set(missing_flags)))
            self.add_error(check, manifest_path, f"{benchmark_id}: benchmark script help missing flag(s): {flags}")
            return

        self_test_result = self.run_benchmark_contract_command(script_path, ["--self-test"], timeout_seconds=120)
        if self_test_result is None:
            self.add_error(check, manifest_path, f"{benchmark_id}: benchmark script --self-test could not run")
            return
        if self_test_result.returncode != 0:
            detail = self.command_failure_detail(self_test_result)
            self.add_error(check, manifest_path, f"{benchmark_id}: benchmark script --self-test failed{detail}")

    def run_benchmark_contract_command(
        self,
        script_path: Path,
        args: list[str],
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[str] | None:
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GIT_")
        }
        try:
            return subprocess.run(
                [sys.executable, str(script_path), *args],
                cwd=self.root,
                env=env,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None

    def command_failure_detail(self, result: subprocess.CompletedProcess[str]) -> str:
        output = "\n".join(part for part in [result.stderr.strip(), result.stdout.strip()] if part)
        if not output:
            return f" with exit code {result.returncode}"
        return f" with exit code {result.returncode}: {output[-500:]}"

    def validate_manifest_path_field(
        self,
        check: str,
        manifest_path: Path,
        benchmark_id: str,
        benchmark: dict,
        field_name: str,
    ) -> str | None:
        value = benchmark.get(field_name)
        if not isinstance(value, str) or not value:
            self.add_error(check, manifest_path, f"{benchmark_id}: {field_name} must be a non-empty string")
            return None
        path = Path(value)
        if path.is_absolute() or value.startswith("~") or ".." in path.parts:
            self.add_error(check, manifest_path, f"{benchmark_id}: {field_name} must be root-relative")
            return None
        return value

    def check_expected_route(
        self,
        check: str,
        fixture_path: Path,
        fixture_id: str,
        expected: dict,
        resolver_text: str,
        source_map_text: str,
    ) -> None:
        skill = expected.get("skill")
        if skill:
            skill_file = self.skill_file_for(skill)
            if not skill_file.exists():
                self.add_error(check, fixture_path, f"{fixture_id}: expected skill not found: {skill}")

        if expected.get("resolver_role") == "tie-breakers-only":
            for needle in ["If a harness exposes a matching skill", "tie-breakers"]:
                if needle not in resolver_text:
                    self.add_error(
                        check,
                        fixture_path,
                        f"{fixture_id}: resolver missing harness/tie-breaker policy: {needle}",
                    )

        agent = expected.get("agent")
        if agent:
            agent_dir = self.root / "os/agents" / agent
            for filename in ["JOB.md", "AGENTS.md"]:
                if not (agent_dir / filename).exists():
                    self.add_error(
                        check,
                        fixture_path,
                        f"{fixture_id}: expected agent file missing: os/agents/{agent}/{filename}",
                    )

        playbook = expected.get("playbook")
        if playbook and not self.resolve_path(playbook).exists():
            self.add_error(check, fixture_path, f"{fixture_id}: expected playbook missing: {playbook}")

        filing_path = expected.get("filing_path")
        if filing_path and not self.reference_exists(filing_path):
            self.add_error(check, fixture_path, f"{fixture_id}: filing path is not reachable: {filing_path}")

        handoff_destination = expected.get("handoff_destination")
        if handoff_destination and not self.reference_exists(handoff_destination):
            self.add_error(
                check,
                fixture_path,
                f"{fixture_id}: handoff destination is not reachable: {handoff_destination}",
            )

        safety_path = expected.get("safety_path")
        if safety_path and not self.resolve_path(safety_path).exists():
            self.add_error(check, fixture_path, f"{fixture_id}: safety path is missing: {safety_path}")

        source_map_entry = expected.get("source_map_entry")
        if source_map_entry and source_map_entry not in source_map_text:
            self.add_error(
                check,
                fixture_path,
                f"{fixture_id}: source map does not contain entry {source_map_entry!r}",
            )

        if expected.get("ask_before_external_action"):
            for needle in ["Pause and ask the user before", "sending email", "posting publicly"]:
                if needle not in resolver_text:
                    self.add_error(
                        check,
                        fixture_path,
                        f"{fixture_id}: resolver missing approval-pause evidence: {needle}",
                    )

    def skill_file_for(self, skill_name: str) -> Path:
        directory_skill = self.root / "os/skills" / skill_name / "SKILL.md"
        if directory_skill.exists():
            return directory_skill
        return self.root / "os/skills" / f"{skill_name}.md"

    def check_fixture_evidence(
        self,
        check: str,
        fixture_path: Path,
        fixture_id: str,
        expected: dict,
        evidence: list,
    ) -> None:
        for item in evidence:
            if not isinstance(item, dict):
                self.add_error(check, fixture_path, f"{fixture_id}: evidence entries must be objects")
                continue
            raw_path = item.get("path")
            contains = item.get("contains", [])
            if not raw_path:
                self.add_error(check, fixture_path, f"{fixture_id}: evidence missing path")
                continue
            if raw_path == "os/skills/MANIFEST.md" and expected.get("skill"):
                self.add_error(
                    check,
                    fixture_path,
                    f"{fixture_id}: manifest may not be used as routing evidence for a skill",
                )
            path = self.resolve_path(raw_path)
            text = self.read_text(path, check)
            for needle in contains:
                if needle not in text:
                    self.add_error(
                        check,
                        path,
                        f"{fixture_id}: evidence missing required text {needle!r}",
                    )

    def looks_like_local_reference(self, candidate: str) -> bool:
        if candidate.startswith("$"):
            return False
        return candidate.endswith((".md", "/")) or "/" in candidate

    def reference_exists(self, candidate: str) -> bool:
        path = Path(candidate).expanduser()
        if path.is_absolute():
            return path.exists()
        return (self.root / candidate).exists() or (self.root / "os" / candidate).exists()


def run_self_test(harness) -> None:
    root = harness.root / "structural_fixture"
    root_agents = root / "AGENTS.md"
    root_agents.parent.mkdir(parents=True)
    root_agents.write_text(
        "# AgentOS\n\n"
        "Unless otherwise stated, local file paths in AgentOS Markdown are relative to the AgentOS repository root.\n",
        encoding="utf-8",
    )
    portability_fixture = root / "os/playbook/PORTABILITY.md"
    portability_fixture.parent.mkdir(parents=True)
    portability_fixture.write_text(
        f"# Fixture\n\nBad internal path: `{root}/os/INDEX.md`\n\nBad parent path: `../INDEX.md`\n",
        encoding="utf-8",
    )
    source_map = root / "os/context/SOURCE_MAP.md"
    source_map.parent.mkdir(parents=True)
    source_map.write_text(
        "# Source Map\n\n"
        "- Local directory: `" + str(root / "definitely-missing") + "`\n"
        "- Private temp directory: `" + "/" + "private" + "/" + "var" + "/folders/aa/private-cache/run.json`\n",
        encoding="utf-8",
    )

    listed_script = root / "os/verification/listed/scripts/benchmark_listed.py"
    listed_script.parent.mkdir(parents=True)
    listed_script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    (root / "os/verification/listed/reports").mkdir()
    unlisted_script = root / "os/verification/unlisted/scripts/benchmark_unlisted.py"
    unlisted_script.parent.mkdir(parents=True)
    unlisted_script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    benchmark_manifest = root / "os/verification/BENCHMARKS.json"
    benchmark_manifest.write_text(
        json.dumps(
            {
                "version": 1,
                "benchmarks": [
                    {
                        "id": "listed",
                        "script": "os/verification/listed/scripts/benchmark_listed.py",
                        "reports_dir": "os/verification/listed/reports",
                        "run_glob": "*/run.json",
                        "summary_path": ["summary"],
                        "weekly_review": {"check_freshness": False},
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    workflow = root / ".github/workflows/agentos-validation.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("name: fixture\n", encoding="utf-8")
    guidance_workflow = root / ".github/workflows/guidance-benchmark-trial.yml"
    guidance_workflow.write_text(
        "name: bad guidance workflow\n"
        "on:\n"
        "  push:\n"
        "  workflow_dispatch:\n"
        "    inputs:\n"
        "      model:\n"
        "        required: false\n"
        "permissions:\n"
        "  contents: read\n"
        "jobs:\n"
        "  guidance:\n"
        "    if: github.ref_name == 'main'\n"
        "    permissions:\n"
        "      contents: write\n"
        "    steps:\n"
        "      - uses: actions/upload-artifact@v4\n"
        "      - run: python3 script --harness all\n"
        "      - run: git push origin HEAD:refs/heads/main\n"
        "  status-pr:\n"
        "    needs: guidance\n"
        "    if: ${{ github.ref_name == 'main' }}\n"
        "    permissions:\n"
        "      contents: write\n"
        "      pull-requests: write\n",
        encoding="utf-8",
    )

    validator = harness.validator(root)
    validator.check_markdown_path_portability()
    validator.check_source_map_path_health()
    validator.check_benchmark_manifest()
    validator.check_pr_readiness_tripwire()
    validator.check_guidance_benchmark_trial_workflow()

    ignored_root = harness.root / "structural_ignored_agent_fixture"
    (ignored_root / "os/agents/ignored-agent").mkdir(parents=True)
    (ignored_root / ".gitignore").write_text(".DS_Store\n", encoding="utf-8")
    (ignored_root / "os/agents/ignored-agent/.DS_Store").write_text("ignored local artifact\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(ignored_root), "init"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    ignored_validator = harness.validator(ignored_root)
    ignored_validator.check_agent_contract_completeness()

    harness.expect(
        "structural catches markdown path portability problems",
        any("hardcodes the AgentOS checkout path" in error.message for error in validator.errors)
        and any("uses a parent-relative AgentOS path" in error.message for error in validator.errors),
    )
    harness.expect(
        "structural catches source map missing path",
        any("listed local path does not exist" in error.message for error in validator.errors),
    )
    harness.expect(
        "structural catches benchmark manifest gaps",
        any("benchmark script help missing flag(s)" in error.message for error in validator.errors)
        and any("benchmark script missing from manifest" in error.message for error in validator.errors),
    )
    harness.expect(
        "structural catches PR readiness tripwire gaps",
        any(error.path == ".github/pull_request_template.md" for error in validator.errors)
        and any("Check PR design readiness fields" in error.message for error in validator.errors),
    )
    harness.expect(
        "structural catches Guidance benchmark workflow contract drift",
        any("must not define custom workflow_dispatch inputs" in error.message for error in validator.errors)
        and any("must not upload benchmark artifacts" in error.message for error in validator.errors)
        and any("must not push generated status updates directly to main" in error.message for error in validator.errors)
        and any("guidance job must not grant write permissions" in error.message for error in validator.errors)
        and any("status-pr job missing status-pr protected environment" in error.message for error in validator.errors)
        and any("status-pr job missing dedicated status PR token" in error.message for error in validator.errors)
        and any("status-pr job must keep repository GITHUB_TOKEN read-only" in error.message for error in validator.errors)
        and any("must keep repository GITHUB_TOKEN permissions read-only" in error.message for error in validator.errors),
    )
    harness.expect(
        "structural ignores gitignored agent artifacts",
        not any("os/agents/ignored-agent" in error.path for error in ignored_validator.errors),
    )
    harness.record(validator, ignored_validator)
