# Implement Features

Status: implementation readiness policy v1.

Use this playbook before implementing feature-sized AgentOS or mapped-project work. The goal is to keep agents from coding before the design source is durable, complete, and ready for the requested scope.

For the callable workflow, use `os/skills/check-implementation-readiness/SKILL.md`. This playbook is the canonical policy; the skill runs the gate.

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

## Design Source

A feature-sized implementation needs a durable design source before coding begins. Acceptable design sources include GitHub issues, PRDs, local Markdown design documents, ADRs, planning notes, or clearly referenced conversation artifacts that have been promoted into durable form.

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
- design readiness marker.

Exact headings are not required when the content is clear, but agents should recommend normalizing messy design sources into this shape before implementation.

## Readiness Marker

Use a lightweight marker in durable design sources:

```md
Design readiness: ready to implement
```

or:

```md
Design readiness: needs consensus
```

Content wins over the marker. A source with `Design readiness: ready to implement` but missing core design information still needs consensus. A source marked `needs consensus` should not be silently overridden.

If a durable design source has no marker, infer readiness from the content and confirm the inference with the user before implementation proceeds. If the user confirms and edits are authorized, add the marker.

If no durable design source exists, the verdict is `Needs Design Consensus`.

## Verdicts

The readiness gate has exactly three verdicts.

### Ready to Implement

Use this when the design is complete for the current implementation scope. The implementing agent may proceed only within the behavior, boundaries, and validation plan the human agreed to.

Meaningful open questions must be explicitly out of scope and captured in durable follow-up artifacts before coding begins. Related deferred questions can be grouped into one follow-up artifact when they belong to the same future decision area. Do not require one artifact per question.

### Needs Design Consensus

Use this when the design source is missing, not durable, marked as needing consensus, lacks a chosen design, lacks non-goals, lacks acceptance criteria, has blocking open questions, or leaves a scope boundary unclear enough that implementation could drift.

Resolve this by asking targeted questions, updating the durable design source, and creating any needed follow-up artifacts before coding begins.

When a design-interview workflow is available and useful for resolving blocking questions, use it. Popular harness-provided examples include `grill-me` and `grill-with-docs` when present. These are conveniences, not Core requirements; targeted questions are the portable fallback.

### Gate Skipped

Use this when the work is small, mechanical, or obvious enough to be exempt from the gate. Record why the gate was skipped so future agents can distinguish intentional bypass from omission.

## Deferred Follow-ups

Do not leave meaningful deferred questions only in chat, model memory, an unpersisted report, or an agent's working context.

If deferred questions are meaningful but out of scope for the current implementation, create durable follow-up artifacts before marking the current scope ready. Use the narrowest appropriate destination:

- GitHub issue when the design source is a tracker issue and tracker writes are authorized;
- local project design doc, usually `docs/design/issue-<number>-implementation-readiness.md`, when GitHub writes are not authorized or the user chooses local docs;
- mapped project docs when the implementation belongs to another project with an existing design-doc convention;
- Personal Overlay when the deferred question is private or personal.

After creating follow-up artifacts, update or propose updating the current design source with a short `Deferred Follow-ups` section that links to them. Only then mark the current implementation scope ready.

## GitHub And External Writes

Before updating or creating GitHub issues, comments, labels, or other tracker state, ask the user unless the current request explicitly authorized tracker writes. If the user declines a GitHub update, create local documentation or the destination the user chooses.

Follow `os/playbook/GITHUB_WORKFLOW.md` for issue and PR writing conventions, branch discipline, and external tracker safety.

## Review-loop Preflight

Review-loop workflows should run the same readiness gate before spawning reviewers.

Proceed only when a durable PR design source has `Design readiness: ready to implement` and still satisfies the design-source standard for the PR scope. Content wins over the marker.

If a durable design source exists but has no readiness marker, infer readiness from durable evidence such as the issue, PR body, or local design doc, then confirm with the user before proceeding.

If only chat or a current user request exists, treat the review target as `Needs Design Consensus` until the design is promoted into a durable source, unless the user explicitly chooses to bypass the gate.

If the user proceeds despite missing or incomplete readiness, record the bypass in the review-loop ledger and final report.

If the loop later detects design creep, treat the bypass as evidence that the PR may need redesign rather than more local fixes.

## Completion Check

Before implementing feature-sized work, confirm:

1. A durable design source exists, or the gate was explicitly skipped.
2. The source has enough problem, design, scope, acceptance, and validation detail for the current implementation.
3. The readiness marker is present, or the inferred readiness was confirmed with the user.
4. Meaningful deferred questions are out of scope and captured in durable follow-up artifacts.
5. The current design source links to those follow-up artifacts when they exist.
6. External tracker writes were approved before they happened.
