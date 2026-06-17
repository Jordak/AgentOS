---
name: ensure-implementation-readiness
description: "Use before implementing feature-sized work: implement, build, add, redesign, substantially refactor, or start an issue/PRD/spec where the outcome changes behavior, workflow, data model, public docs policy, validation policy, or reusable AgentOS structure. Ensures durable design consensus when possible, creates required follow-up artifacts for deferred questions, and returns Ready to Implement, Needs Design Consensus, or Gate Skipped."
---

# Ensure Implementation Readiness

Read `os/playbook/IMPLEMENT_FEATURES.md` first for the policy overview and filing guidance. This skill is the operational owner for readiness verdicts, consensus-provenance interpretation, mode behavior, and readiness-label hygiene. If operational wording in the playbook and this skill diverges, follow this skill and treat the playbook as needing repair.

## Contract

Inputs:

- A feature request, GitHub issue, PRD, ADR, local design document, planning note, PR, branch, or user request to implement work.
- Repository or mapped-project context when the work is project-specific.
- The durable design source when one exists.
- Optional explicit mode: normal/repair mode by default, or check-only mode when the caller must verify readiness without repairing it.
- Current Authorization Boundary or caller-provided write boundary when normal/repair mode might create artifacts, update durable sources, or perform readiness-label hygiene.
- Optional caller-provided effort metadata to preserve in the readiness report when available or relevant under `os/skills/ORCHESTRATION_LOOPS.md`.
- Applicable external-write policy from `os/connections/SAFETY_RULES.md` and `os/playbook/GITHUB_WORKFLOW.md` when the workflow needs to create or update GitHub issues, comments, labels, or other external project state.

Output artifact:

- A concise readiness report with exactly one verdict: `Ready to Implement`, `Needs Design Consensus`, or `Gate Skipped`, plus the mode used, source reviewed, effort metadata when available or relevant, readiness fields, consensus provenance, missing evidence or missing consensus evidence, gate-skip field/state, `Gate Skipped` reason and durable gate-skip record location when present, any proposed source update when readiness repair or bypass recording could not be completed, final readiness label state, and PR-body readiness fields when the work will become a PR.
- Optional durable local follow-up artifacts for deferred questions.
- Optional proposed or approved updates to the source design artifact.
- Optional GitHub issue updates or follow-up issues only when permitted by the applicable external-write policy.

Mutability:

- Mixed. Normal/repair mode is the default: check first, return immediately when the target is already ready, and otherwise perform authorized readiness repair.
- Read-only in check-only mode. Do not grill, repair, create artifacts, edit issues, update design sources, or mutate labels in check-only mode.
- Local-write in normal/repair mode when creating local design docs or follow-up artifacts after the user asked the skill to make the design ready, or after the user declines external tracker updates and accepts a local destination.
- External-write in normal/repair mode only for GitHub issue creation, issue updates, comments, labels, or other tracker state when permitted by the applicable external-write policy.

Tools and connectors:

- Local filesystem, `rg`, and mapped project files.
- GitHub connector or `gh` when checking or updating issue/PR design sources.
- Core design-consensus skills: `grill-with-docs` by default for readiness repair and `grill-me` for pure design questioning.
- The implementation-readiness playbook for policy overview and filing guidance.
- `os/playbook/GITHUB_WORKFLOW.md` for GitHub issue and PR writing conventions.
- `os/playbook/ARTIFACTS.md` when producing substantial human-facing design artifacts.

Safety:

- Follow `os/connections/SAFETY_RULES.md` and `os/playbook/GITHUB_WORKFLOW.md` before external tracker writes.
- Do not treat missing readiness fields as silently ready. In check-only mode, report missing fields or evidence without prompting or editing. In normal/repair mode, infer, explain, and confirm with the user before implementation proceeds, then update or propose the full readiness fields.
- Do not treat a durable design source as consensus by itself. `Ready to Implement` requires valid consensus provenance. If provenance is missing, return `Needs Design Consensus`, or return `Gate Skipped` only when the work is exempt or an explicit bypass is recorded in the durable source's `Gate skipped:` field.
- Do not override `Design readiness: needs consensus` without user confirmation, valid consensus provenance, and an authorized design-source update.
- Do not treat a workflow invocation, assignment packet, normal/repair mode, existing branch, existing PR, caller handoff, coordinator handoff, or worker launch as user confirmation, consensus provenance, or gate-skip authorization. These may authorize the readiness process, but they do not supply the human design decision.
- Do not treat a freeform GitHub comment as human consensus provenance unless it explicitly attests human authorship, states the decision clearly enough to cite, and comes from a repository-trusted author relationship such as `OWNER`, `MEMBER`, or a project-approved collaborator role. Human-attested GitHub comments are a non-adversarial operational provenance signal, not a security guarantee; if author relationship is missing, ambiguous, or untrusted, ask in the current human channel or return `Needs Design Consensus`.
- For issue-driven work, if the issue has `needs design consensus` or an equivalent label, do not return `Ready to Implement` while the label remains. In normal/repair mode, remove that label only after verifying valid consensus provenance and explicit human confirmation under this skill's contract. In check-only mode, return `Gate Skipped` when an explicit bypass is already recorded in the durable source; otherwise report `Needs Design Consensus` instead of mutating the label. For intentional bypasses in normal/repair mode, leave the label in place and return `Gate Skipped` only after updating the durable source's `Gate skipped:` field with the bypass reason and missing evidence. If the field update is not authorized or cannot be completed, report the proposed update and return `Needs Design Consensus`, not `Gate Skipped`.
- Do not leave meaningful deferred questions only in chat, model memory, or an unpersisted report.
- Do not allow chat-only consensus to become the first implementation commit. Promote the agreed design into a durable source before coding, or record an explicit `Gate Skipped` bypass.
- Do not require a design-consensus workflow for readiness checks that need no repair, exempt work, or explicit `Gate Skipped` bypasses. When readiness repair is needed, require a Core design-consensus workflow by default and prefer `grill-with-docs`.

## Modes

### Normal / Repair Mode

Normal/repair mode is the default mode. First run the check-only logic. If the target is already ready, return `Ready to Implement` without unnecessary mutation. If readiness is missing and the Authorization Boundary permits repair, run the readiness repair workflow, promote resolved answers into the durable design source, create required follow-up artifacts, update readiness fields, and perform authorized readiness-label hygiene.

Normal/repair mode may use `grill-with-docs`, `grill-me`, targeted residual questions, local design artifacts, issue-body edits, or label cleanup when those actions are inside the applicable write policy. It authorizes executing the readiness process, not supplying the human side of consensus. It must not self-ratify readiness: agent-authored design text is a proposal until the durable source records valid consensus provenance or, for an intentional bypass, records `Gate skipped:` with the user's bypass reason and missing evidence.

### Check-Only Mode

Check-only mode verifies the invariant without repair. Read durable sources, issue labels, PR bodies, linked design sources, and cited provenance. Return `Ready to Implement`, `Needs Design Consensus`, or `Gate Skipped` with exact evidence and missing evidence. Do not grill, ask new design questions, edit durable sources, create follow-up artifacts, add readiness fields, remove labels, or otherwise mutate local or external state.

## Workflow Phases

1. Establish the target.
   Identify the implementation request, issue, PRD, design doc, PR, branch, or local plan. Determine whether the invocation is normal/repair mode or check-only mode. Apply the playbook's trigger scope and exemptions. If exempt, return `Gate Skipped` with the reason and report the gate-skip field/state as not applicable when no durable design source is required. If the user explicitly bypasses the gate after missing or incomplete readiness is reported, normal/repair mode must update the durable source's `Gate skipped:` field with the bypass reason and missing-readiness summary before returning `Gate Skipped`; if it can only propose that update, return `Needs Design Consensus` with the proposed update. Check-only mode may return `Gate Skipped` only when that bypass record already exists.

2. Locate the durable design source.
   Prefer the linked GitHub issue, PRD, ADR, local design doc, or planning note named by the request or repository. For issue or PR targets, inspect the issue or PR labels, body, comments when cited as provenance, and any referenced design source. If only chat context exists, the verdict is `Needs Design Consensus` until that context is promoted into a durable artifact or an intentional bypass is recorded in the durable source's `Gate skipped:` field. In normal/repair mode, when the user has already asked you to make the work ready, create or update the durable design source first, then evaluate that source before implementation. In check-only mode, do not create or update the source.

