# Implement Features

Status: implementation readiness policy v1.

Use this playbook before implementing feature-sized AgentOS or mapped-project work. The goal is to keep agents from coding before the design source is durable, complete, and ready for the requested scope.

For the callable workflow, use `os/skills/ensure-implementation-readiness/SKILL.md`. This playbook is the canonical policy; the skill runs the gate and, when requested, repairs missing design consensus before implementation starts.

## No First Commit Before Consensus

Feature-sized implementation must not get its first implementation commit before the readiness gate returns `Ready to Implement` or the user explicitly chooses `Gate Skipped` after hearing what readiness evidence is missing.

If the only design source is chat, the first durable action is to create or update a GitHub issue, PRD, ADR, local design doc, or other durable planning note. Do not turn chat consensus directly into implementation code. Once the durable source contains the agreed problem, chosen design, scope boundaries, acceptance criteria, validation plan, and readiness marker, implementation may proceed within that boundary.

`ready-for-agent`, a confident user prompt, or an existing branch name is not enough by itself. The readiness evidence must be visible in a durable source, or the bypass must be recorded as `Gate Skipped`.

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

Resolve this by asking targeted questions or routing through a design-consensus workflow, updating the durable design source, and creating any needed follow-up artifacts before coding begins.

When a design-consensus workflow is available and useful for resolving blocking questions, use it. Use `grill-me` for pure design questioning where no durable docs need to change during the interview. Use `grill-with-docs` when the session needs to update domain language, ADRs, issue bodies, PRDs, local design docs, or other durable design sources as decisions crystallize. These workflows are conveniences, not Core requirements; targeted questions are the portable fallback for simple missing information or unavailable design-loop skills.

### Gate Skipped

Use this when the work is small, mechanical, or obvious enough to be exempt from the gate, or when the user explicitly chooses to bypass the gate after the agent reports the missing or incomplete readiness evidence. Record why the gate was skipped and, for bypasses, summarize what readiness evidence was missing so future agents can distinguish intentional bypass from omission.

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

Review-loop workflows should run the same readiness gate before spawning reviewers.

Proceed only when a durable PR design source has `Design readiness: ready to implement` and still satisfies the design-source standard for the PR scope. Content wins over the marker.

If a durable design source exists but has no readiness marker, infer readiness from durable evidence such as the issue, PR body, or local design doc, then confirm with the user before proceeding.

If only chat or a current user request exists, treat the review target as `Needs Design Consensus` until the design is promoted into a durable source. If the user explicitly chooses to bypass the gate, record a `Gate Skipped` verdict with the bypass reason and missing-readiness summary.

If the user proceeds despite missing or incomplete readiness, record the `Gate Skipped` bypass in the review-loop ledger and final report.

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
3. The readiness marker is present, or the inferred readiness was confirmed with the user.
4. Meaningful deferred questions are out of scope and captured in durable follow-up artifacts.
5. The current design source links to those follow-up artifacts when they exist.
6. External tracker writes complied with the applicable external-write policy before they happened.
7. PR-bound tracked-file edits started from an appropriate branch or worktree under the Branch and Integration Discipline section of `os/playbook/GITHUB_WORKFLOW.md`.
8. Any PR body for the implementation cites readiness evidence and a readiness verdict, preferring a GitHub issue for issue-driven work, or explains the gate skip.
