# Release-Risk Lens

Use this lens only when the reviewer prompt assigns `release-risk` as the optional lens.

## Reviewer Behavior

- Check migration safety, rollout, operational visibility, fallback, dependency risk, performance cliffs, and support burden.
- Look for changes that are hard to revert, hard to observe, hard to migrate, or likely to surprise operators or users.
- Recommend validation or rollout signals that would reduce release uncertainty.
- Treat the lens as weighted attention, not an exclusive scope; still review the full target.

## Prompt Snippet

```md
Apply the `release-risk` lens as extra attention: check migration safety, rollout, operational visibility, fallback, dependency risk, performance cliffs, and support burden. Recommend validation or rollout signals that would reduce release uncertainty.
```
