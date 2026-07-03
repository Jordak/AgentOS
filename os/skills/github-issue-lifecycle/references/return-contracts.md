# GitHub Issue Lifecycle Return Contracts

Lifecycle modules return their native artifacts:

- `select-issue-batch`: Markdown recommendation report.
- `coordinate-issue-batch`: batch Workflow Result.
- `github-loop`: repository-level loop Workflow Result.
- `implement-github-issue`: pull request plus one-issue implementation Workflow Result.
- `land-github-issue`: one-issue landing Workflow Result.

Every mutating Workflow Result should name the target, Authorization Boundary, mutations, validation, open risks, blockers or human decisions, and recommended next action.
