---
name: coordinate-issue-batch
description: Coordinate a full GitHub issue batch pass by selecting or accepting a batch, launching isolated implementation workers when authorized, maintaining a coordinator ledger, waiting for human PR merge events, and landing eligible merged issues through land-github-issue.
---

# Coordinate Issue Batch

## Goal

Coordinate a full GitHub issue batch pass while preserving the boundaries of the narrower workflows it composes.

In normal mode, this skill can call `select-issue-batch` to choose a batch, launch supported isolated implementation workers with callback-first invocation references, track returned Workflow Results and review-correction lifecycle in a coordinator ledger, wait for human PR merge events, and invoke `land-github-issue` for eligible merged issues. It does not turn selection into mutation, does not make implementation workers own batch state, does not continuously poll workers as the normal progress model, and does not merge pull requests.

## Contract

Inputs:

- A target repository or issue tracker, inferred from the current checkout when possible.
- Optional user-provided or caller-provided batch of GitHub issues.
- Optional selection goal or filters for `select-issue-batch` when no explicit batch is supplied.
- Current local agent instructions and project guidance, including `AGENTS.md`.
- Current AgentOS GitHub workflow policy at `os/playbook/GITHUB_WORKFLOW.md`.
- Current orchestration-loop vocabulary and worker handoff guidance at `os/skills/ORCHESTRATION_LOOPS.md`.
- `select-issue-batch`, `implement-github-issue`, and `land-github-issue` when available in the active AgentOS checkout or harness.
- A supported durable worker-launch path when normal mode launches implementation workers. In Codex harnesses that support branch-backed project threads, durable implementation workers should be separate branch-backed threads, not in-thread subagents.
- A callback or result surface for each launched worker when the harness supports one, such as a callback thread id, child-thread URL, coordinator ledger location, or equivalent Workflow Invocation Reference.
- Optional explicit mode: normal, read-only/plan-only, or resume.

Output artifact:

- A coordinator Workflow Result with batch status, selected or provided issues, ledger location, worker branches/worktrees/thread names/invocation references/PRs, worker states, merge-event state, landing outcomes, skipped issues, blockers, validation, mutations performed, open risks, and recommended next action.
- A recoverable coordinator ledger or report in the current reporting mode.
- Optional dedicated GitHub batch tracking issue when the Authorization Boundary explicitly permits creating or using that tracker surface.

Mutability:

- Mixed. Normal mode may perform ordinary coordinator writes inside the Authorization Boundary: read-only selection, coordinator checks, ledger or checkpoint updates on authorized surfaces, branch/worktree/thread setup for supported workers, supported worker-thread renaming before `READY`, callback/invocation-reference handoff, minimal worker handoff packets, and worker launch.
- Read-only/plan-only mode inspects, selects, and proposes the batch, ledger, handoffs, sequencing, and risks without worker launch, tracker mutation, branch/worktree creation, or external writes.
- Resume mode rebuilds or loads the coordinator ledger and continues from the next safe phase under the current Authorization Boundary.

Tools and connectors:

- Local filesystem, `git`, `rg`, GitHub connector or `gh`, and repository-local push helpers when local instructions require them.
- `os/skills/select-issue-batch/SKILL.md` for read-only selection when no explicit batch is supplied.
- `os/skills/implement-github-issue/SKILL.md` or another approved worker contract for assigned implementation workers.
- `os/skills/land-github-issue/SKILL.md` for one-issue acceptance reconciliation and authorized closure after integration evidence exists.
- `os/skills/ORCHESTRATION_LOOPS.md` for Authorization Boundary, Isolation Boundary, Workflow Result, Recovery Record, Recovery Checkpoint, Blocking Human Decision, worker handoff, and Integration Ownership vocabulary.
- `os/playbook/GITHUB_WORKFLOW.md` for GitHub branch, worktree, PR, worker, and issue-closure discipline.

Safety:

