---
name: review-pass
description: Run one read-only review panel pass for a PR, branch/base pair, commit range, patch, or local change set and return a structured Markdown review packet. Use when the user wants a single manual review iteration, fresh-context reviewer panel, verification pass after fixes, lens-based code review, design or issue compliance review, architecture-depth/code-judo review, or when review-loop needs reviewer-panel mechanics without owning them directly.
---

# Review Pass

## Goal

Run one read-only review panel pass and return a review packet that a human or calling workflow can adjudicate. This skill owns the ephemeral reviewer-panel mechanics for a single pass; callers own final decisions and all mutation.

Read `references/reviewer-prompts.md` immediately before assembling reviewer prompts. Read `references/review-packet-template.md` immediately before normalizing or returning a packet. When a reviewer is assigned a named lens, also read that lens's file under `references/lenses/` before sending the prompt. Do not reconstruct prompt templates, lens guidance, packet headings, or packet field labels from memory after compaction or interruption.

## Contract

Inputs:

- A target PR URL or number, branch/base pair, commit range, patch, or local change set.
- A checkout for the target repository, or enough remote context for `gh` or a connector to inspect the target.
- Optional durable design source, issue, PR body, ADR, local design doc, or user-provided baseline intent.
- Optional mode: `fresh` by default, or `verification` when checking prior issue families after fixes or adjudication.
- Optional prior review packet, reviewer finding IDs, issue-family IDs, accepted fixes, declined rationales, fix commits, validation results, and consolidated comment URL for verification mode.
- Optional verification continuity preference, source reviewer aliases, opaque source reviewer handles, and source reviewer finding IDs when a caller wants same-reviewer verification and the harness can safely resume prior reviewers.
- Optional reviewer count, lens plan, custom lens notes, and reporting constraints.
- An explicit user request to run `review-pass`, run a review pass, use a reviewer panel, or perform equivalent read-only panel review counts as authorization to spawn or resume multiple read-only clean-context reviewers when the harness supports them. This authorization covers reviewer reads only, not target edits or external writes.

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
- The active harness's clean-context reviewer or subagent capability when available and authorized by an explicit review-pass or reviewer-panel request, or by a caller such as `review-loop`.
- `make-temp-file` for optional temporary packet paths.
- Per-lens reviewer instructions under `os/skills/review-pass/references/lenses/`.
- The canonical packet template at `os/skills/review-pass/references/review-packet-template.md`.
- `os/skills/thermo-nuclear-review/SKILL.md` as source material for the `deep-review` lens.
- `os/skills/thermo-nuclear-code-quality-review/SKILL.md` and `os/skills/improve-codebase-architecture/LANGUAGE.md` as source material for the `structural-depth` lens.

Safety:

- Do not edit files, commit, push, merge, comment on PRs, label issues, close issues, mark PRs ready, change permissions, or perform external writes.
- Do not run validation commands that may dirty the target checkout. Recommend validation signals for the caller when proof requires a mutating test, build, coverage, or fixture command.
- Treat an explicit `review-pass` or reviewer-panel request as authorization to spawn or resume read-only reviewer subagents for the current pass when the harness supports them. Treat caller-provided panel requests from `review-loop` the same way.
- Keep spawned or resumed reviewers read-only and instruct them not to post comments or mutate state.
- Close every spawned or resumed reviewer after its current pass completes so stale context does not leak into unrelated later passes.
- If the user asks for fixes, commits, PR comments, pushes, ready markers, or loop convergence, route that work to the caller or to `review-loop`.
- Do not copy private connector data, secrets, or unrelated repository context into reviewer prompts or packets.

## Modes

Use `fresh` mode for an independent pass over the current target. The panel gets only the target, repository, base/head or commit range, baseline intent, reviewer alias, optional lens, custom lens notes, and the current prompt template.

Use `verification` mode after a caller has fixed, declined, or otherwise adjudicated prior issue families. The panel gets the target, current head, prior packet or relevant reviewer finding IDs and issue-family IDs, fix commits, accepted fixes, declined rationales, validation results, and any consolidated comment URL. Verification reviewers check the prior issue families and still reread the full current diff for missed or newly introduced issues.

Verification continuity is caller-directed. When a caller provides source reviewer handles and asks for same-reviewer continuity, prefer resuming those reviewers for the current verification pass if the harness can do so safely. If live resumption is unavailable or unsafe, fall back to fresh verification reviewers using the prior packet, source reviewer aliases, and source reviewer finding IDs as the continuity trail. Record the continuity mode and handle availability in the packet so callers such as `review-loop` can preserve it in their ledgers.

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

Lens activation criteria:

| Lens | Use when | Reference |
| --- | --- | --- |
| `general` | The pass is quick, tiny, or needs one balanced reviewer. | `references/lenses/general.md` |
| `correctness` | The target changes behavior, invariants, state transitions, control flow, API contracts, or error paths. | `references/lenses/correctness.md` |
| `tests-regressions` | The target has meaningful regression risk, test coverage questions, fixture changes, migration paths, or user-visible behavior. | `references/lenses/tests-regressions.md` |
| `edge-cases-data-integrity` | The target touches persistence, migration, concurrency, idempotency, partial failure, boundary values, invalid input, or data-loss risk. | `references/lenses/edge-cases-data-integrity.md` |
| `architecture-depth` | The target changes module boundaries, ownership, interfaces, locality, or abstraction shape but does not need the heavier composite structural lens. | `references/lenses/architecture-depth.md` |
| `code-judo` | The target looks behaviorally plausible but may have a smaller implementation shape that deletes concepts, branches, wrappers, flags, conditionals, or layers. | `references/lenses/code-judo.md` |
| `design-compliance` | A durable design source, ADR, PRD, or architecture decision exists and the review should check fit against it. | `references/lenses/design-compliance.md` |
| `issue-compliance` | A tracker issue or acceptance criteria define the expected outcome, non-goals, or validation plan. | `references/lenses/issue-compliance.md` |
| `ux-api-docs` | The target changes user-facing behavior, API ergonomics, compatibility, documentation, naming, or workflows. | `references/lenses/ux-api-docs.md` |
| `deep-review` | The target is broad, correctness-sensitive, security-sensitive, devex-sensitive, feature-gated, cross-package, or otherwise benefits from a harsher branch-audit posture. | `references/lenses/deep-review.md` |
| `security-privacy` | The target touches permissions, secrets, auth boundaries, data exposure, external-account effects, privacy markers, or publication safety. | `references/lenses/security-privacy.md` |
| `release-risk` | The target affects rollout, migration, fallback, observability, dependency risk, performance, or support burden. | `references/lenses/release-risk.md` |
| `structural-depth` | The target is normal-to-broad product or code work where architecture-depth and code-judo attention should be combined into one heavier structural reviewer. | `references/lenses/structural-depth.md` |

Use at most one `structural-depth` reviewer in a normal panel. If structural findings imply larger architecture or code-quality work, report a `Design escape hatch` concern that recommends a standalone `improve-codebase-architecture` or `thermo-nuclear-code-quality-review` pass rather than proposing a broad redesign or invoking those skills inside the pass.

Use `deep-review` as an in-panel lens when a review needs sharper correctness, security, developer-experience, or feature-gate scrutiny. If the target deserves a full branch audit, report a `Design escape hatch` concern that recommends a standalone `thermo-nuclear-review` pass rather than invoking that skill inside the pass.

## Contract Surface Matrix Lens

Use this conditional read-only inspection lens when the target changes skill behavior, workflow semantics, cross-skill ownership, safety rules, state or lifecycle behavior, prompt behavior, artifact schemas, validation policy, privacy boundaries, or filing rules. Skip it for typo fixes, local prose cleanup, narrow examples, and implementation details that do not change a reusable contract.

When applicable, read `references/lenses/contract-surface-matrix.md` and include its guidance in every relevant reviewer prompt. The matrix is not a design doc and does not authorize mutation; it helps reviewers report missing propagation as an issue family with the affected surfaces, not as isolated wording.

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
   - For each assigned named lens, read only the matching file under `references/lenses/` and include its prompt snippet or equivalent instructions in that reviewer's prompt.
   - When the target triggers the Contract Surface Matrix lens, read `references/lenses/contract-surface-matrix.md` and include its prompt snippet or equivalent instructions in every relevant reviewer prompt.
   - Fill the fresh or verification template explicitly for every reviewer.
   - Include target, repository, base/head or current head, baseline intent, reviewer alias, lens, assigned lens guidance, Contract Surface Matrix guidance when applicable, custom lens notes, verification continuity when applicable, reporting mode, read-only rule, full-reread rule, issue-family rule, design-escape-hatch instruction, provisional-ID rule, and clean response sentinel.
   - Spawn clean-context reviewers in parallel when the harness supports it and the pass is authorized by an explicit review-pass or reviewer-panel request, or by a caller such as `review-loop`. If subagents are unavailable, run the pass as a clearly labeled single-agent fallback and state the limitation in the packet.

5. Collect and close:
   - Wait for every reviewer in the pass to report.
   - Capture any harness-provided opaque reviewer handles in a caller-private continuity handoff when same-source verification may be needed; otherwise record that handles are unavailable.
   - Close every spawned or resumed reviewer for this pass.
   - Preserve raw reviewer findings in the packet or summarize them with a reviewer crosswalk when the raw output is too large.

