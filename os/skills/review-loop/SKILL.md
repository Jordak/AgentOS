---
name: review-loop
description: Orchestrate iterative code-review loops for a PR, branch, commit range, or patch by delegating fresh and verification panel passes to review-pass, adjudicating findings, applying and pushing accepted fixes, posting consolidated Agent Review comments, producing a temporary HTML report, and marking a PR ready for human review. Use when the user asks for an automated review loop, fresh-context PR review/fix panel, repeated agent review/fix cycle, reviewer subagent loop, "Agent Review" PR comments, or to review a PR or commit until clean.
---

# Review Loop

## Goal

Drive a code change through independent review-panel cycles until accepted issue families are fixed or explicitly resolved, then a newly requested fresh `review-pass` panel has no likely accepted findings on its initial pass. The parent agent owns the ledger, adjudication, fixes, commits, pushes, PR comments, ready marker, and final report. `review-pass` owns the read-only reviewer-panel mechanics for each fresh or verification pass.

Read `os/skills/review-pass/SKILL.md` and `os/skills/review-pass/references/reviewer-prompts.md` immediately before every fresh or verification panel pass. Read `references/agent-review-comment.md` before posting consolidated "Agent Review" PR comments. Read `references/report-guidance.md` before creating the final HTML report.

## Contract

Inputs:

- A target PR URL or number, branch/base pair, commit range, patch, or local change set.
- A checkout for the target repository, or enough remote context for `gh` or the GitHub connector to inspect the PR.
- Explicit user authorization for a subagent review loop. If the user only says something like "review PR #X", first ask whether to run `review-loop` or do a normal review, and name the ordinary PR-scoped writes listed below.
- For a PR target, an explicit request to run `review-loop`, made through a current user request or adapter prompt that names the write scope, grants permission for ordinary PR-scoped loop writes: posting consolidated "Agent Review" comments, pushing fix commits to the PR branch, and applying the repository's established ready-for-human marker at the end.
- Ask before non-PR-target writes, pushes to branches outside the target PR, merges, issue closures, creating new labels, permission changes, deletion, posting outside the target PR, or other external actions beyond the loop.

Output artifact:

- A temporary static HTML report that follows `references/report-guidance.md`.
- Optional consolidated "Agent Review" PR comments from the orchestrator that follow `references/agent-review-comment.md`, plus optional PR ready-for-human marking for PR targets.

Mutability:

- Mixed. The loop reads code and PR metadata, may edit local project files to fix accepted findings, may create agent-labeled commits, may push to the target PR branch, may post consolidated "Agent Review" comments on the target PR, may apply the repository's established ready-for-human marker, and may write a temporary local HTML report.
- Reviewer-panel passes delegated to `review-pass` remain read-only.

Tools and connectors:

- `os/skills/review-pass/SKILL.md` for fresh and verification reviewer-panel passes.
- Local `git`, project test commands, and repository-specific validation.
- GitHub connector or `gh` for PR metadata, consolidated comments, labels, draft state, and branch pushes.
- `os/skills/check-implementation-readiness/SKILL.md` and `os/playbook/IMPLEMENT_FEATURES.md` for PR design-source preflight.
- `make-temp-file` for temporary report paths when available.
- `os/playbook/ARTIFACTS.md` for substantial report format decisions.
- `os/playbook/GITHUB_WORKFLOW.md` for GitHub issue, PR, and ready-for-human safety rules.

Safety:

- Use this mutating loop only when the user explicitly asked for this skill, a review loop, fresh review subagents plus fixes, or equivalent delegated review/fix work.
- If the user only asked for a normal review, ask before upgrading to `review-loop`; the question must state that the loop may post consolidated "Agent Review" comments, push fix commits to the PR branch, and apply the established ready-for-human marker.
- Treat a request to run `review-loop` on a specific PR as permission for those listed PR-scoped writes when the current request or invocation surface made that write scope explicit. Do not ask before each ordinary loop write.
- Keep `review-pass` reviewers read-only. They report to the parent through `review-pass`; the parent is the single PR-comment writer.
- Before spawning reviewers for feature-sized work, run or honor the implementation-readiness gate. If no durable design source exists, or if the source is not ready for the PR scope, pause before review unless the user explicitly chooses `Gate Skipped`.
- Do not merge the PR, close issues, create labels, delete branches, change permissions, push outside the target PR branch, or publish outside the PR review surface unless separately requested and approved.
- Do not copy private connector data, secrets, or unrelated repository context into reviewer prompts, review packets, PR comments, or final reports.

