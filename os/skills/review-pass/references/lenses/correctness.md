# Correctness Lens

Use this lens only when the reviewer prompt assigns `correctness` as the optional lens.

## Reviewer Behavior

- Check invariants, control flow, state transitions, API contracts, error paths, and false success or false failure cases.
- Trace caller/callee interactions far enough to prove the behavior, not merely suspect it.
- Look for changed assumptions that leave existing behavior accidentally broken.
- Treat the lens as weighted attention, not an exclusive scope; still review the full target.

## Prompt Snippet

```md
Apply the `correctness` lens as extra attention: check invariants, control flow, state transitions, API contracts, error paths, false success cases, and false failure cases. Trace related code far enough to prove each finding before reporting it.
```
