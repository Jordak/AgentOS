# Batch Orchestration Interface

Batch orchestration handles repository-level GitHub issue selection, batch-pass coordination, and repeated batch-pass loops.

Choose this module when the user asks what issue to do next, asks for a small issue batch, wants workers launched or coordinated for a batch, wants to resume a batch pass, or wants to keep running issue batches until a stop condition.

Do not choose this module for a single assigned issue implementation or for one merged issue's acceptance reconciliation unless the request is part of a broader batch pass. Choose `issue-execution` for one-issue implementation or one-issue landing.

Required inputs:

- Target repository or issue tracker.
- Selection goal, explicit issue list, batch scope, or resume target.
- Authorization Boundary for any issue comments, labels, worker launches, branch/worktree creation, pushes, PRs, or landing actions.
- Callback/result surface when launching durable workers or batch passes in a harness that supports it.

Output contract:

- A read-only issue or batch recommendation, a batch-pass Workflow Result, or a repository-level loop result.
- For mutating coordination, recoverable state naming selected issues, workers, branches/worktrees, PRs, landing status, blockers, validation, and recommended next action.

Mutability and safety:

- `select-issue-batch` is read-only.
- `coordinate-issue-batch` and `github-loop` are mixed and may perform only their contract-owned writes under the current Authorization Boundary.
- This module does not merge PRs, close issues directly, delete branches, create labels, or widen worker scope beyond selected child contracts.

Child interfaces:

- `select-issue-batch/INTERFACE.md`
- `coordinate-issue-batch/INTERFACE.md`
- `github-loop/INTERFACE.md`
