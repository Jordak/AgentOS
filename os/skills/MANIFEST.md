# AgentOS Skills Manifest

Status: Core manifest v1.

This manifest records publishable reusable skills, their safety posture, output conventions, filing rules, and verification coverage.

Machine-local exposure state and private live skill adapters belong outside portable Core metadata. Use `personal/os/skills/<skill-name>/CONFIG.md` for private live inputs to Core skills.

Contract reference: `os/skills/SKILL_CONTRACT.md`.

## Summary

- Canonical Core skills: 20.

## Maintenance Fields

Each skill entry records:

- Canonical source.
- Contract status.
- Mutability.
- Tools and connectors.
- Output artifact.
- Filing rule.
- Safety posture.
- Verification coverage.
- Upgrade notes.

## Canonical Skills

### `audit-issues`

- Canonical source: `os/skills/audit-issues/SKILL.md`
- Contract status: full.
- Mutability: mixed: read-only audit of local git and issue tracker state by default; external-write for status comments, issue closures, labels, or other tracker updates only when permitted by the shared external-write policy.
- Tools and connectors: local `git`, GitHub connector or `gh`, project-local issue tracker docs, and `os/playbook/GITHUB_WORKFLOW.md`.
- Output artifact: concise audit report listing closed issues, commented issues, skipped issues, evidence, and follow-up needed.
- Filing rule: no durable local artifact by default; requested audit reports live in the mapped project unless the audit is about AgentOS Core itself; external tracker state stays in the tracker.
- Safety posture: treat issue comments, labels, closures, assignments, milestones, and state changes as external project-state writes governed by `os/connections/SAFETY_RULES.md` and `os/playbook/GITHUB_WORKFLOW.md`; never close human-owned or human-review issues; do not close based on local-only commits, unmerged feature branches, title similarity, or undocumented memory.
- Verification coverage: fetch or otherwise verify the remote integration branch; for every closed issue, record merged PR or commit evidence reachable from that branch and authorization source; for every commented issue, record comment purpose, evidence, and authorization source; record skipped reasons; confirm no human-owned issue was closed and no external write happened outside the shared external-write policy.
- Upgrade notes: Core reusable issue-audit workflow.

### `check-implementation-readiness`

- Canonical source: `os/skills/check-implementation-readiness/SKILL.md`
- Contract status: full.
- Mutability: mixed: read-only by default for inspection and verdicts; local-write when creating local design docs or follow-up artifacts after the user asks the skill to make the design ready or accepts a local destination; external-write only for GitHub issue creation, issue updates, comments, labels, or other tracker state when permitted by the shared external-write policy.
- Tools and connectors: local filesystem, `rg`, mapped project files, GitHub connector or `gh` for issue/PR design sources, optional harness-exposed design-interview workflows when present, `os/playbook/IMPLEMENT_FEATURES.md`, `os/playbook/GITHUB_WORKFLOW.md`, and `os/playbook/ARTIFACTS.md` for substantial human-facing design artifacts.
- Output artifact: readiness report with exactly one verdict, `Ready to Implement`, `Needs Design Consensus`, or `Gate Skipped`, plus optional durable follow-up artifacts, approved source-design updates, and PR-body readiness fields for PR-bound work.
- Filing rule: canonical policy lives in `os/playbook/IMPLEMENT_FEATURES.md`; local design artifacts default to the mapped project's design-doc convention or `docs/design/issue-<number>-implementation-readiness.md`; private/personal design notes belong in the Personal Overlay; approved GitHub updates stay in GitHub.
- Safety posture: do not treat a missing readiness marker as silently ready; infer and confirm with the user before implementation proceeds; do not allow chat-only consensus to become the first implementation commit; follow the shared external-write policy before external tracker writes; do not leave meaningful deferred questions only in chat, model memory, or unpersisted reports.
- Verification coverage: confirms the target was classified as gated, exempt, or explicitly bypassed, the durable source and readiness marker were checked, unmarked readiness was not silently accepted, deferred follow-up artifacts were created where required, external writes complied with the shared external-write policy, and PR-bound work has readiness fields or a recorded gate-skip reason; run `scripts/run-validator` after skill or manifest changes.
- Upgrade notes: Core reusable gate for feature-sized implementation work.

