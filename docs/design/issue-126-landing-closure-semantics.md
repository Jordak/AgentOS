# Issue 126 Landing And Closure Semantics

Design readiness: needs consensus
Consensus provenance: Legacy source predates implementation-readiness policy v2; run `ensure-implementation-readiness` to verify or repair provenance before citing this document as v2 readiness evidence for future implementation.
Gate skipped: not applicable

## Problem

`implement-github-issue` now owns the happy path for one GitHub issue through readiness, implementation, validation, pull request creation, and `review-loop` convergence. Its first version intentionally stops before merge and issue closure.

The next design question is where landing and issue closure belong. A tempting design would let `implement-github-issue` optionally continue after review when the user approves merge or closure. That would make the boundary depend on invocation-time choices: sometimes `implement-github-issue` would own landing and sometimes a broader coordinator would own it.

That ambiguity is risky for future batch coordination. A future `coordinate-issue-batch` workflow needs to compare several worker results, reason about dependency and acceptance-criteria coverage across issues, and decide what order to land or leave open. If each worker can sometimes merge or close its own issue, the coordinator cannot reliably own integration state.

## Chosen Design

Keep the boundary contract-specific, not role-specific.

`implement-github-issue` never merges pull requests, closes issues, or deletes branches. It may be invoked as a Called Workflow by a broader workflow, but the reason it stops is its own contract, not its invocation role. It returns a reviewed pull request plus structured evidence and recommendations that another workflow or human can use for integration.

A future `coordinate-issue-batch` workflow should own landing and issue closure for an approved batch once its contract exists. That workflow may itself be a Called Workflow in a larger invocation. Its integration ownership comes from its contract and authorization boundary, not from being "the caller" in an abstract sense.

This follows the `os/skills/ORCHESTRATION_LOOPS.md` rule that Integration Ownership is contract-defined. Workflow roles such as Calling Workflow and Called Workflow are contextual invocation roles; they do not automatically grant or remove merge, closure, or branch-deletion authority.

## `implement-github-issue` Contract

`implement-github-issue` owns:

- issue readiness repair through `ensure-implementation-readiness`;
- implementation inside the resolved issue scope;
- validation for the touched surface;
- pull request creation with readiness fields;
- `review-loop` invocation and convergence evidence;
- recoverable final reporting with branch, PR, validation, review, and remaining-risk evidence.

`implement-github-issue` does not own:

- PR merge or squash merge;
- issue closure;
- branch deletion;
- post-merge acceptance-criteria reconciliation;
- batch-level ordering, dependency handling, or integration queue decisions.

When its pull request is reviewed and ready, it should return a Workflow Result that includes:

- issue URL and labels at final handoff;
- PR URL and head branch;
- readiness evidence and verdict;
- validation commands and results;
- `review-loop` evidence;
- commit SHAs produced by the worker branch;
- any unresolved human decisions, residual risks, or known acceptance-criteria caveats;
- a recommended next action for the integration owner.

The recommendation may say the PR appears ready to land, but it must not use GitHub auto-closing keywords for the issue reference and must not claim the issue is closed or integrated.

## Future `coordinate-issue-batch` Contract Notes

Do not create a `coordinate-issue-batch` skill in this issue. These notes are durable design input for the future issue that creates that skill, currently tracked by GitHub issue #132.

The future coordinator should:

- treat a full batch pass as its default shape: when no explicit batch is supplied, invoke `select-issue-batch` in read-only mode, then turn the recommendation into a concrete coordinator target inside its own Authorization Boundary;
- also accept a user-provided or caller-provided issue batch for recovery, reruns, human-curated work, and higher-level workflows that already own selection;
- spawn or request isolated worker branches, worktrees, and threads only after explicit authorization;
- use separate Codex branch-backed threads for durable Codex implementation workers when that harness path is available, while keeping the reusable worker contract harness-neutral;
- require each worker to follow `implement-github-issue` or another approved worker contract;
- prevent workers from merging PRs, closing issues, deleting branches, or mutating integration state;
- record every worker Workflow Result in a recoverable coordinator ledger;
- allow a worker thread to remain assigned to its PR for human review corrections after `implement-github-issue` returns reviewed PR evidence, without expanding the `implement-github-issue` contract beyond its reviewed-PR boundary;
- maintain an invocation-owned coordinator ledger by default, and optionally create or use a dedicated GitHub batch tracking issue when the Authorization Boundary explicitly permits that tracker write;
- support normal, read-only, and resume modes; landing is a phase of normal or resume mode, not a separate top-level mode;
- default to at most three parallel implementation workers unless the user or Calling Workflow specifies a different concurrency limit;
- stop for a Blocking Human Decision when coordinator checks show a selected batch is not actually parallel-safe, even if a sequential order is obvious, so planner mistakes and stale evidence are visible;
- leave per-issue readiness and label hygiene to the assigned issue workflow through `ensure-implementation-readiness`, while the coordinator records any stale-label or blocker evidence in the worker handoff;
- give workers only enough batch context to respect their Isolation Boundary and escalation rules; the coordinator remains responsible for the full batch ledger, landing queue, and other workers' state;
- wait for all expected workers to return, fail, block, or be explicitly cancelled before beginning closure review for the batch;
- wait for the worker set to be quiescent before beginning closure review: every expected worker is complete, permanently blocked, failed, or explicitly cancelled, so workers are no longer producing review-correction events for the current batch;
- wait for the user or integration owner to report that all PRs intended for the current landing phase are merged before beginning post-merge landing checks;
- skip permanently blocked, failed, cancelled, or unmerged issues during the landing phase and record their next action in the coordinator ledger instead of blocking landing for completed merged issues;
- process landing and closure candidates one issue at a time from the coordinator ledger;
- record late worker results without interrupting the currently active closure decision;
- compare the worker evidence, merged PR evidence, acceptance criteria, and blocker/dependency state before closing any issue;
- leave issues open with evidence comments when human-review labels, ambiguous acceptance criteria, failed checks, partial implementation, or missing integration proof remain.

