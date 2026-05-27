---
name: review-loop
description: Orchestrate iterative code-review loops for a PR, branch, commit range, or patch by spawning fresh panels of review subagents, adjudicating findings, applying and pushing accepted fixes, requesting per-reviewer re-reviews, producing a temporary HTML report, and marking a PR ready for human review. Use when the user asks for an automated review loop, fresh-context PR review/fix panel, repeated agent review/fix cycle, reviewer subagent loop, "Agent Review" PR comments, or to review a PR or commit until clean.
---

# Review Loop

## Goal

Drive a code change through independent review-panel cycles until every reviewer in the active panel has no accepted findings and is closed, then a newly spawned fresh-context panel has no accepted findings on its initial pass. The parent agent owns the ledger, adjudication, fixes, commits, pushes, PR comments, ready marker, and final report. Review subagents inspect and report; they do not edit files or post PR comments unless the user explicitly changes the workflow.

Read `references/reviewer-prompts.md` immediately before spawning or reusing review subagents. Read `references/report-guidance.md` before creating the final HTML report.

## Contract

Inputs:

- A target PR URL or number, branch/base pair, commit range, patch, or local change set.
- A checkout for the target repository, or enough remote context for `gh` or the GitHub connector to inspect the PR.
- Explicit user authorization for a subagent review loop. If the user only says something like "review PR #X", first ask whether to run `review-loop` or do a normal review, and name the ordinary PR-scoped writes listed below.
- For a PR target, an explicit request to run `review-loop`, made through a current user request or adapter prompt that names the write scope, grants permission for ordinary PR-scoped loop writes: posting consolidated "Agent Review" comments, pushing fix commits to the PR branch, and applying the repository's established ready-for-human marker at the end.
- Ask before non-PR-target writes, pushes to branches outside the target PR, merges, issue closures, creating new labels, permission changes, deletion, posting outside the target PR, or other external actions beyond the loop.

Output artifact:

- A temporary static HTML report that follows `references/report-guidance.md`.
- Optional consolidated "Agent Review" PR comments from the orchestrator and optional PR ready-for-human marking for PR targets.

Mutability:

- Mixed. The loop reads code and PR metadata, may edit local project files to fix accepted findings, may create agent-labeled commits, may push to the target PR branch, may post consolidated "Agent Review" comments on the target PR, may apply the repository's established ready-for-human marker, and may write a temporary local HTML report.

Tools and connectors:

- Local `git`, project test commands, and repository-specific validation.
- GitHub connector or `gh` for PR metadata, consolidated comments, labels, draft state, and branch pushes.
- The active harness's clean-context reviewer/delegation capability for review panels.
- `os/skills/check-implementation-readiness/SKILL.md` and `os/playbook/IMPLEMENT_FEATURES.md` for PR design-source preflight.
- `make-temp-file` for temporary report paths when available.
- `os/playbook/ARTIFACTS.md` for substantial report format decisions.
- `os/playbook/GITHUB_WORKFLOW.md` for GitHub issue, PR, and ready-for-human safety rules.

Safety:

- Spawn review subagents only when the user explicitly asked for this skill, a review loop, fresh review subagents, or equivalent delegated review work.
- If the user only asked for a normal review, ask before upgrading to `review-loop`; the question must state that the loop may post consolidated "Agent Review" comments, push fix commits to the PR branch, and apply the established ready-for-human marker.
- Treat a request to run `review-loop` on a specific PR as permission for those listed PR-scoped writes when the current request or invocation surface made that write scope explicit. Do not ask before each ordinary loop write.
- Keep review subagents read-only by default. They report to the orchestrator; the orchestrator is the single PR-comment writer.
- Before spawning reviewers for feature-sized work, run or honor the implementation-readiness gate. If no durable design source exists, or if the source is not ready for the PR scope, pause before review unless the user explicitly chooses `Gate Skipped`.
- Do not merge the PR, close issues, create labels, delete branches, change permissions, push outside the target PR branch, or publish outside the PR review surface unless separately requested and approved.
- Do not copy private connector data, secrets, or unrelated repository context into reviewer prompts or final reports.
- Close every review subagent after its panel cycle is complete so stale reviewer contexts do not leak into later fresh panels.