6. Normalize the packet:
   - Reopen `references/review-packet-template.md`.
   - Treat findings as claims, not instructions.
   - Deduplicate overlapping findings while preserving which reviewers found them.
   - Convert isolated findings into issue families where they share a failure mode, invariant, missing validation, API contract, privacy risk, UX regression, or structural smell.
   - Use Reviewer Finding IDs for raw reviewer findings and Issue Family IDs for normalized families.
   - For Contract Surface Matrix findings, name the semantic, owner, missing surface, and sibling surfaces checked.
   - Recommend dispositions only: `likely accept`, `likely decline`, or `needs user/design judgment`.
   - Include sibling-search suggestions and validation signals that would prove each likely accepted family is closed.
   - Flag design-escape-hatch concerns when repeated symptoms suggest scope reduction, design clarification, or a different implementation shape.

7. Return the packet:
   - Use the exact packet template in `references/review-packet-template.md`.
   - Include residual risks, limitations, reviewer continuity mode, handle availability, and whether a temporary packet file was written.
   - Do not post the packet externally unless another approved workflow owns that write.

## Filing Rules

- Default output stays in chat.
- Optional temporary packet files live under the system temporary directory.
- Do not create durable AgentOS state by default.
- Project-specific fixes, PR comments, and ready markers belong to the caller, usually `review-loop`.
- If a pass discovers a durable AgentOS improvement, classify the right inbox: GitHub issue or mapped tracker for public-safe actionable project work, propagation review queue for private/tentative/pre-issue proposals, or direct edit only when the user explicitly asks for the canonical edit.

## Quality Bar

- The target, base, head or current head, mode, reviewer count, lens plan, and baseline-intent quality are explicit.
- Reviewers get clean, read-only prompts assembled from the current reference template and assigned per-lens files.
- Every reviewer reviews the full target, even when assigned a lens.
- The packet groups findings by issue family, not only by reviewer chronology.
- The packet uses the exact headings, section order, field labels, ID vocabulary, empty states, and temporary artifact wording from `references/review-packet-template.md`.
- Recommendations are clearly non-final and preserve caller authority.
- For skill, workflow, or reusable contract changes, reviewers check whether changed semantics propagated across affected contract surfaces rather than only the representative paragraph.
- Design-compliance and issue-compliance concerns are compared against the baseline intent when available.
- Structural-depth findings stay review-sized and escalate larger architecture or code-quality work through the design escape hatch.
- Deep-review findings stay review-sized and escalate larger branch-audit work through the design escape hatch.
- Verification mode checks prior issue families and performs a full current-diff reread.
- Verification mode records whether same-source reviewers were resumed or packet/finding-source fallback was used, and whether opaque handles were privately handed off or unavailable.
- Spawned or resumed reviewers are closed after the pass.

## Verification

Before finishing a review pass:

1. Confirm the prompt reference was read for the current pass.
2. Confirm the packet template reference was read before normalizing or returning the packet.
3. Confirm target, repository, base, head or current head, mode, reviewer count, and lens plan.
4. Confirm baseline intent source and any missing-baseline limitation.
5. Confirm every assigned named lens file under `references/lenses/` was read, and unassigned lens files were not required for prompt assembly.
6. Confirm `references/lenses/contract-surface-matrix.md` was read when the target changed reusable contract surfaces.
7. Confirm reviewer prompts included the read-only rule, no-comment rule, dirty-validation rule, assigned lens guidance, Contract Surface Matrix guidance when applicable, issue-family instruction, design-escape-hatch instruction, full-reread instruction, provisional-ID rule, and clean response sentinel.
8. If `deep-review` was assigned, confirm the reviewer received the deep-review lens instructions and no full Thermos orchestration or standalone `thermo-nuclear-review` workflow was run.
9. If `structural-depth` was assigned, confirm the reviewer received the structural-depth lens instructions and no full `improve-codebase-architecture` or `thermo-nuclear-code-quality-review` workflow was run.
10. Confirm an explicit review-pass or reviewer-panel request was treated as authorization for read-only reviewer subagents when the harness supported them, or record why fallback was used.
11. Confirm raw Reviewer Findings were deduped into Issue Families and mapped back to reviewer sources.
12. Confirm every likely accepted family has evidence, a sibling-search suggestion, and a validation signal.
13. Confirm every likely declined issue family has a short rationale.
14. Confirm verification continuity mode was recorded when applicable.
15. Confirm opaque reviewer handle availability was privately handed off or marked unavailable when same-source verification may be needed, and confirm handle values were not exposed in prompts or human-facing packets.
16. Confirm every spawned or resumed reviewer was closed.
17. Confirm no target files, PRs, issues, labels, branches, or external state were changed.
