---
name: review-pass
description: Run one read-only review panel pass for a PR, branch/base pair, commit range, patch, or local change set and return a structured Markdown review packet. Use when the user wants a single manual review iteration, fresh-context reviewer panel, verification pass after fixes, lens-based code review, design or issue compliance review, architecture-depth/code-judo review, or when review-loop needs reviewer-panel mechanics without owning them directly.
---

# Review Pass

## Goal

Run one read-only review panel pass and return a review packet that a human or calling workflow can adjudicate. This skill owns the ephemeral reviewer-panel mechanics for a single pass; callers own final decisions and all mutation.

Read `references/reviewer-prompts.md` immediately before assembling reviewer prompts or normalizing a packet. Do not reconstruct prompt templates, lens guidance, or packet headings from memory after compaction or interruption.

## Contract

Inputs:

- A target PR URL or number, branch/base pair, commit range, patch, or local change set.
- A checkout for the target repository, or enough remote context for `gh` or a connector to inspect the target.
- Optional durable design source, issue, PR body, ADR, local design doc, or user-provided baseline intent.
- Optional mode: `fresh` by default, or `verification` when checking prior findings after fixes or adjudication.
- Optional prior review packet, finding IDs, accepted fixes, declined rationales, fix commits, validation results, and consolidated comment URL for verification mode.
- Optional reviewer count, lens plan, custom lens notes, and reporting constraints.

Output artifact:

- A structured Markdown review packet in chat by default.
- Optional temporary Markdown packet file when requested or when the packet is too large for comfortable chat delivery.

Mutability:

- Read-only for target repositories, GitHub, issue trackers, PR state, and external accounts.
- Local-write only for an optional temporary Markdown packet artifact; no durable local state by default.

Tools and connectors:

- Local filesystem, `git`, `rg`, and existing validation output for read-only inspection.
- GitHub connector or `gh` for PR metadata reads when authorized and available.
- The active harness's clean-context reviewer or subagent capability when available.
- `make-temp-file` for optional temporary packet paths.
- `os/skills/thermo-nuclear-code-quality-review/SKILL.md` and `os/skills/improve-codebase-architecture/LANGUAGE.md` as source material for the `structural-depth` lens.

Safety:

- Do not edit files, commit, push, merge, comment on PRs, label issues, close issues, mark PRs ready, change permissions, or perform external writes.
- Do not run validation commands that may dirty the target checkout. Recommend validation signals for the caller when proof requires a mutating test, build, coverage, or fixture command.
- Keep spawned reviewers read-only and instruct them not to post comments or mutate state.
- Close every spawned reviewer after its pass completes so stale context does not leak into later passes.
- If the user asks for fixes, commits, PR comments, pushes, ready markers, or loop convergence, route that work to the caller or to `review-loop`.
- Do not copy private connector data, secrets, or unrelated repository context into reviewer prompts or packets.

## Modes

Use `fresh` mode for an independent pass over the current target. The panel gets only the target, repository, base/head or commit range, baseline intent, reviewer alias, optional lens, custom lens notes, and the current prompt template.

Use `verification` mode after a caller has fixed, declined, or otherwise adjudicated prior findings. The panel gets the target, current head, prior packet or relevant finding IDs, fix commits, accepted fixes, declined rationales, validation results, and any consolidated comment URL. Verification reviewers check the prior findings and still reread the full current diff for missed or newly introduced issues.

Do not require the caller to manage live subagents, reviewer opening, or reviewer closure. The caller may provide prior packets and decisions, but this skill owns prompt assembly, reviewer lifecycle, collection, and packet normalization for the current pass.

## Lens Plan

Callers do not need to specify lenses. Always apply a baseline review bar for correctness, regressions, missing tests, safety, maintainability, user-facing behavior, and design drift. Named lenses are weighted attention, not exclusive scopes; every reviewer still reviews the full target.

Default reviewer count:

- Use 1 reviewer for a quick manual pass, tiny diff, or constrained local check.
- Use 2 reviewers for small, low-risk, docs-only, test-only, or single-subsystem changes.
- Use 3 reviewers for normal product or code changes.
- Use 4 reviewers for broad, cross-cutting, migration, public API, security, data-integrity, concurrency, or user-facing workflow changes.
- Use 5 reviewers only when the user asks for extra confidence or the target is unusually large or high risk.

Default lens spread:

- 1 reviewer: `general`.
- 2 reviewers: `correctness` and `tests-regressions`.
- 3 reviewers: add `structural-depth`.
- 4 reviewers: add the most relevant of `security-privacy`, `release-risk`, `issue-compliance`, `design-compliance`, or `ux-api-docs`.
- 5 reviewers: add a custom risk lens tied to the target's riskiest subsystem or assumption.

Built-in lenses:

