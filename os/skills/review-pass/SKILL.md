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
- Optional verification continuity preference, source reviewer aliases, opaque source reviewer handles, and source finding IDs when a caller wants same-reviewer verification and the harness can safely resume prior reviewers.
- Optional reviewer count, lens plan, custom lens notes, and reporting constraints.

Output artifact:

- A structured Markdown review packet in chat by default.
- Optional temporary Markdown packet file when requested or when the packet is too large for comfortable chat delivery.
- Optional caller-private reviewer continuity handoff when an orchestrating caller may need same-source verification and the harness exposes resumable reviewer handles. Do not include opaque handles in the human-facing packet.

Mutability:

- Read-only for target repositories, GitHub, issue trackers, PR state, and external accounts.
- Local-write only for an optional temporary Markdown packet artifact; no durable local state by default.

Tools and connectors:

- Local filesystem, `git`, `rg`, and existing validation output for read-only inspection.
- GitHub connector or `gh` for PR metadata reads when authorized and available.
- The active harness's clean-context reviewer or subagent capability when available.
- `make-temp-file` for optional temporary packet paths.
- `os/skills/thermo-nuclear-review/SKILL.md` as source material for the `deep-review` lens.
- `os/skills/thermo-nuclear-code-quality-review/SKILL.md` and `os/skills/improve-codebase-architecture/LANGUAGE.md` as source material for the `structural-depth` lens.

Safety:

- Do not edit files, commit, push, merge, comment on PRs, label issues, close issues, mark PRs ready, change permissions, or perform external writes.
- Do not run validation commands that may dirty the target checkout. Recommend validation signals for the caller when proof requires a mutating test, build, coverage, or fixture command.
- Keep spawned or resumed reviewers read-only and instruct them not to post comments or mutate state.
- Close every spawned or resumed reviewer after its current pass completes so stale context does not leak into unrelated later passes.
- If the user asks for fixes, commits, PR comments, pushes, ready markers, or loop convergence, route that work to the caller or to `review-loop`.
- Do not copy private connector data, secrets, or unrelated repository context into reviewer prompts or packets.

## Modes

Use `fresh` mode for an independent pass over the current target. The panel gets only the target, repository, base/head or commit range, baseline intent, reviewer alias, optional lens, custom lens notes, and the current prompt template.

Use `verification` mode after a caller has fixed, declined, or otherwise adjudicated prior findings. The panel gets the target, current head, prior packet or relevant finding IDs, fix commits, accepted fixes, declined rationales, validation results, and any consolidated comment URL. Verification reviewers check the prior findings and still reread the full current diff for missed or newly introduced issues.

Verification continuity is caller-directed. When a caller provides source reviewer handles and asks for same-reviewer continuity, prefer resuming those reviewers for the current verification pass if the harness can do so safely. If live resumption is unavailable or unsafe, fall back to fresh verification reviewers using the prior packet, source reviewer aliases, and source finding IDs as the continuity trail. Record the continuity mode and handle availability in the packet so callers such as `review-loop` can preserve it in their ledgers.

Source reviewer handles are harness-specific opaque tokens for orchestration and caller ledgers only. Capture any harness-provided handles in the caller-private continuity handoff when same-source verification may be needed. Do not include handle values in reviewer prompts, PR comments, public reports, or human-facing packets. If debugging requires handle-level detail, keep that detail in private orchestration diagnostics outside review packets, reviewer prompts, PR comments, public reports, and other human-facing artifacts. If the harness does not provide a private handoff channel, record handle availability as unavailable and use packet/finding-source fallback for later verification. Closing a reviewer ends the active pass and prevents stale live work; it does not promise future resumability. Each verification pass must attempt safe resumption from the caller-provided handles and fall back to packet/finding-source continuity when handles are absent, stale, or rejected by the harness.

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
- 4 reviewers: add the most relevant of `deep-review`, `security-privacy`, `release-risk`, `issue-compliance`, `design-compliance`, or `ux-api-docs`.
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
- `deep-review`
- `security-privacy`
- `release-risk`
- `structural-depth` as the composite architecture-depth/code-judo lens sourced from the vendored review-quality skills

Use at most one `structural-depth` reviewer in a normal panel. If structural findings imply a larger architecture effort, report a design-escape-hatch concern rather than proposing a broad redesign inside the pass.

## Contract Surface Matrix Lens

