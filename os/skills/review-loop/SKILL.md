---
name: review-loop
description: Orchestrate iterative code-review loops for a PR, branch, commit range, or patch by delegating fresh and verification panel passes to review-pass, conservatively adjudicating issue families, applying and pushing `auto-fix` and `user-approved-fix` fixes, posting consolidated Agent Review comments, producing a temporary HTML report, and marking a PR ready for human review. Use when the user asks for an automated review loop, fresh-context PR review/fix panel, repeated agent review/fix cycle, reviewer subagent loop, "Agent Review" PR comments, or to review a PR or commit until clean.
---

# Review Loop

## Goal

Drive a code change through independent review-panel cycles until every `auto-fix` issue family is fixed or explicitly resolved, every `ask-user` blocker has an explicit user decision, and a newly requested fresh `review-pass` panel has no unresolved `auto-fix` or `ask-user` blockers after parent adjudication. The parent agent owns the ledger, adjudication, fixes, commits, pushes, PR comments, ready marker, and final report. `review-pass` owns the read-only reviewer-panel mechanics for each fresh or verification pass.

Read `os/skills/review-pass/SKILL.md`, `os/skills/review-pass/references/reviewer-prompts.md`, and `os/skills/review-pass/references/review-packet-template.md` immediately before every fresh or verification panel pass. Read `references/agent-review-comment.md` before posting consolidated "Agent Review" PR comments. Read `references/report-guidance.md` before creating the final HTML report.

## Contract

Inputs:

- A target PR URL or number, branch/base pair, commit range, patch, or local change set.
- A checkout for the target repository, or enough remote context for `gh` or the GitHub connector to inspect the PR.
- Explicit user authorization for a review loop. A request to run `review-loop`, "run a review loop", or equivalent delegated review/fix loop includes explicit authorization to request `review-pass` panel cycles, including clean-context reviewer subagents when the harness supports them. If the user only says something like "review PR #X", first ask whether to run `review-loop` or do a normal review, and name the ordinary PR-scoped writes listed below.
- For a PR target, an explicit request to run `review-loop`, made through a current user request or adapter prompt that names the write scope, grants permission for read-only reviewer subagents plus ordinary PR-scoped loop writes: posting consolidated "Agent Review" comments, pushing fix commits to the PR branch, and applying the repository's established ready-for-human marker at the end.
- Route PR merges, issue closures, and branch deletion to a landing-capable workflow or direct human integration step whose contract owns those actions. Ask before non-PR-target writes, pushes to branches outside the target PR, creating new labels, permission changes, posting outside the target PR, or other external actions beyond the loop.

Output artifact:

- A temporary static HTML report that follows `references/report-guidance.md`.
- Optional consolidated "Agent Review" PR comments from the orchestrator that follow `references/agent-review-comment.md`, plus optional PR ready-for-human marking for PR targets.

Mutability:

- Mixed. The loop reads code and PR metadata, may edit local project files to fix `auto-fix` and `user-approved-fix` issue families, may create agent-labeled commits, may push to the target PR branch, may post consolidated "Agent Review" comments on the target PR, may apply the repository's established ready-for-human marker, and may write a temporary local HTML report.
- Reviewer-panel passes delegated to `review-pass` remain read-only.

Tools and connectors:

- `os/skills/review-pass/SKILL.md` for fresh and verification reviewer-panel passes.
- Local `git`, project test commands, and repository-specific validation.
- GitHub connector or `gh` for PR metadata, consolidated comments, labels, draft state, and branch pushes.
- `os/skills/ensure-implementation-readiness/SKILL.md` in check-only mode and `os/playbook/IMPLEMENT_FEATURES.md` for PR design-source preflight.
- `make-temp-file` for temporary report paths when available.
- `os/playbook/ARTIFACTS.md` for substantial report format decisions.
- `os/playbook/GITHUB_WORKFLOW.md` for GitHub issue, PR, and ready-for-human safety rules.

