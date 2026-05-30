# General Lens

Use this lens only when the reviewer prompt assigns `general` as the optional lens.

## Reviewer Behavior

- Balance correctness, regressions, tests, maintainability, safety, user-facing behavior, and design drift.
- Prefer high-confidence findings with concrete evidence over broad speculation.
- Treat the lens as weighted attention, not an exclusive scope; still review the full target.

## Prompt Snippet

```md
Apply the `general` lens as extra attention: balance correctness, regressions, missing tests, maintainability, safety, user-facing behavior, and design drift. Keep reviewing the full target, and avoid low-value style preferences when more material risks exist.
```
