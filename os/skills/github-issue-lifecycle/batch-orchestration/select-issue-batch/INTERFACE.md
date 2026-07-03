# Select Issue Batch Interface

Select and explain the next high-leverage GitHub issue or small issue batch without mutating tracker state or starting workers.

Choose this leaf when the user asks what issue to do next, asks for a batch recommendation, wants a read-only planner for a later batch pass, or needs issue-state and parallel-safety reasoning before coordination.

Do not choose this leaf when the user has already authorized a mutating batch pass, worker launches, branch creation, issue comments, labels, PR work, or landing. Route those requests to `coordinate-issue-batch` after preserving any selection goal.

Required inputs:

- Target repository or issue tracker.
- Optional selection goal, filters, labels, scope, batch size, or sequencing preference.

Output contract:

- Markdown recommendation report with ranked issues, rationale, readiness and blocker evidence, parallel-safety notes, rejected or deferred candidates, assumptions, and handoff notes for coordination.

Mutability and safety:

- Read-only.
- No issue comments, labels, branches, worker launches, PRs, or closure actions.

Implementation:

- Read `IMPLEMENTATION.md` only after this leaf has been selected.