Safety:

- Use this mutating loop only when the user explicitly asked for this skill, a review loop, fresh review subagents plus fixes, or equivalent delegated review/fix work.
- If the user only asked for a normal review, ask before upgrading to `review-loop`; the question must state that the loop may post consolidated "Agent Review" comments, push fix commits to the PR branch, and apply the established ready-for-human marker.
- Treat a request to run `review-loop` on a specific PR as permission to request read-only `review-pass` panel cycles and for the listed PR-scoped writes when the current request or invocation surface made that write scope explicit. Do not ask for separate reviewer-panel permission, and do not ask before each reviewer spawn or ordinary loop write.
- Keep `review-pass` reviewers read-only. They report to the parent through `review-pass`; the parent is the single PR-comment writer.
- Before spawning reviewers for feature-sized work, run or follow `ensure-implementation-readiness` in check-only mode. If check-only returns `Needs Design Consensus`, stop before spawning reviewers and return `blocked`. If it returns `Gate Skipped`, continue only when the bypass is explicit and recorded. Do not grill, repair durable sources, edit issues, add readiness fields, or mutate readiness labels inside `review-loop`.
- Do not merge the PR, close issues, or delete branches through `review-loop`; route those actions to a landing-capable workflow or direct human integration step whose contract owns them. Ask before creating labels, changing permissions, pushing outside the target PR branch, or publishing outside the PR review surface.
- Do not copy private connector data, secrets, or unrelated repository context into reviewer prompts, review packets, PR comments, or final reports.

## Context Recovery Invariant

At the start of every parent-agent turn while `review-loop` is active, and before every `review-pass` invocation, final report, or ready-for-human action, reopen this `SKILL.md` and the relevant reference file. Do not rely on memory of the contract.

After any pause, interruption, resume, unusually long loop, or suspected compaction, assume context may be stale: rebuild the ledger from durable sources first, then reread this skill, then reread `os/skills/review-pass/SKILL.md` and the relevant reference file before continuing.

## Review-Pass Invocation Guard

- Reopen `os/skills/review-pass/SKILL.md`, `os/skills/review-pass/references/reviewer-prompts.md`, and `os/skills/review-pass/references/review-packet-template.md` before every fresh and verification pass. If the harness cannot discover `review-pass` by name, read those canonical files directly and follow them as the fallback.
- Fill every pass request explicitly with the common fields: target, repository, base, head or current head, mode, baseline intent, reviewer count or risk posture, optional lens overrides, custom lens notes, and reporting mode.
- For `fresh` passes, keep reviewer context clean: do not include prior packets, parent analysis, autopilot classifications, complexity posture, lazy-human decisions, fix commits, accepted fixes, declined rationales, consolidated comment URLs, or validation results unless they are part of the baseline intent itself.
- For `verification` passes, include only the needed prior packet, reviewer finding IDs, issue-family IDs, autopilot classifications and rationales, complexity posture, smallest closing moves or lazy-human decisions, fix commits, accepted fixes, declined rationales, consolidated comment URL, and validation results.
- Preserve `review-pass` template rules about read-only review, no reviewer PR comments, issue-family sweeps, design-escape-hatch concerns, full-diff rereads, provisional IDs, and the clean response sentinel.
- When the harness supports reviewer subagents, request a real multi-reviewer `review-pass` panel. Do not fall back to a single-agent review merely because the user did not separately say "subagents"; the loop's explicit `review-pass` panel request carries that authorization.
- Treat the review packet as advisory. The parent owns final accept/decline decisions and records the durable ledger.
- Do not ask the user to manage reviewer opening, reviewer closure, or pass-level prompt assembly; that is `review-pass` responsibility.
- After compaction, rebuild the ledger first, then reload `review-pass`, then request the next pass.

## Reviewer Continuity

Verification should preserve source-reviewer continuity without making the user manage live reviewer state.

