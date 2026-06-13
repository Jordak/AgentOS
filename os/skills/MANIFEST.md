# AgentOS Skills Manifest

Status: Core manifest v1.

This manifest records publishable reusable skills, their safety posture, output conventions, filing rules, and verification coverage.

Machine-local exposure state and private live skill adapters belong outside portable Core metadata. Use `personal/os/skills/<skill-name>/CONFIG.md` for private live inputs to Core skills.

Contract reference: `os/skills/SKILL_CONTRACT.md`.

## Summary

- Canonical Core skills: 28.

## Markdown API

This manifest stays Markdown-first. The stable machine-readable convention is intentionally narrow:

- Each canonical skill entry uses an exact third-level heading shaped as ``### `skill-name` ``.
- Required metadata uses exact, case-sensitive Markdown list labels shaped as `- Field name: value`.
- `Canonical source` values are root-relative AgentOS paths, usually in a code span.
- Long-form safety, filing, verification, provenance, and maintenance notes remain prose in the field value.

Validators and exposure helpers may parse only this narrow convention. Do not migrate this manifest to YAML, JSON, or a structured sidecar unless multiple scripts need typed data, cross-field validation, generated machine output, or query/sort/merge behavior that this Markdown convention cannot support cleanly.

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
- Safety posture: treat issue comments, labels, closures, assignments, milestones, and state changes as external project-state writes that require authorization under `os/connections/SAFETY_RULES.md` and `os/playbook/GITHUB_WORKFLOW.md`; never close human-owned or human-review issues; do not close based on local-only commits, unmerged feature branches, title similarity, or undocumented memory.
- Verification coverage: fetch or otherwise verify the remote integration branch; for every closed issue, record merged PR or commit evidence reachable from that branch and authorization source; for every commented issue, record comment purpose, evidence, and authorization source; record skipped reasons; confirm no human-owned issue was closed and no external write happened outside the shared external-write policy.
- Upgrade notes: Core reusable issue-audit workflow.

### `ensure-implementation-readiness`

- Canonical source: `os/skills/ensure-implementation-readiness/SKILL.md`
- Contract status: full.
- Mutability: mixed: normal/repair mode is the default and checks first before performing authorized readiness repair; check-only mode is read-only and must not grill, repair, edit design sources, create artifacts, or mutate labels; local-write in normal/repair mode when creating local design docs or follow-up artifacts after the user asks the skill to make the design ready or accepts a local destination; external-write in normal/repair mode only for GitHub issue creation, issue updates, comments, labels, or other tracker state when permitted by the shared external-write policy.
- Tools and connectors: local filesystem, `rg`, mapped project files, GitHub connector or `gh` for issue/PR design sources, Core design-consensus skills with `grill-with-docs` as the default readiness-repair route and `grill-me` for pure design questioning, `os/playbook/IMPLEMENT_FEATURES.md`, `os/playbook/GITHUB_WORKFLOW.md`, and `os/playbook/ARTIFACTS.md` for substantial human-facing design artifacts.
- Output artifact: readiness report with exactly one verdict, `Ready to Implement`, `Needs Design Consensus`, or `Gate Skipped`, plus mode used, source reviewed, readiness fields, consensus provenance, missing evidence or missing consensus evidence, gate-skip field/state, `Gate Skipped` reason and durable gate-skip record location when present, any proposed source update when readiness repair or bypass recording could not be completed, final readiness label state, optional durable follow-up artifacts, approved source-design updates, selected design-consensus route, and PR-body readiness fields for PR-bound work.
- Filing rule: operational readiness contract lives in `os/skills/ensure-implementation-readiness/SKILL.md`; policy overview and filing guidance live in `os/playbook/IMPLEMENT_FEATURES.md`; local design artifacts default to the mapped project's design-doc convention or `docs/design/issue-<number>-implementation-readiness.md`; private/personal design notes belong in the Personal Overlay; approved GitHub updates stay in GitHub.
- Safety posture: do not treat missing readiness fields as silently ready; in check-only mode, report missing fields or evidence without prompting or editing; in normal/repair mode, infer and confirm with the user before implementation proceeds, then update or propose the full readiness field set; do not treat durable design existence, an agent-authored artifact, a freeform GitHub comment, or a Calling Workflow handoff as consensus without valid consensus provenance; count human-attested GitHub comments only when they explicitly attest human authorship and come from a trusted repository author relationship; treat those comments as non-adversarial operational provenance signals, not security guarantees; do not allow chat-only consensus to become the first implementation commit; when repairing consensus, carry resolved answers into the durable design source before reporting `Ready to Implement`; for intentional bypasses, return `Gate Skipped` only after updating the durable source's `Gate skipped:` field with the bypass reason and missing evidence, and otherwise report the proposed update with `Needs Design Consensus`; remove `needs design consensus` or equivalent labels only under this skill's normal/repair contract after valid provenance and explicit human confirmation; leave the label in place for `Gate Skipped`; require approval through the shared external-write policy before external tracker writes; do not leave meaningful deferred questions only in chat, model memory, or unpersisted reports.
- Verification coverage: confirms the target was classified as gated, exempt, or explicitly bypassed, the selected mode was honored, the durable source, readiness fields, consensus provenance, gate-skip field/state, `Gate Skipped` reason and durable gate-skip record location when present, any proposed source update when readiness repair or bypass recording could not be completed, final readiness label state, missing consensus evidence when present, and relevant issue labels were checked, missing readiness-field inference followed the selected mode, human-attested GitHub comments counted only with explicit attestation and trusted author evidence as non-adversarial operational provenance rather than a security guarantee, the design-consensus route was selected appropriately with `grill-with-docs` as the default repair route, `grill-me` for pure design questioning, and targeted questions only as support, residual clarification, or a documented unavailable-or-excessive fallback, resolved answers were captured durably before `Ready to Implement`, readiness labels were cleaned up only by this skill in normal/repair mode or left for `Gate Skipped`, deferred follow-up artifacts were created where required, external writes complied with the shared external-write policy, and PR-bound `Gate Skipped` work names durable gate-skip evidence for intentional bypasses while unavailable writes report a proposed update with `Needs Design Consensus`; run `scripts/run-validator` after skill or manifest changes.
- Upgrade notes: Core reusable gate and readiness-repair workflow for feature-sized implementation work.

