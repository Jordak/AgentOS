# Review Pass Reviewer Prompts

Use these prompts as templates for one read-only review panel pass. Fill the target, base/head or commit range, reviewer alias, optional lens, mode, prior findings when applicable, and reporting instructions. Keep prompts narrow enough that reviewers start clean: do not include the parent agent's analysis, suspected fixes, or opinions unless verification mode requires prior adjudication context.

## Prompt Checklist

Before sending a reviewer prompt, confirm it includes:

- target, repository, base, and head or current head;
- baseline intent summary from the issue, PR description, spec, design doc, ADR, commit range, patch, or user request;
- mode: `fresh` or `verification`;
- reviewer alias and optional lens;
- custom lens notes when provided;
- reviewer continuity preference plus source reviewer aliases and source finding IDs in verification mode when applicable; source reviewer handles stay in the orchestration request when needed for resumption;
- reviewer continuity handle availability in verification mode when applicable, without exposing opaque handle values;
- assigned lens guidance loaded from the matching `references/lenses/<lens>.md` file when a named lens is assigned;
- Contract Surface Matrix guidance loaded from `references/lenses/contract-surface-matrix.md` when the target changes reusable contract surfaces;
- source-workflow boundary and design-escape-hatch escalation guidance from the lens file when `deep-review` or `structural-depth` is assigned;
- reporting mode: chat to review-pass orchestrator only;
- instruction to read repository instructions before inspecting the target;
- read-only rule, including no PR comments by reviewers;
- dirty-validation rule: use existing validation output only, do not run validation commands that may dirty the target checkout, and recommend validation signals for the caller instead;
- instruction to generalize each finding into an issue family and look for related occurrences;
- instruction to apply the Contract Surface Matrix guidance for skill, workflow, or reusable contract changes when provided;
- instruction to report design-escape-hatch concerns when repeated findings suggest scope reduction, design clarification, or a different implementation shape;
- instruction to compare implementation shape against the durable design source on fresh review when one is provided;
- finding IDs, fix commits, accepted fixes, declined rationales, consolidated comment URL, and validation results in verification mode when applicable;
- full-diff reread instruction;
- provisional-ID instruction for new findings;
- clean response sentinel: start the response with exactly `No new findings.` on its own first line.

## Lens Guidance

Named lenses are weighted attention, not exclusive scopes. Every reviewer still reviews the full target.

The orchestrator chooses lenses from `SKILL.md`, then loads only the matching reference files below before sending prompts. Do not require every reviewer to read every lens file.

| Lens | Reference |
| --- | --- |
| `general` | `references/lenses/general.md` |
| `correctness` | `references/lenses/correctness.md` |
| `tests-regressions` | `references/lenses/tests-regressions.md` |
| `edge-cases-data-integrity` | `references/lenses/edge-cases-data-integrity.md` |
| `architecture-depth` | `references/lenses/architecture-depth.md` |
| `code-judo` | `references/lenses/code-judo.md` |
| `design-compliance` | `references/lenses/design-compliance.md` |
| `issue-compliance` | `references/lenses/issue-compliance.md` |
| `ux-api-docs` | `references/lenses/ux-api-docs.md` |
| `deep-review` | `references/lenses/deep-review.md` |
| `security-privacy` | `references/lenses/security-privacy.md` |
| `release-risk` | `references/lenses/release-risk.md` |
| `structural-depth` | `references/lenses/structural-depth.md` |

Conditional lens:

- `contract-surface-matrix`: load `references/lenses/contract-surface-matrix.md` when the target changes reusable contract surfaces.

## Fresh Reviewer Prompt

