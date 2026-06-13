---
name: github-loop
description: Repeatedly run or resume GitHub issue batch passes by invoking coordinate-issue-batch until no suitable issues remain or a stop condition halts the repository-level loop.
---

# GitHub Loop

## Goal

Coordinate repeated GitHub issue batch passes for one repository while preserving the boundaries of the narrower workflows it composes.

`github-loop` is the repository-level loop above `coordinate-issue-batch`. It owns the decision to start, resume, or stop successive batch-pass invocations. It passes callback-first invocation references to batch coordinators when the harness supports them, then waits for returned Workflow Results instead of continuously monitoring the coordinator. It does not own issue selection internals, worker launch, batch ledgers, landing, issue closure, PR merge, branch deletion, or per-issue readiness repair.

Inbound invocation is prose-only in v1. A caller may ask `github-loop` to start or resume in the current conversation, thread, or reporting surface, but `github-loop` itself does not accept a caller-supplied Workflow Invocation Reference, result surface, or release instruction. Its callback-first responsibilities are downstream responsibilities for the `coordinate-issue-batch` invocations it launches.

## Contract

Inputs:

- A target GitHub repository or issue tracker, inferred from the current checkout when possible.
- Optional loop goal or selection filters to pass to `coordinate-issue-batch`, such as high-leverage work, ready-only work, label filters, issue scope, or a maximum batch size.
- Optional loop-level caps, such as max passes, max elapsed or budget checkpoint, max batch size, or max parallel workers to pass through to `coordinate-issue-batch`.
- Current local agent instructions and project guidance, including `AGENTS.md`.
- Current AgentOS GitHub workflow policy at `os/playbook/GITHUB_WORKFLOW.md`.
- Current orchestration-loop vocabulary at `os/skills/ORCHESTRATION_LOOPS.md`.
- `coordinate-issue-batch` when available in the active AgentOS checkout or harness.
- Optional explicit mode: normal, read-only/plan-only, or resume.
- No inbound callback/release protocol in v1; treat the user's prose request and current reporting surface as the invocation contract.

Output artifact:

- A GitHub loop Workflow Result with terminal status (`completed`, `blocked`, `failed`, `cancelled`, or `needs-human`), repository, loop goal, mode, Authorization Boundary, loop caps, pass count, effort metadata when available or relevant under `os/skills/ORCHESTRATION_LOOPS.md`, public-safe child coordinator thread names or unavailable reasons, called batch-pass invocation references or public-safe summaries, called batch-pass results, worker-reported raw readiness evidence, worker-reported readiness verdict, and final readiness label state, `Gate Skipped` reasons plus durable gate-skip field/state or missing evidence when present, stale-label contradictions, merge-report state, blockers, needs-human decisions, failures, cancellations, release-instruction handling, stop reason, validation, mutations performed, open risks, and recommended next action.
- A recoverable loop Recovery Record in the current reporting mode.
- Optional dedicated GitHub tracking issue only when the Authorization Boundary explicitly permits creating or using that tracker surface.

Mutability:

- Mixed. Normal mode may perform ordinary loop writes inside the Authorization Boundary: loop Recovery Checkpoints on authorized surfaces, callback-first called-workflow handoff packets, durable called-workflow launches when the harness supports them, supported child coordinator thread renaming to public-safe, legible target-specific names before assignment or `READY`, and resume requests to `coordinate-issue-batch`.
- Read-only/plan-only mode proposes the loop goal, caps, stop policy, recovery surface, and batch-pass sequencing without launching coordinators, creating workers, mutating tracker state, creating branches, or editing local tracked files.
- Resume mode rebuilds or loads the loop Recovery Record and continues from the next safe phase under the current Authorization Boundary.

Durable called-workflow launch authorization:

- A user invoking `github-loop` in normal or resume mode is explicitly asking for the workflow described here, including separate durable `coordinate-issue-batch` called-workflow invocations when the active harness supports them.
- In harnesses with Codex-style thread tools, treat the `github-loop` invocation as the explicit request needed to create a child coordinator thread for each normal batch pass. Do not silently downgrade to same-thread execution merely because the user did not separately say "create a child thread."
- Same-thread execution is a fallback for read-only/plan-only mode, unavailable durable launch tooling, failed or denied thread creation, or an explicitly unsuitable launch surface. When using the fallback, record why it was used in the Recovery Record and final Workflow Result.

