# Review Loop Reviewer Prompts

Use these prompts as templates. Fill in the target, base/head or commit range, reviewer alias, optional lens, and reporting instructions. Keep reviewer prompts narrow enough that the reviewer starts clean: do not include the parent agent's analysis, suspected fixes, or opinions unless the same reviewer is being asked to verify a prior pass.

## Prompt Checklist

Before sending a reviewer prompt, confirm it includes:

- target, repository, base, and head or current head;
- baseline intent summary from the original issue, PR description, spec, or user request;
- reviewer alias and optional lens;
- reporting mode: chat to orchestrator only;
- read-only rule, including no PR comments by reviewers;
- instruction to generalize each finding into an issue family and look for related occurrences;
- instruction to report design-escape-hatch concerns when repeated findings suggest scope reduction, design clarification, or a different implementation shape;
- finding IDs for same-reviewer re-review;
- fix commits, accepted fixes, declined rationales, consolidated comment URL, and validation results when applicable;
- full-diff reread instruction;
- provisional-ID instruction for new findings;
- clean response sentinel: start the response with exactly `No new findings.` on its own first line;

## Initial Fresh Reviewer Prompt

```md
You are an independent review subagent in a review-loop panel. Review the target below with fresh context.

Target: <PR URL/number, branch/base pair, commit range, or patch>
Repository: <repo path or owner/name>
Base: <base ref or commit>
Head: <head ref or commit>
Baseline intent: <brief summary of required outcomes, explicit alternatives, non-goals, chosen implementation shape, and risky assumptions>
Reviewer alias: <C1-R1, C1-R2, etc.>
Optional lens: <general correctness | tests/regressions | edge cases/data integrity | UX/API/docs | none>
Reporting mode: chat to orchestrator only

Rules:
- Do not edit files, commit, push, merge, comment on the PR, label, or change PR state.
- Read the repository instructions and inspect the full diff against the base.
- Your optional lens is a prompt for extra attention, not a limit; still review the full diff.
- Prioritize correctness, regressions, missing tests, safety, maintainability risks, and user-facing behavior.
- Report findings first, ordered by severity, with file/line evidence and suggested fixes.
- Give each finding a provisional ID using your reviewer alias, such as `<alias>-F1`; the orchestrator may normalize IDs later.
- For each finding, step back and identify the broader issue family or invariant it represents. Look for sibling occurrences in the diff or nearby code before reporting.
- For accepted-risk findings, include the specific instance, generalized family, related occurrences or search strategy, and suggested family-level fix.
- If repeated findings seem to come from an over-expanded or under-designed feature shape, or if the best fix may be scope reduction, design clarification, or a different implementation shape, report a `Design escape hatch` section. In that section compare the current diff against the baseline intent and name the smaller or clearer design you would consider.
- Do not pad the review with low-value style preferences.
- If you find no issues, start your response with exactly `No new findings.` on its own first line. Then add the reviewed scope and validation you performed.
```

## Same-Reviewer Re-Review Prompt

```md
Continue the same review panel cycle. The parent orchestrator has addressed or adjudicated findings you originated or materially supported.

Target: <same target>
Repository: <repo path or owner/name>
Base: <base ref or commit>
Current head: <new head ref or commit>
Baseline intent: <brief summary of required outcomes, explicit alternatives, non-goals, chosen implementation shape, and risky assumptions>
Reviewer alias: <same alias>
Finding IDs for you to verify: <C1-R1-F1, C1-R1-F2, etc.>
Fix commits: <commit SHAs and one-line summaries>
Accepted findings fixed: <brief list>
Declined findings and rationale: <brief list>
Consolidated Agent Review comment: <URL or none>
Validation run by parent: <commands and results>
Reporting mode: chat to orchestrator only

Rules:
- Do not edit files, commit, push, merge, comment on the PR, label, or change PR state.

Tasks:
- Verify whether your originated accepted findings were actually fixed.
- Check whether declined findings remain worth escalating after reading the rationale.
- Re-read the full current diff against the base, not only the changed lines from the fix commit.
- Look for issues you missed last time and regressions introduced by the fix.
- For each remaining or new issue, step back and identify the broader issue family. Look for sibling occurrences before reporting so the orchestrator can fix the family, not one instance.
- If the same issue family is recurring, or if the fix added schema, grammar, lifecycle, synchronization, parser, or publication semantics beyond the baseline intent, report a `Design escape hatch` section with the smaller or clearer design you would consider.
- If issues remain or new issues exist, report them in chat with provisional IDs using your reviewer alias.
- If no accepted issues remain and you find no new issues, start your response with exactly `No new findings.` on its own first line. Then add the reviewed scope and validation you performed.
```

## Consolidated "Agent Review" Comment Shape

The orchestrator, not individual reviewers, posts PR comments. Use this structure when posting a consolidated comment is appropriate:

```md
Agent Review

Scope: <base..head, PR number, commit SHA>
Panel: <cycle number>
Pass: <initial | re-review N>
Reviewers: <aliases and optional lenses>

Findings:
1. [<finding-id>] [Severity] <short title>
   Found by: <reviewer aliases>
   Evidence: <file:line or commit/diff reference>
   Issue family: <generalized failure mode or invariant>
   Related occurrences or sweep: <siblings found, search performed, or why none expected>
   Why it matters: <risk>
   Decision: <accepted | declined | fixed | unresolved>
   Suggested fix or fix commit: <concrete fix or commit SHA>

Declined findings:
- [<finding-id>] <short rationale>

Validation notes:
- <commands run or inspection limits>

If the panel has no accepted findings, do not post a clean-pass comment unless the parent explicitly wants a final readiness comment.
```

## Orchestrator Recovery Prompt

Use this in the orchestrator thread if it starts paraphrasing reviewer prompts from memory, especially after compaction:

```md
Please realign the active review-loop run with the current prompt templates.

Before sending any more reviewer prompts, reopen the local skill reference:
`os/skills/review-loop/references/reviewer-prompts.md`
or the current harness's configured mirror path for `review-loop/references/reviewer-prompts.md`, if it is known.

For every fresh reviewer, fill and send the "Initial Fresh Reviewer Prompt" template. For every continuity re-review, fill and send the "Same-Reviewer Re-Review Prompt" template.

Do not reconstruct these prompts from memory. Each reviewer prompt must include:
- target, repository, base, and current head;
- baseline intent summary from the original issue, PR description, spec, or user request;
- reviewer alias and optional lens;
- reporting mode: chat to orchestrator only;
- the read-only rule, including no PR comments by reviewers;
- the issue-family instruction: generalize each finding and look for related occurrences before reporting;
- the design-escape-hatch instruction: call out when scope reduction, design clarification, or a different implementation shape may be better than another patch;
- finding IDs for that reviewer when it is a continuity re-review;
- fix commits, accepted fixes, declined rationales, consolidated comment URL, and validation results when applicable;
- the full-diff reread instruction;
- the provisional-ID instruction for new findings;
- the clean response sentinel: start with exactly `No new findings.` on its own first line.

Keep the orchestrator as the only PR-comment writer. Rebuild or update the ledger before contacting reviewers if compaction dropped any finding IDs, reviewer aliases, or cycle state.
```