### `refresh-benchmark-status`

- Canonical source: `os/skills/refresh-benchmark-status/SKILL.md`
- Contract status: full.
- Mutability: mixed: read-only when inspecting benchmark status and local evidence; local-write when updating `os/verification/BENCHMARK_STATUS.md` from eligible evidence after the user requested or approved the refresh; no external-write behavior.
- Tools and connectors: local filesystem, local `git`, `os/verification/BENCHMARKS.json`, `os/verification/BENCHMARK_STATUS.md`, local Personal Overlay benchmark reports, and `os/playbook/PERSONAL_OVERLAY.md`.
- Output artifact: an updated or proposed Core benchmark status snapshot plus a concise refresh report naming eligible evidence, ineligible evidence, stale entries, and unchanged entries.
- Filing rule: Core status lives in `os/verification/BENCHMARK_STATUS.md`; raw reports and run histories stay in the Personal Overlay report directories configured by `os/verification/BENCHMARKS.json`; deterministic refresh-helper design is deferred to GitHub Issue #30.
- Safety posture: do not copy raw reports, run JSON, transcripts, stdout, stderr, local paths, prompts, session details, account details, private diagnostics, or private evidence into Core; require clean, fresh `main` evidence before marking entries `passing`; ask before caveated or ambiguous updates.
- Verification coverage: confirm benchmark manifest and status file were read, local report paths were resolved through the Personal Overlay rule, used reports had current-schema Git metadata, status labels are allowed, no raw/private evidence was copied into Core, and `scripts/run-validator` passes after skill or status changes.
- Upgrade notes: Core workflow for maintaining the public-safe benchmark snapshot without introducing Core benchmark history.

### `run-benchmarks`

- Canonical source: `os/skills/run-benchmarks/SKILL.md`
- Contract status: full.
- Mutability: mixed: reads Core benchmark configuration and runs local benchmark scripts; local-write when scripts save reports under configured Personal Overlay report directories and when `refresh-benchmark-status` updates `os/verification/BENCHMARK_STATUS.md` after the user requested or approved the refresh; no external-write behavior.
- Tools and connectors: local `git`, filesystem, `os/verification/BENCHMARKS.json`, configured benchmark scripts, `os/playbook/PERSONAL_OVERLAY.md`, and `os/skills/refresh-benchmark-status/SKILL.md`.
- Output artifact: concise benchmark run report naming commands, saved report directories, incompatible scripts, visible pass/fail/unavailable posture, and status-refresh outcome.
- Filing rule: raw reports and run histories stay in Personal Overlay report directories configured by `BENCHMARKS.json`; Core status changes only through `refresh-benchmark-status`; benchmark CLI standardization is deferred to GitHub Issue #33 and deterministic refresh-helper work to #30.
- Safety posture: ask before external harnesses, model-call benchmarks, or commands that may spend credits or require authenticated CLIs; run external/model-call harnesses from a sanitized Core-only checkout or export unless the user explicitly accepts primary-checkout risk for a diagnostic run; do not copy raw/private benchmark evidence into Core; do not produce status-eligible evidence unless the checkout is clean, current `main`, and using the canonical or user-assigned Personal Overlay report directories.
- Verification coverage: confirm benchmark manifest and Personal Overlay policy were read, configured report directories were resolved through the Personal Overlay rule, script help was inspected, compatible scripts and harness choices were selected from the CLI contract, dry-runs were treated as diagnostic/ineligible, Git preflight ran before status-eligible saved reports, model-call work was approved and run from a sanitized Core-only checkout or export when applicable, and status refresh ran or was followed in proposal/report mode unless blocked or declined.
- Upgrade notes: thin orchestration layer for Issue #32; avoids benchmark-specific internals and delegates status interpretation to `refresh-benchmark-status`.

### `expose-skills`