- Do not merge or squash PRs in v1. The integration owner reviews and merges PRs, then reports merge events to the coordinator.
- Do not close issues directly. Invoke or follow `land-github-issue` for eligible merged issues when the Authorization Boundary permits closure.
- Do not delete branches, create labels, change permissions or settings, handle credentials or MFA, or write outside the coordinator's assigned scope unless another approved workflow or explicit user authorization owns that action.
- Do not launch workers for a batch that is not parallel-safe. Stop for a Blocking Human Decision when coordinator checks contradict the selected batch, even if a sequential order is obvious.
- Do not silently downgrade a selected parallel batch to sequential execution.
- Do not make workers responsible for the full batch ledger, landing queue, other workers' detailed state, or selection rationale. Give workers only enough batch context to respect their Isolation Boundary and escalation rules.
- Do not continuously poll worker threads as the normal progress model. Use callback-first Workflow Results, with polling only as bounded bootstrap, timeout, recovery, or diagnostic behavior recorded in the coordinator ledger.
- Leave per-issue readiness repair and label hygiene to assigned worker workflows such as `implement-github-issue`. The coordinator may detect stale labels or blocker contradictions and pass evidence into worker handoffs.
- Treat issue-local design consensus and `grill-with-docs` sessions as worker-owned unless the decision changes the batch ledger, Isolation Boundary, Authorization Boundary, worker assignment, landing sequence, or coordinator-owned integration state.
- Read or write Personal Overlay state only when explicitly assigned and authorized.
- Keep opaque runtime handles, private thread ids, or machine-local details out of public, publishable, or Git-backed ledger surfaces unless policy explicitly permits them.

## Modes

### Normal

Run a full batch pass:

1. Select or accept the batch.
2. Establish the coordinator ledger.
3. Check blocker, dependency, readiness, stale-label, and Isolation Boundary evidence.
4. Set up supported isolated workers with callback-first invocation references when authorized and parallel-safe.
5. Go idle until worker Workflow Results return, using bounded polling only for bootstrap, timeout, recovery, or diagnostics.
6. Track worker Workflow Results, review-correction lifecycle, blocked/failed/cancelled states, PRs, and merge events.
7. Wait for worker quiescence and human merge reports.
8. Invoke or follow `land-github-issue` one issue at a time for eligible merged issues.
9. Return a final coordinator Workflow Result.

### Read-Only / Plan-Only

Inspect, select, and propose the batch, ledger, handoff packets, sequencing, risks, and next actions. Do not create branches, worktrees, threads, labels, issues, PRs, comments, or external state.

### Resume

Rebuild or load the coordinator ledger, verify current branch/worker/PR/issue state as needed, and continue from the next safe phase under the current Authorization Boundary.

Landing is a phase of normal or resume mode, not a separate top-level mode.

## Workflow Phases

1. Establish the target:
   - Identify repository, tracker, base branch, checkout path, mode, Authorization Boundary, and any provided issue batch.
   - Read local instructions, `os/playbook/GITHUB_WORKFLOW.md`, `os/skills/ORCHESTRATION_LOOPS.md`, and the narrow skill contracts this workflow may call.
   - Record the initial Recovery Record: target, mode, Authorization Boundary, ledger surface, current phase, known blockers, and next action.

2. Select or accept the batch:
   - If no explicit batch is supplied, invoke or follow `select-issue-batch` in read-only mode using the requested selection goal and scope filters.
   - If a user or caller provides a batch, record the source and any supplied rationale.
   - Convert the recommendation or provided list into a concrete coordinator target inside this skill's Authorization Boundary.
   - Default max parallel implementation workers: 3, unless the user or Calling Workflow specifies another concurrency limit. If the candidate batch exceeds the limit, choose or ask for a first wave and record the rest as queued.

3. Establish the coordinator ledger:
   - Use an invocation-owned coordinator ledger by default.
   - Create or use a dedicated GitHub batch tracking issue only when the Authorization Boundary explicitly permits that tracker write.
   - Record selected issues, selection evidence, batch source, concurrency limit, worker slots, planned branches/worktrees/thread names, planned Workflow Invocation References, Isolation Boundaries, known dependencies, stale-label evidence, and next action.
   - Create a Recovery Checkpoint before worker launch or any other recovery boundary where losing context would make resumption unsafe.

4. Check blockers and parallel safety:
   - Verify `blocked`, `needs design consensus`, `ready-for-agent`, `ready-for-human`, `needs-human`, `needs-a-human`, HITL, and similar labels as evidence, not truth.
   - Read issue bodies and comments when needed to verify blocker/dependency/readiness signals.
   - Check whether selected issues share an uncoordinated mutable surface or dependency relationship.
   - Stop for a Blocking Human Decision when the coordinator finds the batch is not parallel-safe or the selected plan relies on stale or false evidence. Include the selected plan, contradictory evidence, recommended default, and resume options.
   - Do not perform per-issue label hygiene in the coordinator. Pass issue-local readiness and stale-label evidence to the assigned worker.

