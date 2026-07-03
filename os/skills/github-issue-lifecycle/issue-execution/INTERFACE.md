# Issue Execution Interface

Issue execution handles one assigned GitHub issue from readiness through PR-ready implementation, or one merged issue from integration evidence through authorized acceptance reconciliation and closure.

Choose this module when the user names one issue to implement, asks for one issue's PR-ready worker workflow, asks to verify one issue against merged evidence, or asks to close one issue after integration proof exists.

Do not choose this module for issue selection, batch coordination, repeated batch loops, or multi-worker orchestration. Choose `batch-orchestration` for those requests.

Required inputs:

- Target GitHub issue URL or issue number plus repository.
- Current checkout when implementation or local validation is required.
- Authorization Boundary for readiness repair, local edits, commits, pushes, PR creation, review-loop invocation, issue-body checklist edits, comments, or closure.

Output contract:

- For implementation: PR-ready Workflow Result with readiness evidence, branch/worktree, commits, validation, PR, review-loop status, blockers, and recommended integration-owner action.
- For landing: landing Workflow Result with integration evidence, fulfilled and unmet acceptance criteria, checklist updates, closure action or blocker, validation, and recommended next action.

Mutability and safety:

- Mixed.
- One-issue implementation does not merge PRs, close issues, or delete branches.
- One-issue landing does not merge PRs, spawn workers, widen implementation scope, or close without verified integration evidence and authorization.

Child interfaces:

- `implement-github-issue/INTERFACE.md`
- `land-github-issue/INTERFACE.md`