- When the harness can safely resume the same source reviewers, request that `review-pass` use same-source reviewer continuity and provide the source reviewer aliases, source reviewer handles, relevant reviewer finding IDs, and issue-family IDs.
- When same-source resumption is unavailable, unsafe, or lost after compaction, request packet/finding-source fallback: provide the prior packet, source reviewer aliases, source reviewer finding IDs, autopilot classifications and rationales, complexity posture, smallest closing moves or lazy-human decisions, fix commits, declined rationales, and validation results to fresh verification reviewers.
- Get opaque source reviewer handles from the caller-private continuity handoff returned by `review-pass` when the harness provides one. If the handoff is unavailable, record that limitation and use packet/finding-source fallback.
- Keep opaque source reviewer handles in the loop ledger or orchestration request only; do not put them in reviewer prompts, PR comments, public reports, or human-facing packets. If debugging requires handle-level detail, keep that detail in private orchestration diagnostics outside review packets, reviewer prompts, PR comments, public reports, and other human-facing artifacts.
- Record the continuity mode and source aliases in the ledger and final report so later agents can distinguish same-reviewer verification from packet/finding-source fallback without exposing handles.
- Treat continuity as a verification-quality preference, not as permission for reviewers to keep state open, mutate files, or post PR comments. `review-pass` still owns prompt assembly, reviewer lifecycle, collection, closure, and packet normalization for the current pass.

## Conservative Autopilot

Run the parent loop in conservative autopilot by default unless the user asks for manual adjudication or a more aggressive refactor. Conservative autopilot answers the user's implicit question: what does the agent need the user to know exactly, and what can it confidently do without the user?

Classify every issue family after each packet. Resolve bucket overlap by evidence, scope, and expected churn rather than by the most interruptive label: clearly incorrect, duplicate, speculative, stylistic, out-of-scope, or low-value scope-expanding suggestions are `auto-decline`; evidenced in-scope findings with a small safe fix are `auto-fix`; evidenced in-scope findings that require product, scope, reusable-contract, or design-escape-hatch judgment are `ask-user`.

- `auto-fix`: evidenced by the packet or repository inspection, in scope for the original brief, localized or family-local, consistent with existing project patterns, supported by a clear validation signal, and unlikely to add meaningful concepts, ownership surfaces, or long-term maintenance burden.
- `auto-decline`: incorrect, duplicate, speculative, stylistic without project support, clearly out of scope, a low-value scope expansion, P3 polish, or lower value than the churn.
- `ask-user`: an evidenced in-scope finding whose fix changes product behavior, changes scope, changes workflow semantics, adds or changes a reusable contract, introduces new abstractions, parser/schema/grammar semantics, lifecycle behavior, synchronization logic, permission boundaries, publication rules, or triggers the Design Escape Hatch.

Do not ask the user to adjudicate `auto-fix` or `auto-decline` families one by one. Record the decision and rationale in the ledger, PR comment or chat summary, and final report. Ask only for `ask-user` families or when repository evidence cannot settle the decision.

Before editing an `auto-fix` or `user-approved-fix` family, apply the complexity governor and record the chosen smallest closing move:

1. Delete, simplify, narrow, split, or scope-reduce the problematic shape.
2. Use an existing helper, contract, module, documented pattern, or validation point.
3. Tighten the current code or prose locally.
4. Add narrow validation or tests around existing behavior.
5. Add or extend a new abstraction, schema, parser, lifecycle rule, synchronization mechanism, or reusable contract only when the durable brief already approved that exact mechanism or the user explicitly approves it as `user-approved-fix`.

Treat new concepts as guilty until proven necessary. If the proposed fix increases the concept count, creates another durable surface, or makes future agents understand more rules than before, reclassify it as `ask-user` when the finding is evidenced and in scope; otherwise classify it as `auto-decline` when it is clearly out of scope or lower value than the churn. Keep it as `auto-fix` only when it uses or completes a mechanism the durable brief already approved without expanding that mechanism's semantics. P0/P1 severity can make the lazy-human recommendation urgent; it does not by itself bypass `ask-user`.