### `implement-github-issue`

- Canonical source: `os/skills/implement-github-issue/SKILL.md`
- Contract status: full.
- Mutability: mixed: normal invocation on a GitHub issue authorizes the workflow to invoke or follow `ensure-implementation-readiness` in normal/repair mode with an Authorization Boundary for issue-body/design-source readiness evidence and existing readiness labels; existing non-readiness workflow-label hygiene within the assigned issue scope such as verified stale `blocked` label removal; issue or PR evidence comments; caller-supplied result-surface handling when invoked as a durable Called Workflow and the supplied surface is inside the Authorization Boundary; feature-branch pushes; PR creation with readiness fields; and `review-loop` invocation with its ordinary PR-scoped writes; read-only mode inspects and reports without local or external writes.
- Tools and connectors: local filesystem, `git`, `rg`, project validation commands, project-local domain docs (`DOMAIN.md`/`DOMAIN-MAP.md`, with legacy `CONTEXT.md`/`CONTEXT-MAP.md` aliases) when relevant, GitHub connector or `gh`, repository-local push helpers when local instructions require them, `os/skills/ensure-implementation-readiness/SKILL.md`, `os/playbook/IMPLEMENT_FEATURES.md`, repository GitHub workflow guidance such as `os/playbook/GITHUB_WORKFLOW.md`, `os/skills/review-loop/SKILL.md`, `os/skills/ORCHESTRATION_LOOPS.md` including optional caller-supplied Workflow Invocation References and release instructions, background loop-composition rationale in `docs/adr/0009-contract-based-orchestration-loops.md` and `docs/design/issue-121-loop-composition-conventions.md`, and landing/closure boundary rationale in `docs/design/issue-126-landing-closure-semantics.md`.
- Output artifact: a pull request with readiness fields, review-loop convergence evidence, and a recoverable Workflow Result returned in the current reporting mode or caller-supplied Workflow Invocation Reference, with terminal status (`completed`, `blocked`, `failed`, `cancelled`, or `needs-human`), issue URL and final issue labels, branch/worktree, PR, raw readiness evidence or provenance, readiness verdict, final readiness label state, `Gate Skipped` reason plus durable gate-skip field/state or missing consensus evidence when present, validation, mutations, review-loop status, open risks, release-instruction handling, and recommended next action for the integration owner.
- Filing rule: canonical workflow guidance lives in `os/skills/implement-github-issue/SKILL.md`; issue-specific readiness evidence stays wherever `ensure-implementation-readiness` places it under project policy; PR and review-loop evidence stay on the PR surface or in review-loop temporary reports; reusable project improvements or out-of-scope work belong in the issue tracker or project-approved propagation destination rather than silent scope expansion.
- Safety posture: normal invocation is explicit authorization for the skill's ordinary happy-path writes unless the caller narrows the Authorization Boundary to read-only mode; never merge PRs, close issues, or delete branches through this skill; always ask before permission changes, creating new labels, posting outside the target issue or PR scope, pushing outside the target feature branch, changing repository settings, credentials or MFA, or any external action outside the skill contract; invoke or follow `ensure-implementation-readiness` in normal/repair mode and stop when readiness is not ready unless repaired by that skill or re-followed with an explicit user bypass that returns `Gate Skipped`; do not synthesize an agent-authored design artifact and treat it as consensus; do not remove `needs design consensus` or equivalent readiness labels directly because readiness-label cleanup belongs to `ensure-implementation-readiness`; treat human-owned, HITL, blocked, `ready-for-human`, `needs-human`, `needs-a-human`, or equivalent labels as a Blocking Human Decision unless the current request explicitly authorizes continuing, the repository's label or triage owner resolves the human-owned or human-review state, or the only blocker is a stale `blocked` label whose blocking dependency is verifiably resolved and can be removed under repository label policy; readiness repair may resolve readiness evidence, fields, and authorized readiness-label hygiene under the readiness skill contract, but does not by itself clear human-owned, HITL, or human-review states.
- Verification coverage: confirm local instructions, readiness policy, GitHub workflow policy, and `review-loop` contract were honored; confirm `ensure-implementation-readiness` was invoked in normal/repair mode, including any explicit bypass path that returns `Gate Skipped`; confirm raw readiness evidence or provenance, readiness verdict, final readiness label state, and `Gate Skipped` reason plus durable gate-skip field/state or missing consensus evidence when present, including that readiness repair writes or approved design-source updates were followed by re-running or re-following readiness against the updated durable source before implementation; confirm readiness-label cleanup was performed only by `ensure-implementation-readiness` or left for `Gate Skipped`; confirm human-owned/HITL/blocked/human-review label handling including verified stale-`blocked` removal when used, branch/worktree checkpoint, caller-supplied Workflow Invocation Reference or result-surface handling when present, release-instruction handling, Recovery Checkpoints before external writes and called workflows, preserved unrelated changes, validation commands, PR readiness fields, review-loop result or skip reason, recoverable Workflow Result fields, and absence of merge, issue closure, branch deletion, permission, new-label, or out-of-scope external actions outside the skill contract; run `git diff --check` and `scripts/run-validator` after skill or manifest changes.
- Upgrade notes: introduced for GitHub Issue #125 as the single-issue implementation orchestration skill; keep the happy path narrow, stop at reviewed PR evidence, and defer merge, issue closure, multi-issue selection, parallel workers, and broader landing semantics to later workflows such as a future `coordinate-issue-batch`.

### `land-github-issue`

