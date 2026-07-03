# GitHub Issue Lifecycle Policy

The lifecycle family preserves the contracts of its private modules:

- Selection recommends; it does not mutate.
- Coordination coordinates batches; it does not become a one-issue implementation or closure workflow.
- Implementation produces PR-ready evidence; it does not merge, close issues, or delete branches.
- Landing reconciles already-integrated evidence; it does not spawn new implementation work or guess unmet criteria.

Parent modules route by reading child `INTERFACE.md` files. They load child `IMPLEMENTATION.md` files only after selection.
