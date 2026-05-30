# Tests-Regressions Lens

Use this lens only when the reviewer prompt assigns `tests-regressions` as the optional lens.

## Reviewer Behavior

- Check for missing tests, weakened coverage, fixture drift, brittle assertions, untested migration or rollback paths, and likely regressions.
- Compare tests against the behavior and risk introduced by the target, not only against changed lines.
- Recommend validation signals that would prove a likely accepted issue family is closed.
- Treat the lens as weighted attention, not an exclusive scope; still review the full target.

## Prompt Snippet

```md
Apply the `tests-regressions` lens as extra attention: look for missing tests, weakened coverage, fixture drift, brittle assertions, untested migration or rollback paths, and likely regressions. For each accepted-risk family, name the validation signal that would close it.
```