Tools and connectors:

- Local filesystem, `git`, `rg`, GitHub connector or `gh`, and repository-local push helpers when local instructions require them.
- `os/skills/coordinate-issue-batch/SKILL.md` for each full batch pass.
- `os/skills/ORCHESTRATION_LOOPS.md` for Authorization Boundary, Recovery Record, Recovery Checkpoint, Blocking Human Decision, Workflow Result, and Integration Ownership vocabulary.
- `os/playbook/GITHUB_WORKFLOW.md` for GitHub issue, branch, worker, PR, merge-report, and closure discipline.

Safety:

- Do not run issue selection directly. Pass selection goals and filters to `coordinate-issue-batch`.
- Do not launch implementation workers directly. Worker launch, branch/worktree/thread setup, handoffs, parallel-safety checks, and batch ledgers remain owned by `coordinate-issue-batch`.
- Do not continuously poll `coordinate-issue-batch` as the normal progress model. Pass a Workflow Invocation Reference when supported and wait for a Workflow Result, using polling only as bounded bootstrap, timeout, recovery, or diagnostic behavior recorded in the loop Recovery Record.
- Do not land issues directly. Resume or invoke `coordinate-issue-batch` so its batch ledger can invoke or follow `land-github-issue` for eligible merged issues.
- Do not merge or squash PRs, close issues, delete branches, create labels, change permissions or settings, handle credentials or MFA, or write outside the loop's assigned scope unless another approved workflow or explicit user authorization owns that action.
- Do not start a later batch while the current batch has unmerged ready PRs waiting for human merge reports, failed or cancelled workers, a failed or cancelled batch pass, blocked issues or workers, needs-human states, unresolved Blocking Human Decisions, or incomplete landing decisions.
- Do not silently broaden the selection goal when no issues are selected. Stop for the current goal and recommend a broader rerun when appropriate.
- Keep opaque runtime handles, private thread IDs, and machine-local details out of public, publishable, or Git-backed recovery surfaces unless policy explicitly permits them.
- Read or write Personal Overlay state only when explicitly assigned and authorized.

## Modes

### Normal

This is the default mode when none is specified.

Run repeated batch passes:

1. Establish the loop target, goal, caps, Authorization Boundary, and Recovery Record.
2. Invoke or resume `coordinate-issue-batch` for the current batch pass with a callback or result surface when supported.
3. Go idle until the coordinator Workflow Result returns, using bounded polling only for bootstrap, timeout, recovery, or diagnostics.
4. Consume the coordinator Workflow Result.
5. Stop, pause, or start another pass according to the stop and continue policy.
6. Return a final loop Workflow Result.

When the harness supports a durable called-workflow launch path, run each normal `coordinate-issue-batch` pass as a separate recoverable called-workflow invocation. Same-thread execution is an acceptable fallback, but the loop-level Recovery Record and batch-level coordinator ledger must remain distinct.

For Codex harnesses with thread creation tools, this means start a child coordinator thread for the batch pass after the loop Recovery Checkpoint, rename it to a public-safe, legible target-specific name before assignment or `READY` when thread renaming is supported, pass the `coordinate-issue-batch` request and Authorization Boundary into that child, then wait for or recover its Workflow Result before deciding whether to continue. The user's `github-loop` request is the explicit request for that child coordinator thread; ask again only when the launch would require a permission, scope, cost, or target choice outside this skill's normal Authorization Boundary.

### Read-Only / Plan-Only

Inspect the repository and propose the loop goal, caps, expected batch-pass sequence, stop policy, recovery surface, and risks. Do not launch coordinators, create branches or worktrees, spawn workers, edit issues, change labels, create PRs, post comments, or mutate local tracked files.

### Resume

Rebuild or load the loop Recovery Record, verify the current batch-pass state, and continue from the next safe phase. Resume may pass human merge reports or other approved resume inputs back into `coordinate-issue-batch`; the batch coordinator remains responsible for merge-event handling, worker quiescence, and eligible landing for its batch.

## Workflow Phases

