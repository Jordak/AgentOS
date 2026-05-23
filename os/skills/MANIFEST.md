# AgentOS Skills Manifest

Status: Core manifest v1.

This manifest records publishable reusable skills, their safety posture, output conventions, filing rules, and verification coverage.

Machine-local discoverable mirrors and private live skill adapters belong in the Personal Overlay. Use `personal/os/skills/<skill-name>/CONFIG.md` for private live inputs to Core skills.

Contract reference: `os/skills/SKILL_CONTRACT.md`.

## Summary

- Canonical Core skills: 14.

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
- Mutability: mixed: read-only audit of local git and issue tracker state by default; external-write for status comments, issue closures, labels, or other tracker updates only when the user explicitly asks for tracker updates in the current request or approves a proposed update list.
- Tools and connectors: local `git`, GitHub connector or `gh`, project-local issue tracker docs, and `os/playbook/GITHUB_WORKFLOW.md`.
- Output artifact: concise audit report listing closed issues, commented issues, skipped issues, evidence, and follow-up needed.
- Filing rule: no durable local artifact by default; requested audit reports live in the mapped project unless the audit is about AgentOS Core itself; external tracker state stays in the tracker.
- Safety posture: treat issue comments, labels, closures, assignments, milestones, and state changes as external project-state writes; never close human-owned or human-review issues; do not close based on local-only commits, unmerged feature branches, title similarity, or undocumented memory.
- Verification coverage: fetch or otherwise verify the remote integration branch; for every closed issue, record merged PR or commit evidence reachable from that branch; for every commented issue, record comment purpose and evidence; record skipped reasons; confirm no human-owned issue was closed and no external write happened without approval.
- Upgrade notes: Core reusable issue-audit workflow.

### `check-implementation-readiness`

- Canonical source: `os/skills/check-implementation-readiness/SKILL.md`
- Contract status: full.
- Mutability: mixed: read-only by default for inspection and verdicts; local-write when creating local design docs or follow-up artifacts after the user asks the skill to make the design ready or accepts a local destination; external-write only for GitHub issue creation, issue updates, comments, labels, or other tracker state after explicit user approval in the current request.
- Tools and connectors: local filesystem, `rg`, mapped project files, GitHub connector or `gh` for issue/PR design sources, optional harness-exposed design-interview workflows when present, `os/playbook/IMPLEMENT_FEATURES.md`, `os/playbook/GITHUB_WORKFLOW.md`, and `os/playbook/ARTIFACTS.md` for substantial human-facing design artifacts.
- Output artifact: readiness report with exactly one verdict, `Ready to Implement`, `Needs Design Consensus`, or `Gate Skipped`, plus optional durable follow-up artifacts and approved source-design updates.
- Filing rule: canonical policy lives in `os/playbook/IMPLEMENT_FEATURES.md`; local design artifacts default to the mapped project's design-doc convention or `docs/design/issue-<number>-implementation-readiness.md`; private/personal design notes belong in the Personal Overlay; approved GitHub updates stay in GitHub.
- Safety posture: do not treat a missing readiness marker as silently ready; infer and confirm with the user before implementation proceeds; ask before external tracker writes unless explicitly authorized; do not leave meaningful deferred questions only in chat, model memory, or unpersisted reports.
- Verification coverage: confirms the target was classified as gated, exempt, or explicitly bypassed, the durable source and readiness marker were checked, unmarked readiness was not silently accepted, deferred follow-up artifacts were created where required, and external writes were approved; run `python3 os/verification/scripts/validate_agentos.py` after skill or manifest changes.
- Upgrade notes: Core reusable gate for feature-sized implementation work.

### `refresh-benchmark-status`

