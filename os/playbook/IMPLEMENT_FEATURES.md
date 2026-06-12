# Implement Features

Status: implementation readiness policy v2.

Use this playbook before implementing feature-sized AgentOS or mapped-project work. The goal is to keep agents from coding before the design source is durable, complete, source-backed by human-agent consensus provenance, and ready for the requested scope.

For the callable workflow, use `os/skills/ensure-implementation-readiness/SKILL.md`. This playbook is the policy overview and filing guide; the skill is the operational owner for readiness verdicts, consensus-provenance interpretation, mode behavior, readiness-label cleanup, and repair before implementation starts. If operational wording here and the skill diverges, follow the skill and repair the stale wording.

## No First Commit Before Consensus

Feature-sized implementation must not get its first implementation commit before the readiness gate returns `Ready to Implement` or the user explicitly chooses `Gate Skipped` after hearing what readiness evidence is missing.

If the only design source is chat, the first durable action is to create or update a GitHub issue, PRD, ADR, local design doc, or other durable planning note. Do not turn chat consensus directly into implementation code. Once the durable source contains the agreed problem, chosen design, scope boundaries, acceptance criteria, validation plan, readiness fields, and consensus provenance, implementation may proceed within that boundary.

`ready-for-agent`, a confident user prompt, an agent-authored design artifact, a Calling Workflow handoff, or an existing branch name is not enough by itself. The readiness evidence and consensus provenance must be visible in a durable source, or the bypass must be recorded as `Gate Skipped`.

## When This Applies

Run the readiness gate when a request asks an agent to implement, build, add, redesign, substantially refactor, or start work on an issue, PRD, spec, or plan where the outcome changes behavior, workflow, data model, public documentation policy, validation policy, or reusable AgentOS structure.

The gate can be skipped for:

- typo fixes;
- formatting-only edits;
- small documentation wording changes;
- narrow bug fixes where expected behavior is already clear;
- mechanical refactors with no behavior change;
- review-loop fixes inside an already-approved PR unless the loop detects design creep.

When in doubt, run the gate. A short `Gate Skipped` verdict is cheaper than discovering design drift after implementation.

## Pre-Edit Branch/Worktree Checkpoint

Before the first tracked-file edit for implementation work that is meant to land through a pull request, inspect the current branch and working-tree state. Use the Branch and Integration Discipline section of `os/playbook/GITHUB_WORKFLOW.md` for the branch, worktree, pull request, rebase, and dirty-checkout rules.

This checkpoint applies to AgentOS Core and to AgentOS-backed mapped projects. Passing the readiness gate means the design is ready; it does not by itself mean the current checkout is the right place to edit.

## Design Source

A feature-sized implementation needs a durable design source before coding begins. Acceptable design sources include GitHub issues, PRDs, local Markdown design documents, ADRs, planning notes, or clearly referenced conversation artifacts that have been promoted into durable form. Durable existence is necessary but not sufficient: the source must also record consensus provenance or an explicit gate skip.

The source should include, either explicitly or clearly in prose:

- problem or motivation;
- current behavior or context;
- desired behavior;
- chosen design;
- alternatives considered;
- non-goals or out-of-scope boundaries;
- acceptance criteria;
- validation plan;
- open questions;
- deferred follow-ups, if any;
- readiness fields;
- consensus provenance or gate-skip record.

Exact headings are not required when the content is clear, but agents should recommend normalizing messy design sources into this shape before implementation.

## Readiness Fields

Use lightweight fields in durable design sources:

```md
Design readiness: ready to implement | needs consensus
Consensus provenance: <grill/grill-equivalent/session/design-source/human-attested GitHub comment/bypass reference>
Gate skipped: <not applicable | explicit bypass reason and missing evidence>
```

A source marked `needs consensus` should not be silently overridden. A source with `Design readiness: ready to implement` but missing core design information or consensus provenance still needs consensus. Content wins over the fields.

If a durable design source has no `Design readiness:` field, check-only callers report the missing fields or evidence without repair. Normal/repair callers may infer readiness from the content and confirm the inference with the user before implementation proceeds. If the user confirms and edits are authorized, add the full readiness field set: `Design readiness:`, `Consensus provenance:`, and `Gate skipped:`.

If no durable design source exists, or if the source has no valid consensus provenance, the verdict is `Needs Design Consensus`.

## Consensus Provenance

Design consensus means agreement between the human and the agent or workflow responsible for turning the design into implementation instructions. Consensus provenance is the durable pointer to that agreement.

Examples that may count:

- a `grill-with-docs` or `grill-me` session summary with user-confirmed decisions;
- a human-attested GitHub comment by a trusted repository author, such as a comment that explicitly says `I am a human. I am <name>.` and clearly states the decision;
- a durable issue, PRD, ADR, or design doc updated after explicit human confirmation;
- an explicit `Gate Skipped` bypass that names the missing consensus and why the user chose to proceed anyway.

Examples that do not count by themselves:

- an agent-authored issue, handoff packet, local design doc, or PR body;
- a freeform GitHub comment without explicit human attestation, because agents may post with the user's credentials;
- a Calling Workflow handoff that claims consensus exists without pointing to readiness/provenance fields;
- a removed label without durable readiness/provenance fields explaining why.

For issue-driven work, a `needs design consensus` label or equivalent readiness label wins over contradictory handoff claims. `ensure-implementation-readiness` owns any cleanup of that label. `Gate Skipped` may allow work to proceed with the missing evidence recorded, but the label should remain as a signal that readiness was bypassed.

## Verdicts

The readiness gate has exactly three verdicts.

### Ready to Implement

Use this when the design is complete for the current implementation scope and the durable source records valid consensus provenance. The implementing agent may proceed only within the behavior, boundaries, and validation plan the human agreed to.