## Context Recovery Invariant

At the start of every parent-agent turn while `review-loop` is active, and before every panel spawn, re-review request, final report, or ready-for-human action, reopen this `SKILL.md` and the relevant reference file. Do not rely on memory of the contract.

After any pause, interruption, resume, unusually long loop, or suspected compaction, assume context may be stale: rebuild the ledger from durable sources first, then reread this skill, then reread `references/reviewer-prompts.md` or `references/report-guidance.md` before continuing.

## Prompt Assembly Guard

- Reopen `references/reviewer-prompts.md` before every fresh reviewer spawn and every same-reviewer re-review. Do not reconstruct reviewer prompts from memory, especially after compaction, interruption, or a long loop.
- Fill the relevant template fields explicitly: target, repository, base, head or current head, reviewer alias, optional lens, finding IDs, fix commits, accepted fixes, declined rationales, consolidated comment URL, validation results, and reporting mode.
- Preserve the template rules about read-only review, no PR comments by reviewers, issue-family sweeps, full-diff rereads, provisional IDs, and the clean response sentinel.
- After compaction, rebuild the ledger first, then reload `references/reviewer-prompts.md`, then contact reviewers. If a live orchestrator has drifted from the templates, use the recovery prompt in `references/reviewer-prompts.md`.

## Efficiency Controls

- Use a moderate, balanced, or medium effort level for the orchestrator by default when the harness exposes reasoning-effort controls. Reserve high or extra-high effort for reviewer subagents, genuinely ambiguous adjudication, and hard design tradeoffs.
- Keep the orchestrator focused on ledger management, deduplication, implementation, validation, and reporting. Do not spend high reasoning effort on bookkeeping or HTML formatting unless the report itself is the user-facing deliverable being polished.
- Batch work by issue family. After accepting a finding, define the underlying class of issue, search or inspect for sibling occurrences, and fix the whole family before asking reviewers to re-review.
- Prefer one family-level fix commit over several single-occurrence commits when the related fixes are cohesive. Keep separate commits for unrelated families or risky changes that need isolated validation.
- Run cheap deterministic checks, `rg` searches, self-tests, or narrow scripts to sweep for sibling occurrences before spending another reviewer pass.
- Use soft budget checkpoints rather than hard loop stops. They are awareness checkpoints, not automatic aborts.
- Trigger a checkpoint after roughly 60-90 minutes, after two fresh panel cycles, after eight fix commits, when a fixed family is rediscovered, or when the loop appears to be finding diminishing returns.
- At a checkpoint, summarize elapsed time if known, panel cycles, fix commits, accepted and declined issue families, remaining risk, current confidence, cost/effort posture, and the next planned review step. Continue by default unless the user set a budget cap, the next step expands scope, the loop appears to be thrashing, or the checkpoint raises a design-escape-hatch concern.
- The parent agent may always pause and ask the user for judgment when user input would improve the outcome, even if the workflow would otherwise allow the loop to continue. Prefer reaching out early when a design choice, scope boundary, product behavior, or implementation shape seems uncertain.

## Design Escape Hatch

Use this when the loop starts finding symptoms of an under-designed or over-expanded feature rather than isolated defects.

Before the first reviewer panel, establish a baseline intent summary from the original issue, PR description, spec, or user request:

- required outcomes and acceptance criteria;
- explicit alternatives the brief allowed;
- non-goals or scope boundaries when stated;
- the implementation shape currently chosen by the PR;
- assumptions that would be expensive to harden if they are wrong.

Pause and ask the user whether to continue, narrow, split, or redesign when any of these are true:

- the same issue family appears in two fresh panels or is rediscovered after a fix;
- a freeform document, prose field, or human-facing artifact starts requiring parser-grade validation, schema semantics, lifecycle semantics, synchronization logic, or grammar rules not explicit in the brief;
- fixing review findings would materially expand the feature beyond the original acceptance criteria;
- the simpler alternative allowed by the brief would remove a whole issue family;
- fix commits in one family become larger or more complex than the original implementation;
- reviewers are repeatedly finding edge cases in a newly invented model rather than independent bugs;
- the parent agent thinks user judgment would be useful before spending more time.

At the escape hatch, do not silently keep patching. Report:

1. what the original brief required;
2. what the implementation added or assumed;
3. which findings are symptoms of that added design;
4. the smallest viable redesign or scope reduction;
5. the cost and safety tradeoff of continuing the loop versus changing direction.

Accepted findings can be resolved by simplifying, narrowing, splitting, or deleting the problematic design, not only by adding code. If the user chooses to continue the current design, record that decision in the ledger and continue with the normal fix/re-review workflow.

## Workflow Phases

1. Establish the target:
   - Identify the repository, PR or commit target, base branch, head branch, and current branch.
   - Read the repository's local instructions and review policy.
   - Fetch or inspect current PR metadata when network access and permissions allow.
   - For feature-sized targets, apply the implementation-readiness preflight from `os/playbook/IMPLEMENT_FEATURES.md`: locate the durable design source from the issue, PR body, ADR, or local design doc; confirm it is `Ready to Implement` for the PR scope or record an explicit `Gate Skipped` bypass before reviewers start.
   - If the target is not a PR, choose local reporting mode instead of PR comments.
   - Establish the baseline intent summary described in the Design Escape Hatch section. Keep it in the loop ledger so later findings can be compared against the original brief and allowed alternatives.

2. Choose the fresh panel size:
   - Use 2 reviewers for small, single-subsystem, low-risk, docs-only, test-only, or very small diffs.
   - Use 3 reviewers as the default for normal product or code PRs.
   - Use 4 reviewers for broad, cross-cutting, multi-subsystem, migration, public API, security, data-integrity, concurrency, or user-facing workflow changes.
   - Use 5 reviewers only for unusually large or high-risk PRs, or when the user asks for extra confidence.
   - Give every reviewer the full diff. Optionally assign lightweight lenses to improve diversity, but do not make any reviewer responsible only for a slice.

3. Set the loop ledger:
   - Track each panel cycle, reviewer alias, reviewer status, pass number, raw findings, normalized finding IDs, accepted/declined decisions, fix commits, validation results, consolidated comment URL or chat status, and closure status.
   - Normalize findings into stable IDs such as `C1-R2-F3`.
   - If compaction or interruption loses details, rebuild the ledger from consolidated "Agent Review" comments, commit history, local validation output, and active subagent summaries.
   - Prefer one consolidated "Agent Review" comment per panel pass for PR targets. For non-PR targets, keep reviewer output in chat and the final report.

4. Run a fresh reviewer panel:
   - Spawn the selected number of review subagents in parallel with clean contexts. Do not fork the parent context unless the target cannot otherwise be described.
   - Reopen `references/reviewer-prompts.md` and fill the initial fresh reviewer template for each reviewer.
   - Give each subagent only the target, base/head or commit range, reviewer alias, optional lens, the baseline intent summary, and the initial reviewer prompt from `references/reviewer-prompts.md`.
   - Require a full review of the current diff or PR, not a narrow check of suspected issues.
   - Ask the first fresh panel to compare the implementation shape against the durable design source and flag any first-commit design drift before the loop starts treating symptoms as isolated bugs.
   - Ask reviewers to call out design-escape-hatch concerns when the best fix may be scope reduction, design clarification, or a different implementation shape rather than another patch.
   - Wait for all reviewers in the panel to report before adjudicating the panel.