## Context Recovery Invariant

At the start of every parent-agent turn while `review-loop` is active, and before every `review-pass` invocation, final report, or ready-for-human action, reopen this `SKILL.md` and the relevant reference file. Do not rely on memory of the contract.

After any pause, interruption, resume, unusually long loop, or suspected compaction, assume context may be stale: rebuild the ledger from durable sources first, then reread this skill, then reread `os/skills/review-pass/SKILL.md` and the relevant reference file before continuing.

## Review-Pass Invocation Guard

- Reopen `os/skills/review-pass/SKILL.md` and `os/skills/review-pass/references/reviewer-prompts.md` before every fresh and verification pass. If the harness cannot discover `review-pass` by name, read those canonical files directly and follow them as the fallback.
- Fill the pass request explicitly: target, repository, base, head or current head, mode, baseline intent, reviewer count or risk posture, optional lens overrides, custom lens notes, prior packet, finding IDs, fix commits, accepted fixes, declined rationales, consolidated comment URL, validation results, and reporting mode.
- Preserve `review-pass` template rules about read-only review, no reviewer PR comments, issue-family sweeps, design-escape-hatch concerns, full-diff rereads, provisional IDs, and the clean response sentinel.
- Treat the review packet as advisory. The parent owns final accept/decline decisions and records the durable ledger.
- Do not ask the user to manage reviewer opening, reviewer closure, or pass-level prompt assembly; that is `review-pass` responsibility.
- After compaction, rebuild the ledger first, then reload `review-pass`, then request the next pass.

## Reviewer Continuity

Verification should preserve source-reviewer continuity without making the user manage live reviewer state.

- When the harness can safely resume the same source reviewers, request that `review-pass` use same-source reviewer continuity and provide the source reviewer aliases, source reviewer handles, and relevant finding IDs.
- When same-source resumption is unavailable, unsafe, or lost after compaction, request packet/finding-source fallback: provide the prior packet, source reviewer aliases, source finding IDs, fix commits, declined rationales, and validation results to fresh verification reviewers.
- Get opaque source reviewer handles from the caller-private continuity handoff returned by `review-pass` when the harness provides one. If the handoff is unavailable, record that limitation and use packet/finding-source fallback.
- Keep opaque source reviewer handles in the loop ledger or orchestration request only; do not put them in reviewer prompts, PR comments, public reports, or human-facing packets. If debugging requires handle-level detail, keep that detail in private orchestration diagnostics outside review packets, reviewer prompts, PR comments, public reports, and other human-facing artifacts.
- Record the continuity mode and source aliases in the ledger and final report so later agents can distinguish same-reviewer verification from packet/finding-source fallback without exposing handles.
- Treat continuity as a verification-quality preference, not as permission for reviewers to keep state open, mutate files, or post PR comments. `review-pass` still owns prompt assembly, reviewer lifecycle, collection, closure, and packet normalization for the current pass.

## Efficiency Controls

- Use a moderate, balanced, or medium effort level for the orchestrator by default when the harness exposes reasoning-effort controls. Reserve high or extra-high effort for `review-pass` reviewer quality, genuinely ambiguous adjudication, and hard design tradeoffs.
- Keep the orchestrator focused on ledger management, deduplication, implementation, validation, PR-surface writes, and reporting.
- Batch work by issue family. After accepting a finding, define the underlying class of issue, search or inspect for sibling occurrences, and fix the whole family before requesting verification.
- Prefer one family-level fix commit over several single-occurrence commits when the related fixes are cohesive. Keep separate commits for unrelated families or risky changes that need isolated validation.
- Run cheap deterministic checks, `rg` searches, self-tests, or narrow scripts to sweep for sibling occurrences before spending another reviewer pass.
- Use soft budget checkpoints rather than hard loop stops. They are awareness checkpoints, not automatic aborts.
- Trigger a checkpoint after roughly 60-90 minutes, after two fresh panel cycles, after eight fix commits, when a fixed family is rediscovered, or when the loop appears to be finding diminishing returns.
- At a checkpoint, summarize elapsed time if known, panel cycles, fix commits, accepted and declined issue families, remaining risk, current confidence, cost/effort posture, and the next planned review step. Continue by default unless the user set a budget cap, the next step expands scope, the loop appears to be thrashing, or the checkpoint raises a design-escape-hatch concern.
- The parent agent may always pause and ask the user for judgment when user input would improve the outcome, even if the workflow would otherwise allow the loop to continue. Prefer reaching out early when a design choice, scope boundary, product behavior, or implementation shape seems uncertain.