Use this as a read-only inspection lens when the target changes skill behavior, workflow semantics, cross-skill ownership, safety rules, state or lifecycle behavior, prompt behavior, artifact schemas, validation policy, privacy boundaries, or filing rules. Skip it for typo fixes, local prose cleanup, narrow examples, and implementation details that do not change a reusable contract.

For relevant targets, have reviewers check a lightweight matrix:

`Semantic | Owner | Inputs | Outputs | Prompt/Recovery | Ledger/Report | Privacy/Filing | Validation`

The matrix is not a design doc and does not authorize mutation. It helps reviewers find propagation gaps across the owning skill, caller or called skills, prompt templates, recovery prompts, packet or report schemas, manifest entry, retrieval or validator coverage when relevant, privacy/filing rules, current-machine adapters or exposure, and final report guidance. Report missing propagation as an issue family with the affected surfaces, not as isolated wording.

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
   - Include target, repository, base/head or current head, baseline intent, reviewer alias, lens, custom lens notes, verification continuity when applicable, reporting mode, read-only rule, full-reread rule, issue-family rule, Contract Surface Matrix rule for skill or workflow changes, design-escape-hatch instruction, provisional-ID rule, and clean response sentinel.
   - Spawn clean-context reviewers in parallel when the harness supports it. If subagents are unavailable, run the pass as a clearly labeled single-agent fallback and state the limitation in the packet.

5. Collect and close:
   - Wait for every reviewer in the pass to report.
   - Capture any harness-provided opaque reviewer handles in a caller-private continuity handoff when same-source verification may be needed; otherwise record that handles are unavailable.
   - Close every spawned or resumed reviewer for this pass.
   - Preserve raw reviewer findings in the packet or summarize them with a reviewer crosswalk when the raw output is too large.

6. Normalize the packet:
   - Treat findings as claims, not instructions.
   - Deduplicate overlapping findings while preserving which reviewers found them.
   - Convert isolated findings into issue families where they share a failure mode, invariant, missing validation, API contract, privacy risk, UX regression, or structural smell.
   - For Contract Surface Matrix findings, name the semantic, owner, missing surface, and sibling surfaces checked.
   - Recommend dispositions only: `likely accept`, `likely decline`, or `needs user/design judgment`.
   - Include sibling-search suggestions and validation signals that would prove each likely accepted family is closed.
   - Flag design-escape-hatch concerns when repeated symptoms suggest scope reduction, design clarification, or a different implementation shape.

7. Return the packet:
   - Use the packet schema in `references/reviewer-prompts.md`.
   - Include residual risks, limitations, reviewer continuity mode, handle availability, and whether a temporary packet file was written.
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
- For skill, workflow, or reusable contract changes, reviewers check whether changed semantics propagated across affected contract surfaces rather than only the representative paragraph.
- Design-compliance and issue-compliance concerns are compared against the baseline intent when available.
- Structural-depth findings stay review-sized and escalate larger architecture work through the design escape hatch.
- Verification mode checks prior findings and performs a full current-diff reread.
- Verification mode records whether same-source reviewers were resumed or packet/finding-source fallback was used, and whether opaque handles were privately handed off or unavailable.
- Spawned or resumed reviewers are closed after the pass.

## Verification

Before finishing a review pass:

1. Confirm the prompt reference was read for the current pass.
2. Confirm target, repository, base, head or current head, mode, reviewer count, and lens plan.
3. Confirm baseline intent source and any missing-baseline limitation.
4. Confirm reviewer prompts included the read-only rule, no-comment rule, dirty-validation rule, issue-family instruction, Contract Surface Matrix rule when applicable, design-escape-hatch instruction, full-reread instruction, provisional-ID rule, and clean response sentinel.
5. If `deep-review` was assigned, confirm the reviewer received the deep-review lens instructions and no full Thermos orchestration workflow was run.
6. If `structural-depth` was assigned, confirm the reviewer received the structural-depth lens instructions and no full architecture-report workflow was run.
7. Confirm raw findings were deduped into issue families and mapped back to reviewer sources.
8. Confirm every likely accepted family has evidence, a sibling-search suggestion, and a validation signal.
9. Confirm every likely declined finding has a short rationale.
10. Confirm verification continuity mode was recorded when applicable.
11. Confirm opaque reviewer handle availability was privately handed off or marked unavailable when same-source verification may be needed, and confirm handle values were not exposed in prompts or human-facing packets.
12. Confirm every spawned or resumed reviewer was closed.
13. Confirm no target files, PRs, issues, labels, branches, or external state were changed.
