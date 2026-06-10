# Orchestration Loops

Status: convention v1.

Use this convention when a skill or workflow coordinates repeated steps toward a convergence condition, delegates to other workflows, mutates project state over multiple phases, waits on human decisions, or needs to resume safely after interruption, compaction, or handoff.

Not every skill is an Orchestration Loop. Simple read-only skills and single-shot utilities can satisfy `os/skills/SKILL_CONTRACT.md` without carrying the full loop convention.

## Source Of Truth

This file is the progressively discovered Core convention for loop-shaped AgentOS skills.

Background and rationale live in:

- `docs/adr/0009-contract-based-orchestration-loops.md`
- `docs/design/issue-121-loop-composition-conventions.md`

Do not duplicate the whole rationale into each skill. Link here when a skill needs the convention.

## Core Principle

AgentOS composes loop-shaped skills through workflow contracts and invocation-scoped boundaries, not through a hardcoded parent/child hierarchy or one giant orchestrator.

A workflow can be an Orchestration Loop by kind while also being a Called Workflow in a larger invocation. For example, `review-loop` is an Orchestration Loop. When `implement-github-issue` invokes it, `review-loop` is also the Called Workflow for that invocation.

## Workflow Kind And Invocation Roles

An **Orchestration Loop** is a workflow kind: it coordinates repeated steps toward a convergence condition.

A **Calling Workflow** is the workflow that delegates work in a specific invocation.

A **Called Workflow** is the workflow being delegated to in a specific invocation.

Calling Workflow and Called Workflow are contextual invocation roles, not permanent classifications.

## Authorization Boundary

An **Authorization Boundary** is the effective mutation permission for a workflow invocation.

If a Calling Workflow provides no explicit Authorization Boundary, the Called Workflow's own contract is the default Authorization Boundary.

A Calling Workflow may narrow the Authorization Boundary, such as invoking an otherwise mutating workflow in advisory or read-only mode.

A Calling Workflow may widen the Authorization Boundary only when all of these are true:

- higher-priority policy allows the wider action;
- current user authorization allows it;
- connector, account, and repository rules allow it;
- the Called Workflow contract supports or explicitly accepts that wider mode.

A Called Workflow must not treat silence as authorization for actions outside its contract. When it discovers broader work is needed, it should return a Workflow Result with evidence, risks, and any Blocking Human Decision. The Calling Workflow decides whether to widen the boundary, call another workflow, or stop.

## Mutation Ownership

Mutation is owned by the workflow whose contract and Authorization Boundary explicitly include that mutation surface.

The Calling Workflow owns the broader run state, invocation boundary, and integration surfaces outside the Called Workflow's contract.

For example, `review-loop` may perform its normal PR-scoped mutations when invoked normally: fix commits on the target PR branch, consolidated Agent Review comments, and the repository's established ready-for-human marker. It still may not merge the PR, close issues, create labels, or push outside the target PR branch, because those surfaces are outside the `review-loop` contract.

If a Calling Workflow wants advisory evidence only, it should invoke a read-only mode or a narrower Called Workflow such as `review-pass`.

## Integration Ownership

**Integration Ownership** is the contract-defined responsibility to bring a workflow target to its completed, landed, closed, ready, or otherwise integrated state.

Integration Ownership is contract-defined, not role-defined. A Called Workflow may own integration of its own target when its contract and Authorization Boundary say so. A Calling Workflow may own a broader target that remains open after the Called Workflow completes.

As a directional principle, a workflow should own integration of the largest explicit target that is fully inside its contract and Authorization Boundary. It should not integrate broader parent targets merely because it completed a child target or can see the next tempting action.

When broader integration is needed, the workflow should return a Workflow Result with evidence and a recommended next action.

## Workflow Result

A **Workflow Result** is the return shape a Called Workflow provides to its Calling Workflow.

The Called Workflow may use a domain-specific result artifact, but the Calling Workflow must be able to extract the generic fields it needs to continue safely.

A Workflow Result should include:

- Called Workflow: name and invocation reference when available;
- status: a workflow-specific status such as `completed`, `blocked`, `failed`, `cancelled`, or `needs-human`;
- evidence: links, paths, commits, comments, reports, packets, verdicts, or other artifacts produced;
- mutations performed: local edits, commits, pushes, comments, labels, external writes, or `none`;
- validation: checks run and results;
- open risks or unresolved decisions: especially any Blocking Human Decision;
- recommended next action.