5. Adjudicate and consolidate findings:
   - Read each finding as a claim, not an instruction.
   - Deduplicate overlapping findings while preserving which reviewers found them.
   - Convert isolated findings into issue families when they share the same underlying failure mode, invariant, missing validation, API contract, privacy risk, or UX regression.
   - For every accepted family, record the generalized rule, representative examples, sibling-search strategy, expected fix shape, and validation signal that would prove the family is closed.
   - Compare accepted issue families against the baseline intent summary. If a family mostly exists because the implementation chose a heavier design than the brief required, trigger the Design Escape Hatch before implementing another fix.
   - Accept findings that identify real correctness, safety, regression, maintainability, test, or UX risks.
   - Decline findings that are incorrect, out of scope, stylistic without project support, duplicates, or lower-value than the churn they would create. Record a short rationale.
   - Ask the user when the decision changes product behavior, expands scope, cannot be resolved from repository context, or when user judgment would be useful for a design-escape-hatch call.
   - For PR targets, post one consolidated "Agent Review" comment for the panel pass when there are accepted findings or useful declined-finding rationale. Do not have reviewers post separate PR comments.

6. Fix accepted findings:
   - Implement fixes in the parent workspace, preserving unrelated user changes.
   - Sweep for sibling occurrences in the same issue family before committing, using repository search, tests, fixtures, or small scripts when useful.
   - Before adding new schema, grammar, parser, lifecycle, synchronization, or publication semantics to satisfy a finding, check whether the Design Escape Hatch should fire.
   - Run the smallest trustworthy validation for the touched surface, broadening when shared behavior or user-facing workflows are affected.
   - Commit accepted fixes with an agent-prefixed subject, such as `#<agent-name> fix review finding about retries`. Use the active agent or harness name, for example `codex`, `claude`, or `gemini`; do not hard-code one agent name into the skill.
   - Push fixes to the target PR branch for PR targets. Otherwise leave local changes and report the needed external action.

7. Re-review with reviewer continuity:
   - Reopen `references/reviewer-prompts.md` and fill the same-reviewer re-review template for each reviewer.
   - Return to each reviewer in the active panel with only the finding IDs it originated or materially supported, plus fix commit SHAs, declined-finding rationales, validation results, and the consolidated comment URL if any.
   - Ask every reviewer to verify its originated findings and perform a full reread for missed or newly introduced issues.
   - If a reviewer reports new findings, adjudicate them, fix accepted findings, and re-review with that same reviewer.
   - If a reviewer challenges a declined rationale, reassess once from repository evidence; ask the user if the dispute changes product behavior, scope, or remains genuinely ambiguous.
   - Continue the inner loop until all reviewers in the active panel report no accepted findings and have been closed.
   - Pause for the user if the loop stops making progress, the same disputed finding repeats after a clear rationale, or more than five fix/re-review rounds occur in one panel cycle without convergence.

8. Confirm with a new fresh panel:
   - After all reviewers in the active panel are clean and closed, start a new outer panel cycle with fresh subagents sized to the current PR scope.
   - If the new fresh panel has no accepted findings on its initial pass, the loop is complete.
   - If the new fresh panel has accepted findings, run the inner panel loop again, close every reviewer when clean, and then spawn another fresh panel.
   - Run a soft budget checkpoint before another fresh panel when a checkpoint trigger is met.
   - Pause for the user if more than five fresh panel cycles find accepted issues, because the PR likely needs a larger design pass or narrower scope. Also pause earlier when the Design Escape Hatch triggers.

9. Produce the final report and ready marker:
   - Read `references/report-guidance.md` and follow its required report structure.
   - Create a temporary static HTML report. Make the first viewport show the target, final status, panel count, reviewer count, remaining risks, and readiness recommendation.
   - Link every commit hash, short or long, to its GitHub commit URL when a GitHub repository URL is available.
   - Link the report in the orchestrator's chat with a clickable Markdown link to the absolute `.html` path, such as `[Review Loop Report](/absolute/path/review-loop-report.html)`. Do not wrap the link in backticks or a code fence, so the app can open it in an HTML renderer or browser.
   - For PR targets, use the repository convention for ready-for-human marking: draft PR ready state, an existing `ready-for-human` label, or a final PR comment. Do not invent labels without checking that they exist or are accepted by the repository.

