# Coordinate Issue Batch Interface

Coordinate one GitHub issue batch pass by selecting or accepting a batch, launching isolated implementation workers when authorized, tracking results, waiting for merge events, and landing eligible merged issues through the issue-execution landing leaf.

Choose this leaf when the user asks to run one batch pass, execute an accepted batch, launch implementation workers, maintain a coordinator ledger, handle returned worker Workflow Results, or reconcile eligible merged issues for one batch.

Do not choose this leaf for repeated repository-level passes without a single current batch target; route repeated passes to `github-loop`. Do not choose it for one assigned issue implementation; route that to `issue-execution`.

Required inputs:

- Target repository or accepted issue batch.
- Authorization Boundary for worker launch, issue/PR comments, labels, branch/worktree creation, pushes, PRs, and landing actions.
- Callback or result surface when durable workers are launched.

Output contract:

- Batch Workflow Result with selected issues, workers, branches/worktrees, PRs, landing status, validation, blockers, effort metadata when relevant, mutations, and recommended next action.

Mutability and safety:

- Mixed.
- Does not merge PRs, close issues directly outside the landing leaf, delete branches, create labels, or widen worker scopes beyond assigned issue contracts.

Implementation:

- Read `IMPLEMENTATION.md` only after this leaf has been selected.