5. Prepare worker setup and minimal handoffs:
   - Assign each launched worker one issue, branch, isolated worktree, base branch, rebase policy, Isolation Boundary, Authorization Boundary, owned scope, workflow mode, validation expectations, PR expectations, Personal Overlay restrictions, prohibited actions, expected Workflow Result, recovery checkpoint expectations, release instruction, and blocked/failed/needs-human reporting rules.
   - In Codex, use separate branch-backed project threads for durable implementation workers when available. Do not use in-thread subagents for durable implementation workers that need branches and worktrees.
   - When the harness supports worker thread renaming, create or assign the worker thread, rename it to a legible target-specific name, record the thread name and Workflow Invocation Reference in the coordinator ledger, and only then send the `READY` signal or substantive assignment.
   - For a `coordinate-issue-batch` to `implement-github-issue` worker, use a pointer-first assignment packet with these fields: assigned issue URL and number; worker branch and isolated worktree; base branch and rebase policy; instruction to run `implement-github-issue` in the assigned mode; Isolation Boundary; Authorization Boundary; callback or result surface; release instruction; durable sources to read, including `AGENTS.md`, the issue body, `os/playbook/GITHUB_WORKFLOW.md`, `os/skills/ORCHESTRATION_LOOPS.md`, and `os/skills/implement-github-issue/SKILL.md`; validation expectations; PR and readiness-field expectations; Personal Overlay restrictions; prohibited actions, especially merge, issue closure, branch deletion, integration-branch mutation, label creation, permission changes, and writes outside the assigned scope; expected Workflow Result fields; and blocked, failed, and needs-human reporting rules.
   - Include only enough batch context for the worker to respect its Isolation Boundary and escalation rules, such as sibling issue numbers, known shared surfaces to avoid, dependency notes that affect the assigned issue, and escalation rules. Do not make the worker responsible for the full batch ledger, selection rationale, landing queue, or other workers' detailed state.

6. Launch and track workers:
   - Launch supported workers only in normal mode and only after the ledger checkpoint, parallel-safety checks, worker setup, thread naming when available, and callback/reference recording pass.
   - After launch, let the coordinator go idle until worker Workflow Results return. Use runtime polling only as bounded bootstrap, timeout, recovery, or diagnostic behavior, and record the reason and bound in the ledger.
   - Preserve one worker per isolated checkout, index, branch, and issue scope.
   - Track states such as `queued`, `launched`, `implementing`, `ready-for-human-review`, `revising-after-review`, `complete`, `permanently-blocked`, `failed`, `cancelled`, `merged`, `landing-skipped`, and `landed`.
   - Let workers run issue-local readiness repair, design consensus, implementation, validation, PR creation, review-loop convergence, and review-comment corrections within their assigned scope.
   - Route worker decisions to the coordinator only when they change the batch ledger, Isolation Boundary, Authorization Boundary, worker assignment, landing sequence, or coordinator-owned integration state.

7. Wait for quiescence and merge reports:
   - Do not begin post-merge landing checks while workers may still produce review-correction events for the current batch.
   - Treat the worker set as quiescent when every expected worker is complete, permanently blocked, failed, or explicitly cancelled.
   - Wait for the integration owner to report which completed PRs intended for the current landing phase are merged.
   - Record unmerged, blocked, failed, and cancelled issues as skipped for landing with their next action.

8. Land eligible issues:
   - Fetch or otherwise verify the remote integration branch when landing checks require current integration evidence.
   - For each eligible merged issue, invoke or follow `land-github-issue` one issue at a time under an explicit landing Authorization Boundary.
   - Skip issues whose PRs are unmerged, whose acceptance criteria are ambiguous, whose human-review labels block closure, or whose landing authorization is absent.
   - Record fulfilled, skipped, blocked, failed, cancelled, unmerged, unresolved, and landed outcomes in the coordinator ledger.

9. Report the coordinator Workflow Result:
   - Include issue URLs, selection source, ledger surface, branch/worktree/thread status, PRs, merge-event status, landing outcomes, skipped issues, validation, mutations, open risks, and recommended next action.
   - State clearly that PR merge/squash, branch deletion, new label creation, and any out-of-boundary external action remain outside v1 unless a separate approved workflow or direct human step owns them.