- Canonical source: `os/skills/land-github-issue/SKILL.md`
- Contract status: full.
- Mutability: mixed: normal landing mode mutates the target issue only when the Authorization Boundary explicitly permits target-issue checklist edits, issue comments needed for recovery or closure evidence, and issue closure; read-only mode is an explicit narrowing; checklist-update-only and comment-authorized modes are narrower mutating modes; no PR merge, branch deletion, worker spawning, label creation, permission change, or mutation outside the target issue.
- Tools and connectors: local filesystem, `git`, especially fetch and integration-branch reachability checks; GitHub connector or `gh` for issue, PR, commit, label, body-edit, comment, and closure operations when authorized; `os/playbook/GITHUB_WORKFLOW.md`; `os/skills/audit-issues/SKILL.md`; and `os/skills/ORCHESTRATION_LOOPS.md`.
- Output artifact: Workflow Result naming issue URL, labels, integration branch, evidence checked, fulfilled acceptance criteria, unmet or ambiguous acceptance criteria, checklist mutations made or proposed, closure action or blocker, validation, open risks, and recommended Calling Workflow action.
- Filing rule: canonical workflow guidance lives in `os/skills/land-github-issue/SKILL.md`; issue-specific closure evidence and checklist state stay on the GitHub issue; caller ledgers and broader integration decisions belong to the Calling Workflow; broader stale-issue sweeps stay with `audit-issues`; implementation recovery belongs to `implement-github-issue` or a follow-up issue when the caller decides more work is needed.
- Safety posture: require an explicit Authorization Boundary before issue-body edits, issue comments, or closure; verify acceptance criteria against evidence reachable from the remote integration branch; check off only fulfilled Markdown checkbox criteria; leave unmet or ambiguous criteria unchecked and return them to the caller; treat obsolete, disputed, or supposedly out-of-scope criteria as closure blockers until the issue body is updated under authorization; never close based on local commits, unmerged feature branches, title similarity, local-only inspection, or unchecked assumptions; do not close human-owned or human-review issues; do not merge PRs, delete branches, spawn workers, create labels, change permissions, or mutate out-of-target issue state.
- Verification coverage: confirm local instructions, GitHub workflow policy, `audit-issues`, and orchestration-loop guidance were honored; confirm target issue, repository, integration branch, and Authorization Boundary; fetch or otherwise verify the remote integration branch; check evidence PRs or commits for reachability; classify every acceptance criterion; update or propose fulfilled checkboxes while preserving unmet and ambiguous criteria; block closure when criteria, integration evidence, authorization, issue-comment authorization, or human-review state is incomplete; record a recoverable Workflow Result; run `git diff --check` and `scripts/run-validator` after skill or manifest changes.
- Upgrade notes: introduced for GitHub Issue #128 as the one-issue landing and closure workflow after integration evidence exists.

### `select-issue-batch`

- Canonical source: `os/skills/select-issue-batch/SKILL.md`
- Contract status: full.
- Mutability: read-only by default for local files, GitHub, branches, worktrees, issues, labels, and PRs; if the user asks to turn a recommendation into tracker updates, worker launch, branch creation, issue comments, labels, or PR work, stop after the recommendation and tell the caller or user to explicitly invoke `coordinate-issue-batch` or another authorized mutating workflow in a separate step.
- Tools and connectors: local filesystem and `git` for repository identity and local policy files; read-only GitHub connector or `gh` for issue and PR metadata; `os/playbook/GITHUB_WORKFLOW.md`; `os/skills/ORCHESTRATION_LOOPS.md`; and mutating coordination workflow contracts when the user wants execution after selection.
- Output artifact: Markdown recommendation report with ranked issues, rationale, raw readiness and blocker evidence, stale-label checks, recommended first lanes, parallel-safety assessment, rejected or deferred candidates, assumptions, and coordinator handoff notes.
- Filing rule: default output stays in chat; no durable AgentOS state is created by default; approved execution plans, recovery records, issue or PR comments, branch and worktree state, or coordinator ledgers belong to the downstream coordinator or approved mutating workflow that owns execution or coordination.
- Safety posture: do not mutate GitHub, branches, worktrees, local files, labels, issue state, PR state, or repository settings by default; do not spawn workers or start execution from this skill; treat `blocked`, `HITL`, `ready-for-agent`, `ready-for-human`, `needs-human`, `needs-a-human`, and similar labels as candidate-state evidence to verify, not as truth or automatic selection blockers; do not turn normal starting states such as `needs design consensus`, missing readiness evidence, missing readiness fields, sparse acceptance criteria, or HITL participation into selector-level Blocking Human Decisions; do not return final `Ready to Implement`, `Needs Design Consensus`, or `Gate Skipped` verdicts because those belong to `ensure-implementation-readiness`; if the user asks for external writes, execution, or coordination, stop after the recommendation and tell the caller or user to explicitly invoke `coordinate-issue-batch` or another authorized mutating workflow in a separate step.
- Verification coverage: confirm the target repository and inspected issue scope, read-only posture, label and blocker inspection, stale-label checks, raw readiness evidence, absence of selector-owned readiness verdicts, future-leverage ranking rationale, candidate-state handling of current blocked/HITL/human-review evidence without automatic exclusion, recommended first lane for each selected issue when readiness or human participation affects handoff, inclusion rationale for each selected issue, parallel-safety assessment, absence of external writes or branch/worktree/worker actions, and `git diff --check` plus `scripts/run-validator` after skill or manifest changes.
- Upgrade notes: introduced for GitHub Issue #129 as the read-only issue-selection planner; keep selection and explanation separate from worker execution or tracker mutation, even when a mutating coordinator invokes the planner as its read-only selection phase.

### `coordinate-issue-batch`

