# Review Packet Template

Use this file as the canonical rendering template for `review-pass` Review Packets. `reviewer-prompts.md` owns reviewer prompt mechanics; this file owns packet shape, headings, IDs, field labels, examples, and empty states.

## Rendering Rules

- Use the exact section headings and section order shown in the canonical template.
- Do not omit top-level sections. Use `None.` or `Not applicable.` when a section has no content.
- Severity values are exactly `P0`, `P1`, `P2`, or `P3`. Do not append labels such as `High` or `Medium`.
- Reviewer aliases use `P<panel-number>-R<reviewer-number>`, where `P` means panel, for example `P1-R2`.
- Reviewer Finding IDs append `F<finding-number>` to the reviewer alias, for example `P1-R2-F3`.
- Issue Family IDs use `IF<family-number>`, for example `IF1`.
- Verification packets may preserve an `IF` ID from a prior packet when the caller supplied that packet and the family is clearly the same. New issue families receive new `IF` IDs.
- Issue-family titles are prose summaries. Do not wrap the whole title in backticks. Bold the title in the heading.
- In `## Panel`, render reviewer aliases, lens names, and mode values as plain text instead of inline code so narrow clients do not chip-wrap short values.
- Avoid long inline code spans for shell commands, regexes, or searches. If the text includes backslashes, bracket escapes, pipes, or enough length to wrap awkwardly, summarize it in prose or use a fenced code block.
- Do not include opaque reviewer handle values in the packet. Report only handle availability.
- Fixed prior issue families do not appear under `## Issue Families`; summarize them in `## Verification Results`.
- Within each issue family, render `Recommended disposition`, `Failure mode`, and `Suggested fix shape` as the first three fields.
- If chat output is a summary because the packet is too large, `## Temporary Packet Artifact` must name the temporary Markdown file that contains the complete packet.

## Severity

- `P0`: release-blocking or immediately dangerous correctness, data-loss, security, privacy, or external-effect risk.
- `P1`: likely accepted high-impact correctness, regression, safety, privacy, or contract risk.
- `P2`: likely accepted medium-impact risk, missing validation, maintainability concern, or user-facing rough edge.
- `P3`: low-impact concern, polish issue, or optional follow-up that may be declined.

## Canonical Template

```md
# Review Packet

## Packet Summary

Target: <target>
Repository: <repo path or owner/name>
Mode: <fresh | verification>
Base: <base ref or commit>
Head: <head or current head>
Baseline intent: <summary and source, or limitation>
Model and effort metadata: <requested model/effort, actual model/effort if reported, selection source, override notes, or unknown/not reported/not applicable>
Reviewer continuity: <same-source reviewers resumed | packet/finding-source fallback | none | not applicable>
Continuity handle availability: <private handoff available | unavailable | not applicable>

## Panel

| Reviewer | Lens | Mode | Notes |
| --- | --- | --- | --- |
| <reviewer-alias> | <lens> | <fresh or verification> | <brief coverage or verification note> |

## Coverage

<scope inspected, metadata read, validation output used, and limitations>

## Issue Families

### IF1. Severity: P1 - **Family title**

**Recommended disposition:** <likely accept | likely decline | needs user/design judgment>
**Failure mode:** <generalized invariant or risk>
**Suggested fix shape:** <family-level fix, simplification, scope reduction, or none>
**Found by:** `<reviewer-finding-id>`, `<reviewer-finding-id>`
**Evidence:** <file:line, diff hunk, command output, source link, or reviewer-cited evidence>
**Representative findings:** <concrete reviewer observations that exemplify this family>
**Related occurrences or sibling search:** <siblings found, search performed, or recommended search>
**Validation signal:** <test, command, inspection, or proof that would close it>

## Verification Results

<Not applicable. | bullets summarizing fixed prior IFs, continuing IFs listed above, declined issue families reassessed, and new regressions>

## Design Escape Hatch

<None. | bullets naming scope, design-consensus, or implementation-shape concerns>

## Recommended Dispositions

- Likely accept: <IF IDs or None>
- Likely decline: <IF IDs plus brief rationale, or None>
- Needs user/design judgment: <IF IDs and decision needed, or None>

## Reviewer Crosswalk

- <reviewer-alias>: <reviewer finding IDs or clean sentinel>; lens <lens>; notable coverage <summary>.

## Residual Risks And Limitations

<missing metadata, weak baseline, unavailable subagents, skipped commands, confidence limits, or None.>

## Temporary Packet Artifact

<None. Complete packet returned in chat. | Complete packet written to `<temporary path>`; chat output summarizes issue families only.>
```

## Empty States

