## Summary

- Previously, <current behavior or problem>
- This PR <desired change>
- Validation will show <evidence>

Readiness evidence: <GitHub issue preferred, PRD, ADR, local design doc, durable gate-skip record, or exempt-work reason>
Readiness verdict: Ready to Implement

For feature-sized implementation, `Readiness evidence:` should usually point to the GitHub issue that contains or links the agreed design under `os/playbook/IMPLEMENT_FEATURES.md`. The cited durable source must already contain the full readiness field set: `Design readiness:`, `Consensus provenance:`, and `Gate skipped:`. Use a PRD, ADR, or local design doc only when the design is too large, architectural, private, or not naturally issue-shaped. Use `Readiness verdict: Gate Skipped` only for exempt work or an intentional bypass; for feature-sized intentional bypasses, point `Readiness evidence:` to the durable source whose `Gate skipped:` field records the reason and missing evidence. For truly exempt work where no durable source is required, a short exempt-work reason is enough.

## Validation

-