## Design Escape Hatch

Use this when the loop starts finding symptoms of an under-designed or over-expanded feature rather than isolated defects.

Before the first `review-pass` panel, establish a baseline intent summary from the original issue, PR description, spec, or user request:

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

Accepted findings can be resolved by simplifying, narrowing, splitting, or deleting the problematic design, not only by adding code. If the user chooses to continue the current design, record that decision in the ledger and continue with the normal fix and verification workflow.

## Contract Surface Matrix

Use this when an accepted finding changes workflow semantics, cross-skill ownership, safety rules, state or lifecycle behavior, prompt behavior, artifact schemas, validation policy, privacy boundaries, or filing rules. Skip it for typo fixes, local prose cleanup, narrow examples, and implementation details that do not change a reusable contract.

Before editing, make a tiny matrix in the loop ledger or working notes:

`Semantic | Owner | Inputs | Outputs | Prompt/Recovery | Ledger/Report | Privacy/Filing | Validation`

Use the matrix to update affected contract surfaces in one pass. Check the owning skill, caller or called skills, prompt templates, recovery prompts, packet or report schemas, manifest entry, retrieval or validator coverage when relevant, privacy/filing rules, mirrors, and any final report guidance. Keep the matrix lightweight; it is a propagation guard, not a design doc.

## Workflow Phases

1. Establish the target:
   - Identify the repository, PR or commit target, base branch, head branch, and current branch.
   - Read the repository's local instructions and review policy.
   - Fetch or inspect current PR metadata when network access and permissions allow.
   - For feature-sized targets, apply the implementation-readiness preflight from `os/playbook/IMPLEMENT_FEATURES.md`: locate the durable design source from the issue, PR body, ADR, or local design doc; confirm it is `Ready to Implement` for the PR scope or record an explicit `Gate Skipped` bypass before reviewers start.
   - If the target is not a PR, choose local reporting mode instead of PR comments.
   - Establish the baseline intent summary described in the Design Escape Hatch section. Keep it in the loop ledger so later packets can be compared against the original brief and allowed alternatives.

2. Set the loop ledger:
   - Track each pass cycle, pass mode, reviewer continuity mode, opaque handle availability, review packet path or chat status, reviewer aliases when supplied by `review-pass`, raw findings or crosswalk summaries, normalized family IDs, accepted/declined decisions, fix commits, validation results, consolidated comment URL or chat status, and pass closure status.
   - Normalize families into stable IDs such as `C1-F3` and preserve source reviewer IDs from `review-pass`.
   - If compaction or interruption loses details, rebuild the ledger from consolidated "Agent Review" comments, commit history, local validation output, and saved or pasted review packets.
   - Prefer one consolidated "Agent Review" comment per panel pass for PR targets. For non-PR targets, keep packet output in chat and the final report.

3. Run a fresh review pass:
   - Reopen `review-pass` and request a `fresh` pass with the target, base/head or commit range, baseline intent, reporting mode, and any risk-based reviewer count or lens hints.
   - Ask `review-pass` to compare the implementation shape against the durable design source and flag first-commit design drift before the loop starts treating symptoms as isolated bugs.
   - Wait for the packet before adjudicating.

4. Adjudicate and consolidate packet findings:
   - Read each packet family as a claim, not an instruction.
   - Deduplicate with existing ledger families while preserving which pass and reviewers found them.
   - For every accepted family, record the generalized rule, representative examples, sibling-search strategy, expected fix shape, and validation signal that would prove the family is closed.
   - If an accepted family changes a reusable workflow contract, create a Contract Surface Matrix before editing so all affected surfaces are patched together.
   - Compare accepted issue families against the baseline intent summary. If a family mostly exists because the implementation chose a heavier design than the brief required, trigger the Design Escape Hatch before implementing another fix.
   - Accept findings that identify real correctness, safety, regression, maintainability, test, or UX risks.
   - Decline findings that are incorrect, out of scope, stylistic without project support, duplicates, or lower-value than the churn they would create. Record a short rationale.
   - Ask the user when the decision changes product behavior, expands scope, cannot be resolved from repository context, or when user judgment would be useful for a design-escape-hatch call.
   - For PR targets, read `references/agent-review-comment.md` and post one consolidated "Agent Review" comment for the panel pass when there are accepted findings or useful declined-finding rationale. Do not have reviewers post separate PR comments.