- Canonical source: `os/skills/coordinate-issue-batch/SKILL.md`
- Contract status: full.
- Mutability: mixed: normal mode may perform ordinary coordinator writes inside the Authorization Boundary, including read-only issue selection, coordinator checks, ledger or checkpoint updates on authorized surfaces, caller-supplied result-surface handling when invoked as a durable Called Workflow, branch/worktree/thread setup for supported workers, supported public-safe worker-thread renaming before `READY` or substantive assignment, callback/invocation-reference handoff, minimal pointer-first worker handoff packets, and worker launch; read-only/plan-only mode performs no worker launch, tracker mutation, branch/worktree creation, or external writes; resume mode rebuilds or loads the coordinator ledger and continues under the current Authorization Boundary.
- Tools and connectors: local filesystem, `git`, `rg`, GitHub connector or `gh`, repository-local push helpers when required, `os/skills/select-issue-batch/SKILL.md`, `os/skills/implement-github-issue/SKILL.md`, `os/skills/land-github-issue/SKILL.md`, `os/skills/ORCHESTRATION_LOOPS.md`, and `os/playbook/GITHUB_WORKFLOW.md`; in Codex harnesses that support branch-backed project threads, durable implementation workers should use separate branch-backed threads rather than in-thread subagents.
- Output artifact: coordinator Workflow Result plus a recoverable coordinator ledger or report naming terminal status (`completed`, `blocked`, `failed`, `cancelled`, or `needs-human`), selected or provided issues, ledger location, worker branches, worktrees, PRs, worker lifecycle states and needs-human decisions, worker-reported raw readiness evidence, worker-reported readiness verdict, final readiness label state, `Gate Skipped` reasons plus durable gate-skip field/state or missing evidence when present, stale-label contradictions, public-safe thread names and invocation references or redacted private-surface summaries, merge-event state, landing outcomes, skipped issues, blockers, release-instruction handling, validation, mutations performed, open risks, and recommended next action; return the result through a caller-supplied Workflow Invocation Reference when available; report detailed child outcomes for mixed aggregate results while aggregate status precedence and richer status maps remain deferred to GitHub issue #158; optional dedicated GitHub batch tracking issue only when explicitly authorized.
- Filing rule: canonical workflow guidance lives in `os/skills/coordinate-issue-batch/SKILL.md`; batch-run ledgers default to the invocation-owned coordinator surface; dedicated GitHub batch tracking issues are optional recovery surfaces and require explicit authorization; per-issue implementation-readiness gates, repair, verdicts, and related label changes stay with assigned issue workflows; issue-specific closure evidence and checklist state stay on GitHub through `land-github-issue`.
- Safety posture: do not merge or squash PRs, delete branches, create labels, change permissions or settings, handle credentials or MFA, read or write Personal Overlay state, or write outside the coordinator's assigned scope unless another approved workflow or explicit user authorization owns that action; do not close issues directly and use `land-github-issue` for eligible merged issues when closure is authorized; do not launch non-parallel-safe batches or silently downgrade them to sequential execution; keep workers scoped to their assigned issue and boundary context rather than the full batch ledger; use callback-first Workflow Results instead of continuous worker polling except for bounded bootstrap, timeout, recovery, or diagnostic behavior; pass raw readiness and stale-label evidence to assigned issue workflows but do not decide implementation readiness or perform readiness-label hygiene in the coordinator.
- Verification coverage: confirm local instructions, GitHub workflow policy, orchestration-loop guidance, directly called skill contracts, mode, Authorization Boundary, caller-supplied Workflow Invocation Reference or result-surface handling when present, release-instruction handling, selection or provided-batch source, parallel-safety checks, raw readiness evidence handoff without coordinator readiness verdict decisions, preservation of worker-reported raw readiness evidence, worker-reported readiness verdict, final readiness label state, `Gate Skipped` reasons plus durable gate-skip field/state or missing evidence, and stale-label contradictions in ledger and final result surfaces, ledger surface, Recovery Checkpoints, worker handoffs with Workflow Invocation References and release instructions when supported, public-safe or redacted/private-surface handling for thread names and invocation references, supported worker-thread renaming to public-safe names before `READY` or substantive assignment, Codex branch-backed thread behavior when applicable, absence of continuous worker polling except recorded bounded bootstrap/timeout/recovery/diagnostics, absence of unauthorized merges/closures/branch deletion/label creation/permission changes/Personal Overlay access, worker quiescence including canonical terminal status, needs-human handling, release handling or unavailable/not-applicable reasons, and human merge reports before landing, eligible merged issue landing through `land-github-issue`, final Workflow Result fields, `git diff --check`, and `scripts/run-validator`.
- Upgrade notes: introduced for GitHub Issue #132 as the full batch-pass coordinator that composes read-only selection, isolated implementation workers, human PR merge events, and eligible issue landing while keeping `select-issue-batch`, `implement-github-issue`, and `land-github-issue` caller-independent.

### `github-loop`

