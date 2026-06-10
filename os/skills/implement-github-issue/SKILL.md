---
name: implement-github-issue
description: Take one ready GitHub issue in a repository checkout through implementation, validation, pull request creation, review-loop convergence, and recoverable final reporting while stopping before merge and issue closure.
---

# Implement GitHub Issue

## Goal

Own the happy path for one GitHub issue from assignment to a reviewed pull request. The skill composes existing AgentOS contracts instead of duplicating them: `ensure-implementation-readiness` owns the design gate, `GITHUB_WORKFLOW` owns protected-main and pull-request discipline, and `review-loop` owns PR review/fix convergence.

This first version stops at a PR ready for parent or human review. It must stop before merge and issue closure, and it does not delete branches, change permissions, create labels, or take broader integration ownership unless a separate request explicitly authorizes that action.

## Contract

Inputs:

- A GitHub issue URL or issue number plus the target repository, inferred from the current checkout when possible.
- A repository checkout for the target project.
- Current local agent instructions and project guidance, including `AGENTS.md`.
- The durable design source for the issue, usually the GitHub issue body.
- `os/skills/ensure-implementation-readiness/SKILL.md`, `os/playbook/IMPLEMENT_FEATURES.md`, `os/playbook/GITHUB_WORKFLOW.md`, and `os/skills/review-loop/SKILL.md`.
- Optional explicit mode: normal mutating mode by default, or read-only mode when the caller says not to write.

Output artifact:

- A pull request with `Readiness evidence:` and `Readiness verdict:` fields.
- A recoverable Workflow Result in the current reporting mode, naming issue, branch, worktree, PR, readiness verdict, validation, review-loop status, mutations, open risks, and recommended next action.
- Optional issue or PR comments when useful for recovery or handoff.

Mutability:

- Mixed. In normal mode, invoking this skill on a GitHub issue authorizes the ordinary happy-path writes needed for this workflow: issue-body readiness/design updates, existing label changes for readiness or workflow hygiene within the assigned issue scope, issue or PR comments for recoverable status and evidence, feature-branch pushes, PR creation with readiness fields, and `review-loop` invocation with its ordinary PR-scoped writes.
- Read-only when the caller explicitly says read-only mode, audit-only, no writes, no external writes, or equivalent. In read-only mode, inspect and report the planned steps and blockers without mutating local files or external state.

Tools and connectors:

- Local filesystem, `git`, `rg`, project-specific validation commands, GitHub connector or `gh`, and `scripts/agent-push` for AgentOS feature-branch pushes when available.
- `os/skills/ensure-implementation-readiness/SKILL.md` and `os/playbook/IMPLEMENT_FEATURES.md` for readiness.
- `os/playbook/GITHUB_WORKFLOW.md` for branch, worktree, PR, issue, and closure discipline.
- `os/skills/review-loop/SKILL.md` for PR convergence.
- `os/skills/ORCHESTRATION_LOOPS.md`, with background in `docs/adr/0009-contract-based-orchestration-loops.md` and `docs/design/issue-121-loop-composition-conventions.md`, for orchestration-loop vocabulary when local AgentOS loop semantics matter.

Safety:

- Treat normal invocation as explicit authorization for the ordinary happy-path writes listed in this contract, unless the caller narrows the Authorization Boundary to read-only mode.
- Ask before merge, issue closure, branch deletion, permission changes, creating new labels, posting outside the target issue or PR scope, pushing outside the target feature branch, changing repository settings, handling credentials or MFA, or any external action outside this contract.
- Do not implement when `ensure-implementation-readiness` returns `Needs Design Consensus` unless that skill repairs the durable source to `Ready to Implement` or the user explicitly chooses `Gate Skipped`.
- Do not treat a `ready-for-agent` label as a substitute for the readiness gate.
- Preserve unrelated local changes. If the checkout is dirty before edits, identify whether changes are yours; stop or isolate work rather than overwriting user changes.
- Do not merge `main` into the feature branch. Rebase on the integration branch when updating a branch you own.
- Do not use GitHub auto-closing keywords with issue references in PR text unless issue closure is intentionally in scope after integration. This v1 does not close the issue.

## Workflow Phases

1. Establish the target:
   - Identify the issue, repository, current branch, remote, base branch, and checkout path.
   - Read local instructions, `os/playbook/GITHUB_WORKFLOW.md`, and the narrow skill contracts this workflow will call.
   - Inspect the issue body, labels, linked PR or design context, and comments relevant to readiness or blockers.
   - Record the initial Recovery Record: issue URL, repository, branch, worktree, current phase, Authorization Boundary, known blockers, and next action.

2. Run the readiness gate:
   - Invoke or follow `ensure-implementation-readiness` for the issue.
   - Prefer the GitHub issue as the durable design source for issue-driven work.
   - If the verdict is `Needs Design Consensus`, let the readiness skill own targeted questions, design-consensus routing, durable-source repair, and readiness-label hygiene inside this skill's Authorization Boundary.
   - If the user chooses `Gate Skipped`, record the bypass reason and missing evidence in the Recovery Record and PR readiness fields.
   - Do not proceed to implementation until the verdict is `Ready to Implement` or `Gate Skipped`.

3. Check branch and worktree discipline:
   - Run `git status --short --branch` before tracked-file edits.
   - Use the harness-provided worktree and branch when present.
   - Do not edit tracked AgentOS Core or publishable support files on `main` for PR-bound work.
   - If no suitable branch exists, create or switch to an isolated feature branch/worktree according to `GITHUB_WORKFLOW`.

