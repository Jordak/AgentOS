# Issue 121 Loop Composition Conventions

Design readiness: ready to implement

## Problem

AgentOS has strong individual skills such as `ensure-implementation-readiness`, `review-loop`, `review-pass`, `audit-issues`, and GitHub workflow playbooks. As of this design being written, AgentOS does not yet have shared conventions for composing those skills into nested control loops.

The immediate goal is to define the conventions that future loop-shaped skills can reuse, starting with a single-GitHub-issue implementation loop and later an outer issue-selection and parallel-worker loop.

## Working Decisions

### Design source shape

Use this design doc as the working design source for GitHub issue #121.

Create a separate ADR only if the grill session settles a hard-to-reverse architecture rule that future readers need to understand independently, such as ownership of mutation and durable loop state across calling and called workflows.

Update `DOMAIN.md` only for stable domain-language terms that should become part of the AgentOS glossary, not for implementation-specific checklist details.

The #121 implementation should include one short ADR. The ADR should capture the architecture decision to compose loop-shaped skills through contracts, Authorization Boundaries, Workflow Results, Recovery Records, Recovery Checkpoints, and contract-defined Integration Ownership instead of through a hardcoded parent/child hierarchy or one giant orchestrator. This design doc remains the detailed issue-specific source.

The ADR path should be `docs/adr/0009-contract-based-orchestration-loops.md`, titled **Contract-Based Orchestration Loops**.

The decision should state that AgentOS composes loop-shaped skills through workflow contracts and invocation-scoped boundaries. A Called Workflow's contract is its default Authorization Boundary; Calling Workflows may narrow or explicitly widen that boundary only under policy and user authorization. Orchestration Loops preserve resumability through Recovery Records and Recovery Checkpoints, and Integration Ownership is defined by each workflow contract rather than by calling/called role.

### Final filing shape

Do not bloat `os/skills/SKILL_CONTRACT.md` with full Orchestration Loop conventions, because not every skill is loop-shaped.

Create a separate progressively discovered Core convention file at `os/skills/ORCHESTRATION_LOOPS.md`. Add only a small dedicated `## Orchestration Loops` section to `os/skills/SKILL_CONTRACT.md` so loop-shaped skills know where to find the detailed convention.

Keep `DOMAIN.md` limited to stable glossary terms. Keep this design doc as the issue-specific rationale and readiness source. Update existing skills only where they need to declare how they satisfy or relate to the convention.

Use minimal propagation for the #121 implementation. In scope: create `os/skills/ORCHESTRATION_LOOPS.md`, add the small `## Orchestration Loops` link section to `os/skills/SKILL_CONTRACT.md`, update `DOMAIN.md`, and add only narrow cross-references to `review-loop` and `review-pass` if needed to show how existing artifacts map to Workflow Results. Out of scope: rewriting existing skills, changing report templates, adding broad validators, or implementing new issue loops.

### Workflow kind versus invocation role

Separate what a workflow is from the role it plays in one invocation.

An **Orchestration Loop** is a workflow kind: it coordinates repeated steps toward a convergence condition. A workflow can be an Orchestration Loop even when another workflow calls it.

A **Calling Workflow** is the workflow that delegates work in a specific invocation. A **Called Workflow** is the workflow being delegated to in that invocation. These are contextual roles, not permanent classifications.

For example, `review-loop` is an Orchestration Loop by kind. When `implement-github-issue-loop` invokes it, `review-loop` is also the Called Workflow for that invocation. When `review-loop` invokes `review-pass`, `review-loop` is the Calling Workflow and `review-pass` is the Called Workflow.

### Mutation ownership

Mutation is owned by the Called Workflow for the surfaces explicitly inside its contract. The Calling Workflow owns the broader run state, invocation boundary, and any integration surface outside the Called Workflow's contract.

For example, `implement-github-issue-loop` may invoke `review-loop` and allow `review-loop` to perform its normal PR-scoped mutations: fix commits on the target PR branch, consolidated Agent Review comments, and the repository's established ready-for-human marker. `review-loop` still may not merge the PR, close issues, create labels, or push outside the target PR branch, because those surfaces are outside the `review-loop` contract.

If a Calling Workflow wants only advisory evidence, it should invoke a read-only mode or a narrower Called Workflow such as `review-pass`.

### Authorization boundaries

An **Authorization Boundary** is the effective mutation permission for a workflow invocation.

If the Calling Workflow provides no explicit Authorization Boundary, the Called Workflow's own contract is the default Authorization Boundary. The Calling Workflow may narrow the Authorization Boundary, such as invoking an otherwise mutating workflow in advisory or read-only mode. The Calling Workflow may widen the Authorization Boundary only when the wider scope is allowed by higher-priority policy, current user authorization, connector/account rules, repository rules, and the Called Workflow contract supports or explicitly accepts that wider mode.

A Called Workflow must not treat silence as authorization for actions outside its contract.