- Canonical source: `os/skills/expose-skills/SKILL.md`
- Contract status: full.
- Mutability: mixed: read-only dry run by default; current-machine local-write with `--no-dry-run` when creating global symlink adapters under `~/.agents/skills`; backup-backed current-machine replacement with `--replace-existing-copy --no-dry-run` for same-name Core skill directories.
- Tools and connectors: local filesystem, `os/skills/MANIFEST.md`, and `os/skills/expose-skills/scripts/expose_skills.py`.
- Output artifact: skill exposure dry-run or apply report, optional current-machine symlink adapters under the global harness skill root, and optional same-name Core skill directory backups under `~/.agents/skills/.archive/expose-skills/`.
- Filing rule: keep canonical skill behavior in `os/skills/`; keep global adapter state out of this manifest; dry-run and apply output stays in chat unless the user asks for a local report.
- Safety posture: default to dry run; ask before `--no-dry-run` writes unless the user explicitly requested apply behavior; expose only Core manifest skills in v1; do not scan Personal Overlay skills, copy skill files, create junctions, replace same-name Core skill directories without `--replace-existing-copy`, overwrite wrong-target symlinks, replace files, or delete global skill dirs; replacement mode intentionally does not byte-compare same-name directory provenance.
- Verification coverage: run dry run with a temporary `HOME`; run `--no-dry-run` with a temporary `HOME` and confirm symlink creation; verify scoped `--skill` behavior; run `python3 os/skills/expose-skills/scripts/expose_skills.py --self-test`; verify existing-copy, `--replace-existing-copy` dry-run and apply behavior, backup creation, partial-failure reporting, wrong-target, regular-file, unknown-skill, unrelated global skill, dry-run exit-code, apply exit-code, and symlink-permission failure behavior; run `scripts/run-validator`.
- Upgrade notes: introduced for GitHub Issue #62 as the symlink-adapter successor to the retired copy-based exposure workflow; Personal Overlay exposure is doc-only in v1.

### `thermo-nuclear-code-quality-review`

- Canonical source: `os/skills/thermo-nuclear-code-quality-review/SKILL.md`
- Contract status: full.
- Mutability: read-only.
- Tools and connectors: local repository files, `git diff`, project instructions, local search, tests when the caller asks for validation, and no external connectors by default.
- Output artifact: strict code-quality review findings focused on structural regressions, missed simplification, spaghetti growth, file-size pressure, type and layer cleanliness, and maintainability risks.
- Filing rule: review output stays in chat or the calling review artifact by default; durable follow-up belongs in the mapped project or the invoking workflow's report, not in AgentOS.
- Safety posture: do not edit files, post comments, push, or change external state unless another explicitly invoked workflow owns those actions; this skill is reviewer guidance by default.
- Verification coverage: confirm the target diff or code area was inspected, findings prioritize structural risks over nits, no external writes happened, and skill validation plus `scripts/run-validator` pass after skill changes.
- Upgrade notes: vendored from `cursor/plugins` path `thermos/skills/thermo-nuclear-code-quality-review/SKILL.md` at ref `5102244dabd626b101cff40accbe7f7d1eeefa15`; the original import used the matching `cursor-team-kit` copy at ref `26878d6606afd611197c900bf2dc451ee2e80a74`; review upstream diffs deliberately, preserve `UPSTREAM.md`, and run `expose-skills` dry run when current-machine discoverability matters after accepted updates.

### `thermo-nuclear-review`

- Canonical source: `os/skills/thermo-nuclear-review/SKILL.md`
- Contract status: full.
- Mutability: read-only.
- Tools and connectors: local repository files, `git diff`, project instructions, local search, local validation evidence, and read-only `gh` or `glab` PR/MR discussion inspection when a PR/MR exists and the independent audit finds medium-or-higher risk findings.
- Output artifact: rigorous correctness, security, devex, and feature-gate review findings scoped to changed code.
- Filing rule: review output stays in chat or the calling review artifact by default; durable follow-up belongs in the mapped project or the invoking workflow's report, not in AgentOS.
- Safety posture: do not edit files, post comments, push, change PR state, label or close issues, change permissions, or perform external writes unless another explicitly invoked workflow owns those actions; this skill is reviewer guidance by default.
- Verification coverage: confirm the target diff or code area was inspected, findings are scoped to added or modified code, severity is calibrated, PR/MR discussion was checked when required and available, no unfinished-research findings were reported, and skill validation plus `scripts/run-validator` pass after skill changes.
- Upgrade notes: vendored from `cursor/plugins` path `thermos/skills/thermo-nuclear-review/SKILL.md` at ref `5102244dabd626b101cff40accbe7f7d1eeefa15`; review upstream diffs deliberately, preserve `UPSTREAM.md`, keep `review-pass` deep-review lens guidance aligned, and run `expose-skills` dry run when current-machine discoverability matters after accepted updates.

