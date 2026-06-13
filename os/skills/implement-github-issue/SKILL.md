---
name: implement-github-issue
description: Take one GitHub issue in a repository checkout through readiness gating, implementation, validation, pull request creation, review-loop convergence, and recoverable final reporting while stopping before merge, issue closure, and branch deletion.
---

# Implement GitHub Issue

## Goal

Own the happy path for one GitHub issue from assignment to a reviewed pull request. The skill composes narrower workflow contracts instead of duplicating them: `ensure-implementation-readiness` owns the design gate, the repository's GitHub workflow guidance owns protected-branch and pull-request discipline, and `review-loop` owns PR review/fix convergence.

This skill stops at a PR ready for parent, coordinator, or human review. It must stop before merge and issue closure, and it never deletes branches or takes broader integration ownership. Landing and issue closure belong to a workflow or human integration action whose own contract explicitly owns those surfaces, such as `land-github-issue` after integration evidence exists.

## Contract

Inputs:

- A GitHub issue URL or issue number plus the target repository, inferred from the current checkout when possible.
- A repository checkout for the target project.
- Current local agent instructions and project guidance, including `AGENTS.md`.
- Existing durable design sources when already linked from the issue, request, repository, or project guidance.
- Relevant project domain docs when present, such as `DOMAIN.md` and `DOMAIN-MAP.md`, with legacy `CONTEXT.md` and `CONTEXT-MAP.md` as aliases.
- `ensure-implementation-readiness`, repository GitHub workflow guidance, and `review-loop` when available in the active AgentOS checkout or harness.
- Optional caller-supplied Workflow Invocation Reference or result surface, plus an explicit release instruction, when this skill is invoked as a durable Called Workflow.
- Optional caller-provided effort metadata or caller effort prescription to preserve in handoffs and the final Workflow Result under `os/skills/ORCHESTRATION_LOOPS.md`.
- Optional explicit mode: normal mutating mode by default, or read-only mode when the caller says not to write.

Output artifact:

- A pull request with `Readiness evidence:` and `Readiness verdict:` fields.
- A recoverable Workflow Result in the current reporting mode or caller-supplied Workflow Invocation Reference, with terminal status (`completed`, `blocked`, `failed`, `cancelled`, or `needs-human`), issue URL and final issue labels, branch, worktree, PR, effort metadata when available or relevant, raw readiness evidence or provenance, readiness verdict, final readiness label state, `Gate Skipped` reason plus durable gate-skip field/state or missing consensus evidence when present, validation, review-loop status, mutations, open risks, release-instruction handling, and recommended next action for the integration owner.
- Optional issue or PR comments when useful for recovery or handoff.

Mutability:

- Mixed. In normal mode, invoking this skill on a GitHub issue authorizes the ordinary happy-path writes needed for this workflow: invoking or following `ensure-implementation-readiness` in normal/repair mode with an Authorization Boundary for issue-body/design-source readiness evidence and existing readiness labels; existing non-readiness workflow-label hygiene within the assigned issue scope, such as verified stale `blocked` label removal; issue or PR comments for recoverable status and evidence; caller-supplied result-surface handling when this skill is invoked as a durable Called Workflow and the supplied surface is inside the Authorization Boundary; feature-branch pushes; PR creation with readiness fields; and `review-loop` invocation with its ordinary PR-scoped writes.
- Read-only when the caller explicitly says read-only mode, audit-only, no writes, no external writes, or equivalent. In read-only mode, inspect and report the planned steps and blockers without mutating local files or external state.

Tools and connectors:

- Local filesystem, `git`, `rg`, project-specific validation commands, GitHub connector or `gh`, and repository-local push helpers when local instructions require them.
- Project-local domain docs when relevant, such as `DOMAIN.md` and `DOMAIN-MAP.md`, with legacy `CONTEXT.md` and `CONTEXT-MAP.md` as aliases.
- `os/skills/ensure-implementation-readiness/SKILL.md` and `os/playbook/IMPLEMENT_FEATURES.md` for readiness when AgentOS skills are available.
- `os/playbook/GITHUB_WORKFLOW.md` or equivalent repository guidance for branch, worktree, PR, issue, and closure discipline.
- `os/skills/review-loop/SKILL.md` for PR convergence when available.
- `os/skills/ORCHESTRATION_LOOPS.md`, with background in `docs/adr/0009-contract-based-orchestration-loops.md` and `docs/design/issue-121-loop-composition-conventions.md`, for AgentOS orchestration-loop vocabulary and recovery semantics when those Core files are available.
- `docs/design/issue-126-landing-closure-semantics.md` for the durable decision that `implement-github-issue` does not own merge, issue closure, or branch deletion.
- `os/skills/land-github-issue/SKILL.md` only as a downstream integration-owner reference; this skill does not call or own it.

Safety:

- Treat normal invocation as explicit authorization for the ordinary happy-path writes listed in this contract, unless the caller narrows the Authorization Boundary to read-only mode.
- Do not merge PRs, close issues, or delete branches through this skill. User requests for those actions must route to a workflow or direct integration step whose contract owns landing and closure.
- A caller-supplied result surface named in the assignment is in scope only when the Authorization Boundary permits it. If the surface is unavailable, private where a public-safe report is needed, or outside the Authorization Boundary, return the Workflow Result in the current reporting mode and record the unavailable result-surface reason.
- Ask before permission changes, creating new labels, posting outside the target issue or PR scope or outside an authorized caller-supplied result surface, pushing outside the target feature branch, changing repository settings, handling credentials or MFA, or any external action outside this contract.
- Do not implement when `ensure-implementation-readiness` returns `Needs Design Consensus` unless that skill repairs the durable source to `Ready to Implement` or is re-followed with an explicit user bypass and returns `Gate Skipped`.
- Do not remove `needs design consensus` or equivalent readiness labels directly. During the readiness phase, any readiness-label mutation is performed under the `ensure-implementation-readiness` contract. After readiness returns, consume and verify the verdict instead of performing cleanup yourself.
- Do not treat a `ready-for-agent` label as a substitute for the readiness gate.
- Treat human-owned, HITL, blocked, `ready-for-human`, `needs-human`, `needs-a-human`, or equivalent labels as a Blocking Human Decision. Continue only when the current request explicitly authorizes continuing despite that label state, the repository's label or triage owner resolves the human-owned or human-review state, or the only blocker is a stale `blocked` label whose blocking dependency is verifiably resolved. `ensure-implementation-readiness` may resolve readiness evidence, readiness fields, and authorized readiness-label hygiene; it does not by itself clear human-owned, HITL, or human-review states.
- Preserve unrelated local changes. If the checkout is dirty before edits, identify whether changes are yours; stop or isolate work rather than overwriting user changes.
- Do not merge `main` into the feature branch. Rebase on the integration branch when updating a branch you own.
- Do not use GitHub auto-closing keywords with issue references in PR text. This skill does not close the issue.

## Workflow Phases

1. Establish the target:
   - Identify the issue, repository, current branch, remote, base branch, and checkout path.
   - Read local instructions, repository GitHub workflow guidance, and the narrow skill contracts this workflow will call.
   - Inspect the issue body, labels, linked PR or design context, and comments relevant to readiness or blockers.
   - Read project-local domain docs when relevant to the implementation surface or required by local instructions, using `DOMAIN.md` and `DOMAIN-MAP.md` with legacy `CONTEXT.md` and `CONTEXT-MAP.md` as aliases.
   - If issue labels indicate human ownership, HITL, blocked state, or human review, record a Blocking Human Decision and stop unless the current request explicitly authorizes continuing, the repository's label or triage owner resolves the human-owned or human-review state, or the only blocker is a stale `blocked` label whose blocking dependency is verifiably resolved.
   - Record the initial Recovery Record: issue URL, repository, branch, worktree, current phase, Authorization Boundary, effort metadata when available or relevant, any caller-supplied Workflow Invocation Reference or result surface, release instruction, known blockers, and next action.

