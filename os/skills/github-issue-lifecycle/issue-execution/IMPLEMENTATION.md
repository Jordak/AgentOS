# Issue Execution Implementation

## Routing Algorithm

Read child interfaces before selecting a leaf:

1. Read `implement-github-issue/INTERFACE.md`.
2. Read `land-github-issue/INTERFACE.md`.

Choose `implement-github-issue` when the issue still needs implementation work, readiness repair, local code or docs changes, validation, a branch, commits, a pull request, or review-loop convergence.

Choose `land-github-issue` only when implementation evidence already exists on the remote integration branch or an already-merged PR, and the request is to reconcile acceptance criteria, update fulfilled checklist items, comment with evidence, or close the issue under authorization.

After selecting the leaf, read only that leaf's `IMPLEMENTATION.md` and follow its contract.

## Sequencing

- Run implementation readiness before feature-sized implementation work through the selected implementation leaf.
- Keep landing and closure separate from implementation. A PR-ready implementation result may recommend landing, but it does not own merge, issue closure, or branch deletion.
- Landing may return unmet criteria to the caller rather than spawning new implementation work.

## Recovery

For mutating work, preserve the selected leaf's Recovery Record before external writes, PR creation, review-loop invocation, issue-body edits, closure, or pauses for human decisions.

## Verification

- Implementation changes should run the selected leaf's local validation commands and repository validators.
- Landing should verify evidence is reachable from the remote integration branch before checklist updates or closure.
- Run `scripts/run-validator` after changing this module or child lifecycle modules.
