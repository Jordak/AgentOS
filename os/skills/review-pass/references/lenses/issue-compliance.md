# Issue-Compliance Lens

Use this lens only when the reviewer prompt assigns `issue-compliance` as the optional lens.

## Reviewer Behavior

- Compare the target against the current issue's requested outcomes, acceptance criteria, non-goals, and validation plan.
- Check whether the implementation closes the intended issue without expanding scope or leaving required follow-through undone.
- Report missing propagation across related issue surfaces when a workflow or contract changes.
- Treat the lens as weighted attention, not an exclusive scope; still review the full target.

## Prompt Snippet

```md
Apply the `issue-compliance` lens as extra attention: compare the target against the current issue's requested outcomes, acceptance criteria, non-goals, and validation plan. Report issue drift, missing required behavior, or untracked scope expansion.
```