### `improve-codebase-architecture`

- Canonical source: `os/skills/improve-codebase-architecture/SKILL.md`
- Contract status: full.
- Mutability: mixed: read-only while exploring architecture and presenting candidates; local-write when creating temporary HTML reports; mapped-project local-write only after the user chooses a candidate and approves domain-doc or ADR updates during the grilling loop.
- Tools and connectors: local repository files, project domain docs (`DOMAIN.md`/`DOMAIN-MAP.md`, with legacy `CONTEXT.md`/`CONTEXT-MAP.md` fallback), `docs/adr/`, local search, optional exploration subagents, temporary HTML output, and no external connectors by default.
- Output artifact: temporary static HTML architecture-review report with deepening candidates, before/after visuals, recommendation strengths, and a top recommendation; optional project domain-doc or ADR updates after user approval.
- Filing rule: reports live under the system temporary directory; project-specific domain docs and ADRs live in the mapped project; no durable AgentOS state is created by default.
- Safety posture: do not write project domain docs or ADRs until the user has selected a candidate or approved the specific update; do not treat a review candidate as implementation approval; external writes require separate approval through the relevant workflow.
- Verification coverage: confirm domain docs and relevant ADRs were checked, generated reports exist under the temp directory when produced, proposed modules use the skill's architecture vocabulary, ADR conflicts are surfaced when real, and skill validation plus `scripts/run-validator` pass after skill changes.
- Upgrade notes: vendored from `mattpocock/skills` path `skills/engineering/improve-codebase-architecture/` at ref `0288510dd61ff6ef7c2003834082ab8f2387e80e`; preserve companion references and `UPSTREAM.md`, reapply AgentOS domain-doc alias patches after upstream updates, and run `expose-skills` dry run when current-machine discoverability matters after accepted updates.

### `check-vendored-skill-upstreams`

- Canonical source: `os/skills/check-vendored-skill-upstreams/SKILL.md`
- Contract status: full.
- Mutability: read-only for the AgentOS checkout and upstream sources; local-write only for temporary fixtures when `--self-test` runs under the system temporary directory.
- Tools and connectors: local filesystem, `os/skills/*/UPSTREAM.md`, skill-local Python helper plus no-network self-test sidecar, and public GitHub HTTP API for supported upstream sources.
- Output artifact: text or JSON freshness report with one row per vendored skill, including status, vendored ref, latest path-touching upstream ref, notes, and compare URLs when useful.
- Filing rule: output stays in chat or the invoking weekly review report by default; no run history or upstream status snapshot is written to Core.
- Safety posture: never auto-update vendored files, open PRs or issues, post comments, change automations, or write external state; update availability is only a prompt for a reviewed vendoring PR.
- Verification coverage: run the helper with `--self-test` for parser discovery, status classification, malformed metadata, strict exits, directory-style upstream paths, and report shape; run text and JSON checks against the AgentOS root; run skill validation; run `scripts/run-validator`; and run `expose-skills` dry run before review or merge when current-machine discoverability matters. Apply current-machine exposure only after explicit user approval or after the reviewed PR lands.
- Upgrade notes: Core reusable freshness check for vendored skill `UPSTREAM.md` files; compare against the latest commit touching the upstream path rather than repository HEAD to avoid noisy unrelated updates.

### `review-pass`