- Canonical source: `os/skills/refresh-benchmark-status/SKILL.md`
- Contract status: full.
- Mutability: mixed: read-only when inspecting benchmark status and local evidence; local-write when updating `os/verification/BENCHMARK_STATUS.md` from eligible evidence after the user requested or approved the refresh; no external-write behavior.
- Tools and connectors: local filesystem, local `git`, `os/verification/BENCHMARKS.json`, `os/verification/BENCHMARK_STATUS.md`, local Personal Overlay benchmark reports, and `os/playbook/PERSONAL_OVERLAY.md`.
- Output artifact: an updated or proposed Core benchmark status snapshot plus a concise refresh report naming eligible evidence, ineligible evidence, stale entries, and unchanged entries.
- Filing rule: Core status lives in `os/verification/BENCHMARK_STATUS.md`; raw reports and run histories stay in the Personal Overlay report directories configured by `os/verification/BENCHMARKS.json`; deterministic refresh-helper design is deferred to GitHub Issue #30.
- Safety posture: do not copy raw reports, run JSON, transcripts, stdout, stderr, local paths, prompts, session details, account details, private diagnostics, or private evidence into Core; require clean, fresh `main` evidence before marking entries `passing`; ask before caveated or ambiguous updates.
- Verification coverage: confirm benchmark manifest and status file were read, local report paths were resolved through the Personal Overlay rule, used reports had current-schema Git metadata, status labels are allowed, no raw/private evidence was copied into Core, and `python3 os/verification/scripts/validate_agentos.py` passes after skill or status changes.
- Upgrade notes: Core workflow for maintaining the public-safe benchmark snapshot without introducing Core benchmark history.

### `run-benchmarks`

- Canonical source: `os/skills/run-benchmarks/SKILL.md`
- Contract status: full.
- Mutability: mixed: reads Core benchmark configuration and runs local benchmark scripts; local-write when scripts save reports under configured Personal Overlay report directories and when `refresh-benchmark-status` updates `os/verification/BENCHMARK_STATUS.md` after the user requested or approved the refresh; no external-write behavior.
- Tools and connectors: local `git`, filesystem, `os/verification/BENCHMARKS.json`, configured benchmark scripts, `os/playbook/PERSONAL_OVERLAY.md`, and `os/skills/refresh-benchmark-status/SKILL.md`.
- Output artifact: concise benchmark run report naming commands, saved report directories, incompatible scripts, visible pass/fail/unavailable posture, and status-refresh outcome.
- Filing rule: raw reports and run histories stay in Personal Overlay report directories configured by `BENCHMARKS.json`; Core status changes only through `refresh-benchmark-status`; benchmark CLI standardization is deferred to GitHub Issue #33 and deterministic refresh-helper work to #30.
- Safety posture: ask before external harnesses, model-call benchmarks, or commands that may spend credits or require authenticated CLIs; do not copy raw/private benchmark evidence into Core; do not produce status-eligible evidence unless the checkout is clean, current `main`, and using the canonical or user-assigned Personal Overlay report directories.
- Verification coverage: confirm benchmark manifest and Personal Overlay policy were read, configured report directories were resolved through the Personal Overlay rule, script help was inspected, compatible scripts were selected from the CLI contract, dry-runs were treated as diagnostic/ineligible, Git preflight ran before status-eligible saved reports, model-call work was approved, and status refresh ran or was followed in proposal/report mode unless blocked or declined.
- Upgrade notes: thin orchestration layer for Issue #32; avoids benchmark-specific internals and delegates status interpretation to `refresh-benchmark-status`.

### `mirror-skills`

- Canonical source: `os/skills/mirror-skills/SKILL.md`
- Contract status: full.
- Mutability: mixed: read-only in audit mode; local-write in sync mode when creating or updating current-machine skill mirrors.
- Tools and connectors: local filesystem, `os/skills/MANIFEST.md`, optional Personal Overlay config, and `os/skills/mirror-skills/scripts/mirror_skills.py`.
- Output artifact: mirror audit report and optional current-machine mirror files under a configured mirror root.
- Filing rule: keep canonical skill behavior in `os/skills/`; keep machine-local mirror state out of this manifest; mirror audit output stays in chat unless the user asks for a local report.
- Safety posture: default to audit-only; ask before writing outside the workspace unless the active harness has already approved the exact mirror root and write scope; do not delete extra mirror files unless the user explicitly asks for pruning.
- Verification coverage: run the mirror audit script in audit mode; run a `--sync` smoke test against a temporary mirror root; verify scoped `--skill` audit and sync behavior; verify Personal Overlay skill discovery and collision handling; run skill validation and the AgentOS validator when available.
- Upgrade notes: private live mirror roots and validator paths belong in `personal/os/skills/mirror-skills/CONFIG.md`.

### `reverse-mirror-skills`