- Canonical source: `os/skills/github-loop/SKILL.md`
- Contract status: full.
- Invocation contract: prose-only inbound in v1. A caller may ask `github-loop` to start or resume in the current conversation, thread, or reporting surface, but `github-loop` itself does not accept a caller-supplied Workflow Invocation Reference, result surface, or release instruction; callback-first references and release instructions are downstream handoff fields for called `coordinate-issue-batch` invocations.
- Mutability: mixed: normal mode may perform ordinary loop writes inside the Authorization Boundary, including loop Recovery Checkpoints on authorized surfaces, callback-first called-workflow handoff packets, durable called-workflow launches when the harness supports them, supported public-safe child coordinator thread renaming to legible target-specific names before assignment or `READY`, post-create/resume/rename checkpointing of actual child coordinator references before assignment or `READY`, and resume requests to `coordinate-issue-batch`; invoking `github-loop` in normal or resume mode is the explicit request to create separate durable coordinator child threads when the active harness supports them; read-only/plan-only mode performs no coordinator launch, tracker mutation, branch/worktree creation, worker launch, issue edit, label change, PR work, or local tracked-file mutation; resume mode rebuilds or loads the loop Recovery Record and continues under the current Authorization Boundary.
- Tools and connectors: local filesystem, `git`, `rg`, GitHub connector or `gh`, repository-local push helpers when required, `os/skills/coordinate-issue-batch/SKILL.md`, `os/skills/ORCHESTRATION_LOOPS.md`, and `os/playbook/GITHUB_WORKFLOW.md`; when a harness supports durable called-workflow launches, each normal batch pass should run as a separate recoverable `coordinate-issue-batch` invocation, with same-thread execution only as a recorded fallback that keeps loop and batch recovery records distinct.
- Output artifact: GitHub loop Workflow Result plus a recoverable loop Recovery Record naming terminal status (`completed`, `blocked`, `failed`, `cancelled`, or `needs-human`), repository, loop goal, mode, Authorization Boundary, loop caps, pass count, public-safe child coordinator thread names or unavailable reasons, called batch-pass invocation references or public-safe summaries, called batch-pass results, worker-reported raw readiness evidence, worker-reported readiness verdict, final readiness label state, `Gate Skipped` reasons plus durable gate-skip field/state or missing evidence when present, stale-label contradictions, merge-report state, blockers, needs-human decisions, failures, cancellations, downstream release-instruction handling, stop reason, validation, mutations performed, open risks, and recommended next action; report detailed child outcomes for mixed aggregate results while aggregate status precedence and richer status maps remain deferred to GitHub issue #158; optional dedicated GitHub tracking issue only when explicitly authorized.
- Filing rule: canonical workflow guidance lives in `os/skills/github-loop/SKILL.md`; loop-run ledgers default to the invocation-owned reporting surface; dedicated GitHub tracking issues are optional recovery surfaces and require explicit authorization; batch ledgers, worker states, landing queues, and issue-specific closure evidence stay with `coordinate-issue-batch` and its called workflows; issue implementation-readiness gates, repair, verdicts, and related label hygiene stay with assigned issue workflows through their readiness contracts.
- Safety posture: do not run issue selection, launch implementation workers, or land issues directly; invoke or resume `coordinate-issue-batch` for each full batch pass; use callback-first Workflow Results instead of continuously polling `coordinate-issue-batch` except for bounded bootstrap, timeout, recovery, or diagnostic behavior; do not start a later batch while the current batch has failed or cancelled workers, a failed or cancelled batch pass, blocked workers or issues, needs-human states, unresolved Blocking Human Decisions, ready PRs waiting on human merge reports, or incomplete landing decisions; do not silently broaden the selection goal when no issues are selected; do not merge or squash PRs, close issues, delete branches, create labels, change permissions or settings, handle credentials or MFA, read or write Personal Overlay state, or write outside the loop's assigned scope unless another approved workflow or explicit user authorization owns that action.
- Verification coverage: confirm local instructions, GitHub workflow policy, orchestration-loop guidance, and `coordinate-issue-batch` were honored; confirm mode, loop goal, caps, Authorization Boundary, and prose-only inbound invocation contract, Recovery Checkpoints before batch launch or resume, separate durable called-workflow invocation for each normal/resume batch pass when supported or recorded same-thread fallback reason, supported public-safe child coordinator thread renaming before assignment or `READY`, post-create/resume/rename checkpointing of actual child coordinator thread name, invocation reference or result surface, redaction or unavailable reason, and release instruction before assignment or `READY`, Workflow Invocation Reference and release instruction for called batch passes when supported, release-instruction handling in called results and downstream loop reporting, preservation of worker-reported raw readiness evidence, worker-reported readiness verdict, final readiness label state, `Gate Skipped` reasons plus durable gate-skip field/state or missing evidence, and stale-label contradictions from called batch results, absence of continuous coordinator polling except recorded bounded bootstrap/timeout/recovery/diagnostics, absence of direct issue selection/worker launch/landing, clean-settled prior batch before any later batch starts, failed/cancelled/blocked/needs-human/unmerged/human-decision stop handling, final Workflow Result fields, absence of unauthorized merge/closure/branch deletion/label creation/permission changes/out-of-scope external writes/Personal Overlay access, `git diff --check`, and `scripts/run-validator`.
- Upgrade notes: introduced for GitHub Issue #151 as the repository-level repeated batch-pass loop above `coordinate-issue-batch`; keep v1 conservative and preserve caller-independent contracts for `select-issue-batch`, `coordinate-issue-batch`, `implement-github-issue`, and `land-github-issue`.

### `grill-me`

- Canonical source: `os/skills/grill-me/SKILL.md`
- Contract status: partial.
- Mutability: read-only.
- Tools and connectors: user-provided plan or design context and local codebase exploration when a question can be answered from the codebase.
- Output artifact: a conversational grilling session that walks the design tree one question at a time and includes a recommended answer for each question.
- Filing rule: output stays in chat or the invoking workflow's result artifact by default; the vendored upstream skill does not create durable AgentOS state by itself.
- Safety posture: read-only; ask questions, inspect local evidence when available, and do not edit files or perform connector or external writes as part of this skill.
- Verification coverage: confirm the vendored `SKILL.md` matches `mattpocock/skills` at the recorded `UPSTREAM.md` ref, the source-routing fixture resolves to `grill-me`, the vendored upstream freshness check reports `grill-me` up-to-date, and `scripts/run-validator` plus `git diff --check` pass after skill or manifest changes.
- Upgrade notes: vendored from `mattpocock/skills` for GitHub Issue #122; preserve `UPSTREAM.md`, keep the skill aligned with upstream, and avoid local AgentOS behavior patches unless a future issue explicitly approves them.

### `grill-with-docs`

