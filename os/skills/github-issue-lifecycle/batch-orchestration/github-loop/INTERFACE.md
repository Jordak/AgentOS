# GitHub Loop Interface

Run or resume repeated GitHub issue batch passes by invoking batch coordination until no suitable issues remain or a stop condition halts the repository-level loop.

Choose this leaf when the user asks to keep going through issues, repeatedly run issue batches, resume a repository-level issue loop, or continue batch passes until a stated cap or stop condition.

Do not choose this leaf for one batch pass; route that to `coordinate-issue-batch`. Do not choose it for read-only next-issue advice; route that to `select-issue-batch`.

Required inputs:

- Target repository or issue tracker.
- Optional loop goal, filters, caps, batch size, parallelism limit, or resume context.
- Authorization Boundary and callback/result behavior for downstream batch passes.

Output contract:

- Repository-level loop Workflow Result with pass outcomes, aggregate status, batch-pass references, blockers, validation, mutations, and recommended next action.

Mutability and safety:

- Mixed.
- Does not select issues directly, launch workers directly, land issues directly, merge PRs, close issues, or delete branches. Those responsibilities stay with selected child workflows.

Implementation:

- Read `IMPLEMENTATION.md` only after this leaf has been selected.