2. Run the readiness gate:
   - Invoke or follow `ensure-implementation-readiness` in normal/repair mode for the issue, passing along the issue context, project guidance, discovered design sources, and this skill's Authorization Boundary.
   - Let the readiness workflow own locating, creating, or repairing the durable design source, including issue-body updates, design-consensus routing, consensus provenance, deferred follow-up artifacts, readiness fields, and readiness-label hygiene when those writes are authorized.
   - Do not synthesize a design doc, handoff packet, or readiness field and then treat that agent-authored artifact as design consensus. Readiness requires the readiness workflow's returned verdict backed by durable consensus provenance, or its returned `Gate Skipped` verdict backed by a durable gate-skip field/state for an explicit bypass.
   - After readiness repair writes or approved design-source updates are applied, re-run or re-follow `ensure-implementation-readiness` against the updated durable source before starting implementation.
   - Before invoking the readiness workflow in a mode that may perform external writes, or before carrying out a readiness-workflow-directed external write in this skill's thread, update the Recovery Record in an authorized checkpoint surface.
   - If the user chooses to bypass after readiness reports missing evidence, re-follow `ensure-implementation-readiness` with that explicit bypass and consume its returned `Gate Skipped` verdict only when the readiness report names the durable source `Gate skipped:` field or an exemption where no durable source is required. Then record the bypass reason, missing evidence, and durable gate-skip record location in the Recovery Record and PR readiness fields.
   - If the readiness verdict is `Ready to Implement`, verify that any `needs design consensus` label has been removed by the readiness workflow before continuing.
   - If the readiness verdict is `Gate Skipped`, continue only with the bypass reason and durable gate-skip field/state recorded in the Recovery Record and PR readiness fields; a `needs design consensus` label may remain.
   - If the readiness verdict is `Needs Design Consensus`, stop before implementation and return a recoverable result naming the missing consensus evidence.

3. Check branch and worktree discipline:
   - Run `git status --short --branch` before tracked-file edits.
   - Use the harness-provided worktree and branch when present.
   - Do not edit tracked files on a protected integration branch for PR-bound work.
   - If no suitable branch or worktree exists, create or switch to an isolated feature branch or worktree according to repository guidance.

4. Implement inside the issue boundary:
   - Keep changes within the issue's desired behavior, non-goals, and acceptance criteria.
   - Prefer existing project patterns and narrow edits over new durable machinery.
   - Add or update tests, fixtures, manifest metadata, source-routing evidence, or docs only when they directly support the issue.
   - Before leaving a long-running or interruptible point, update the Recovery Record in the current reporting mode.

5. Validate:
   - Run the smallest trustworthy local checks for the touched surface, broadening for shared workflow or validation-policy changes.
   - Follow project-local validation instructions. For AgentOS skill or manifest changes in this repository, run `git diff --check` and `scripts/run-validator`.
   - Record skipped checks with reasons.

6. Commit and push:
   - Inspect the diff and status before staging.
   - Commit cohesive changes with an agent-prefixed subject.
   - Use the repository's documented push path. For AgentOS public repository persistence, use `scripts/agent-push` when available.
   - Push only the target feature branch.

7. Create the pull request:
   - Before creating the PR or posting related evidence comments, update the Recovery Record in an authorized checkpoint surface.
   - Create a PR against the integration branch with a body that starts from prior behavior, explains why it changes, summarizes the new behavior, and includes validation.
   - Include exact readiness fields. Use `Ready to Implement` for a passed gate, or `Gate Skipped` only for an exempt gate or explicit bypass backed by the durable source's `Gate skipped:` field:

```md
Readiness evidence: <GitHub issue, PRD, ADR, local design doc, durable gate-skip record, or exempt-work reason>
Readiness verdict: <Ready to Implement | Gate Skipped>
```

   - Avoid GitHub issue auto-closing language because this workflow stops before issue closure.
   - Record the PR URL in the Recovery Record.

8. Run review-loop:
   - Before invoking `review-loop`, update the Recovery Record in an authorized checkpoint surface so the issue, PR, branch, raw readiness evidence or provenance, readiness verdict, final readiness label state, `Gate Skipped` reason plus durable gate-skip field/state or missing consensus evidence when present, validation state, effort metadata when available or relevant, Authorization Boundary, and next action are recoverable.
   - Invoke `review-loop` on the PR with its normal PR-scoped Authorization Boundary unless this skill was narrowed to read-only mode, passing or recording applicable effort metadata per `os/skills/ORCHESTRATION_LOOPS.md`.
   - Let `review-loop` own reviewer-panel delegation, review/fix convergence, PR comments, fix commits, pushes to the target PR branch, and ready-for-human marking inside its contract.
   - Treat the review-loop final report or Workflow Result as evidence for this skill's final result.
   - If review-loop returns a Blocking Human Decision, record it recoverably and pause instead of guessing.

9. Report final Workflow Result:
   - Begin with `Status:` using one canonical terminal value: `completed`, `blocked`, `failed`, `cancelled`, or `needs-human`. Include whether the PR is ready for integration-owner review, naming the parent, coordinator, or human owner when known.
   - Include issue URL and final issue labels, PR link, branch and worktree, effort metadata when available or relevant, raw readiness evidence or provenance, readiness verdict, final readiness label state, `Gate Skipped` reason and durable gate-skip field/state or missing consensus evidence when present, mutations performed, commits, validation, review-loop evidence, open risks, and recommended next action for the integration owner.
   - When the caller supplied a Workflow Invocation Reference or result surface, return the Workflow Result there when available, and then stop or wait according to the explicit release instruction.
   - State clearly that merge, issue closure, branch deletion, and any broader integration action remain out of scope for this skill and must be handled by a landing-capable workflow such as `land-github-issue` after integration evidence exists, or by a direct human integration step.

## Recovery Record

Maintain enough state to resume safely after compaction, interruption, handoff, or a called workflow result. The record can live in chat, issue comments, PR comments, commits, temporary files, local notes, or the final report depending on the current reporting mode and Authorization Boundary.

Create or update an authorized Recovery Checkpoint before every external write, before starting a called workflow that may outlive the current context, before yielding for a Blocking Human Decision, and before ending a turn with incomplete workflow work. Use the narrowest authorized surface available, such as an issue comment, PR comment, commit, temporary file, local note, chat pause message, or final report.

For this skill, recover at least:

- issue URL and repository;
- relevant issue labels and whether any label state created or resolved a Blocking Human Decision;
- branch, base branch, worktree, and current commit SHA when available;
- Authorization Boundary, including any read-only narrowing, and effort metadata when available or relevant;
- caller-supplied Workflow Invocation Reference or result surface, using only public-safe stable references in public or Git-backed surfaces and redacting private runtime handles when needed;
- release instruction, including whether the worker should stop after returning the result, remain assigned for review corrections, or wait for a caller release signal;
- raw readiness evidence or provenance, readiness verdict, final readiness label state, and `Gate Skipped` reason plus durable gate-skip field/state or missing consensus evidence when present;
- current phase and next safe action;
- PR URL after creation;
- validation commands and results;
- review-loop status, effort metadata when available or relevant, report path or comment URL, and any unresolved Blocking Human Decision;
- mutations performed, including issue edits, labels, comments, commits, pushes, and PR state changes;
- open risks and recommended next action for the integration owner, including any landing recommendation without claiming merge or issue closure.

## Filing Rules