- Canonical source: `os/skills/grill-with-docs/SKILL.md`
- Contract status: partial.
- Mutability: mixed: interviews are read-only until a project documentation update is agreed; local-write for glossary or ADR updates during an approved project documentation workflow; no connector or external-write behavior by itself.
- Tools and connectors: user-provided plan or design context, local repository code, existing `CONTEXT.md`/`CONTEXT-MAP.md` domain docs, `docs/adr/`, and no external connectors by default.
- Output artifact: conversational design-consensus interview plus inline project documentation updates when the session resolves glossary terms or ADR-worthy decisions and local write scope is approved.
- Filing rule: keep the vendored upstream skill files mirrored exactly from `mattpocock/skills`; project glossary updates follow upstream `CONTEXT.md`/`CONTEXT-MAP.md` conventions; ADRs live under the target project's `docs/adr/`; AgentOS-specific adaptation should live in callers, repository instructions, or future upstream-aligned changes rather than patching the mirrored skill body.
- Safety posture: ask one question at a time, recommend a default answer without treating it as consent, inspect local code/docs instead of asking when the answer can be discovered safely, and do not post GitHub comments, edit issue bodies, label, commit, push, merge, close issues, or perform external writes; tracked-file documentation edits require the user's approved write scope or a calling workflow that already owns those writes.
- Verification coverage: confirm the upstream files are mirrored exactly except for AgentOS `UPSTREAM.md`, confirm provenance points at a full GitHub commit SHA, confirm manifest metadata uses the Markdown API, and run `scripts/run-validator` plus `git diff --check` after skill or manifest changes.
- Upgrade notes: vendored from `mattpocock/skills` path `skills/engineering/grill-with-docs/` at ref `e3b90b5238f38cdea5996e16861dcae28ef52eda`; preserve companion references and `UPSTREAM.md`, keep upstream files mirrored exactly unless a future issue explicitly approves a local patch, and run `expose-skills` dry run when current-machine discoverability matters after accepted updates.

### `vendor-skill`

- Canonical source: `os/skills/vendor-skill/SKILL.md`
- Contract status: full.
- Mutability: mixed: read-only while auditing upstream source, license, provenance, and existing Core state; local-write when the user asks to vendor or update Core skill files, manifest entries, provenance, or safe fixtures; external-write only under the shared GitHub/external-write policy for issue body edits, labels, PRs, comments, pushes, or other tracker/repository state.
- Tools and connectors: local filesystem, `rg`, `git`, `curl` or `gh` for public GitHub source reads, raw upstream file comparisons, `os/skills/check-vendored-skill-upstreams/`, `os/skills/expose-skills/`, AgentOS validators, and GitHub issue/PR tooling when the vendoring work is issue-driven.
- Output artifact: a Core skill directory under `os/skills/<skill-name>/`, `UPSTREAM.md` provenance with license notice, manifest metadata, optional source-routing fixture, and a concise vendoring report naming source, ref, license, local patches, validation, and blockers.
- Filing rule: canonical vendored skills live under `os/skills/`; source and license provenance lives in each skill's `UPSTREAM.md`; Core maintenance metadata lives in `os/skills/MANIFEST.md`; current-machine adapter state stays out of Core and is handled by `expose-skills`; unresolved source/license questions belong in the issue tracker or calling workflow, not in guessed provenance.
- Safety posture: support only public GitHub upstreams with machine-checkable paths and full commit SHAs in v1; stop for human review on private repos, non-GitHub sources, current-machine installed/global adapters, missing or ambiguous licenses, incompatible terms, or non-machine-checkable refs; do not broaden validators or freshness checkers to make incorrect provenance pass; ask before external writes or current-machine exposure changes.
- Verification coverage: confirm source/path/ref, license usability and included notice, listed vendored files, exact raw upstream diffs unless local patches are explicitly documented, honest manifest contract status, `git diff --check`, `scripts/run-validator`, upstream-checker self-test when relevant, supported upstream freshness check when available, `expose-skills` dry run when discoverability matters, and absence of private state or current-machine adapter paths in Core.
- Upgrade notes: introduced from GitHub Issue #138 after the #122/#123 vendoring pilots; keep source-first, license-first behavior conservative until a separate issue expands supported upstream types or license policy.

### `refresh-benchmark-status`

- Canonical source: `os/skills/refresh-benchmark-status/SKILL.md`
- Contract status: full.
- Mutability: mixed: read-only when inspecting benchmark status and local evidence; local-write when updating `os/verification/BENCHMARK_STATUS.md` from eligible evidence after the user requested or approved the refresh; no external-write behavior.
- Tools and connectors: local filesystem, local `git`, `os/verification/scripts/refresh_benchmark_status.py`, `os/verification/scripts/apply_benchmark_status_candidate.py`, `os/verification/BENCHMARKS.json`, `os/verification/BENCHMARK_STATUS.md`, local Personal Overlay benchmark reports, and `os/playbook/PERSONAL_OVERLAY.md`.
- Output artifact: an updated or proposed Core benchmark status snapshot plus a concise refresh report naming eligible evidence, ineligible evidence, stale entries, public-safe non-passing details, and unchanged entries.
- Filing rule: Core status lives in `os/verification/BENCHMARK_STATUS.md`; raw reports and run histories stay in the Personal Overlay report directories configured by `os/verification/BENCHMARKS.json`; deterministic candidate generation lives in `os/verification/scripts/refresh_benchmark_status.py`, and approved Core status writes use `os/verification/scripts/apply_benchmark_status_candidate.py` with public-safe candidate facts only.
- Safety posture: do not copy raw reports, run JSON, transcripts, stdout, stderr, local paths, prompts, session details, account details, private diagnostics, private evidence, or verbatim judge rationales into Core; require clean, fresh `main` evidence before marking entries `passing`; ask before caveated or ambiguous updates.
- Verification coverage: confirm benchmark manifest and status file were read, local report paths were resolved through the Personal Overlay rule, the deterministic helper ran or manual inspection was justified, used reports had current-schema Git metadata, each non-passing status-counting result has a public-safe detail row or an explicit unchanged-entry reason, status labels are allowed, no raw/private evidence was copied into Core, and refresh-helper/applicator self-tests plus `scripts/run-validator` pass after helper, skill, or status changes.
- Upgrade notes: Core workflow for maintaining the public-safe benchmark snapshot without introducing Core benchmark history.