```md
You are an independent reviewer in a read-only review-pass panel. Review the target below with fresh context.

Target: <PR URL/number, branch/base pair, commit range, or patch>
Repository: <repo path or owner/name>
Base: <base ref or commit>
Head: <head ref or commit>
Baseline intent: <brief summary of required outcomes, explicit alternatives, non-goals, chosen implementation shape, and risky assumptions; say when weak or missing>
Mode: fresh
Reviewer alias: <P1-R1, P1-R2, etc.>
Optional lens: <general | correctness | tests-regressions | edge-cases-data-integrity | architecture-depth | code-judo | design-compliance | issue-compliance | ux-api-docs | deep-review | security-privacy | release-risk | structural-depth | none>
Custom lens notes: <target-specific concerns or none>
Assigned lens guidance: <paste the prompt snippet or equivalent instructions from references/lenses/<lens>.md, or none>
Contract Surface Matrix guidance: <paste the prompt snippet or equivalent instructions from references/lenses/contract-surface-matrix.md when applicable, or none>
Reporting mode: chat to review-pass orchestrator only

Rules:
- Do not edit files, commit, push, merge, comment on the PR, label, close issues, mark ready, or change external state.
- Use existing validation output only. Do not run validation commands that may dirty the target checkout; recommend validation signals for the caller instead.
- Read the repository instructions and inspect the full target against the base.
- Your optional lens is a prompt for extra attention, not a limit; still review the full target.
- Apply the assigned lens guidance exactly as provided. If it is `none`, continue with the baseline review priorities.
- Prioritize correctness, regressions, missing tests, safety, maintainability risks, user-facing behavior, and design drift.
- Report findings first, ordered by severity, with file/line evidence and suggested fixes.
- Give each finding a provisional ID using your reviewer alias, such as `<alias>-F1`; the review-pass orchestrator may normalize IDs later.
- For each finding, step back and identify the broader issue family or invariant it represents. Look for sibling occurrences in the diff or nearby code before reporting.
- For accepted-risk findings, include the specific instance, generalized family, related occurrences or search strategy, and suggested family-level fix.
- Apply the Contract Surface Matrix guidance when provided.
- Compare the implementation shape against the baseline intent and durable design source when provided. If the target added major architecture, parsing, synchronization, lifecycle, validation, or public-policy semantics that the design source did not agree to, report that as a design-readiness finding rather than treating only the symptoms as bugs.
- If repeated findings seem to come from an over-expanded or under-designed feature shape, or if the best fix may be scope reduction, design clarification, or a different implementation shape, report a `Design escape hatch` section. In that section compare the current target against the baseline intent and name the smaller or clearer design you would consider.
- Do not pad the review with low-value style preferences.
- If you find no issues, start your response with exactly `No new findings.` on its own first line. Then add the reviewed scope and validation you performed.
```

## Verification Reviewer Prompt

```md
You are an independent reviewer in a read-only review-pass verification panel. The caller has addressed or adjudicated prior findings. Verify the prior findings and reread the full current target.

Target: <same target>
Repository: <repo path or owner/name>
Base: <base ref or commit>
Current head: <new head ref or commit>
Baseline intent: <brief summary of required outcomes, explicit alternatives, non-goals, chosen implementation shape, and risky assumptions; say when weak or missing>
Mode: verification
Reviewer alias: <P2-R1, P2-R2, etc.>
Optional lens: <general | correctness | tests-regressions | edge-cases-data-integrity | architecture-depth | code-judo | design-compliance | issue-compliance | ux-api-docs | deep-review | security-privacy | release-risk | structural-depth | none>
Custom lens notes: <target-specific concerns or none>
Assigned lens guidance: <paste the prompt snippet or equivalent instructions from references/lenses/<lens>.md, or none>
Contract Surface Matrix guidance: <paste the prompt snippet or equivalent instructions from references/lenses/contract-surface-matrix.md when applicable, or none>
Reviewer continuity: <same-source reviewer resumed | packet/finding-source fallback | none; include source reviewer aliases and finding IDs when applicable>
Continuity handle availability: <private handoff available | unavailable | not applicable; never include opaque handle values>
Prior packet or findings for you to verify: <finding IDs and summaries relevant to this reviewer or lens>
Fix commits: <commit SHAs and one-line summaries>
Accepted findings fixed: <brief list>
Declined findings and rationale: <brief list>
Consolidated Agent Review comment: <URL or none>
Validation run by caller: <commands and results>
Reporting mode: chat to review-pass orchestrator only

Rules:
- Do not edit files, commit, push, merge, comment on the PR, label, close issues, mark ready, or change external state.
- Use existing validation output only. Do not run validation commands that may dirty the target checkout; recommend validation signals for the caller instead.
- Read the repository instructions and inspect the full current target against the base.
- Your optional lens is a prompt for extra attention, not a limit; still review the full target.
- Apply the assigned lens guidance exactly as provided. If it is `none`, continue with the baseline review priorities.

Tasks:
- If same-source reviewer continuity is active, verify your own prior findings while still rereading the full current target. If packet/finding-source fallback is active, use the source reviewer aliases and finding IDs as the continuity trail without assuming access to the original reviewer context.
- Verify whether the prior accepted findings were actually fixed.
- Check whether declined findings remain worth escalating after reading the rationale.
- Re-read the full current target against the base, not only the changed lines from the fix commit.
- Look for issues missed last time and regressions introduced by the fix.
- For each remaining or new issue, step back and identify the broader issue family. Look for sibling occurrences before reporting so the caller can fix the family, not one instance.
- Apply the Contract Surface Matrix guidance when provided.
- If the same issue family is recurring, or if the fix added schema, grammar, lifecycle, synchronization, parser, or publication semantics beyond the baseline intent, report a `Design escape hatch` section with the smaller or clearer design you would consider.
- If issues remain or new issues exist, report them in chat with provisional IDs using your reviewer alias.
- If no accepted issues remain and you find no new issues, start your response with exactly `No new findings.` on its own first line. Then add the reviewed scope and validation you performed.
```