1. Establish the target:
   - Identify repository, issue tracker, integration branch, checkout path, mode, loop goal, caps, Authorization Boundary, and reporting mode.
   - Read local instructions, `os/playbook/GITHUB_WORKFLOW.md`, `os/skills/ORCHESTRATION_LOOPS.md`, and `os/skills/coordinate-issue-batch/SKILL.md`.
   - Record the initial Recovery Record: target, mode, loop goal, caps, Authorization Boundary, effort metadata when available or relevant, ledger surface, current phase, known blockers, and next action.

2. Plan the next batch pass:
   - If this is pass 1, prepare the `coordinate-issue-batch` request from the loop goal, selection filters, caps, and Authorization Boundary.
   - If resuming, identify whether the next safe action is to resume an in-progress batch, pass in human merge reports, or decide whether a settled prior batch permits another pass.
   - Preserve the layer boundary: pass selection goals to `coordinate-issue-batch` rather than selecting issues directly.

3. Create a Recovery Checkpoint:
   - Before starting or resuming a batch pass, checkpoint the loop Recovery Record on an authorized surface.
   - Include the current pass number, expected `coordinate-issue-batch` Workflow Result, planned public-safe child coordinator thread name or rename-unavailable reason, Workflow Invocation Reference or result surface when available, loop caps, Authorization Boundary, effort metadata when available or relevant, and next action.
   - Keep private runtime references out of public or Git-backed surfaces.

4. Invoke or resume `coordinate-issue-batch`:
   - Start a separate durable called-workflow invocation when the harness supports it.
   - In Codex harnesses, create or resume a child coordinator thread for the `coordinate-issue-batch` pass; do not treat same-thread execution as the default.
   - When thread renaming is supported, rename the child coordinator thread to a public-safe, legible target-specific name before sending the assignment or `READY` signal; otherwise record why a public-safe rename was unavailable.
   - After create or resume, and after any supported rename, update the loop Recovery Record with the actual public-safe child coordinator thread name or rename-unavailable reason, actual Workflow Invocation Reference or result surface when available, any redaction or unavailable reason, and release instruction before sending the assignment or `READY` signal.
   - Pass a Workflow Invocation Reference, expected coordinator Workflow Result shape, applicable effort metadata, and release instruction to the coordinator when the harness supports a callback or result surface.
   - After launch, let the loop go idle until the coordinator returns its Workflow Result. Use runtime polling only as bounded bootstrap, timeout, recovery, or diagnostic behavior, and record the reason and bound in the Recovery Record.
   - Use same-thread fallback only when a separate durable invocation is unavailable, fails, is denied, or is explicitly unsuitable, and record the fallback reason.
   - Do not launch implementation workers directly from `github-loop`.
   - Wait for or recover the coordinator Workflow Result before deciding whether to start another batch pass.

5. Consume the coordinator result:
   - Record selected issues, worker states, PRs, effort metadata from the coordinator result when available or relevant, worker-reported raw readiness evidence, worker-reported readiness verdict, and final readiness label state, `Gate Skipped` reasons plus durable gate-skip field/state or missing evidence when present, stale-label contradictions, merge-report state, landing outcomes, skipped issues, blockers, needs-human decisions, failures, cancellations, release-instruction handling, validation, mutations, open risks, and recommended next action.
   - Treat failed or cancelled workers, failed or cancelled batch passes, blocked workers or issues, needs-human states, unresolved Blocking Human Decisions, and ready unmerged PRs as loop stop conditions.
   - Let `coordinate-issue-batch` finish any same-batch duties it can safely finish, including authorized landing of eligible succeeded and merged issues, before treating blocked work as a loop-level stop.

6. Decide whether to continue:
   - Start another batch only when the previous batch is cleanly settled:
     - every launched worker is quiescent;
     - no worker or batch pass failed or was cancelled;
     - no worker or issue remains blocked or needs a human decision;
     - no ready PRs are waiting on human merge reports;
     - all eligible merged work was landed or explicitly skipped by `coordinate-issue-batch`;
     - the coordinator result recommends continuing selection for the current loop goal;
     - loop-level caps and Authorization Boundary permit another pass.
   - If `coordinate-issue-batch` returns no selected issues, stop successfully for the current loop goal and recommend a broader rerun only when useful.
   - If successful PRs and blocked or needs-human work coexist, return a combined stop report naming both the merge-report state and the blocker or human decision needed.