### `run-benchmarks`

- Canonical source: `os/skills/run-benchmarks/SKILL.md`
- Contract status: full.
- Mutability: mixed: reads Core benchmark configuration and runs local benchmark scripts; local-write when scripts save reports under configured Personal Overlay report directories and when `refresh-benchmark-status` updates `os/verification/BENCHMARK_STATUS.md` after the user requested or approved the refresh; no external-write behavior.
- Tools and connectors: local `git`, filesystem, `os/verification/BENCHMARKS.json`, configured benchmark scripts, `os/playbook/PERSONAL_OVERLAY.md`, `os/skills/refresh-benchmark-status/SKILL.md`, `os/verification/scripts/refresh_benchmark_status.py`, and `os/verification/scripts/apply_benchmark_status_candidate.py` through the refresh workflow.
- Output artifact: concise benchmark run report naming commands, saved report directories, incompatible scripts, visible pass/fail/unavailable posture, and status-refresh outcome.
- Filing rule: raw reports and run histories stay in Personal Overlay report directories configured by `BENCHMARKS.json`; Core status changes only through `refresh-benchmark-status`; benchmark CLI standardization is deferred to GitHub Issue #33; deterministic status-refresh candidate generation lives in `os/verification/scripts/refresh_benchmark_status.py`, and approved status-file application lives in `os/verification/scripts/apply_benchmark_status_candidate.py`.
- Safety posture: ask before external harnesses, model-call benchmarks, or commands that may spend credits or require authenticated CLIs; run current status-refresh targets from a clean remote-fresh git checkout when they need Git metadata or index state; run export-compatible diagnostic harnesses from a sanitized Core-only checkout or export unless the user explicitly accepts primary-checkout risk; do not copy raw/private benchmark evidence into Core; do not produce status-eligible evidence unless the checkout is clean, current `main`, and using the canonical or user-assigned Personal Overlay report directories.
- Verification coverage: confirm benchmark manifest and Personal Overlay policy were read, configured report directories were resolved through the Personal Overlay rule, script help was inspected, manifest entries were classified by `weekly_review.check_freshness`, compatible scripts and harness choices were selected from the CLI contract, dry-runs and `check_freshness: false` suites were treated as diagnostic/current-status-ineligible, Git preflight ran before status-eligible saved reports, model-call work was approved and run from the required root shape, and status refresh ran or was followed in proposal/report mode unless blocked or declined.
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
- Tools and connectors: local filesystem, `git`, `rg`, optional GitHub connector or `gh` reads for PR metadata, review subagents when available and authorized by an explicit review-pass or reviewer-panel request, or by a caller such as `review-loop`, `make-temp-file` for optional packet paths, the canonical packet template under `os/skills/review-pass/references/review-packet-template.md`, per-lens prompt references under `os/skills/review-pass/references/lenses/`, and the vendored review skills as source material for lens guidance.
- Output artifact: structured Markdown review packet following `os/skills/review-pass/references/review-packet-template.md`, with target, baseline intent, effort metadata when available and relevant, panel table, coverage, issue families, verification results, recommended dispositions, design-escape-hatch concerns, reviewer crosswalk, residual risks, reviewer continuity mode and handle availability when applicable, optional caller-private continuity handoff, and optional temporary packet path.
- Filing rule: no durable AgentOS state by default; chat output by default; optional temporary packet files live under the system temporary directory; project fixes, PR comments, pushes, ready markers, and durable loop ledgers belong to callers such as `review-loop`.
- Safety posture: read-only reviewer-panel workflow; treat an explicit review-pass or reviewer-panel request as authorization for read-only reviewer subagents when the harness supports them; do not edit files, commit, push, merge, comment on PRs, label, close issues, mark ready, change permissions, run validation commands that may dirty the checkout, expose opaque reviewer handles, or perform external writes; keep spawned or resumed reviewers read-only and close them after each pass.
- Verification coverage: confirm target/base/head, mode, baseline-intent source or limitation, effort metadata when available or relevant, reviewer count, lens plan, reviewer authorization or fallback, reviewer continuity mode and opaque handle availability when applicable, current prompt templates, canonical packet template usage, assigned per-lens reference files, dirty-validation rule, optional caller adjudication context in verification mode, Contract Surface Matrix review for skill/workflow contract changes, deep-review and structural-depth instructions when assigned, issue-family normalization, recommended dispositions, sibling-search suggestions, validation signals, reviewer closure, and absence of target, PR, issue, handle exposure, or external writes.
- Upgrade notes: Core reusable read-only panel-pass workflow introduced by GitHub Issue #54; `review-loop` depends on it for fresh and verification reviewer-panel mechanics.

### `review-loop`