- Canonical source: `os/skills/review-pass/SKILL.md`
- Contract status: full.
- Mutability: read-only for target repositories, GitHub, issue trackers, PR state, and external accounts; local-write only for optional temporary Markdown packet artifacts.
- Tools and connectors: local filesystem, `git`, `rg`, optional GitHub connector or `gh` reads for PR metadata, review subagents when available, `make-temp-file` for optional packet paths, and the vendored review skills as source material for lens guidance.
- Output artifact: structured Markdown review packet with target, baseline intent, panel, lens plan, coverage, issue families, recommended dispositions, design-escape-hatch concerns, reviewer crosswalk, residual risks, reviewer continuity mode and handle availability when applicable, optional caller-private continuity handoff, and optional temporary packet path.
- Filing rule: no durable AgentOS state by default; chat output by default; optional temporary packet files live under the system temporary directory; project fixes, PR comments, pushes, ready markers, and durable loop ledgers belong to callers such as `review-loop`.
- Safety posture: read-only reviewer-panel workflow; do not edit files, commit, push, merge, comment on PRs, label, close issues, mark ready, change permissions, run validation commands that may dirty the checkout, expose opaque reviewer handles, or perform external writes; keep spawned or resumed reviewers read-only and close them after each pass.
- Verification coverage: confirm target/base/head, mode, baseline-intent source or limitation, reviewer count, lens plan, reviewer continuity mode and opaque handle availability when applicable, current prompt templates, dirty-validation rule, Contract Surface Matrix review for skill/workflow contract changes, deep-review and structural-depth instructions when assigned, issue-family normalization, recommended dispositions, sibling-search suggestions, validation signals, reviewer closure, and absence of target, PR, issue, handle exposure, or external writes.
- Upgrade notes: Core reusable read-only panel-pass workflow introduced by GitHub Issue #54; `review-loop` depends on it for fresh and verification reviewer-panel mechanics.

### `review-loop`

- Canonical source: `os/skills/review-loop/SKILL.md`
- Contract status: full.
- Mutability: mixed: reads local code, GitHub PR metadata, and review context; may edit project files, create fix commits, push to a target PR branch, post consolidated Agent Review PR comments, apply the repository's established ready-for-human marker, and write a temporary HTML report when explicitly authorized for a review loop.
- Tools and connectors: `os/skills/review-pass/SKILL.md` for fresh and verification reviewer-panel passes, local `git`, project validation commands, GitHub connector or `gh`, `make-temp-file`, `os/skills/check-implementation-readiness/SKILL.md`, `os/playbook/IMPLEMENT_FEATURES.md`, `os/playbook/ARTIFACTS.md`, and `os/playbook/GITHUB_WORKFLOW.md`.
- Output artifact: temporary static HTML review-loop report, optional project fix commits, optional consolidated PR comments, and optional ready-for-human PR marker.
- Filing rule: no durable AgentOS state by default; temporary reports live under the system temporary directory; project fixes, commits, branches, and reports live in the target project; PR comments and ready markers stay in GitHub.
- Safety posture: use only after explicit review-loop authorization; delegate reviewer-panel mechanics to read-only `review-pass`; keep opaque reviewer handles out of reviewer prompts, PR comments, public reports, and human-facing packets; run or honor the implementation-readiness gate for feature-sized PRs before reviewers start; do not merge, close issues, create labels, delete branches, change permissions, push outside the target PR branch, or publish outside the PR review surface without separate approval.
- Verification coverage: confirm target/base/head and review-pass sizing, durable design readiness or recorded gate skip for feature-sized targets, baseline intent, review-pass template usage, Contract Surface Matrix use or explicit skip for semantic contract changes, verification reviewer continuity mode and opaque handle availability, deep-review and structural-depth lens instructions when assigned, accepted/declined findings, sibling sweeps, validation commands, consolidated Agent Review comment shape when posted, clean final fresh review-pass packet, temporary HTML report, and absence of unapproved external writes or handle exposure.
- Upgrade notes: Core reusable orchestration workflow for fresh-context PR review/fix loops; reviewer-panel mechanics now live in `review-pass`.

### `run-agentos-doctor`

- Canonical source: `os/skills/run-agentos-doctor/SKILL.md`
- Contract status: full.
- Mutability: read-only by default; local-write or current-machine write only after explicit user approval when applying adapter remediation, applying Core skill exposure, editing Personal Overlay files, changing automations, or writing outside the checkout.
- Tools and connectors: local filesystem, skill-local `os/skills/run-agentos-doctor/scripts/agentos_doctor.py`, `scripts/install_global_agent_instructions.py`, `os/skills/expose-skills/scripts/expose_skills.py`, `os/playbook/GETTING_STARTED.md`, and relevant Personal Overlay automation notes when present.
- Output artifact: concise setup health report with deterministic script facts, agent interpretation for ambiguous local state, and approval-gated next steps.
- Filing rule: default output stays in chat; deterministic helper and tests stay under `os/skills/run-agentos-doctor/scripts/`; private setup notes and automation state stay in the Personal Overlay; current-machine adapter state is not recorded in the Core manifest.
- Safety posture: read-only by default; distinguish script facts from agent judgment; do not expose private file contents; do not treat helper automation counts or ambiguous automation prose as active recurring evidence; ask before writes or current-machine changes.
- Verification coverage: run the doctor script or explain why it could not run; confirm feature worktree runs use `--primary-agentos-home` or warn about limited interpretation; use expose-skills dry-run mode for Core skill exposure diagnosis when requested; classify automation evidence conservatively in the skill, not from helper counts alone; run `python3 os/verification/scripts/validate_agentos.py` after skill or manifest changes.
- Upgrade notes: Core skill wrapper for AgentOS setup health checks; keeps vague judgment in agent instructions while deterministic checks remain in the script.