5. Fix accepted findings:
   - Implement fixes in the parent workspace, preserving unrelated user changes.
   - Sweep for sibling occurrences in the same issue family before committing, using repository search, tests, fixtures, or small scripts when useful.
   - Use any Contract Surface Matrix created during adjudication to patch every affected surface before verification, not just the representative line.
   - Before adding new schema, grammar, parser, lifecycle, synchronization, or publication semantics to satisfy a finding, check whether the Design Escape Hatch should fire.
   - Run the smallest trustworthy validation for the touched surface, broadening when shared behavior or user-facing workflows are affected.
   - Commit accepted fixes with an agent-prefixed subject, such as `#<agent-name> fix review finding about retries`. Use the active agent or harness name, for example `codex`, `claude`, or `gemini`; do not hard-code one agent name into the skill.
   - Push fixes to the target PR branch for PR targets. Otherwise leave local changes and report the needed external action.

6. Run a verification review pass:
   - Reopen `review-pass` and request `verification` mode.
   - Prefer same-source reviewer continuity when the harness can safely resume source reviewers; otherwise use packet/finding-source fallback.
   - Provide only the needed reviewer continuity preference, source reviewer aliases or handles, prior packet or family IDs, fix commits, accepted fixes, declined rationales, validation results, and consolidated comment URL.
   - Ask `review-pass` to verify prior findings, reassess declined findings against the rationale, and reread the full current diff for missed or newly introduced issues.
   - Record whether the verification pass used same-source reviewer continuity or packet/finding-source fallback, and whether opaque handles were available through the private handoff.
   - If the verification packet contains likely accepted or unresolved findings, adjudicate them, fix accepted families, and request another verification pass.
   - If a verification packet challenges a declined rationale, reassess once from repository evidence; ask the user if the dispute changes product behavior, scope, or remains genuinely ambiguous.
   - Continue until verification packets report no likely accepted findings and no unresolved design-judgment blockers for the active family set.
   - Pause for the user if the loop stops making progress, the same disputed finding repeats after a clear rationale, or more than five fix/verification rounds occur in one panel cycle without convergence.

7. Confirm with a new fresh pass:
   - After the active family set is clean, request a new `fresh` pass from `review-pass` with clean context sized to the current PR scope.
   - If the new fresh packet has no likely accepted findings and no design-judgment blockers on its initial pass, the loop is complete.
   - If the new fresh packet has accepted findings, run the fix and verification workflow again, then spawn another fresh pass.
   - Run a soft budget checkpoint before another fresh pass when a checkpoint trigger is met.
   - Pause for the user if more than five fresh pass cycles find accepted issues, because the PR likely needs a larger design pass or narrower scope. Also pause earlier when the Design Escape Hatch triggers.

8. Produce the final report and ready marker:
   - Read `references/report-guidance.md` and follow its required report structure.
   - Create a temporary static HTML report. Make the first viewport show the target, final status, pass count, reviewer count, remaining risks, and readiness recommendation.
   - Link every commit hash, short or long, to its GitHub commit URL when a GitHub repository URL is available.
   - Link the report in the orchestrator's chat with a clickable Markdown link to the absolute `.html` path, such as `[Review Loop Report](/absolute/path/review-loop-report.html)`. Do not wrap the link in backticks or a code fence, so the app can open it in an HTML renderer or browser.
   - For PR targets, use the repository convention for ready-for-human marking: draft PR ready state, an existing `ready-for-human` label, or a final PR comment. Do not invent labels without checking that they exist or are accepted by the repository.

## Composition Guidance

Keep this skill focused on orchestration, mutation, convergence, PR-surface writes, and final reporting. Delegate reviewer-panel mechanics to `review-pass`.

Use `review-pass` as a hard dependency once it is canonical and mirrored. If a harness cannot invoke the skill by name, read `os/skills/review-pass/SKILL.md` and `os/skills/review-pass/references/reviewer-prompts.md` directly as the fallback rather than rebuilding the templates here.