7. Report the loop Workflow Result:
   - Begin with `Status:` using one canonical terminal value: `completed`, `blocked`, `failed`, `cancelled`, or `needs-human`.
   - For mixed batch-pass outcomes, report the detailed batch, worker, issue, merge-report, landing, blocked, needs-human, failed, and cancelled states. Aggregate status precedence rules and richer status maps are deferred to GitHub issue #158.
   - Include repository, loop goal, mode, Authorization Boundary, pass count, effort metadata when available or relevant, public-safe child coordinator thread names or unavailable reasons, batch invocation references or public-safe summaries, batch result summaries, worker-reported raw readiness evidence, worker-reported readiness verdict, and final readiness label state, `Gate Skipped` reasons plus durable gate-skip field/state or missing evidence when present, stale-label contradictions, release-instruction handling, stop reason, validation, mutations performed, open risks, and recommended next action.
   - Return the result in the current prose reporting surface. Do not wait for a caller release signal; inbound caller-supplied Workflow Invocation References, result surfaces, and release instructions are out of scope for `github-loop` v1.
   - State clearly that merge, branch deletion, new label creation, and out-of-boundary external actions remain outside v1 unless a separate approved workflow or direct human step owns them.

## Stop Conditions

Stop the repository-level loop when any of these are true:

- `coordinate-issue-batch` returns no selected issues for the current loop goal or filters.
- A Blocking Human Decision is needed.
- A worker, issue, or batch pass returns `needs-human`.
- A worker fails or is cancelled, or the batch pass fails or is cancelled.
- A worker or issue returns or remains blocked after the batch coordinator finishes same-batch work it can safely finish.
- Ready PRs need human merge reports before landing can continue.
- The user explicitly stops the loop.
- Loop-level caps are reached, such as max passes, max elapsed, or a budget checkpoint.
- The Authorization Boundary does not permit the next required action.
- Validation fails in a way the called workflow cannot resolve inside its own contract.

## Loop Recovery Record

The loop Recovery Record must be recoverable enough to resume after interruption, compaction, called-workflow completion, human merge reports, or handoff.

Recover at least:

- loop id or invocation reference when available;
- prose invocation request and current reporting surface; if another workflow called `github-loop`, record that the inbound contract is still prose-only and no caller-supplied callback/result surface or release instruction is supported in v1;
- repository and integration branch;
- loop goal, mode, Authorization Boundary, and effort metadata when available or relevant;
- loop-level caps and pass-through caps for `coordinate-issue-batch`;
- ledger or checkpoint surface;
- current pass number and current phase;
- called `coordinate-issue-batch` public-safe child coordinator thread names or rename-unavailable reasons, invocation references, callback/result surfaces, release instructions, pre-assignment actual-reference checkpoints, release-instruction handling, or public-safe summaries;
- bounded polling reason, bound, and result when runtime polling was used for bootstrap, timeout, recovery, or diagnostics;
- batch result summaries, including selected issues, worker status, PRs, effort metadata when available or relevant, worker-reported raw readiness evidence, worker-reported readiness verdict, final readiness label state, `Gate Skipped` reasons plus durable gate-skip field/state or missing evidence when present, stale-label contradictions, merge-report state, landing outcomes, skipped issues, blockers, needs-human decisions, failures, cancellations, validation, release-instruction handling, and recommended next action;
- Blocking Human Decisions with exact question, recommended default, decision state, recovery location, and resume rule;
- mutations performed by `github-loop`;
- next safe action.

Public, publishable, or Git-backed recovery surfaces must use only public-safe fields. Keep private thread ids, opaque runtime handles, and machine-local details in an authorized private surface or record that the stable reference is unavailable or redacted.

## Filing Rules

- Canonical workflow guidance lives in this skill.
- Loop-run ledgers default to the invocation-owned reporting surface.
- Dedicated GitHub tracking issues are optional recovery surfaces and require explicit authorization.
- Batch ledgers, worker states, landing queues, and issue-specific closure evidence stay with `coordinate-issue-batch` and its called workflows.
- Issue implementation-readiness gates, repair, verdicts, and related label hygiene stay with assigned issue workflows through their readiness contracts.
- Reusable improvements outside this contract belong in follow-up issues or project-approved propagation destinations rather than silent scope expansion.