### `double-steelman`

- Canonical source: `os/skills/double-steelman/SKILL.md`
- Contract status: full.
- Mutability: read-only for quick conversational comparisons; local-write to a temporary HTML file for complex comparisons; durable local-write only when the user asks to save a decision brief or durable note.
- Tools and connectors: user-provided context, local files, project code, AgentOS context when relevant, and current official or primary sources when a decision depends on unstable facts; codebase inspection and credible convention or best-practice sources for technical architecture decisions; the `make-temp-file` skill for temporary HTML artifact paths.
- Output artifact: conversational decision support for simple comparisons, or a temporary static HTML decision brief for complex comparisons, with the strongest honest case for each viable side, objections, cruxes, uncertainty, sources when possible, and a recommendation by default.
- Filing rule: default output stays in chat for simple comparisons; complex decision briefs live in a temporary `.html` file and the final response links to it; saved durable briefs live in the mapped project or relevant AgentOS layer only when requested; durable AgentOS decisions are recorded only when the user explicitly asks.
- Safety posture: preserve the user's agency; do not invent facts, preferences, constraints, or motives; avoid false balance; treat medical, legal, financial, mental health, and other high-stakes personal decisions as structured decision support rather than settled professional advice.
- Verification coverage: confirms all materially viable sides were considered or explicitly excluded, no side was straw-manned, facts/predictions/values are separated, current claims were checked when needed, citations are included when possible, temporary HTML artifacts exist and are linked when produced, and no durable write happened without request.
- Upgrade notes: Core reusable decision-support workflow.

### `make-temp-file`

- Canonical source: `os/skills/make-temp-file/SKILL.md`
- Contract status: full.
- Mutability: local-write; creates temporary files under the system temporary directory through the bundled helper.
- Tools and connectors: local Bash helper, `mktemp` or `gmktemp`, and no external connectors.
- Output artifact: real temporary file path or paths created by the helper and returned in chat.
- Filing rule: temporary files stay in the system temporary directory; no durable AgentOS filing by default.
- Safety posture: do not hand-assemble temp paths; reject path-like prefixes; ask before creating many files or handling sensitive data that needs stricter storage controls.
- Verification coverage: run the helper with default and explicit prefix/extension arguments; confirm reported paths exist and multiple paths are unique when requested; run skill validation and `expose-skills` dry run after canonical changes when current-machine discoverability matters.
- Upgrade notes: Core reusable temp-file helper workflow.

### `meeting-notes`

- Canonical source: `os/skills/meeting-notes/SKILL.md`
- Contract status: full.
- Mutability: read-only by default; local-write only when the user asks to record durable decisions.
- Tools and connectors: user-provided notes, transcript, or bullets; connector reads only if explicitly supplied or requested.
- Output artifact: meeting notes with summary, decisions, action items, open questions, and optional follow-up draft.
- Filing rule: add durable decisions to the appropriate Personal Overlay decisions log only when the user asks; default output stays in chat unless a file is requested.
- Safety posture: preserve uncertainty; do not invent owners, deadlines, decisions, attendees, or commitments; ask before external sends or durable sensitive filing.
- Verification coverage: confirms owners, dates, decisions, action items, unknowns, external-send safety, and requested durable decision filing.
- Upgrade notes: Core reusable meeting-notes workflow.

### `research-brief`