## Review Packet Schema

Return review packets with this structure unless the caller requested a narrower format:

```md
Review Packet

Target: <target>
Repository: <repo path or owner/name>
Mode: <fresh | verification>
Base: <base ref or commit>
Head: <head or current head>
Baseline Intent: <summary and source, or limitation>
Panel: <reviewer aliases and count>
Lens Plan: <reviewer alias -> lens>
Coverage: <scope inspected, metadata read, limitations>
Reviewer Continuity: <same-source reviewers resumed | packet/finding-source fallback | none; include source aliases or limitation, never opaque reviewer handles>
Continuity Handle Availability: <private handoff available | unavailable | not applicable; never include opaque handle values>

Issue Families:
1. [<family-id>] [Severity] <family title>
   Recommended disposition: <likely accept | likely decline | needs user/design judgment>
   Found by: <reviewer aliases and provisional finding IDs>
   Evidence: <file:line, diff hunk, command output, or source link>
   Failure mode: <generalized invariant or risk>
   Representative findings: <short summaries>
   Related occurrences or sibling search: <siblings found, search performed, or recommended search>
   Suggested fix shape: <family-level fix, simplification, scope reduction, or none>
   Validation signal: <test, command, inspection, or proof that would close it>

Design Escape Hatch:
- <none, or specific concern comparing target shape against baseline intent>

Recommended Dispositions:
- Likely accept: <family IDs>
- Likely decline: <finding/family IDs and rationale>
- Needs user/design judgment: <family IDs and the decision needed>

Reviewer Crosswalk:
- <reviewer alias>: <raw finding IDs, clean sentinel, lens, notable coverage>

Residual Risks And Limitations:
- <missing metadata, weak baseline, unavailable subagents, skipped commands, or confidence limits>

Temporary Packet Artifact:
- <path or none>
```

## Caller Handoff Notes

The packet is advisory. The caller owns final accept/decline decisions and any mutation. For `review-loop`, the caller should record packet families in its ledger, post any consolidated PR comments itself, apply fixes itself, then invoke `review-pass` again in verification or fresh mode as appropriate.

## Recovery Prompt

Use this in the review-pass orchestrator thread if it starts paraphrasing reviewer prompts from memory, especially after compaction:

```md
Please realign the active review-pass run with the current prompt templates.

Before sending any more reviewer prompts, reopen:
`os/skills/review-pass/references/reviewer-prompts.md`
or the current harness's configured adapter path for `review-pass/references/reviewer-prompts.md`, if it is known.

For every assigned named lens, also reopen only the matching file under:
`os/skills/review-pass/references/lenses/`
or the current harness's configured adapter path for `review-pass/references/lenses/`, if it is known.

When the target changes reusable contract surfaces, also reopen:
`os/skills/review-pass/references/lenses/contract-surface-matrix.md`
or the current harness's configured adapter path for `review-pass/references/lenses/contract-surface-matrix.md`, if it is known.

For every fresh reviewer, fill and send the "Fresh Reviewer Prompt" template. For every verification reviewer, fill and send the "Verification Reviewer Prompt" template.

Do not reconstruct these prompts from memory. Each reviewer prompt must include:
- target, repository, base, and current head;
- baseline intent summary and source or limitation;
- mode, reviewer alias, optional lens, and custom lens notes;
- assigned lens guidance loaded from `references/lenses/<lens>.md` when a named lens is assigned;
- Contract Surface Matrix guidance loaded from `references/lenses/contract-surface-matrix.md` when the target changes reusable contract surfaces;
- source-workflow boundary and design-escape-hatch escalation guidance from the assigned lens file when `deep-review` or `structural-depth` is assigned;
- reporting mode: chat to review-pass orchestrator only;
- the repository-instruction rule;
- the read-only rule, including no PR comments by reviewers;
- the dirty-validation rule: use existing validation output only, do not run validation commands that may dirty the target checkout, and recommend validation signals for the caller instead;
- the issue-family instruction: generalize each finding and look for related occurrences before reporting;
- the Contract Surface Matrix guidance for skill, workflow, or reusable contract changes when applicable;
- the design-escape-hatch instruction: call out when scope reduction, design clarification, or a different implementation shape may be better than another patch;
- prior finding IDs, fixes, declined rationales, comments, and validation when it is a verification pass;
- reviewer continuity preference plus source reviewer aliases and source finding IDs when applicable; source reviewer handles stay in the orchestration request when needed for resumption;
- continuity handle availability when applicable, without exposing opaque handle values;
- the full-diff reread instruction;
- the provisional-ID instruction for new findings;
- the clean response sentinel: start with exactly `No new findings.` on its own first line.

Keep review-pass read-only. Close every spawned or resumed reviewer after collecting its report, then return a packet using the Review Packet Schema.
```