4. Implement inside the issue boundary:
   - Keep changes within the issue's desired behavior, non-goals, and acceptance criteria.
   - Prefer existing project patterns and narrow edits over new durable machinery.
   - Add or update tests, fixtures, manifest metadata, source-routing evidence, or docs only when they directly support the issue.
   - Before leaving a long-running or interruptible point, update the Recovery Record in the current reporting mode.

5. Validate:
   - Run the smallest trustworthy local checks for the touched surface, broadening for shared workflow or validation-policy changes.
   - For AgentOS skill or manifest changes, run `git diff --check` and `scripts/run-validator`.
   - Record skipped checks with reasons.

6. Commit and push:
   - Inspect the diff and status before staging.
   - Commit cohesive changes with an agent-prefixed subject.
   - For AgentOS public repository persistence, use `scripts/agent-push` when available; otherwise follow `GITHUB_WORKFLOW` and report the fallback.
   - Push only the target feature branch.

7. Create the pull request:
   - Create a PR against the integration branch with a body that starts from prior behavior, explains why it changes, summarizes the new behavior, and includes validation.
   - Include exact readiness fields. Use `Ready to Implement` for a passed gate, or `Gate Skipped` only for an explicit bypass with the bypass reason in `Readiness evidence:`:

```md
Readiness evidence: <GitHub issue, PRD, ADR, local design doc, or gate-skip reason>
Readiness verdict: <Ready to Implement | Gate Skipped>
```

   - Avoid GitHub issue auto-closing language because this workflow stops before issue closure.
   - Record the PR URL in the Recovery Record.

8. Run review-loop:
   - Before invoking `review-loop`, update the Recovery Record in an authorized checkpoint surface so the issue, PR, branch, readiness verdict, validation state, Authorization Boundary, and next action are recoverable.
   - Invoke `review-loop` on the PR with its normal PR-scoped Authorization Boundary unless this skill was narrowed to read-only mode.
   - Let `review-loop` own reviewer-panel delegation, review/fix convergence, PR comments, fix commits, pushes to the target PR branch, and ready-for-human marking inside its contract.
   - Treat the review-loop final report or Workflow Result as evidence for this skill's final result.
   - If review-loop returns a Blocking Human Decision, record it recoverably and pause instead of guessing.

9. Report final Workflow Result:
   - Begin with status and whether the PR is ready for parent or human review.
   - Include issue and PR links, branch and worktree, readiness evidence and verdict, mutations performed, commits, validation, review-loop evidence, open risks, and recommended next action.
   - State clearly that merge, issue closure, branch deletion, and any broader integration action remain out of scope unless separately approved.

## Recovery Record

Maintain enough state to resume safely after compaction, interruption, handoff, or a called workflow result. The record can live in chat, issue comments, PR comments, commits, local notes, or the final report depending on the current reporting mode and Authorization Boundary.

Create or update an authorized Recovery Checkpoint before starting a called workflow that may outlive the current context, before yielding for a Blocking Human Decision, before ending a turn with incomplete workflow work, and before any external write after which lost context would make recovery unsafe. Use the narrowest authorized surface available, such as an issue comment, PR comment, commit, local note, chat pause message, or final report.

For this skill, recover at least:

- issue URL and repository;
- branch, base branch, worktree, and current commit SHA when available;
- Authorization Boundary, including any read-only narrowing;
- readiness evidence and verdict;
- current phase and next safe action;
- PR URL after creation;
- validation commands and results;
- review-loop status, report path or comment URL, and any unresolved Blocking Human Decision;
- mutations performed, including issue edits, labels, comments, commits, pushes, and PR state changes;
- open risks and recommended parent/human action.

## Filing Rules

- Canonical reusable workflow guidance lives in this skill.
- Issue-specific design and readiness evidence stay in the GitHub issue unless the design is too large, private, architectural, or better suited to a local design doc.
- PR and review-loop evidence stay on the PR surface or in review-loop's temporary report.
- Do not create durable AgentOS state by default for ordinary project implementation details.
- If this workflow discovers a reusable AgentOS improvement outside the assigned issue, file it as a follow-up issue or propagation item rather than expanding scope silently.

## Quality Bar

- The issue has a durable readiness source with `Ready to Implement` or an explicit `Gate Skipped` bypass before implementation.
- Branch/worktree discipline was checked before tracked-file edits.
- Implementation stays inside the issue boundary.
- Validation matches the touched surface and includes `scripts/run-validator` plus `git diff --check` for AgentOS skill or manifest changes.
- The PR body includes readiness fields and avoids accidental issue-closing language.
- `review-loop` is invoked or explicitly skipped with a reason; reviewer logic is not duplicated here.
- The final result is recoverable and names every mutation, validation signal, open risk, and next action.
- The workflow stops before merge, issue closure, branch deletion, permission changes, and new label creation unless separately approved.

## Verification

Before finishing:

1. Confirm local instructions, readiness policy, GitHub workflow policy, and `review-loop` contract were read or honored.
2. Confirm the readiness verdict and evidence are recorded.
3. Confirm branch/worktree status was inspected before edits.
4. Confirm no unrelated user changes were overwritten.
5. Confirm validation commands and results are recorded.
6. Confirm the PR body includes `Readiness evidence:` and `Readiness verdict:`.
7. Confirm review-loop was run, or record why it could not be run.
8. Confirm the final Workflow Result includes issue, branch/worktree, PR, commits, validation, review-loop evidence, open risks, and recommended next action.
9. Confirm merge, issue closure, branch deletion, permission changes, and new label creation were not performed without separate approval.
10. If this skill or its manifest entry changed, run `git diff --check` and `scripts/run-validator`.
