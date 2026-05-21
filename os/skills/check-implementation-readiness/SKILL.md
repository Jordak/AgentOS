---
name: check-implementation-readiness
description: Use before implementing feature-sized work: implement, build, add, redesign, substantially refactor, or start an issue/PRD/spec where the outcome changes behavior, workflow, data model, public docs policy, validation policy, or reusable AgentOS structure. Checks durable design consensus, creates or proposes follow-up artifacts for deferred questions, and returns Ready to Implement, Needs Design Consensus, or Gate Skipped.
---

# Check Implementation Readiness

Read `os/playbook/IMPLEMENT_FEATURES.md` first. That playbook owns the readiness policy, including exemptions, design-source requirements, marker rules, verdict definitions, deferred follow-up rules, and review-loop preflight behavior. This skill runs that policy.

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
- Optional harness-exposed design-interview workflows such as `grill-me`, `grill-with-docs`, or an equivalent, when present.
- The implementation-readiness playbook for policy.
- `os/playbook/GITHUB_WORKFLOW.md` for GitHub issue and PR writing conventions.
- `os/playbook/ARTIFACTS.md` when producing substantial human-facing design artifacts.

Safety:

- Ask before external tracker writes unless the current user request explicitly authorized them.
- Do not treat a missing readiness marker as silently ready. Infer, explain, and confirm with the user before implementation proceeds.
- Do not override `Design readiness: needs consensus` without user confirmation and an authorized design-source update.
- Do not leave meaningful deferred questions only in chat, model memory, or an unpersisted report.
- Do not formally depend on non-Core or current-machine skills.

## Workflow Phases

1. Establish the target.
   Identify the implementation request, issue, PRD, design doc, PR, branch, or local plan. Apply the playbook's trigger scope and exemptions. If exempt, return `Gate Skipped` with the reason.

2. Locate the durable design source.
   Prefer the linked GitHub issue, PRD, ADR, local design doc, or planning note named by the request or repository. For PR review work, inspect the linked issue, PR body, and any referenced design source. If only chat context exists, the verdict is `Needs Design Consensus` until that context is promoted into a durable artifact.

3. Check readiness.
   Evaluate the source against the playbook's design-source standard and readiness-marker rules. Content wins over the marker.

4. Confirm unmarked inference.
   If the source lacks `Design readiness:`, infer readiness from the content. Tell the user the inferred verdict, reasons, implementation boundary, and marker or edit you plan to make. Wait for confirmation before implementation proceeds. If edits are authorized, add or propose the marker after confirmation.

5. Handle open questions.
   Classify open questions as blocking or deferred using the playbook's rules. If a design-interview workflow such as `grill-me`, `grill-with-docs`, or an equivalent is available, use it to resolve blocking questions; otherwise ask targeted questions directly. Ask before GitHub issue creation or updates unless tracker writes were explicitly authorized. If GitHub writes are not authorized, create or propose the local artifact destination named by the playbook unless the project has a better convention or the user redirects. Update or propose updating the current design source with a `Deferred Follow-ups` section linking to created artifacts.

6. Report the verdict.
   Include the source reviewed, satisfied and missing readiness fields, implementation boundary, non-goals, created or proposed follow-up artifacts, and whether external writes happened, were proposed, or were skipped.

## Filing Rules

- Follow the implementation-readiness playbook for follow-up artifact destinations.
- Approved GitHub issue updates and follow-up issues stay in GitHub.
- Private or personal design notes belong in the Personal Overlay.
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

1. Confirm the playbook was read for the policy.
2. Confirm the target was correctly classified as gated or exempt.
3. Confirm the verdict is `Ready to Implement`, `Needs Design Consensus`, or `Gate Skipped`.
4. Confirm the design source's marker and content were both checked.
5. Confirm unmarked readiness was not silently accepted.
6. Confirm deferred follow-up artifacts were created or proposed where required.
7. Confirm external tracker writes were approved before they happened.
8. If this skill or its manifest entry changed, run `python3 os/verification/scripts/validate_agentos.py`.