For example, `review-loop` keeps its default PR-scoped writes when called normally: fix commits to the target PR branch, consolidated Agent Review comments, and the repository's established ready-for-human marker. A Calling Workflow may narrow that to review-only behavior. It may not silently grant `review-loop` permission to merge or close issues, because those actions are outside the `review-loop` contract.

A Called Workflow should not upgrade itself beyond its current Authorization Boundary. When it discovers that broader work is needed, it should return a Workflow Result with a Blocking Human Decision or recommended next action. The Calling Workflow decides whether to widen the Authorization Boundary, call another workflow, or stop. A Called Workflow may ask for escalation only when its own contract explicitly includes that escalation mode.

### Recovery records

A **Recovery Record** is the minimum durable or reconstructable state a Calling Workflow needs to resume safely after a pause, compaction, handoff, or Called Workflow completion.

A Recovery Record is a recoverability obligation, not necessarily a separate file format. A workflow may satisfy the obligation through GitHub issue comments, PR comments, branch state, commits, temporary reports, chat pause messages, design docs, local artifacts, or a dedicated record file when the workflow needs one.

The convention should define what must be recoverable. Each Orchestration Loop should choose the narrowest storage mechanism that fits its mutability, privacy, and reporting surface.

For every mutating Orchestration Loop, the Recovery Record should preserve at least:

- target: the issue, PR, branch, repository, artifact, or task the loop is operating on;
- workflow invocation references: available references for the Calling Workflow and Called Workflows, including thread IDs, child-thread URLs, subagent handles, report paths, comment URLs, issue URLs, PR URLs, and commit SHAs when safe;
- authorization boundary: mutations and external writes allowed for this run, plus actions that still require approval;
- current phase: enough information to resume without guessing;
- blocking human decisions: exact question, recommended default, and decision state such as `unresolved`, `approved`, or `declined/accepted-risk`;
- Called Workflow results: links or summaries of returned evidence, reports, comments, commits, or verdicts;
- validation evidence: commands or checks run, result, and skipped validation with reason;
- next action: the next safe step.

Opaque runtime handles, private thread IDs, or harness-internal references should be kept out of public, publishable, or Git-backed checkpoint surfaces when they could expose private or irrelevant implementation details. Public issue comments, PR comments, design docs, commits, branch state, and reports should contain only public-safe stable references. Store private runtime references only on an authorized private surface, such as Personal Overlay orchestration state, or record that the stable reference is unavailable or redacted.

### Blocking human decisions

A **Blocking Human Decision** is a human decision that must be resolved before an Orchestration Loop can safely continue along its current path.

A Blocking Human Decision should record:

- decision needed: the exact question the human must answer;
- why now: what would become unsafe, ambiguous, or scope-expanding without the decision;
- recommended default: what the Calling Workflow recommends;
- allowed outcomes: the choices the loop can safely handle, usually `approved`, `declined/accepted-risk`, or `redirected`;
- decision state: `unresolved` until the human answers;
- recovery location: where the decision is checkpointed;
- resume rule: what the workflow should do after each allowed outcome.

`HITL` remains useful as an issue planning label, but workflow contracts should use Blocking Human Decision when naming a concrete decision that blocks loop progress.

### Workflow results

A **Workflow Result** is the return shape a Called Workflow provides to its Calling Workflow. The Called Workflow may use a domain-specific result artifact, but the Calling Workflow must be able to extract the generic Workflow Result fields it needs to continue safely.

A Workflow Result should include:

- Called Workflow: name and invocation reference when available;
- status: a workflow-specific status such as `completed`, `blocked`, `failed`, `cancelled`, or `needs-human`;
- evidence: links, paths, commits, comments, reports, packets, verdicts, or other artifacts produced;
- mutations performed: local edits, commits, pushes, comments, labels, external writes, or `none`;
- validation: checks run and results;
- open risks or unresolved decisions: especially any Blocking Human Decision;
- recommended next action.

Domain-specific result artifacts should keep their names and richer structure. For example, a `Review Packet` is the Workflow Result produced by `review-pass`. It satisfies the generic Workflow Result convention through its target, mode, reviewer coverage, issue families, verification results, residual risks, and reporting location. A future `review-loop` final report or result summary can likewise serve as the Workflow Result for `review-loop` when it is called by `implement-github-issue-loop`.

Workflow Results should be Markdown-first and field-stable by default. Called Workflows should use predictable labels such as `Status`, `Evidence`, `Mutations performed`, `Validation`, `Open risks`, and `Recommended next action` where possible, but should not introduce JSON, YAML, or a separate schema unless a script or validator genuinely needs deterministic parsing.

The Called Workflow returns evidence and status. The Calling Workflow decides what that result means for the broader Orchestration Loop.

### Parallel called workflows

Parallel Called Workflows require an **Isolation Boundary**.