- Canonical source: `os/skills/reverse-mirror-skills/SKILL.md`
- Contract status: full.
- Mutability: mixed: read-only in audit/recommendation mode; local-write after approval when importing a skill into Core or the Personal Overlay, updating manifest metadata, backing up or archiving local skills, generating active-harness metadata, or refreshing current-machine mirrors.
- Tools and connectors: local filesystem tools, `git`, `os/skills/MANIFEST.md`, `os/skills/SKILL_CONTRACT.md`, `os/playbook/PERSONAL_OVERLAY.md`, the `mirror-skills` workflow, optional skill validation helpers, and GitHub only when the user explicitly asks to create tracking issues.
- Output artifact: prioritized recommendation table for local skills and optional canonical skill files, Core manifest entry, backup/archive directories, refreshed mirror files, and user-approved follow-up issues.
- Filing rule: reusable public-safe imports live under `os/skills/` and get manifest entries; private user-specific imports live under `personal/os/skills/` and do not get Core manifest entries; local mirror backups stay under the mirror root archive; Personal Overlay backups stay under the Personal Overlay skills archive; audit output stays in chat unless the user asks for a local report.
- Safety posture: treat local skills as potentially private or externally owned until reviewed; require approval before import, overwrite, archive, delete, permanent delete, mirror sync, or issue creation; default local deletion to archive/move; do not overwrite canonical skills automatically; do not record machine-local mirror state in the manifest; do not import externally sourced skills without explicit vendor/fork approval.
- Verification coverage: validate the skill with `quick_validate.py` when available; run `python3 os/verification/scripts/validate_agentos.py`; run scoped `mirror-skills` audit/sync smoke checks; manually confirm no bundled reverse mirror script, no future Personal Overlay governance dependency, no specific-person reference, backup behavior, bulk approval behavior, external-origin exclusion behavior, and protected-main behavior.
- Upgrade notes: complements `mirror-skills` by reviewing local harness skills before promoting approved ones into AgentOS; revisit after the deferred Personal Overlay skills governance design lands.

### `review-loop`

- Canonical source: `os/skills/review-loop/SKILL.md`
- Contract status: full.
- Mutability: mixed: reads local code, GitHub PR metadata, and review context; may edit project files, create fix commits, push to a target PR branch, post consolidated Agent Review PR comments, apply the repository's established ready-for-human marker, and write a temporary HTML report when explicitly authorized for a review loop.
- Tools and connectors: local `git`, project validation commands, GitHub connector or `gh`, review subagents when available, `make-temp-file`, `os/playbook/ARTIFACTS.md`, and `os/playbook/GITHUB_WORKFLOW.md`.
- Output artifact: temporary static HTML review-loop report, optional project fix commits, optional consolidated PR comments, and optional ready-for-human PR marker.
- Filing rule: no durable AgentOS state by default; temporary reports live under the system temporary directory; project fixes, commits, branches, and reports live in the target project; PR comments and ready markers stay in GitHub.
- Safety posture: use only after explicit review-loop authorization; keep reviewer subagents read-only; do not merge, close issues, create labels, delete branches, change permissions, push outside the target PR branch, or publish outside the PR review surface without separate approval.
- Verification coverage: confirm target/base/head and panel sizing, baseline intent, reviewer prompt templates, accepted/declined findings, sibling sweeps, validation commands, clean final reviewer panel, temporary HTML report, and absence of unapproved external writes.
- Upgrade notes: Core reusable orchestration workflow for fresh-context PR review/fix loops.

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
- Verification coverage: run the helper with default and explicit prefix/extension arguments; confirm reported paths exist and multiple paths are unique when requested; run skill validation and mirror audit after canonical changes.
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
- Mutability: local-write; external-write only if the user explicitly asks for GitHub issue edits, comments, labels, or other external state changes.
- Tools and connectors: local AgentOS files, `rg`, `git`, local validators, and GitHub issue context when issue-driven.
- Output artifact: new or updated skill, resolver guidance, manifest entry, deterministic validator, retrieval fixture, smoke example, or propagation queue proposal.
- Filing rule: canonical skills live under `os/skills/`; deterministic checks live in `os/verification/scripts/validate_agentos.py` or a clearly warranted local script; retrieval/smoke fixtures live under `os/verification/retrieval/`; unapproved durable state proposals live in the appropriate Personal Overlay propagation queue.
- Safety posture: require at least one concrete example; do not copy private connector data into durable artifacts; ask before external writes, automation activation, destructive edits, or installing harness mirrors.
- Verification coverage: run `python3 os/verification/scripts/validate_agentos.py`; run `python3 os/verification/scripts/validate_agentos.py --self-test` when validator behavior changes; add or update a safe smoke example for new durable behavior.
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
- manifest entries do not record current-machine mirror paths or state.
