# Edge-Cases-Data-Integrity Lens

Use this lens only when the reviewer prompt assigns `edge-cases-data-integrity` as the optional lens.

## Reviewer Behavior

- Check boundary values, invalid input, partial failure, concurrency, idempotency, persistence, migration, rollback, and data-loss risks.
- Look for state that can become partially applied, stale, duplicated, silently dropped, or impossible to reconcile.
- Prefer concrete failure paths and representative data examples.
- Treat the lens as weighted attention, not an exclusive scope; still review the full target.

## Prompt Snippet

```md
Apply the `edge-cases-data-integrity` lens as extra attention: check boundary values, invalid input, partial failure, concurrency, idempotency, persistence, migration, rollback, and data-loss risks. Prefer concrete failure paths and representative data examples.
```