## Quality Bar

- The skill composes `coordinate-issue-batch` without duplicating selection, worker launch, batch ledger, or landing responsibilities.
- Normal mode owns repeated batch-pass sequencing while preserving explicit Authorization Boundaries.
- Read-only/plan-only mode performs no local or external mutation.
- Resume mode can reconstruct enough loop state to continue safely.
- The inbound `github-loop` contract is prose-only in v1; callback/result surfaces and release instructions are passed only to called batch-pass workflows.
- Each batch pass has a Recovery Checkpoint before launch or resume.
- Separate durable called-workflow invocations are the normal path when the harness supports them; same-thread execution is a recorded fallback that keeps loop and batch recovery records distinct.
- Each called batch pass receives a Workflow Invocation Reference and release instruction when the harness supports it.
- Supported child coordinator threads are renamed to public-safe, legible target-specific names before assignment or `READY`, or the unavailable rename is recorded.
- Actual child coordinator thread names, invocation references or result surfaces, redaction or unavailable reasons, and release instructions are checkpointed after create/resume/rename and before assignment or `READY`.
- The loop goes idle after batch-pass launch and uses polling only as bounded bootstrap, timeout, recovery, or diagnostic behavior.
- Another pass starts only after the prior batch is cleanly settled.
- No selected issues ends the loop for the current goal instead of silently broadening scope.
- Failed or cancelled workers, failed or cancelled batch passes, blocked workers or issues, needs-human states, unresolved human decisions, and unmerged ready PRs stop the loop before later batch selection.
- The final Workflow Result makes canonical terminal status, effort metadata when available or relevant, worker-reported raw readiness evidence, worker-reported readiness verdict, final readiness label state, `Gate Skipped` reasons plus durable gate-skip field/state or missing evidence when present, stale-label contradictions, merge reports, blockers, release-instruction handling, validation, mutations, open risks, and next action recoverable.

## Verification

Before finishing:

1. Confirm local instructions, GitHub workflow policy, orchestration-loop guidance, and `coordinate-issue-batch` were read or honored.
2. Confirm mode, loop goal, loop caps, Authorization Boundary, and prose-only inbound invocation contract.
3. Confirm the loop did not perform issue selection, worker launch, or landing directly.
4. Confirm Recovery Checkpoints before starting or resuming batch passes.
5. Confirm each normal or resume batch pass used a separate durable called-workflow invocation when supported, or recorded why same-thread fallback was necessary.
6. Confirm supported child coordinator threads were renamed to public-safe, legible target-specific names before assignment or `READY`, or record why a public-safe rename was unavailable, and confirm the actual child coordinator thread name, invocation reference or result surface, redaction or unavailable reason, and release instruction were checkpointed before assignment or `READY`.
7. Confirm each called batch pass received a Workflow Invocation Reference and release instruction when supported.
8. Confirm the loop used callback-first Workflow Results and did not continuously poll `coordinate-issue-batch` except for recorded bounded bootstrap, timeout, recovery, or diagnostics.
9. Confirm any called `coordinate-issue-batch` pass returned a recoverable Workflow Result with release-instruction handling, or a Blocking Human Decision, before the loop continued.
10. Confirm no later batch started while the prior batch had failed or cancelled workers, failed or cancelled batch passes, blocked work, needs-human states, unresolved human decisions, ready unmerged PRs, or incomplete landing decisions.
11. Confirm no PR merge/squash, branch deletion, issue closure, label creation, permission change, out-of-scope external write, or Personal Overlay access happened without explicit authorization.
12. Confirm final Workflow Result includes canonical terminal status, repository, loop goal, pass count, batch result summaries, effort metadata when available or relevant, worker-reported raw readiness evidence, worker-reported readiness verdict, final readiness label state, `Gate Skipped` reasons plus durable gate-skip field/state or missing evidence when present, stale-label contradictions, stop reason, downstream release-instruction handling, validation, mutations, open risks, and recommended next action.
13. If this skill or its manifest entry changed, run `git diff --check` and `scripts/run-validator`.