An Isolation Boundary is the scope that lets a Calling Workflow run Called Workflows concurrently without uncoordinated mutation of the same surface. It does not have to be precise source-file ownership. Valid Isolation Boundaries can include an issue or task, branch and worktree, PR, artifact, domain or module area when clear, read-only exploration lane, or an explicit non-overlap assumption paired with a coordinator-owned conflict-resolution phase.

For each parallel Called Workflow, the Calling Workflow should provide:

- an Isolation Boundary;
- an explicit Authorization Boundary;
- a Workflow Invocation Reference;
- an expected Workflow Result;
- a Recovery Checkpoint before launch;
- a coordinator-owned integration or conflict-resolution step after results return.

Parallel Called Workflows must not share an uncoordinated mutable surface. They should not share the same working tree, index, branch, issue-body edit, PR comment stream, or other mutation surface unless the Calling Workflow has a designed coordination rule for that surface.

Future worker handoff issues should define the detailed handoff shape for implementation workers. This design only establishes the general loop composition convention.

### Integration ownership

**Integration Ownership** is the contract-defined responsibility to bring a workflow target to its completed, landed, closed, ready, or otherwise integrated state.

Integration Ownership is contract-defined, not role-defined. A Called Workflow may own integration of its own target when its contract and Authorization Boundary say so. A Calling Workflow may own a broader target that remains open after the Called Workflow completes.

As a directional principle, a workflow should own integration of the largest explicit target that is fully inside its contract and Authorization Boundary. It should not integrate broader parent targets merely because it completed a child target or can see the next tempting action. When broader integration is needed, it should return a Workflow Result with evidence and a recommended next action.

For example, a future `implement-github-issue-loop` may own integration of its target implementation issue after landing semantics are designed. A PRD-level loop may call multiple issue loops and own integration of the parent PRD only after the child issues are integrated. `review-loop` does not merge today because its contract targets review convergence, not landing.

### Recovery checkpointing

A **Recovery Checkpoint** is a durable write or update that preserves the current Recovery Record, or enough of it to resume safely from the checkpointed phase.

A mutating Orchestration Loop must create or update a Recovery Checkpoint on an authorized durable surface before any recovery boundary where losing context would make resumption unsafe.

Recovery boundaries include:

- yielding to the user for a human decision;
- starting, waiting on, or resuming a Called Workflow that may outlive the current context;
- performing external writes;
- spawning parallel workers;
- ending a turn with loop work incomplete;
- handing off to another thread, agent, or workflow.

The checkpoint surface can be an existing durable surface such as a GitHub issue comment, PR comment, design doc, final report, branch commit, or local artifact. Public, publishable, or Git-backed checkpoint surfaces must use only public-safe Recovery Record fields. Private runtime handles belong in an authorized private surface or should be redacted with an explicit limitation. If no authorized durable surface exists, the loop should ask for permission to create or update one, include the public-safe Recovery Record fields in the user-facing pause message as a best-effort fallback, or stop before doing work that would become unsafe to resume.

## Open Design Questions

- Which Recovery Record fields should be optional, mode-specific, or public-safe only?
- Which existing result artifacts should explicitly declare that they satisfy the Workflow Result convention?
- Which parallel worker details belong in the future worker handoff design rather than this composition convention?
- Which existing skill contracts should be updated to declare their Integration Ownership explicitly?
- What belongs in Core skill contracts versus issue-specific design docs?
- Which parts of the convention should be enforced by validation fixtures, if any?

## Scope

In scope:

- Calling/called ownership conventions for nested AgentOS skills.
- Recoverable state conventions for mutating orchestration loops.
- HITL blocker representation and recovery.
- External-write and integration-boundary rules.
- Compatibility with `review-loop`, `review-pass`, `ensure-implementation-readiness`, `audit-issues`, and `os/playbook/GITHUB_WORKFLOW.md`.

Out of scope:

- Implementing `implement-github-issue-loop`.
- Implementing `select-next-issues-loop`.
- Creating subagent workers or parallel execution.
- Replacing the existing `review-loop` and `review-pass` contracts.
- Adding deterministic validators unless this design identifies narrow objective invariants worth checking.

## Validation Plan

- Run `scripts/run-validator`.
- Run `git diff --check`.
- Inspect the final design against GitHub issue #121 acceptance criteria.
- Inspect `DOMAIN.md` to ensure glossary additions stay domain-language, not implementation specification.
- Inspect `os/skills/ORCHESTRATION_LOOPS.md` to ensure it links to existing `review-loop`, `review-pass`, `ensure-implementation-readiness`, `audit-issues`, and `GITHUB_WORKFLOW` contracts rather than duplicating them.
- Do not add a deterministic validator in this slice; the convention is prose-shaped and should mature before scripts enforce it.

## PR Readiness Fields

```md
Readiness evidence: docs/design/issue-121-loop-composition-conventions.md and GitHub issue #121
Readiness verdict: Ready to Implement
```
