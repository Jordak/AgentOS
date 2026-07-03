# Implement GitHub Issue Interface

Take one GitHub issue through readiness gating, implementation, validation, pull request creation, and review-loop convergence while stopping before merge, issue closure, and branch deletion.

Choose this leaf when the user assigns one issue for implementation or asks for a PR-ready result for one issue.

Do not choose this leaf when the issue already has merged integration evidence and the request is acceptance reconciliation or closure. Route that to `land-github-issue`.

Required inputs:

- GitHub issue URL or issue number plus repository.
- Repository checkout and local instructions.
- Durable readiness evidence or authorization to run readiness repair.
- Authorization Boundary for local edits, commits, pushes, PR creation, issue/PR comments, and review-loop invocation.

Output contract:

- Pull request with readiness fields when implementation succeeds.
- Recoverable Workflow Result naming issue, labels, readiness verdict, branch/worktree, PR, commits, validation, review-loop evidence, mutations, risks, and recommended integration-owner action.

Mutability and safety:

- Mixed.
- Does not merge PRs, close issues, delete branches, create labels, or push outside the target feature branch.

Implementation:

- Read `IMPLEMENTATION.md` only after this leaf has been selected.