When pausing for the user, use a lazy-human brief instead of dumping raw issue-family adjudication:

1. what the user needs to decide exactly;
2. what the loop can confidently do without the user;
3. what the loop is declining to avoid complexity;
4. the recommended default.

After the brief, record exactly one `ask-user` decision state:

- `user-approved-fix`: the user wants the loop to make the change; route the family through the normal fix, validation, and verification path.
- `user-declined/accepted-risk`: the user chooses not to fix or explicitly accepts the residual risk; record the rationale and include it in the final report.
- `unresolved`: no user decision yet; this blocks ready marking and final convergence.

Before yielding for an `ask-user` decision, make the unresolved blocker recoverable in the current reporting mode: record the issue-family ID, autopilot classification, lazy-human brief, exact decision needed, and decision state `unresolved` in the loop ledger and in either the consolidated Agent Review comment when a PR comment is appropriate and authorized, or the chat pause message when comments are not being posted. After the user answers, record `user-approved-fix` or `user-declined/accepted-risk` before continuing. If recovery cannot find a resolved decision, treat the family as `unresolved` and ask again.

## Efficiency Controls

- Use a moderate, balanced, or medium effort level for the orchestrator by default when the harness exposes reasoning-effort controls. Reserve high or extra-high effort for `review-pass` reviewer quality, genuinely ambiguous adjudication, and hard design tradeoffs.
- Keep the orchestrator focused on ledger management, deduplication, implementation, validation, PR-surface writes, and reporting.
- Batch work by issue family. When a candidate Reviewer Finding identifies real risk, normalize it into an Issue Family, then search or inspect for sibling occurrences and fix the whole family before requesting verification.
- Prefer one family-level fix commit over several single-occurrence commits when the related fixes are cohesive. Keep separate commits for unrelated families or risky changes that need isolated validation.
- Run cheap deterministic checks, `rg` searches, self-tests, or narrow scripts to sweep for sibling occurrences before spending another reviewer pass.
- Use soft budget checkpoints rather than hard loop stops. They are awareness checkpoints, not automatic aborts.
- Trigger a checkpoint after roughly 60-90 minutes, after two fresh panel cycles, after eight fix commits, when a fixed family is rediscovered, or when the loop appears to be finding diminishing returns.
- At a checkpoint, summarize elapsed time if known, panel cycles, fix commits, accepted and declined issue families, remaining risk, current confidence, cost/effort posture, and the next planned review step. Continue by default unless the user set a budget cap, the next step expands scope, the loop appears to be thrashing, or the checkpoint raises a design-escape-hatch concern.
- The parent agent may always pause and ask the user for judgment when user input would improve the outcome, even if the workflow would otherwise allow the loop to continue. Prefer reaching out early when a design choice, scope boundary, product behavior, or implementation shape seems uncertain.
- When complexity creep is a known risk, ask `review-pass` for simplicity or `code-judo` attention in the pass request. Prefer concrete deletion or scope-reduction findings over broad architecture work unless the target's risk really requires a heavier structural lens.

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

Accepted issue families can be resolved by simplifying, narrowing, splitting, or deleting the problematic design, not only by adding code. If the user chooses to continue the current design, record that decision in the ledger and continue with the normal fix and verification workflow.

## Contract Surface Matrix

Use this when an `auto-fix` or `user-approved-fix` issue family changes workflow semantics, cross-skill ownership, safety rules, state or lifecycle behavior, prompt behavior, artifact schemas, validation policy, privacy boundaries, or filing rules. Skip it for typo fixes, local prose cleanup, narrow examples, and implementation details that do not change a reusable contract.

Before editing, make a tiny matrix in the loop ledger or working notes:

`Semantic | Owner | Inputs | Outputs | Prompt/Recovery | Ledger/Report | Privacy/Filing | Validation`