Call narrower playbooks for their owned surfaces: GitHub workflow policy for PR state, `make-temp-file` for temporary paths, and repository-specific test or release skills when present. Use the vendored `thermo-nuclear-code-quality-review` and `improve-codebase-architecture` skills through `review-pass` lenses, not as nested workflows inside `review-loop`.

## Quality Bar

- The loop captures target, base, head, baseline intent, final reviewed commit SHA or local diff state, and review-pass sizing rationale.
- Feature-sized review targets have a `Ready to Implement` design source or an explicit `Gate Skipped` bypass recorded before reviewers are spawned.
- Every fresh or verification panel pass is delegated to `review-pass` or its canonical fallback files.
- The orchestrator owns one durable ledger and posts at most one consolidated "Agent Review" comment per panel pass.
- Findings are generalized into issue families where possible, and accepted families are swept before verification.
- Repeated findings in the same issue family trigger a design-escape-hatch check rather than automatic patch accumulation.
- Accepted semantic contract changes use a Contract Surface Matrix, or explicitly skip it because the fix is local and non-contractual.
- The parent agent reaches out to the user whenever user judgment would help decide scope, design direction, or whether to keep investing in the loop.
- Accepted findings have concrete fix commits or local changes, plus validation evidence.
- Declined findings have short rationales and are not silently dropped.
- Verification passes prefer same-source reviewer continuity when safely available, record opaque handle availability and any packet/finding-source fallback, check prior fixes, and reread the full current diff.
- The final state is supported by a fresh `review-pass` packet with no likely accepted findings on its initial pass.
- The final HTML report follows `references/report-guidance.md` and can be reconstructed from consolidated PR comments, review packets, and commits.
- PR-scoped comments and commits are factual and clearly labeled as agent-generated review work.

## Filing Rules

- Do not create durable AgentOS state by default.
- Temporary reports live under the system temporary directory unless the user asks for a project-local artifact.
- Project-specific code fixes, commits, branches, and reports live in the target project, not AgentOS.
- PR comments and ready markers stay in GitHub.
- If the loop discovers a durable AgentOS improvement, file it through the propagation review queue unless the user explicitly asks for the exact canonical edit.

## Verification

Before finishing:

1. Confirm the target, base, head, final reviewed commit SHA or local diff state, and review-pass sizing rationale.
2. Confirm the baseline intent summary was captured from the original brief, including allowed alternatives and non-goals when available.
3. Confirm feature-sized review targets had a durable `Ready to Implement` design source or an explicit `Gate Skipped` bypass before reviewers were spawned.
4. Confirm every design-escape-hatch trigger was either surfaced to the user, explicitly declined with rationale, or found not applicable.
5. Confirm every fresh and verification pass used `review-pass` or its canonical fallback files.
6. Confirm the final fresh `review-pass` packet had no likely accepted findings on its initial pass.
7. Confirm every accepted finding or issue family has a fix, a scope/design change, or an explicit unresolved-risk note.
8. Confirm every declined finding has a rationale.
9. Confirm accepted issue families were swept for sibling occurrences before verification.
10. Confirm accepted semantic contract changes used a Contract Surface Matrix, or record why the matrix was skipped.
11. Confirm review-pass requests used the current fresh or verification templates, including reporting mode, read-only rule, no-reviewer-PR-comment rule, dirty-validation rule, issue-family sweep instruction, design-escape-hatch instruction, full-reread instruction, provisional-ID rule, and clean response sentinel.
12. If a structural-depth lens was assigned, confirm `review-pass` supplied the structural-depth lens instructions and no full architecture-report workflow was run inside `review-loop`.
13. Confirm verification continuity mode and opaque handle availability were recorded for verification passes without exposing handle values.
14. Confirm soft budget checkpoints were surfaced when checkpoint triggers occurred.
15. Confirm validation commands and results are captured.
16. Confirm fix commits use the active agent-name prefix.
17. Confirm the temporary HTML report exists, follows `references/report-guidance.md`, hyperlinks commit hashes to GitHub commits when possible, and is linked in the orchestrator's chat as a clickable absolute-path `.html` Markdown link.
18. Confirm consolidated "Agent Review" comments followed `references/agent-review-comment.md` when posted.
19. Confirm no merges, issue closures, label creation, permission changes, non-target-branch pushes, or other out-of-loop external writes happened without current user authorization.
