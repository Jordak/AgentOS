# Contract-Based Orchestration Loops

Design readiness: ready to implement

AgentOS should compose loop-shaped skills through workflow contracts and invocation-scoped boundaries, not through a hardcoded parent/child hierarchy or one giant orchestrator.

Issue #121 defines the detailed loop composition convention in `docs/design/issue-121-loop-composition-conventions.md`. This ADR records the core architecture decision behind that design.

## Context

AgentOS already has loop-shaped and panel-shaped skills such as `review-loop` and `review-pass`. More loops are planned, including a single-GitHub-issue implementation loop and a later issue-selection loop that may coordinate parallel workers.

A naive design would make the outermost loop own every decision and mutation. That would simplify one direction of control, but it would make existing skills less reusable and would force each larger loop to learn the internals of every workflow it calls.

Another naive design would let called workflows freely expand their scope when they discover useful next actions. That would preserve local autonomy, but it would make nested loops hard to reason about and could silently widen external-write authority.

AgentOS needs a middle path: reusable workflows should keep their own contracts, while calling workflows remain responsible for the broader target they are coordinating.

## Decision

AgentOS composes loop-shaped skills through contracts and invocation-scoped boundaries.

An Orchestration Loop is a workflow kind. Calling Workflow and Called Workflow are invocation roles, not permanent classifications. A workflow can be an Orchestration Loop and also be a Called Workflow in a larger invocation.

A Called Workflow's contract is its default Authorization Boundary. A Calling Workflow may narrow that boundary, such as invoking a mutating workflow in advisory mode. It may widen the boundary only when the wider scope is supported by the Called Workflow contract and explicitly allowed by policy and user authorization.

A Called Workflow should not upgrade itself beyond its current Authorization Boundary. When it discovers that broader work is needed, it should return a Workflow Result with evidence, risks, and any Blocking Human Decision. The Calling Workflow decides whether to widen the boundary, call another workflow, or stop.

Orchestration Loops preserve resumability through Recovery Records and Recovery Checkpoints. Recovery is a workflow obligation, not necessarily a single file format.

Integration Ownership is contract-defined, not role-defined. A workflow should own integration of the largest explicit target fully inside its contract and Authorization Boundary. Broader parent targets remain owned by the workflow whose contract covers them.

## Consequences

Nested Orchestration Loops can call other Orchestration Loops without collapsing into a single controller. For example, a future issue-implementation loop may call `review-loop` while `review-loop` continues to own its normal PR-scoped review/fix behavior.

Existing workflow artifacts can become domain-specific Workflow Results instead of being renamed or flattened. For example, a `Review Packet` remains the native result artifact from `review-pass` while satisfying the generic Workflow Result convention.

The design requires workflows to be explicit about Authorization Boundaries, Recovery Records, Workflow Results, Blocking Human Decisions, and Integration Ownership when they are loop-shaped or mutating. Simple skills do not need to carry the full convention.

AgentOS keeps the full convention in a progressively discovered file at `os/skills/ORCHESTRATION_LOOPS.md` and links to it from a small `## Orchestration Loops` section in `os/skills/SKILL_CONTRACT.md`.

## Alternatives Considered

Make the outermost loop own all mutation and integration. This was rejected because it would make larger loops micromanage called workflows and would reduce the value of existing skill contracts.

Let called workflows expand their own authority whenever they discover useful next actions. This was rejected because it would make nested loops hard to recover, review, and authorize.

Build a single giant issue-to-merge orchestrator first. This was rejected because AgentOS already has useful smaller loops, and the safer path is to define composition conventions before building larger loops around them.

## Validation

The implementation for issue #121 should:

- create `os/skills/ORCHESTRATION_LOOPS.md`;
- add a small `## Orchestration Loops` section to `os/skills/SKILL_CONTRACT.md`;
- keep the detailed rationale in `docs/design/issue-121-loop-composition-conventions.md`;
- keep stable terminology in `DOMAIN.md`;
- avoid adding deterministic validators until the convention has matured.

Readiness evidence: `docs/design/issue-121-loop-composition-conventions.md` and GitHub issue #121

Readiness verdict: Ready to Implement