Use the matrix to update affected contract surfaces in one pass. Check the owning skill, caller or called skills, prompt templates, recovery prompts, packet or report schemas, manifest entry, source-routing or validator coverage when relevant, privacy/filing rules, current-machine adapters or exposure, and any final report guidance. Keep the matrix lightweight; it is a propagation guard, not a design doc.

## Workflow Phases

1. Establish the target:
   - Identify the repository, PR or commit target, base branch, head branch, and current branch.
   - Read the repository's local instructions and review policy.
   - Fetch or inspect current PR metadata when network access and permissions allow.
   - For feature-sized targets, apply the implementation-readiness preflight by invoking or following `ensure-implementation-readiness` in check-only mode against the issue, PR body, ADR, or local design doc. Continue only on `Ready to Implement` or an explicit recorded `Gate Skipped` verdict. If check-only returns `Needs Design Consensus`, stop before reviewer spawning and return `blocked` with the missing consensus evidence.
   - If the target is not a PR, choose local reporting mode instead of PR comments.
   - Establish the baseline intent summary described in the Design Escape Hatch section. Keep it in the loop ledger so later packets can be compared against the original brief and allowed alternatives.

2. Set the loop ledger:
   - Track each pass cycle, pass mode, reviewer continuity mode, opaque handle availability, review packet path or chat status, reviewer aliases when supplied by `review-pass`, raw reviewer findings or crosswalk summaries, normalized family IDs, autopilot classification (`auto-fix`, `auto-decline`, or `ask-user`), accepted/declined/user-decision status, `ask-user` decision state, unresolved `ask-user` blockers, lazy-human brief status, complexity posture, chosen smallest closing move, fix commits, validation results, consolidated comment URL or chat status, and pass closure status.
   - Normalize families into stable ledger IDs such as `C1-IF3` and preserve source reviewer finding IDs from `review-pass`.
   - If compaction or interruption loses details, rebuild the ledger from consolidated "Agent Review" comments, chat pause messages, user replies, conversation summaries, commit history, local validation output, and saved or pasted review packets. Recover autopilot classifications, rationales, ask-user decision states, lazy-human briefs or user decisions, complexity posture, and smallest closing moves from the newest durable source or chat-reporting source that contains them. If no source contains a resolved `ask-user` decision, recover the family as `unresolved` and ask again rather than inferring approval or accepted risk.
   - Prefer one consolidated "Agent Review" comment per panel pass for PR targets. For non-PR targets, keep packet output in chat and the final report.

3. Run a fresh review pass:
   - Reopen `review-pass` and request a `fresh` pass with the target, base/head or commit range, baseline intent, reporting mode, and any risk-based reviewer count or lens hints.
   - Ask `review-pass` to compare the implementation shape against the durable design source and flag first-commit design drift before the loop starts treating symptoms as isolated bugs.
   - When the user or prior loop history points at over-complexity, ask for simplicity or `code-judo` attention so reviewers surface smaller shapes that preserve behavior while deleting moving parts.
   - Wait for the packet before adjudicating.

