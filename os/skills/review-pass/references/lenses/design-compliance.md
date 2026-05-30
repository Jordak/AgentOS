# Design-Compliance Lens

Use this lens only when the reviewer prompt assigns `design-compliance` as the optional lens.

## Reviewer Behavior

- Compare the target against the durable design source, ADRs, PRD, planning note, or user-provided baseline intent.
- Check required outcomes, chosen implementation shape, explicit alternatives, non-goals, and risky assumptions.
- Report drift from the source as a design-readiness or compliance issue when the target changes semantics beyond what the source agreed to.
- Treat the lens as weighted attention, not an exclusive scope; still review the full target.

## Prompt Snippet

```md
Apply the `design-compliance` lens as extra attention: compare the target against the durable design source, ADRs, PRD, planning note, or baseline intent. Report drift from required outcomes, chosen implementation shape, explicit alternatives, non-goals, or risky assumptions.
```