- Canonical source: `os/skills/research-brief/SKILL.md`
- Contract status: full.
- Mutability: read-only.
- Tools and connectors: web/current official sources, direct source material, or connector reads when explicitly relevant.
- Output artifact: answer with evidence, caveats, and recommended next step.
- Filing rule: no default durable filing; file only when the user asks or when a separate AgentOS workflow requires it.
- Safety posture: verify current docs for fast-moving tools; separate facts from inference; cite web or connector sources; ask before external writes or durable filing.
- Verification coverage: confirms whether current sources were required, source quality, fact/inference separation, citation presence, and no unrequested writes.
- Upgrade notes: Core reusable research workflow.

### `skillify-agentos`

- Canonical source: `os/skills/skillify-agentos/SKILL.md`
- Contract status: full.
- Mutability: local-write; external-write only when permitted by the shared external-write policy.
- Tools and connectors: local AgentOS files, `rg`, `git`, local validators, and GitHub issue context when issue-driven.
- Output artifact: new or updated skill, resolver guidance, manifest entry, deterministic validator, retrieval fixture, smoke example, or propagation queue proposal.
- Filing rule: canonical skills live under `os/skills/`; deterministic checks live in `os/verification/scripts/validate_agentos.py` or a clearly warranted local script; retrieval/smoke fixtures live under `os/verification/retrieval/`; unapproved durable state proposals live in the appropriate Personal Overlay propagation queue.
- Safety posture: require at least one concrete example; do not copy private connector data into durable artifacts; follow the shared external-write policy before external writes; ask before automation activation, destructive edits, or current-machine skill exposure changes.
- Verification coverage: run `scripts/run-validator`; run `scripts/run-validator --self-test` when validator behavior changes; add or update a safe smoke example for new durable behavior; confirm external writes complied with the shared external-write policy.
- Upgrade notes: Core reusable workflow for turning repeated work into durable AgentOS behavior.

### `verify-privacy`

- Canonical source: `os/skills/verify-privacy/SKILL.md`
- Contract status: full.
- Mutability: read-only by default; local-write only when the user asks to add privacy markers, fix leaks, update docs, or save a privacy report.
- Tools and connectors: local filesystem reads, `git`, `rg`, AgentOS validators, Gitleaks, optional TruffleHog, and no external connectors by default.
- Output artifact: concise privacy audit report with verdict, commands run, reviewed scope, blockers, warnings, marker recommendations, and exact next fixes.
- Filing rule: default output stays in chat; saved privacy reports live under `personal/os/verification/privacy/`; proposed durable marker additions live in `personal/os/verification/privacy-markers.txt`; public-safe validator or skill improvements live in Core only when they do not include private examples.
- Safety posture: never treat Gitleaks as a complete personal-info audit; do not expose private marker contents unnecessarily; ask before deleting, publishing, changing repository visibility, altering external GitHub state, connector reads, or durable file changes not requested by the user.
- Verification coverage: run the publication precheck and staged snapshot privacy scan when publication or commit safety is in scope; treat working-tree Gitleaks as advisory mixed-tree coverage; confirm ignored private overlay files are excluded and ignore coverage is checked; perform a semantic crawl of high-risk Core areas; report exact file and line evidence for blockers where possible.
- Upgrade notes: Core reusable privacy-audit workflow; AgentOS publication and Core/Personal Overlay separation are supported use cases.

### `weekly-update`

- Canonical source: `os/skills/weekly-update/SKILL.md`
- Contract status: full.
- Mutability: read-only by default.
- Tools and connectors: user-provided facts and relevant local AgentOS context when requested.
- Output artifact: concise weekly update or status draft.
- Filing rule: no default durable filing; update memory only if the user asks or the active workflow calls for it.
- Safety posture: do not invent progress, blockers, dates, or commitments; label unknowns; ask for missing facts if the update will be sent to other people; treat outbound updates as drafts.
- Verification coverage: confirms no invented facts, labeled unknowns, missing fact handling for external drafts, and no unapproved sends.
- Upgrade notes: Core reusable status-drafting workflow.

## Deterministic Check Targets

Future validators can use this manifest to check:

- canonical source paths exist;
- mutating skills name safety rules;
- skills that produce durable artifacts name filing rules;
- skills marked `full` include verification guidance;
- manifest entries do not record current-machine installed-skill paths or exposure state.