4. Adjudicate and consolidate packet findings:
   - Read each packet family as a claim, not an instruction.
   - Deduplicate with existing ledger families while preserving which pass and reviewers found them.
   - Apply Conservative Autopilot before asking the user for issue-family decisions. Classify every family as `auto-fix`, `auto-decline`, or `ask-user`.
   - For every `auto-fix` or `user-approved-fix` family, record the generalized rule, representative examples, sibling-search strategy, expected fix shape, and validation signal that would prove the family is closed.
   - If an `auto-fix` or `user-approved-fix` family changes a reusable workflow contract, create a Contract Surface Matrix before editing so all affected surfaces are patched together.
   - Compare `auto-fix` and `user-approved-fix` issue families against the baseline intent summary. If a family mostly exists because the implementation chose a heavier design than the brief required, trigger the Design Escape Hatch before implementing another fix.
   - Accept `auto-fix` issue families that identify real correctness, safety, regression, maintainability, test, or UX risks and can be closed with the complexity governor.
   - Decline `auto-decline` issue families that are incorrect, out of scope, stylistic without project support, duplicates, or lower-value than the churn they would create. Record a short rationale.
   - Ask the user only for unresolved `ask-user` families, unresolved evidence disputes, product/scope changes, or design-escape-hatch calls. Use the lazy-human brief format from Conservative Autopilot, record the `unresolved` blocker before yielding, and record the resulting state as `user-approved-fix`, `user-declined/accepted-risk`, or `unresolved` before continuing. The `unresolved` state blocks ready marking and final convergence.
   - For PR targets, read `references/agent-review-comment.md` and post one consolidated "Agent Review" comment for the panel pass when there are `auto-fix` issue families, resolved `ask-user` decisions, useful declined issue-family rationale, or unresolved `ask-user` blockers. Post before an `ask-user` pause when a PR comment is appropriate and authorized; otherwise include the same recoverable blocker fields in the chat pause message. Do not have reviewers post separate PR comments.

5. Fix `auto-fix` and `user-approved-fix` issue families:
   - Implement fixes in the parent workspace, preserving unrelated user changes.
   - Sweep for sibling occurrences in the same issue family before committing, using repository search, tests, fixtures, or small scripts when useful.
   - Use any Contract Surface Matrix created during adjudication to patch every affected surface before verification, not just the representative line.
   - Before editing, choose the smallest closing move from the complexity governor and record the expected complexity delta. Prefer deletion, simplification, scope reduction, or an existing project pattern over new machinery.
   - Before adding new schema, grammar, parser, lifecycle, synchronization, publication semantics, durable contract surfaces, or named abstractions to satisfy a finding, confirm the durable brief already approved that exact mechanism or the family is a `user-approved-fix`. Otherwise recheck whether the family should be `ask-user` or whether the Design Escape Hatch should fire. P0/P1 evidence should shape the recommended default, not skip user judgment.
   - Run the smallest trustworthy validation for the touched surface, broadening when shared behavior or user-facing workflows are affected.
   - Commit those fixes with an agent-prefixed subject, such as `#<agent-name> fix review finding about retries`. Use the active agent or harness name, for example `codex`, `claude`, or `gemini`; do not hard-code one agent name into the skill.
   - Push fixes to the target PR branch for PR targets. Otherwise leave local changes and report the needed external action.

6. Run a verification review pass:
   - Reopen `review-pass` and request `verification` mode.
   - Prefer same-source reviewer continuity when the harness can safely resume source reviewers; otherwise use packet/finding-source fallback.
   - Provide only the needed reviewer continuity preference, source reviewer aliases or handles, prior packet, reviewer finding IDs, issue-family IDs, autopilot classifications and rationales, complexity posture, smallest closing moves or lazy-human decisions, fix commits, accepted fixes, declined rationales, validation results, and consolidated comment URL.
   - Ask `review-pass` to verify prior issue families, reassess declined issue families against the rationale, check whether accepted fixes honored the recorded complexity posture and smallest closing move, and reread the full current diff for missed or newly introduced issues.
   - Record whether the verification pass used same-source reviewer continuity or packet/finding-source fallback, and whether opaque handles were available through the private handoff.
   - If the verification packet contains remaining or new issue families, adjudicate them before deciding whether the loop is still blocked; fix `auto-fix` and `user-approved-fix` families, record or reassess `auto-decline` rationales, and pause for unresolved `ask-user` blockers.
   - If a verification packet challenges a declined rationale, reassess once from repository evidence; ask the user if the dispute changes product behavior, scope, or remains genuinely ambiguous.
   - Continue until the active family set has no unresolved `auto-fix` or `ask-user` blockers after Conservative Autopilot adjudication. Remaining reviewer concerns may be terminal only when recorded as `auto-decline` with rationale or as `user-declined/accepted-risk` by explicit user decision.
   - Pause for the user if the loop stops making progress, the same disputed finding repeats after a clear rationale, or more than five fix/verification rounds occur in one panel cycle without convergence.