- `## Issue Families`: use `None.` when there are no open or newly found issue families.
- `## Verification Results`: use `Not applicable.` in fresh mode. In verification mode, list fixed prior families and continuing families; use `None.` only when there was no prior family context to verify.
- `## Design Escape Hatch`: use `None.` unless the packet should signal a pause for design consensus, scope reduction, or a different implementation shape.
- `## Recommended Dispositions`: keep all three bullets and use `None` for empty groups.
- `## Residual Risks And Limitations`: use `None.` only when there are no meaningful limitations to report.
- `## Temporary Packet Artifact`: always state whether the complete packet is in chat or in a temporary Markdown file.

## Clean Packet Example

```md
# Review Packet

## Packet Summary

Target: PR #123
Repository: owner/repo
Mode: fresh
Base: origin/main
Head: feature/review-template
Baseline intent: Issue #77 requires a canonical packet template and prompt delegation.
Model and effort metadata: requested effort not applicable; actual model/effort not reported; selection source not applicable.
Reviewer continuity: not applicable
Continuity handle availability: not applicable

## Panel

| Reviewer | Lens | Mode | Notes |
| --- | --- | --- | --- |
| P1-R1 | correctness | fresh | Full target review |
| P1-R2 | tests-regressions | fresh | Full target review |

## Coverage

Reviewed the full diff, issue #77, and existing review-pass prompt references. No validation commands were run by reviewers.

## Issue Families

None.

## Verification Results

Not applicable.

## Design Escape Hatch

None.

## Recommended Dispositions

- Likely accept: None
- Likely decline: None
- Needs user/design judgment: None

## Reviewer Crosswalk

- P1-R1: clean sentinel `No new findings.`; lens correctness; notable coverage full diff and issue criteria.
- P1-R2: clean sentinel `No new findings.`; lens tests-regressions; notable coverage prompt fixtures and validation plan.

## Residual Risks And Limitations

Reviewers used existing validation output only.

## Temporary Packet Artifact

None. Complete packet returned in chat.
```

## Findings Packet Example

```md
# Review Packet

## Packet Summary

Target: PR #123
Repository: owner/repo
Mode: verification
Base: origin/main
Head: feature/review-template@abc1234
Baseline intent: Issue #77 requires exact packet rendering, `DOMAIN.md` language, and prompt delegation.
Model and effort metadata: requested effort high for verification panel; actual model/effort not reported; selection source Calling Workflow override.
Reviewer continuity: packet/finding-source fallback
Continuity handle availability: unavailable

## Panel

| Reviewer | Lens | Mode | Notes |
| --- | --- | --- | --- |
| P2-R1 | correctness | verification | Verified IF1; full target reread |
| P2-R2 | structural-depth | verification | Checked template ownership and caller surfaces |

## Coverage

Reviewed the current diff against `origin/main`, the prior packet, issue #77, `DOMAIN.md`, `reviewer-prompts.md`, and `review-loop` caller references. No validation commands were run by reviewers.

## Issue Families

### IF1. Severity: P1 - **Template rules are not referenced from the recovery prompt**

**Recommended disposition:** likely accept
**Failure mode:** Recovery after compaction can reconstruct packet rendering from stale inline schema instead of reopening the canonical template.
**Suggested fix shape:** Update recovery guidance to reopen `review-packet-template.md` before returning a packet.
**Found by:** `P2-R1-F1`, `P2-R2-F1`
**Evidence:** `os/skills/review-pass/references/reviewer-prompts.md:194`
**Representative findings:** `P2-R1-F1` observed the recovery prompt only reopens `reviewer-prompts.md`; `P2-R2-F1` found the same missing template reference in the final recovery instruction.
**Related occurrences or sibling search:** Search for stale inline packet-schema ownership across `os/skills`.
**Validation signal:** A targeted search confirms packet-template ownership is explicit and stale inline packet-schema ownership references are gone.

## Verification Results

- `IF2`: fixed by the current head; the prompt checklist now points to the canonical packet template.
- `IF1`: still open and listed under `## Issue Families`.

## Design Escape Hatch

None.

## Recommended Dispositions

- Likely accept: `IF1`
- Likely decline: None
- Needs user/design judgment: None

## Reviewer Crosswalk

- P2-R1: `P2-R1-F1`; lens correctness; notable coverage prompt recovery and packet rendering ownership.
- P2-R2: `P2-R2-F1`; lens structural-depth; notable coverage caller/called skill propagation.

## Residual Risks And Limitations

Reviewers did not run `scripts/run-validator`; caller should run it after fixes.

## Temporary Packet Artifact

None. Complete packet returned in chat.
```