The coordinator can be messaged by multiple workers while it is active. Its contract should make progress deterministic through a barrier and queue:

1. During worker execution, record incoming Workflow Results and blocker states.
2. Do not start issue-closure review until the expected worker set is resolved by completion, failure, blocking, or cancellation.
3. During closure review, process one issue at a time.
4. If new worker information arrives mid-review, checkpoint it and return to it after the current closure item reaches a durable decision.

This keeps "drop nothing" behavior in the coordinator's recoverable ledger rather than relying on live memory.

## Audit And Closure Evidence

`audit-issues` remains the reusable contract for issue tracker reconciliation after integration evidence exists. A landing or coordinator workflow should reuse or follow that evidence standard instead of duplicating issue-audit semantics informally.

Before any issue closure:

- fetch or otherwise verify the remote integration branch, usually `origin/main`;
- verify the resolving PR was merged into the integration branch or its merge/squash commit is reachable from that branch;
- confirm the issue's acceptance criteria are materially satisfied;
- confirm no human-review label such as `ready-for-human`, `needs-human`, `needs-a-human`, or equivalent still requires a human closure decision;
- close only with a factual comment that cites the merged PR, integration commit, integration branch, and relevant validation evidence.

A pushed feature branch, local-only commit, unmerged PR, title similarity, or "looks done" code inspection is not enough closure evidence.

## Approval Boundaries

For `implement-github-issue`, user approval cannot widen the skill into merge, issue-closure, or branch-deletion ownership. A request to land or close should be routed to a workflow whose contract owns landing and closure, or to a direct human-supervised integration action outside `implement-github-issue`.

For a future coordinator, the contract should require explicit approval for:

- spawning workers or creating external workflow state;
- merge or squash merge;
- issue closure;
- branch deletion;
- label changes that alter human-review, readiness, or blocked state;
- comments outside the coordinator's assigned issue/PR scope;
- any external action outside the coordinator contract.

Merge approval should not silently imply issue-closure approval. Issue-closure approval should not silently imply branch-deletion approval.

## Non-Goals

- Do not implement `coordinate-issue-batch` in this issue.
- Do not add deterministic validators for landing semantics in this issue.
- Do not change `review-loop` into a merge or closure workflow.
- Do not allow worker branches or child issue workers to close their assigned issues.
- Do not close GitHub issue #126 as part of this implementation; closure still waits for PR integration and the applicable human review.

## Acceptance Criteria

- `implement-github-issue` explicitly stops before merge, issue closure, and branch deletion without an invocation-time optional landing mode.
- Existing GitHub workflow guidance preserves `review-loop` as PR-scoped and `audit-issues` as the post-integration issue-audit contract.
- The future `coordinate-issue-batch` contract notes are recorded durably without creating a placeholder skill.
- Closure semantics require integration-branch proof and acceptance-criteria reconciliation.
- Human-review labels remain blockers for agent closure.
- Approval boundaries distinguish merge, issue closure, and branch deletion.
- Validation passes for touched AgentOS skill and playbook surfaces.

## Validation Plan

- Run `git diff --check`.
- Run `scripts/run-validator`.
- Inspect `os/skills/implement-github-issue/SKILL.md`, `os/playbook/GITHUB_WORKFLOW.md`, `os/skills/ORCHESTRATION_LOOPS.md`, and `os/skills/MANIFEST.md` for consistent contract-specific integration ownership.

## PR Readiness Fields

```md
Readiness evidence: docs/design/issue-126-landing-closure-semantics.md and GitHub issue #126
Readiness verdict: Ready to Implement
```