Domain-specific result artifacts should keep their names and richer structure. For example, a `Review Packet` remains the native result artifact from `review-pass` while satisfying this convention through its target, mode, reviewer coverage, issue families, verification results, residual risks, and reporting location.

Prefer Markdown-first, field-stable results. Use predictable labels such as `Status`, `Evidence`, `Mutations performed`, `Validation`, `Open risks`, and `Recommended next action` where possible. Do not introduce JSON, YAML, or a separate schema unless a script or validator genuinely needs deterministic parsing.

## Recovery Record

A **Recovery Record** is the minimum durable or reconstructable state needed to resume an Orchestration Loop safely after a pause, compaction, handoff, or Called Workflow completion.

A Recovery Record is a recoverability obligation, not necessarily a separate file format. A workflow may satisfy the obligation through GitHub issue comments, PR comments, branch state, commits, temporary reports, chat pause messages, design docs, local artifacts, or a dedicated record file when one is warranted.

For every mutating Orchestration Loop, the Recovery Record should preserve at least:

- target: the issue, PR, branch, repository, artifact, or task the loop is operating on;
- workflow invocation references: available references for the Calling Workflow and Called Workflows, including thread IDs, child-thread URLs, subagent handles, report paths, comment URLs, issue URLs, PR URLs, and commit SHAs when safe;
- authorization boundary: mutations and external writes allowed for this run, plus actions that still require approval;
- current phase: enough information to resume without guessing;
- blocking human decisions: exact question, recommended default, and decision state such as `unresolved`, `approved`, or `declined/accepted-risk`;
- Called Workflow results: links or summaries of returned evidence, reports, comments, commits, or verdicts;
- validation evidence: commands or checks run, result, and skipped validation with reason;
- next action: the next safe step.

Keep opaque runtime handles, private thread IDs, or harness-internal references out of public, publishable, or Git-backed checkpoint surfaces when they could expose private or irrelevant implementation details. Public issue comments, PR comments, design docs, commits, branch state, and reports should contain only public-safe stable references. Store private runtime references only on an authorized private surface, such as Personal Overlay orchestration state, or record that the stable reference is unavailable or redacted.

## Recovery Checkpoint

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

## Blocking Human Decision

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

## Parallel Called Workflows

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

Future worker handoff issues should define the detailed handoff shape for implementation workers. This file establishes the general loop composition convention.

## Existing Workflow Mapping

Existing AgentOS workflows keep their native contracts and artifacts:

- `review-loop` (`os/skills/review-loop/SKILL.md`) is an Orchestration Loop for PR-scoped review/fix convergence. It may own PR-scoped review mutations inside its contract, but it does not merge PRs or close issues.
- `review-pass` (`os/skills/review-pass/SKILL.md`) is a read-only Called Workflow shape. Its Review Packet can serve as a domain-specific Workflow Result.
- `ensure-implementation-readiness` (`os/skills/ensure-implementation-readiness/SKILL.md`) owns the feature-sized readiness gate and readiness-repair workflow, including durable design-source updates when authorized.
- `audit-issues` (`os/skills/audit-issues/SKILL.md`) owns evidence-backed issue tracker reconciliation after integration evidence exists.
- `os/playbook/GITHUB_WORKFLOW.md` owns repository branch, PR, external-write, and issue-closure discipline.

Link to these contracts rather than copying their rules into every new loop.

## Skill Contract Guidance

When a skill is an Orchestration Loop or can be invoked by one, its skill contract or manifest entry should make the relevant boundaries clear:

- whether it is read-only, mutating, or mode-dependent;
- what target it owns;
- what external writes require additional approval;
- what it may call;
- what Workflow Result it returns;
- what Recovery Record or Recovery Checkpoint it maintains;
- what Integration Ownership, if any, belongs to the skill.

Keep this proportional. A small read-only helper does not need loop-specific boilerplate.

## Validation

Before changing this convention or a loop-shaped skill that depends on it:

1. Run `scripts/run-validator`.
2. Run `git diff --check`.
3. Inspect affected skill contracts or manifest entries for clear Authorization Boundaries, Workflow Results, Recovery Records, and Integration Ownership where relevant.
4. Keep deterministic validators shallow and objective until the convention matures enough to enforce mechanically.