3. Check readiness.
   Evaluate the source against the playbook's design-source standard, readiness-field rules, consensus provenance rules, gate-skip field, and issue-label state. Content wins over the fields. A durable issue, PRD, ADR, local design doc, or handoff packet is necessary but not sufficient; it must record consensus provenance or an explicit gate skip. PR-body fields, Recovery Records, or caller handoffs may surface the bypass, but they do not substitute for the source `Gate skipped:` field unless they are the durable source being checked.
   Legacy sources with only the old `Design readiness:` marker are not automatically grandfathered. In check-only mode, report the missing consensus provenance or gate-skip evidence. In normal/repair mode, confirm with the user that the old source still reflects human-agent consensus before updating the current source to the full readiness field set. Do not bulk-migrate unrelated historical ADRs or design docs merely because policy v2 exists.

4. Check consensus provenance.
   Verify that `Consensus provenance:` points to a valid grill session, grill-equivalent process, human-attested GitHub comment from a trusted repository author, durable design-source update after explicit human confirmation, or explicit gate-skip reference in the source. A Calling Workflow handoff, coordinator handoff, worker assignment, existing branch, existing PR, or normal/repair-mode instruction that claims consensus exists without a concrete provenance pointer is not enough. If a target issue still has `needs design consensus`, the label wins over `Ready to Implement` unless this normal/repair invocation verifies provenance and removes the label under this skill's contract. Check-only mode must return `Gate Skipped` for an explicit recorded bypass; otherwise it must report the contradiction rather than repair it.

5. Confirm unmarked or partially marked inference.
   If the source lacks readiness fields, check-only mode reports `Needs Design Consensus` with the missing fields or evidence and does not prompt or edit. In normal/repair mode, infer readiness from the content, tell the user the inferred verdict, reasons, implementation boundary, and readiness-field edit you plan to make, then wait for confirmation before implementation proceeds. If edits are authorized, add or propose the full readiness field set: `Design readiness:`, `Consensus provenance:`, and `Gate skipped:`.

6. Handle open questions and repair.
   Classify open questions as blocking or deferred using the playbook's rules. In check-only mode, report missing consensus, missing provenance, stale labels, blocking questions, and the recommended repair route without mutating. In normal/repair mode, own the repair loop:
   - Use `grill-with-docs` by default when decisions need to sharpen domain language or ADR-worthy rationale, or when the readiness repair must result in updates to an issue body, PRD, local design doc, or other durable design source. When invoking or following it from an AgentOS workflow, pass the prescribed model/effort and prescription source from `os/skills/ORCHESTRATION_LOOPS.md`, or an explicit no-override/default statement, into the called workflow request when the harness can honor a separate invocation boundary; record prescribed and effective effort/status in this skill's readiness report when available or relevant.
   - Use `grill-me` only for pure design questioning where the durable source already exists and no domain glossary, ADR, issue body, or local design document needs to change during the questioning. When invoking or following it from an AgentOS workflow, pass the prescribed model/effort and prescription source from `os/skills/ORCHESTRATION_LOOPS.md`, or an explicit no-override/default statement, into the called workflow request when the harness can honor a separate invocation boundary; record prescribed and effective effort/status in this skill's readiness report when available or relevant.
   - Use targeted questions as supporting mechanics inside the selected workflow, post-workflow clarifications for narrow residual gaps, or the fallback only when the Core design-consensus skills are unavailable or explicitly excessive for the scope. If targeted questions are used without `grill-me` or `grill-with-docs`, explain why a grill workflow was unavailable or excessive for the scope.
   Ask one question at a time, recommend a default answer, inspect the codebase or existing docs instead of asking when the answer is discoverable, and carry resolved answers back into the durable design source before declaring the scope ready. `grill-with-docs` should supply the docs-aware interview path by default, but this skill or its approved caller owns issue-body, PRD, local-design-doc, and other durable-source updates under the applicable write policy. Follow that policy before GitHub issue creation, issue-body edits, comments, or label updates. If GitHub writes are not authorized, create the local artifact named by the playbook unless the project has a better convention or the user redirects. If required durable source updates, consensus provenance, gate-skip records, or follow-up artifacts are not created, the verdict remains `Needs Design Consensus` unless the work is exempt from the gate. Update or propose updating the current design source with readiness fields and a `Deferred Follow-ups` section linking to created artifacts. For an intentional bypass, update the full readiness field set with `Gate skipped:` containing the bypass reason and missing evidence before returning `Gate Skipped`; if the update can only be proposed, report that proposal while returning `Needs Design Consensus`. Do not treat PR fields or a Recovery Record alone as the durable bypass record. Remove `needs design consensus` only in normal/repair mode, only under this skill's contract, and only after valid consensus provenance and explicit human confirmation are present. Leave the label in place for `Gate Skipped`.