- `general`
- `correctness`
- `tests-regressions`
- `edge-cases-data-integrity`
- `architecture-depth`
- `code-judo`
- `design-compliance`
- `issue-compliance`
- `ux-api-docs`
- `security-privacy`
- `release-risk`
- `structural-depth` as the composite architecture-depth/code-judo lens sourced from the vendored review-quality skills

Use at most one `structural-depth` reviewer in a normal panel. If structural findings imply a larger architecture effort, report a design-escape-hatch concern rather than proposing a broad redesign inside the pass.

## Workflow Phases

1. Establish the target:
   - Identify the repository, target type, base, head or current head, and local checkout.
   - Read repository instructions and review policy.
   - Inspect PR metadata, issue links, branch state, or local diff context when available.
   - Choose `fresh` or `verification` mode.

2. Establish baseline intent:
   - Derive required outcomes, explicit alternatives, non-goals, chosen implementation shape, and risky assumptions from the PR body, issue, spec, design doc, ADR, commit description, or user request.
   - If the baseline is weak or missing, proceed for manual review but flag the limitation in the packet.
   - Do not enforce implementation-readiness gates here; callers such as `review-loop` decide whether missing design evidence blocks the larger workflow.

3. Choose the panel:
   - Use the caller's reviewer count and lenses when provided.
   - Otherwise choose the smallest panel and lens spread that matches target size and risk.
   - Give every reviewer the full target. Use lenses only to diversify attention.

4. Assemble and run prompts:
   - Reopen `references/reviewer-prompts.md`.
   - Fill the fresh or verification template explicitly for every reviewer.
   - Include target, repository, base/head or current head, baseline intent, reviewer alias, lens, custom lens notes, reporting mode, read-only rule, full-reread rule, issue-family rule, design-escape-hatch instruction, provisional-ID rule, and clean response sentinel.
   - Spawn clean-context reviewers in parallel when the harness supports it. If subagents are unavailable, run the pass as a clearly labeled single-agent fallback and state the limitation in the packet.

5. Collect and close:
   - Wait for every reviewer in the pass to report.
   - Close every spawned reviewer for this pass.
   - Preserve raw reviewer findings in the packet or summarize them with a reviewer crosswalk when the raw output is too large.

6. Normalize the packet:
   - Treat findings as claims, not instructions.
   - Deduplicate overlapping findings while preserving which reviewers found them.
   - Convert isolated findings into issue families where they share a failure mode, invariant, missing validation, API contract, privacy risk, UX regression, or structural smell.
   - Recommend dispositions only: `likely accept`, `likely decline`, or `needs user/design judgment`.
   - Include sibling-search suggestions and validation signals that would prove each likely accepted family is closed.
   - Flag design-escape-hatch concerns when repeated symptoms suggest scope reduction, design clarification, or a different implementation shape.

7. Return the packet:
   - Use the packet schema in `references/reviewer-prompts.md`.
   - Include residual risks, limitations, and whether a temporary packet file was written.
   - Do not post the packet externally unless another approved workflow owns that write.

## Filing Rules

- Default output stays in chat.
- Optional temporary packet files live under the system temporary directory.
- Do not create durable AgentOS state by default.
- Project-specific fixes, PR comments, and ready markers belong to the caller, usually `review-loop`.
- If a pass discovers a durable AgentOS improvement, route it through the propagation review queue unless the user explicitly asks for the canonical edit.

## Quality Bar

- The target, base, head or current head, mode, reviewer count, lens plan, and baseline-intent quality are explicit.
- Reviewers get clean, read-only prompts assembled from the current reference template.
- Every reviewer reviews the full target, even when assigned a lens.
- The packet groups findings by issue family, not only by reviewer chronology.
- Recommendations are clearly non-final and preserve caller authority.
- Design-compliance and issue-compliance concerns are compared against the baseline intent when available.
- Structural-depth findings stay review-sized and escalate larger architecture work through the design escape hatch.
- Verification mode checks prior findings and performs a full current-diff reread.
- Spawned reviewers are closed after the pass.

## Verification

Before finishing a review pass:

1. Confirm the prompt reference was read for the current pass.
2. Confirm target, repository, base, head or current head, mode, reviewer count, and lens plan.
3. Confirm baseline intent source and any missing-baseline limitation.
4. Confirm reviewer prompts included the read-only rule, no-comment rule, issue-family instruction, design-escape-hatch instruction, full-reread instruction, provisional-ID rule, and clean response sentinel.
5. If `structural-depth` was assigned, confirm the reviewer received the structural-depth lens instructions and no full architecture-report workflow was run.
6. Confirm raw findings were deduped into issue families and mapped back to reviewer sources.
7. Confirm every likely accepted family has evidence, a sibling-search suggestion, and a validation signal.
8. Confirm every likely declined finding has a short rationale.
9. Confirm every spawned reviewer was closed.
10. Confirm no target files, PRs, issues, labels, branches, or external state were changed.