- Canonical reusable workflow guidance lives in this skill.
- Issue-specific design and readiness evidence stay wherever the readiness workflow places them under project policy.
- PR and review-loop evidence stay on the PR surface or in review-loop's temporary report.
- Do not create durable global or framework state by default for ordinary project implementation details.
- If this workflow discovers a reusable project improvement or any work outside the assigned issue, file it as a follow-up issue or project-approved propagation item rather than expanding scope silently.

## Quality Bar

- The readiness workflow returned `Ready to Implement` or `Gate Skipped` before implementation, and any intentional bypass names the durable source `Gate skipped:` field or an exemption where no durable source is required.
- `ensure-implementation-readiness` was invoked in normal/repair mode, including any explicit bypass path that returns `Gate Skipped`.
- After readiness repair writes or approved design-source updates, the updated durable source was rechecked by `ensure-implementation-readiness` before implementation started.
- `implement-github-issue` did not remove readiness labels directly; readiness-label cleanup stayed under `ensure-implementation-readiness`.
- Human-owned, HITL, blocked, or human-review labels were resolved, explicitly authorized, or recorded as a Blocking Human Decision before mutating implementation work.
- Branch/worktree discipline was checked before tracked-file edits.
- Implementation stays inside the issue boundary.
- Validation matches the touched surface and follows project-local instructions, including `scripts/run-validator` plus `git diff --check` for AgentOS skill or manifest changes in this repository.
- The PR body includes readiness fields and avoids accidental issue-closing language.
- `review-loop` is invoked or explicitly skipped with a reason; reviewer logic is not duplicated here.
- The final result is recoverable and names its canonical terminal status, every mutation, validation signal, open risk, and next action.
- When called with a Workflow Invocation Reference or result surface, the final Workflow Result is returned through that surface when available and the release instruction is followed.
- The workflow stops before merge, issue closure, and branch deletion. Permission changes, new label creation, and other out-of-scope external actions also remain outside this contract unless another approved workflow owns them.

## Verification

Before finishing:

1. Confirm local instructions, readiness policy, GitHub workflow policy, and `review-loop` contract were read or honored.
2. Confirm `ensure-implementation-readiness` was invoked in normal/repair mode, including any explicit bypass path that returns `Gate Skipped`, and the readiness verdict, evidence, and durable gate-skip field/state are recorded.
3. Confirm any readiness repair writes or approved design-source updates were followed by re-running or re-following `ensure-implementation-readiness` against the updated durable source before implementation.
4. Confirm `needs design consensus` or equivalent readiness-label cleanup was performed only by `ensure-implementation-readiness`, or left in place for `Gate Skipped`.
5. Confirm human-owned, HITL, blocked, or human-review labels were resolved, explicitly authorized, or recorded as a Blocking Human Decision before mutating implementation work; if `blocked` was removed, confirm the blocker was verifiably resolved and no other blocker remained.
6. Confirm branch/worktree status was inspected before edits.
7. Confirm a Recovery Checkpoint was created before external writes, called workflows, Blocking Human Decision pauses, and incomplete turn endings.
8. Confirm no unrelated user changes were overwritten.
9. Confirm validation commands and results are recorded.
10. Confirm the PR body includes `Readiness evidence:` and `Readiness verdict:`.
11. Confirm review-loop was run, or record why it could not be run.
12. Confirm the final Workflow Result includes canonical terminal status, issue, effort metadata when available or relevant, raw readiness evidence or provenance, readiness verdict, final readiness label state, Gate Skipped reason plus durable gate-skip field/state or missing consensus evidence when present, branch/worktree, PR, commits, validation, review-loop evidence, open risks, recommended next action, any caller-supplied Workflow Invocation Reference or result surface, and release-instruction handling.
13. Confirm merge, issue closure, branch deletion, permission changes, new label creation, and other out-of-scope external actions were not performed without a separate approved workflow or direct user-supervised action.
14. If this skill or its manifest entry changed, run `git diff --check` and `scripts/run-validator`.