## Composition Guidance

Keep this as one orchestration skill by default. Call narrower skills or playbooks for their owned surfaces: GitHub workflow policy for PR state, `make-temp-file` for temporary paths, and repository-specific test or release skills when present.

Split into additional skills only after a subworkflow is reused independently. Good split candidates are a generic reviewer-agent prompt skill, a PR review report generator, or a GitHub ready-for-human transition skill. Until then, references are lighter than nested skills.

## Quality Bar

- Fresh panel size matches PR size and risk.
- Orchestrator and reviewer effort levels are assigned intentionally, with highest effort reserved for review quality rather than bookkeeping.
- The loop preserves and uses a baseline intent summary from the original brief, including explicit alternatives and non-goals when available.
- Feature-sized review targets have a `Ready to Implement` design source or an explicit `Gate Skipped` bypass recorded before reviewers are spawned.
- Reviewers are context-independent at the start of each fresh panel cycle.
- Reviewer prompts are assembled from the current templates, not memory.
- The orchestrator owns one ledger and posts at most one consolidated "Agent Review" comment per panel pass.
- Findings are generalized into issue families where possible, and accepted families are swept before re-review.
- Repeated findings in the same issue family trigger a design-escape-hatch check rather than automatic patch accumulation.
- The parent agent reaches out to the user whenever user judgment would help decide scope, design direction, or whether to keep investing in the loop.
- Each reviewer verifies its own originated findings after fixes while still performing a full reread.
- Accepted findings have concrete fix commits or local changes, plus validation evidence.
- Declined findings have short rationales and are not silently dropped.
- The inner loop ends only after all active-panel reviewers report no accepted findings and are closed.
- The final state is supported by a fresh panel with no accepted findings on its initial pass.
- The final HTML report follows `references/report-guidance.md` and can be reconstructed from consolidated PR comments and commits.
- PR-scoped comments and commits are factual and clearly labeled as agent-generated review work.

## Filing Rules

- Do not create durable AgentOS state by default.
- Temporary reports live under the system temporary directory unless the user asks for a project-local artifact.
- Project-specific code fixes, commits, branches, and reports live in the target project, not AgentOS.
- PR comments and ready markers stay in GitHub.
- If the loop discovers a durable AgentOS improvement, file it through the propagation review queue unless the user explicitly asks for the exact canonical edit.

## Verification

Before finishing:

1. Confirm the target, base, head, final reviewed commit SHA or local diff state, and panel-size rationale.
2. Confirm the baseline intent summary was captured from the original brief, including allowed alternatives and non-goals when available.
3. Confirm feature-sized review targets had a durable `Ready to Implement` design source or an explicit `Gate Skipped` bypass before reviewers were spawned.
4. Confirm every design-escape-hatch trigger was either surfaced to the user, explicitly declined with rationale, or found not applicable.
5. Confirm every reviewer in each active panel had a clean final report and was closed.
6. Confirm the final fresh panel had no accepted findings on its initial pass.
7. Confirm every accepted finding or issue family has a fix, a scope/design change, or an explicit unresolved-risk note.
8. Confirm every declined finding has a rationale.
9. Confirm accepted issue families were swept for sibling occurrences before re-review.
10. Confirm reviewer prompts used the current initial or same-reviewer templates, including reporting mode, read-only rule, no-reviewer-PR-comment rule, issue-family sweep instruction, design-escape-hatch instruction, full-reread instruction, provisional-ID rule, and clean response sentinel.
11. Confirm soft budget checkpoints were surfaced when checkpoint triggers occurred.
12. Confirm validation commands and results are captured.
13. Confirm fix commits use the active agent-name prefix.
14. Confirm the temporary HTML report exists, follows `references/report-guidance.md`, hyperlinks commit hashes to GitHub commits when possible, and is linked in the orchestrator's chat as a clickable absolute-path `.html` Markdown link.
15. Confirm no merges, issue closures, label creation, permission changes, non-target-branch pushes, or other out-of-loop external writes happened without current user authorization.