Meaningful open questions must be explicitly out of scope and captured in durable follow-up artifacts before coding begins. Related deferred questions can be grouped into one follow-up artifact when they belong to the same future decision area. Do not require one artifact per question.

### Needs Design Consensus

Use this when the design source is missing, not durable, marked as needing consensus, lacks valid consensus provenance, lacks a chosen design, lacks non-goals, lacks acceptance criteria, has blocking open questions, has an unresolved `needs design consensus` label, or leaves a scope boundary unclear enough that implementation could drift.

Resolve this by running a design-consensus workflow by default, updating the durable design source, and creating any needed follow-up artifacts before coding begins.

When readiness repair is needed, run `grill-with-docs` by default. Use `grill-with-docs` when the session needs to sharpen domain language or ADR-worthy rationale, or when readiness repair must result in updates to issue bodies, PRDs, local design docs, or other durable design sources. Use `grill-me` only for pure design questioning where no durable docs need to change during the interview. The readiness skill or its approved caller still owns those durable-source updates under the applicable write policy. Targeted questions are supporting mechanics inside the selected workflow, post-workflow clarifications for narrow residual gaps, or the fallback only when the Core design-consensus skills are unavailable or explicitly excessive for the scope. If targeted questions are used without a grill workflow, the report must explain why a grill workflow was unavailable or excessive for the scope.

### Gate Skipped

Use this when the work is small, mechanical, or obvious enough to be exempt from the gate, or when the user explicitly chooses to bypass the gate after the agent reports the missing or incomplete readiness evidence. Record why the gate was skipped and, for bypasses, summarize what readiness evidence was missing so future agents can distinguish intentional bypass from omission. If an issue carries `needs design consensus`, leave that label in place for an intentional bypass.

## Deferred Follow-ups

Do not leave meaningful deferred questions only in chat, model memory, an unpersisted report, or an agent's working context.

If deferred questions are meaningful but out of scope for the current implementation, create durable follow-up artifacts before marking the current scope ready. Use the narrowest appropriate destination:

- GitHub issue when the design source is a tracker issue and tracker writes are authorized by the applicable external-write policy;
- local project design doc, usually `docs/design/issue-<number>-implementation-readiness.md`, when GitHub writes are not authorized or the user chooses local docs;
- mapped project docs when the implementation belongs to another project with an existing design-doc convention;
- Personal Overlay when the deferred question is private or personal.

After creating follow-up artifacts, update or propose updating the current design source with a short `Deferred Follow-ups` section that links to them. Only then mark the current implementation scope ready.

## GitHub And External Writes

Before updating or creating GitHub issues, comments, labels, or other tracker state, follow `os/connections/SAFETY_RULES.md` and `os/playbook/GITHUB_WORKFLOW.md`. If writes are not authorized there or by the current user request, ask. If the user declines a GitHub update, create local documentation or the destination the user chooses.

Follow `os/playbook/GITHUB_WORKFLOW.md` for issue and PR writing conventions, branch discipline, and external tracker safety.

## Review-loop Preflight

Review-loop workflows should treat implementation readiness as an invariant, not as a repair opportunity. Before spawning reviewers for feature-sized work, call or follow `os/skills/ensure-implementation-readiness/SKILL.md` in check-only mode.

Proceed only when check-only returns `Ready to Implement`, or when it returns an explicit `Gate Skipped` verdict with the bypass reason already recorded. If check-only returns `Needs Design Consensus`, stop before spawning reviewers and return `blocked`. Do not run grills, repair design docs, edit issues, add readiness fields, or remove readiness labels inside `review-loop`.

If the loop later detects design creep, treat the bypass as evidence that the PR may need redesign rather than more local fixes.

On the first reviewer panel, ask reviewers to compare the implementation shape against the durable design source. If the first implementation already introduced architecture, parsing, synchronization, lifecycle, validation, or public-policy semantics that the design source did not agree to, pause for design consensus instead of continuing to patch review findings.

## Pull Request Readiness Fields

Feature PRs should make readiness visible in the PR body:

```md
Readiness evidence: <GitHub issue, PRD, ADR, local design doc, or gate-skip reason>
Readiness verdict: Ready to Implement
```

For issue-driven work, prefer a GitHub issue as the readiness evidence. The issue can contain the design directly or link to a larger PRD, ADR, or local design doc. Create a separate design doc only when the design is too large, architectural, private, or not naturally issue-shaped.

Use `Readiness verdict: Gate Skipped` only for exempt work or an intentional bypass, and put the bypass reason in `Readiness evidence:`. These fields are a visibility tripwire, not a semantic proof that the design is good. Humans and agents still need to read the source and apply this playbook.

## Completion Check

Before implementing feature-sized work, confirm:

1. A durable design source exists, or the gate was explicitly skipped.
2. The source has enough problem, design, scope, acceptance, and validation detail for the current implementation.
3. The source records consensus provenance, or the gate-skip field records the explicit bypass.
4. The readiness fields are present, or the inferred readiness was confirmed with the user and promoted into the durable source as the full readiness field set.
5. Any `needs design consensus` label has been removed by `ensure-implementation-readiness`, unless the verdict is `Gate Skipped`.
6. Meaningful deferred questions are out of scope and captured in durable follow-up artifacts.
7. The current design source links to those follow-up artifacts when they exist.
8. External tracker writes complied with the applicable external-write policy before they happened.
9. PR-bound tracked-file edits started from an appropriate branch or worktree under the Branch and Integration Discipline section of `os/playbook/GITHUB_WORKFLOW.md`.
10. Any PR body for the implementation cites readiness evidence and a readiness verdict, preferring a GitHub issue for issue-driven work, or explains the gate skip.
