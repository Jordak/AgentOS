# Land GitHub Issue Interface

Verify one GitHub issue's acceptance criteria against remote integration-branch evidence, update fulfilled checklist criteria, and close the issue only when closure is authorized and fully evidenced.

Choose this leaf when the resolving PR or commit is already merged or otherwise reachable from the remote integration branch, and the user or calling workflow asks to reconcile issue acceptance criteria or close the issue.

Do not choose this leaf to implement missing work, create PRs, merge PRs, delete branches, or coordinate multi-issue batches.

Required inputs:

- GitHub issue URL or issue number plus repository.
- Remote integration branch or merged PR evidence.
- Explicit Authorization Boundary for issue-body edits, issue comments, and closure.

Output contract:

- Workflow Result naming evidence checked, fulfilled criteria, unmet or ambiguous criteria, checklist mutations made or proposed, closure action or blocker, validation, risks, and recommended next action.

Mutability and safety:

- Mixed with explicit authorization for issue edits/comments/closure.
- Never closes based on local-only commits, unmerged branches, title similarity, or unchecked assumptions.

Implementation:

- Read `IMPLEMENTATION.md` only after this leaf has been selected.
