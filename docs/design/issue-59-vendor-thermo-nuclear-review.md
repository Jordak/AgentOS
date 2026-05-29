# Issue 59: Vendor Thermo Nuclear Review

Design readiness: ready to implement

## Problem

AgentOS currently vendors Cursor Thermos' strict maintainability rubric through `thermo-nuclear-code-quality-review`, but not the sibling `thermo-nuclear-review` skill for deep correctness, security, developer-experience, and feature-gate-leak review. That leaves the Thermos review family only partially available to AgentOS review workflows.

## Chosen Design

Vendor Cursor's `thermos/skills/thermo-nuclear-review/SKILL.md` into AgentOS Core as `os/skills/thermo-nuclear-review/SKILL.md`, with an `UPSTREAM.md` provenance file that records the Cursor repository, upstream path, pinned ref, local AgentOS patches, update procedure, and MIT license notice.

Adapt the upstream skill into the AgentOS skill contract while preserving the review rubric. Remove unsupported Cursor frontmatter such as `disable-model-invocation`; add AgentOS source, contract, mutability, safety, filing, and verification sections.

Expose the skill to review workflows through `review-pass` lens guidance rather than as an always-on nested workflow. Add a `deep-review` lens that draws from `thermo-nuclear-review`, and note in `review-loop` that Thermos review material should be used through `review-pass` lenses.

## Scope

In scope:

- Add the vendored Core skill and provenance.
- Update `os/skills/MANIFEST.md`.
- Wire `review-pass` and `review-loop` guidance to expose the new vendored review material through lenses.
- Sync the current-machine mirror after validation.

Out of scope:

- Vendoring the full Cursor `thermos` orchestrator.
- Vendoring Cursor subagent definitions as AgentOS agents.
- Making `review-loop` always run this review.
- Closing issue #59 before the resolving PR is reviewed and merged.

## Acceptance Criteria

- `os/skills/thermo-nuclear-review/SKILL.md` exists and validates as a Codex skill.
- `os/skills/thermo-nuclear-review/UPSTREAM.md` records upstream provenance and the MIT license.
- `os/skills/MANIFEST.md` includes the new skill and correct Core skill count.
- `review-pass` exposes a `deep-review` lens tied to the vendored skill.
- `review-loop` points callers to `review-pass` lenses instead of nesting the full workflow.
- The current-machine mirror for `thermo-nuclear-review` is in sync.

## Validation Plan

- Run Codex skill validation for `os/skills/thermo-nuclear-review`.
- Run `scripts/run-validator`.
- Run scoped `mirror-skills` audit/sync for `thermo-nuclear-review`.
- Run Codex skill validation for the mirrored skill.
- Run the vendored upstream freshness check when available.
