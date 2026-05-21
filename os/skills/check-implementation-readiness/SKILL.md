---
name: check-implementation-readiness
description: Check whether a feature-sized issue, PRD, local design doc, or implementation request has durable design consensus before an agent starts coding; create or propose follow-up artifacts for deferred questions and return Ready to Implement, Needs Design Consensus, or Gate Skipped.
---

# Check Implementation Readiness

Use this skill before implementing feature-sized work. It runs the policy in `os/playbook/IMPLEMENT_FEATURES.md`, which is the canonical source for the readiness standard.

## Goal

Prevent implementation from starting before the design source is durable, complete for the requested scope, and either explicitly marked ready or confirmed by the user after inference.

## Contract

Inputs:

- A feature request, GitHub issue, PRD, ADR, local design document, planning note, PR, branch, or user request to implement work.
- Repository or mapped-project context when the work is project-specific.
- The durable design source when one exists.
- User approval for external tracker writes when the workflow needs to create or update GitHub issues, comments, labels, or other external project state.

Output artifact:

- A concise readiness report with exactly one verdict: `Ready to Implement`, `Needs Design Consensus`, or `Gate Skipped`.
- Optional durable local follow-up artifacts for deferred questions.
- Optional proposed or approved updates to the source design artifact.
- Optional GitHub issue updates or follow-up issues only when the user approves tracker writes or explicitly authorized them in the current request.

Mutability:

- Mixed. Read-only by default for inspection and verdicts.
- Local-write when creating local design docs or follow-up artifacts after the user asked the skill to make the design ready, or after the user declines external tracker updates and accepts a local destination.
- External-write only for GitHub issue creation, issue updates, comments, labels, or other tracker state after explicit user approval in the current request.

Tools and connectors:

- Local filesystem, `rg`, and mapped project files.
- GitHub connector or `gh` when checking or updating issue/PR design sources.
- `os/playbook/IMPLEMENT_FEATURES.md` for the policy.
- `os/playbook/GITHUB_WORKFLOW.md` for GitHub issue and PR writing conventions.
- `os/playbook/ARTIFACTS.md` when producing substantial human-facing design artifacts.

Safety:

- Ask before external tracker writes unless the current user request explicitly authorized them.
- Do not treat a missing readiness marker as silently ready. Infer, explain, and confirm with the user before implementation proceeds.
- Do not override `Design readiness: needs consensus` without user confirmation and an authorized design-source update.
- Do not leave meaningful deferred questions only in chat, model memory, or an unpersisted report.
- Do not formally depend on non-Core or current-machine skills.

## Verdicts

Return exactly one of these verdicts.

### Ready to Implement

Use when the design is complete for the current scope and has no blocking open questions. Meaningful deferred questions must be explicitly out of scope and captured in durable follow-up artifacts before this verdict is final.

### Needs Design Consensus

Use when the design source is missing, not durable, marked as needing consensus, missing required design content, or has blocking open questions or unclear scope boundaries.

### Gate Skipped

Use when the work is exempt because it is small, mechanical, or obvious: typo fixes, formatting-only edits, small wording changes, narrow bug fixes with clear expected behavior, or mechanical refactors with no behavior change.

## Workflow Phases

1. Establish the target:
   - Identify the implementation request, issue, PRD, design doc, PR, branch, or local plan.
   - Determine whether the task is feature-sized or gate-exempt under `os/playbook/IMPLEMENT_FEATURES.md`.
   - If exempt, return `Gate Skipped` with the reason.

2. Locate the durable design source:
   - Prefer the linked GitHub issue, PRD, ADR, local design doc, or planning note.
   - For PR review work, inspect the linked issue, PR body, and any referenced design source.
   - If only chat context exists, the verdict is `Needs Design Consensus` until that context is promoted into a durable artifact.

3. Check design completeness:
   - Confirm the source covers problem or motivation, current behavior or context, desired behavior, chosen design, alternatives considered, non-goals, acceptance criteria, validation plan, open questions, deferred follow-ups, and readiness marker.
   - Exact headings are not required when prose clearly contains the needed information.
   - Content wins over the marker.

4. Handle missing readiness markers:
   - If the source lacks `Design readiness:`, infer readiness from the content.
   - Tell the user the inferred verdict, the reasons, the implementation boundary, and the marker or edit you plan to make.
   - Wait for confirmation before implementation proceeds.
   - If edits are authorized, add or propose the marker after confirmation.

5. Handle open questions:
   - Classify open questions as blocking or deferred.
   - Blocking questions produce `Needs Design Consensus`.
   - Meaningful deferred questions must be out of scope and captured in durable follow-up artifacts. Related questions can be grouped into one follow-up artifact.
   - Ask before GitHub issue creation or updates unless tracker writes were explicitly authorized.
   - If GitHub writes are not authorized, create or propose a local artifact such as `docs/design/issue-<number>-implementation-readiness.md`, unless the project has a better convention or the user redirects.
   - Update or propose updating the current design source with a `Deferred Follow-ups` section linking to created artifacts.

6. Report the verdict:
   - Include the source reviewed.
   - Include satisfied and missing readiness fields.
   - Include the implementation boundary and non-goals.
   - Include created or proposed follow-up artifacts.
   - Include whether external writes happened, were proposed, or were skipped.

## Confirmation Shape

When inferring readiness from an unmarked source, use a short structured confirmation:

```text
I do not see a Design readiness marker. I infer this is Ready to Implement because <reasons>.

Implementation boundary: only implement <scope>; do not address <non-goals/deferred items>.

With your confirmation, I will add `Design readiness: ready to implement` to <artifact> and proceed.
```

For incomplete sources:

```text
I do not see a Design readiness marker. I infer this Needs Design Consensus because <missing or unclear items>.

Before implementation, resolve:
1. <question>
2. <question>

I can help turn those answers into the design source.
```

## Filing Rules

- Canonical policy lives in `os/playbook/IMPLEMENT_FEATURES.md`.
- Local design artifacts for AgentOS Core and mapped projects default to `docs/design/issue-<number>-implementation-readiness.md` unless a project convention exists.
- Private or personal design notes belong in the Personal Overlay.
- GitHub issue updates and follow-up issues stay in GitHub when approved.
- Do not store current-machine mirror state or private live inputs in Core.

## Quality Bar

- The verdict is one of the three allowed values.
- The design source is durable, or the report says why it is not.
- Missing marker inference is explicit and confirmed before implementation proceeds.
- Meaningful deferred questions are captured durably, not only in chat.
- External writes are approved before they happen.
- The implementation boundary is clear enough that another agent can avoid design creep.

## Verification

Before finishing:

1. Confirm `os/playbook/IMPLEMENT_FEATURES.md` was read for the policy.
2. Confirm the target was correctly classified as gated or exempt.
3. Confirm the verdict is `Ready to Implement`, `Needs Design Consensus`, or `Gate Skipped`.
4. Confirm the design source's marker and content were both checked.
5. Confirm unmarked readiness was not silently accepted.
6. Confirm deferred follow-up artifacts were created or proposed where required.
7. Confirm external tracker writes were approved before they happened.
8. If this skill or its manifest entry changed, run `python3 os/verification/scripts/validate_agentos.py`.