7. Report the verdict.
   Include the mode, source reviewed, effort metadata when available or relevant, satisfied and missing readiness fields, consensus provenance, missing consensus evidence when present, gate-skip field/state, `Gate Skipped` reason and durable gate-skip record location when present, final readiness label state, implementation boundary, non-goals, design-consensus route used or recommended, created follow-up artifacts, proposed source-design updates, and whether external writes happened, were proposed, or were skipped. If an intentional bypass could not be recorded, report the proposed `Gate skipped:` update while returning `Needs Design Consensus`. If the work will become a PR, include the exact `Readiness evidence:` and `Readiness verdict:` lines the PR body should carry. Prefer a GitHub issue as readiness evidence for issue-driven work; use a design doc only when the design is too large, architectural, private, or not naturally issue-shaped.

## Filing Rules

- Follow the implementation-readiness playbook for follow-up artifact destinations.
- Approved GitHub issue updates and follow-up issues stay in GitHub.
- Private or personal design notes belong in the Personal Overlay.
- Do not store current-machine exposure state or private live inputs in Core.

## Quality Bar

- The verdict is one of the three allowed values.
- The mode is honored: check-only performs no mutation; normal/repair mode performs only authorized repair.
- The design source is durable, or the report says why it is not.
- The source records valid consensus provenance, or the verdict is `Needs Design Consensus`, or `Gate Skipped` is backed by an exemption or the source's `Gate skipped:` field.
- When the user asked to make the work ready, resolved design answers have been promoted into the durable design source before `Ready to Implement`.
- Missing readiness-field inference is mode-specific: check-only reports missing evidence without mutation, while normal/repair confirms and promotes the full readiness field set before implementation proceeds.
- Issue labels such as `needs design consensus` are reconciled only by this skill in normal/repair mode; callers consume the verdict and do not perform readiness-label cleanup directly.
- Meaningful deferred questions are captured durably, not only in chat.
- External writes comply with the applicable external-write policy before they happen.
- The implementation boundary is clear enough that another agent can avoid design creep.
- For PR-bound work, the readiness report supplies PR-body readiness fields.

## Verification

Before finishing:

1. Confirm the playbook was read for the policy.
2. Confirm the target was correctly classified as gated or exempt.
3. Confirm the mode was honored, including no mutations in check-only mode.
4. Confirm the verdict is `Ready to Implement`, `Needs Design Consensus`, or `Gate Skipped`.
5. Confirm the design source's readiness fields, content, consensus provenance, gate-skip field, and relevant issue labels were checked.
6. Confirm workflow invocation, assignment packet, normal/repair mode, existing branch, existing PR, caller handoff, coordinator handoff, or worker launch was not treated as user confirmation, consensus provenance, or gate-skip authorization.
7. Confirm effort metadata was preserved in the readiness report when available or relevant.
8. Confirm unmarked readiness was not silently accepted.
9. Confirm human-attested GitHub comments counted only when explicit attestation and trusted repository author evidence were present.
10. Confirm the selected design-consensus route was appropriate: `grill-with-docs` by default for readiness repair, `grill-me` for pure design questioning, targeted questions only as a documented unavailable-or-excessive fallback or residual clarification, or no repair loop needed.
11. Confirm resolved answers were captured in the durable design source before reporting `Ready to Implement`.
12. Confirm `needs design consensus` or equivalent labels were removed only by this skill in normal/repair mode, or left in place for `Gate Skipped`.
13. Confirm deferred follow-up artifacts were created where required.
14. Confirm external tracker writes complied with the applicable external-write policy before they happened.
15. Confirm PR-bound work has visible PR-body readiness fields, and that `Gate Skipped` intentional bypasses name the durable `Gate skipped:` field; if writes were unavailable, confirm the proposed update was reported with `Needs Design Consensus` instead of `Gate Skipped`.
16. If this skill or its manifest entry changed, run `scripts/run-validator`.