- Canonical source: `os/skills/review-loop/SKILL.md`
- Contract status: full.
- Mutability: mixed: reads local code, GitHub PR metadata, and review context; may delegate read-only reviewer-panel passes to subagents through `review-pass`, edit project files to fix `auto-fix` and explicit `user-approved-fix` issue families, create fix commits, push those fixes to a target PR branch, post consolidated Agent Review PR comments, apply the repository's established ready-for-human marker only when no unresolved `auto-fix` or `ask-user` blockers remain, and write a temporary HTML report when explicitly authorized for a review loop.
- Tools and connectors: `os/skills/review-pass/SKILL.md` for fresh and verification reviewer-panel passes, local `git`, project validation commands, GitHub connector or `gh`, `make-temp-file`, `os/skills/ensure-implementation-readiness/SKILL.md` in check-only mode, `os/skills/ORCHESTRATION_LOOPS.md` for effort guidance and workflow-result conventions, `os/playbook/IMPLEMENT_FEATURES.md`, `os/playbook/ARTIFACTS.md`, and `os/playbook/GITHUB_WORKFLOW.md`.
- Output artifact: temporary static HTML review-loop report with effort metadata when available and relevant, early `blocked` result when check-only readiness fails before reviewers spawn, optional `auto-fix` and `user-approved-fix` project fix commits, optional consolidated PR comments, and optional ready-for-human PR marker after no unresolved `auto-fix` or `ask-user` blockers remain.
- Filing rule: no durable AgentOS state by default; temporary reports live under the system temporary directory; project fixes, commits, branches, and reports live in the target project; PR comments and ready markers stay in GitHub.
- Safety posture: use only after explicit review-loop authorization; treat `review-pass` panel requests as permission for read-only reviewer subagents when the harness supports them; delegate reviewer-panel mechanics to read-only `review-pass`; do not fix `ask-user` families before an explicit `user-approved-fix` decision; do not mark ready with unresolved `auto-fix` or `ask-user` blockers; keep opaque reviewer handles out of reviewer prompts, PR comments, public reports, and human-facing packets; run or follow `ensure-implementation-readiness` in check-only mode for feature-sized PRs before reviewers start; return `blocked` before spawning reviewers when check-only reports `Needs Design Consensus`; do not grill, repair design sources, add readiness fields, or mutate readiness labels inside `review-loop`; do not merge PRs, close issues, or delete branches through `review-loop`; route those actions to a landing-capable workflow or direct human integration step whose contract owns them; ask before creating labels, changing permissions, pushing outside the target PR branch, or publishing outside the PR review surface.
- Verification coverage: confirm target/base/head and review-pass sizing, `ensure-implementation-readiness` check-only result of `Ready to Implement` or `Gate Skipped` for feature-sized targets, early `blocked` status before reviewer spawning when readiness is missing with check-only mode, source reviewed, verdict, missing consensus evidence, gate-skip state, label state, and next repair owner, baseline intent, review-pass template usage, Contract Surface Matrix use or explicit skip for semantic contract changes, `review-pass` panel authorization or fallback, orchestration-loop effort guidance and prescribed/effective effort reporting when relevant, verification reviewer continuity mode and opaque handle availability, deep-review and structural-depth lens instructions when assigned, conservative-autopilot classifications and rationales, complexity posture and smallest closing moves or lazy-human decisions, auto-fix/auto-decline/user-decision issue families, user-approved-fix ask-user decision routing, user-declined/accepted-risk decisions, unresolved ask-user blocker handling, sibling sweeps, validation commands, propagated Agent Review/report context, adjudicated-clean final fresh review-pass packet with no unresolved auto-fix or ask-user blockers, temporary HTML report, and absence of unapproved external writes or handle exposure.
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
- Output artifact: new or updated skill, resolver guidance, manifest entry, deterministic validator, source-routing fixture, smoke example, or propagation queue proposal.
- Filing rule: canonical skills live under `os/skills/`; deterministic checks live in `os/verification/scripts/validate_agentos.py` or a clearly warranted local script; source-routing/smoke fixtures live under `os/verification/source-routing/`; unapproved durable state proposals live in the appropriate Personal Overlay propagation queue.
- Safety posture: require at least one concrete example; do not copy private connector data into durable artifacts; follow the shared external-write policy before external writes; ask before automation activation, destructive edits, or current-machine skill exposure changes.
- Verification coverage: run `scripts/run-validator`; run `scripts/run-validator --self-test` when validator behavior changes; add or update a safe smoke example for new durable behavior; confirm external writes complied with the shared external-write policy.
- Upgrade notes: Core reusable workflow for turning repeated work into durable AgentOS behavior.

### `promote-private-skill-to-core`

- Canonical source: `os/skills/promote-private-skill-to-core/SKILL.md`
- Contract status: full.
- Mutability: mixed: read-only by default for promotion audits; local-write only when the user explicitly approves creating or updating Core skills, local design docs, safe fixtures, or Personal Overlay config; external-write only when permitted by the shared external-write policy.
- Tools and connectors: local filesystem, `rg`, `git`, AgentOS validators, privacy scanners, `verify-privacy`, optional read-only GitHub issue or PR context, and no connector account reads by default.
- Output artifact: promotion audit report by default; when implementation is explicitly approved, a sanitized Core skill or skill update, Core manifest update, optional safe smoke fixture, and optional Personal Overlay config or private thin-adapter instructions.
- Filing rule: Core-safe promoted skills live under `os/skills/`; Core maintenance facts live in this manifest; private inputs for reusable Core skills live in `personal/os/skills/<skill-name>/CONFIG.md` when needed; private skill governance remains in ignored `personal/os/skills/MANIFEST.md`; private examples, generated outputs, live agent state, histories, reports, queues, and run logs remain in the Personal Overlay.
- Safety posture: do not scan, enumerate, copy, expose, or summarize Personal Overlay skills without explicit private-scope authorization; require maintained private skill governance or stop with a governance-review recommendation; do not copy private examples, local paths, account IDs, connector details, live agent state, generated outputs, histories, queues, or run logs into Core; do not modify `expose-skills` to scan or expose Personal Overlay skills; ask before external writes, connector reads, Personal Overlay writes, current-machine exposure changes, or destructive edits.
- Verification coverage: confirm audit-only versus implementation-approved mode, candidate governance status, reusable evidence, private/Core boundary map, mandatory sanitization checklist, private preservation plan, validator and diff-check results after Core edits, absence of unapproved Personal Overlay writes or external writes, and absence of private examples, paths, account details, live state, generated outputs, or run histories in Core.
- Upgrade notes: Core reusable workflow introduced for GitHub Issue #23 after #19 established Personal Overlay skill manifest guidance and #74 kept skill manifests Markdown-first with a stricter Markdown API.

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
