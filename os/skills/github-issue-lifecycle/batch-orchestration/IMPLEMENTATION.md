# Batch Orchestration Implementation

## Routing Algorithm

Read child interfaces before selecting a leaf:

1. Read `select-issue-batch/INTERFACE.md`.
2. Read `coordinate-issue-batch/INTERFACE.md`.
3. Read `github-loop/INTERFACE.md`.

Choose `select-issue-batch` when the user asks for a recommendation, ranking, next issue, or batch proposal and has not authorized mutation.

Choose `coordinate-issue-batch` when the user asks to run one batch pass, launch or track implementation workers, convert an accepted batch into execution, wait for merge reports, or land eligible merged issues from a specific batch.

Choose `github-loop` when the user asks to keep running or resume successive batch passes until no suitable issues remain, a cap is reached, or a stop condition fires.

After selecting the leaf, read only that leaf's `IMPLEMENTATION.md` and follow its contract.

## Sequencing

- Preserve `os/playbook/GITHUB_WORKFLOW.md` branch, worktree, PR, issue closure, and external-write discipline.
- Use `os/skills/ORCHESTRATION_LOOPS.md` for callback-first workflow invocation, Recovery Records, effort metadata, and aggregate statuses.
- Do not let a batch-level request bypass one-issue readiness gates or landing/closure gates owned by issue-execution leaves.

## Recovery

For mutating or delegated work, maintain a Recovery Record before external writes, worker launches, child-thread creation, or pauses for human decisions. The selected leaf implementation defines the required fields.

## Verification

- For read-only selection, verify the recommendation names evidence and blockers.
- For mutating coordination, verify selected workers, PRs, landing actions, skipped items, validation, and next owner are recoverable.
- Run `scripts/run-validator` after changing this module or child lifecycle modules.