7. Confirm with a new fresh pass:
   - After the active family set is clean, request a new `fresh` pass from `review-pass` with clean context sized to the current PR scope.
   - Adjudicate the new fresh packet without leaking prior parent analysis into the reviewer prompt.
   - If the new fresh packet leaves no unresolved `auto-fix` or `ask-user` blockers after Conservative Autopilot adjudication, the loop is complete.
   - If the new fresh packet has `auto-fix` families, run the fix and verification workflow again, then spawn another fresh pass. If it has unresolved `ask-user` blockers, pause with a lazy-human brief; only a later `user-approved-fix` state enters fix and verification.
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

Use `review-pass` as a hard dependency once it is canonical and exposed. If a harness cannot invoke the skill by name, read `os/skills/review-pass/SKILL.md`, `os/skills/review-pass/references/reviewer-prompts.md`, and `os/skills/review-pass/references/review-packet-template.md` directly as the fallback rather than rebuilding the templates here.

Call narrower playbooks for their owned surfaces: GitHub workflow policy for PR state, `make-temp-file` for temporary paths, and repository-specific test or release skills when present. Use the vendored `thermo-nuclear-review`, `thermo-nuclear-code-quality-review`, and `improve-codebase-architecture` skills through `review-pass` lenses, not as nested workflows inside `review-loop`.

## Quality Bar

- The loop captures target, base, head, baseline intent, final reviewed commit SHA or local diff state, and review-pass sizing rationale.
- Feature-sized review targets pass `ensure-implementation-readiness` check-only mode with `Ready to Implement`, or have an explicit `Gate Skipped` bypass recorded before reviewers are spawned; missing readiness returns `blocked` without review-phase repair.
- Every fresh or verification panel pass is delegated to `review-pass` or its canonical fallback files.
- The orchestrator owns one durable ledger and posts at most one consolidated "Agent Review" comment per panel pass.
- Findings are generalized into issue families where possible, and accepted families are swept before verification.
- Every issue family has an autopilot classification, rationale, and either a smallest closing move, decline reason, lazy-human brief, explicit user decision, or unresolved blocking state.
- `auto-fix` and `user-approved-fix` fixes use the complexity governor and prefer deletion, simplification, scope reduction, or existing patterns over new machinery.
- `auto-fix` never adds new durable machinery unless the durable brief already approved that exact mechanism; otherwise the family is `ask-user` until it becomes `user-approved-fix`.
- Repeated findings in the same issue family trigger a design-escape-hatch check rather than automatic patch accumulation.
- `auto-fix` and `user-approved-fix` semantic contract changes use a Contract Surface Matrix, or explicitly skip it because the fix is local and non-contractual.
- The parent agent reaches out to the user whenever unresolved `ask-user` judgment blocks convergence, and uses the lazy-human brief format when it pauses.
- Unresolved `ask-user` blockers are recorded in the current reporting mode before the parent yields, so recovery can either find an explicit decision or ask again.
- `auto-fix` and `user-approved-fix` issue families have concrete fix commits or local changes, plus validation evidence.
- Declined issue families have short rationales and are not silently dropped.
- Verification passes prefer same-source reviewer continuity when safely available, record opaque handle availability and any packet/finding-source fallback, check prior fixes, and reread the full current diff.
- The final state is supported by a fresh `review-pass` packet whose families leave no unresolved `auto-fix` or `ask-user` blockers after parent adjudication.
- The final HTML report follows `references/report-guidance.md` and can be reconstructed from consolidated PR comments, review packets, and commits.
- PR-scoped comments and commits are factual and clearly labeled as agent-generated review work.

## Filing Rules