## Coordinator Ledger

The coordinator ledger must be recoverable enough to resume after interruption, compaction, worker returns, human merge events, or handoff.

Recover at least:

- batch id or invocation reference;
- repository and integration branch;
- mode and Authorization Boundary;
- ledger surface and checkpoint history;
- selected or provided issues and selection evidence;
- concurrency limit and queued issues;
- worker branch, worktree, thread name when available, Workflow Invocation Reference or callback surface when available, PR, assigned issue, Isolation Boundary, Authorization Boundary, release instruction, and worker state;
- worker Workflow Result evidence, validation, review-loop evidence, and open risks;
- bounded polling reason, bound, and result when runtime polling was used for bootstrap, timeout, recovery, or diagnostics;
- human-review, review-correction, merge, landing, skipped, blocked, failed, cancelled, and unresolved state;
- Blocking Human Decisions with exact question, recommended default, decision state, and resume rule;
- mutations performed;
- next action.

## Filing Rules

- Canonical workflow guidance lives in this skill.
- Batch-run ledgers default to the invocation-owned coordinator surface.
- Dedicated GitHub batch tracking issues are optional recovery surfaces and require explicit authorization.
- Worker issue readiness and label changes stay with assigned worker workflows such as `implement-github-issue`.
- Issue-specific closure evidence and checklist state stay on the GitHub issue through `land-github-issue`.
- Reusable improvements outside the batch coordinator contract belong in follow-up issues or project-approved propagation destinations.

## Quality Bar

- The skill composes `select-issue-batch`, `implement-github-issue`, and `land-github-issue` without duplicating their owned logic or widening their contracts.
- Normal mode owns a full batch pass while preserving explicit Authorization Boundaries for worker launch, tracking issue creation, landing, closure, and other external writes.
- Read-only/plan-only mode performs no local or external mutation.
- Resume mode can reconstruct enough ledger state to continue safely.
- Every launched worker has an Isolation Boundary, branch/worktree, Authorization Boundary, Workflow Invocation Reference when supported, release instruction, and expected Workflow Result.
- Supported durable worker threads are renamed before `READY`, and worker handoffs are minimal pointer-first packets rather than copied workflow contracts.
- The coordinator goes idle after worker launch and uses polling only as bounded bootstrap, timeout, recovery, or diagnostic behavior.
- Non-parallel-safe selected batches stop for a Blocking Human Decision.
- Workers own issue-local design/readiness questions, while coordinator-owned batch decisions return to the coordinator.
- Landing waits for worker quiescence and human merge reports.
- Eligible merged issues are landed one at a time through `land-github-issue`.
- Blocked, failed, cancelled, unmerged, ambiguous, and unauthorized issues are skipped for landing with next-action evidence.

## Verification

Before finishing:

1. Confirm local instructions, GitHub workflow policy, orchestration-loop guidance, and directly called skill contracts were read or honored.
2. Confirm mode and Authorization Boundary.
3. Confirm selection source or provided batch source.
4. Confirm parallel-safety checks and any Blocking Human Decisions.
5. Confirm coordinator ledger surface and Recovery Checkpoints.
6. Confirm worker handoffs include required fields, Workflow Invocation References when supported, release instructions, and only boundary-relevant batch context.
7. Confirm Codex durable workers use branch-backed project threads when that harness path is available, not in-thread subagents.
8. Confirm supported worker threads were renamed before `READY`, or record why renaming was unavailable.
9. Confirm the coordinator used callback-first Workflow Results and did not continuously poll workers except for recorded bounded bootstrap, timeout, recovery, or diagnostics.
10. Confirm per-issue readiness repair and label hygiene stayed with assigned worker workflows.
11. Confirm no PR merge/squash, branch deletion, label creation, permission change, out-of-scope issue mutation, or Personal Overlay access happened without explicit authorization.
12. Confirm landing checks waited for worker quiescence and human merge reports.
13. Confirm `land-github-issue` was invoked or followed only for eligible merged issues under an explicit landing Authorization Boundary.
14. Confirm final Workflow Result includes selected issues, ledger state, worker states, PRs, merge status, landing outcomes, skipped issues, validation, mutations, open risks, and recommended next action.
15. If this skill or its manifest entry changed, run `git diff --check` and `scripts/run-validator`.