- Do not create durable AgentOS state by default.
- Temporary reports live under the system temporary directory unless the user asks for a project-local artifact.
- Project-specific code fixes, commits, branches, and reports live in the target project, not AgentOS.
- PR comments and ready markers stay in GitHub.
- If the loop discovers a durable AgentOS improvement, classify the right inbox: GitHub issue or mapped tracker for public-safe actionable project work, propagation review queue for private/tentative/pre-issue proposals, or direct edit only when the user explicitly asks for the exact canonical edit.

## Verification

Before finishing:

1. Confirm the target, base, head, final reviewed commit SHA or local diff state, and review-pass sizing rationale.
2. Confirm the baseline intent summary was captured from the original brief, including allowed alternatives and non-goals when available.
3. Confirm feature-sized review targets passed `ensure-implementation-readiness` check-only mode with `Ready to Implement`, or had an explicit `Gate Skipped` bypass before reviewers were spawned; if readiness was missing, confirm the loop returned `blocked` before spawning reviewers.
4. Confirm every design-escape-hatch trigger was either surfaced to the user, explicitly declined with rationale, or found not applicable.
5. Confirm every fresh and verification pass used `review-pass` or its canonical fallback files.
6. Confirm the final fresh `review-pass` packet left no unresolved `auto-fix` or `ask-user` blockers after parent adjudication.
7. Confirm every issue family was classified as `auto-fix`, `auto-decline`, or `ask-user`, with rationale.
8. Confirm every `auto-fix` issue family has a fix or a scope/design change.
9. Confirm every accepted fix recorded the smallest closing move from the complexity governor, or recorded why new machinery was necessary.
10. Confirm every declined issue family has a rationale, including complexity/churn rationale when relevant.
11. Confirm every unresolved `ask-user` blocker has a recoverable lazy-human brief before yielding and remains non-terminal, and every resolved `ask-user` family has either a verified `user-approved-fix` or an explicit `user-declined/accepted-risk` decision.
12. Confirm `auto-fix` and `user-approved-fix` issue families were swept for sibling occurrences before verification.
13. Confirm `auto-fix` and `user-approved-fix` semantic contract changes used a Contract Surface Matrix, or record why the matrix was skipped.
14. Confirm verification review-pass requests included autopilot classifications and rationales, complexity posture, smallest closing moves or lazy-human decisions, accepted fixes, declined rationales, and validation results when applicable.
15. Confirm review-pass requests used the current fresh or verification templates, including reporting mode, read-only rule, no-reviewer-PR-comment rule, dirty-validation rule, issue-family sweep instruction, design-escape-hatch instruction, full-reread instruction, provisional-ID rule, and clean response sentinel.
16. If a deep-review lens was assigned, confirm `review-pass` supplied the deep-review lens instructions and no full standalone `thermo-nuclear-review` workflow was run inside `review-loop`.
17. If a structural-depth lens was assigned, confirm `review-pass` supplied the structural-depth lens instructions and no full standalone `improve-codebase-architecture` or `thermo-nuclear-code-quality-review` workflow was run inside `review-loop`.
18. Confirm explicit `review-pass` panel requests were treated as permission for read-only reviewer subagents when the harness supported them, or record why `review-pass` used fallback.
19. Confirm verification continuity mode and opaque handle availability were recorded for verification passes without exposing handle values.
20. Confirm soft budget checkpoints were surfaced when checkpoint triggers occurred.
21. Confirm validation commands and results are captured.
22. Confirm fix commits use the active agent-name prefix.
23. Confirm the temporary HTML report exists, follows `references/report-guidance.md`, hyperlinks commit hashes to GitHub commits when possible, and is linked in the orchestrator's chat as a clickable absolute-path `.html` Markdown link.
24. Confirm consolidated "Agent Review" comments followed `references/agent-review-comment.md` when posted.
25. Confirm no PR merges, issue closures, or branch deletion happened through `review-loop`; confirm no label creation, permission changes, non-target-branch pushes, or other out-of-loop external writes happened without current user authorization.
