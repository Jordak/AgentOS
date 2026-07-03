# Orchestration Loops

Status: convention v1.

Use this convention when a skill or workflow coordinates repeated steps toward a convergence condition, delegates to other workflows, mutates project state over multiple phases, waits on human decisions, or needs to resume safely after interruption, compaction, or handoff.

Not every skill is an Orchestration Loop. Simple read-only skills and single-shot utilities can satisfy `os/skills/SKILL_CONTRACT.md` without carrying the full loop convention.

## Source Of Truth

This file is the progressively discovered Core convention for loop-shaped AgentOS skills.

Background and rationale live in:

- `docs/adr/0009-contract-based-orchestration-loops.md`
- `docs/adr/0011-callback-first-orchestration.md`
- `docs/adr/0012-agentos-workflow-effort-levels.md`
- `docs/design/issue-121-loop-composition-conventions.md`

Do not duplicate the whole rationale into each skill. Link here when a skill needs the convention.

## Core Principle

AgentOS composes loop-shaped skills through workflow contracts and invocation-scoped boundaries, not through a hardcoded parent/child hierarchy or one giant orchestrator.

A workflow can be an Orchestration Loop by kind while also being a Called Workflow in a larger invocation. For example, `review-loop` is an Orchestration Loop. When `implement-github-issue` invokes it, `review-loop` is also the Called Workflow for that invocation.

Durable Called Workflow execution is callback-first. A Calling Workflow should pass a callback thread id, invocation reference, ledger surface, issue or PR comment surface, or equivalent result target to the Called Workflow when the harness supports it. The Called Workflow reports its Workflow Result there when it completes, blocks, fails, is cancelled, or needs a human decision; the Calling Workflow does not continuously poll for progress as the normal control pattern.

## Workflow Kind And Invocation Roles

An **Orchestration Loop** is a workflow kind: it coordinates repeated steps toward a convergence condition.

A **Calling Workflow** is the workflow that delegates work in a specific invocation.

A **Called Workflow** is the workflow being delegated to in a specific invocation.

Calling Workflow and Called Workflow are contextual invocation roles, not permanent classifications.

## Callback-First Invocation

A **Workflow Invocation Reference** is the stable callback or coordination reference a Calling Workflow gives to a Called Workflow for one invocation. It may be a callback thread id, child-thread URL, coordinator ledger location, issue or PR comment surface, local report path, or another durable reference appropriate to the harness and Authorization Boundary.

When a Calling Workflow delegates durable work, it should include a Workflow Invocation Reference, expected Workflow Result shape, and explicit release instruction in the launch context. The release instruction says whether the Called Workflow should stop after returning its result, remain assigned for review corrections, or wait for a caller release signal.

A Called Workflow should return completion, blocked, failed, cancelled, and needs-human states through the invocation reference when the reference is available. After returning the result, it should stop or wait according to the release instruction. It should not assume the caller is watching the worker live.

Convention v1 standardizes callback result surfaces, terminal status vocabulary, and aggregate status selection for workflows that summarize mixed child outcomes. For workflows that aggregate child, worker, issue, PR, landing, batch-pass, or phase outcomes, the top-level `Status:` is the caller-facing control state selected by the Aggregate Status rule below, while an `Aggregate status map:` preserves the detailed child outcomes.

Runtime polling of Called Workflows is not the normal orchestration pattern. It is allowed only as bounded bootstrap, timeout, recovery, or diagnostic behavior. After callback setup is acknowledged or a called workflow is simply active, do not poll for ordinary progress; the Calling Workflow should record a waiting-for-callback state, stop its active turn, and record any later polling reason, bound, and result in its Recovery Record.

## Minimal Assignment Packets

Calling Workflows should send pointer-first assignment packets to Called Workflows. A packet should include only the invocation-specific facts needed to begin safely:

- target: issue, PR, branch, artifact, design source, or other durable task pointer;
- Workflow Invocation Reference and release instruction;
- Isolation Boundary and Authorization Boundary;
- workflow mode and owned scope;
- prescribed model/effort when the caller is overriding or confirming the workflow default, including prescription source, or an explicit no-override/default statement when that matters for recovery;
- required durable sources to read, such as local instructions, issue bodies, ADRs, playbooks, and skill contracts;
- validation and expected Workflow Result requirements;
- prohibited actions and escalation rules.

Do not copy whole skill contracts, playbooks, issue bodies, or batch ledgers into each launch message when stable pointers are sufficient. Workflow-specific handoff shapes belong in the workflow that owns the launch, while this convention keeps the reusable rule small.

## Effort Recommendations

An **Effort Recommendation** is the model-effort level a workflow would prefer for an invocation when the active harness supports such control. It is an invocation-level intention, not a guarantee that a live thread can switch effort repeatedly inside one turn.

A **Prescribed Effort** is the effort requested by a workflow default, Calling Workflow override, user instruction, custom-agent configuration, or platform default. An **Effective Effort** is the effort actually used when it is observable.

Calling Workflows may prescribe model and effort for a Called Workflow invocation when scope, risk, latency, cost, token budget, or review quality requires it. When the harness can create a separate run, thread, worker, subagent, custom agent, or model request for the Called Workflow, it should apply the prescribed effort there when supported by the selected model and harness.

When multiple skills run in one live thread and the harness cannot reliably switch effort mid-turn, the thread's current effort is the Effective Effort. The workflow should report Effective Effort source/status as inherited from the current thread, overridden, unsupported or degraded, unknown, or not reported, and separately record any meaningful prescribed/effective mismatch.

Explicit user budget, latency, cost, or quality instructions override AgentOS defaults. Platform limits, model support, custom-agent configuration, and harness runtime behavior may also override or constrain the prescribed value. Record those overrides when they matter for trust, validation, cost, recovery, or handoff.

Vendored upstream `SKILL.md` files should stay aligned with upstream. AgentOS-specific effort policy for vendored skills belongs in AgentOS-owned caller instructions, wrapper workflows, routing or manifest metadata when appropriate, or this reusable convention. Do not edit upstream-vendored skill bodies solely to add AgentOS effort policy.

### Effort Lookup

Use this table as the durable lookup home for initial AgentOS workflow effort recommendations. Future workflows should apply the assignment logic in `docs/adr/0012-agentos-workflow-effort-levels.md` and add rows here when a named workflow becomes part of the reusable orchestration surface.

| Workflow | Default effort | Escalation guidance |
| --- | --- | --- |
| `github-loop` | `medium` | Use `high` only when the same thread must perform substantial design or integration-risk adjudication. |
| `coordinate-issue-batch` | `medium` | Use `high` for unusually tangled dependency, safety, or human-decision states. |
| `implement-github-issue` | `high` | When true Called Workflow delegation is available, prescribe child workflow effort separately and report effective effort for each invocation. |
| `ensure-implementation-readiness` | `medium` | Use `high` when consensus is fuzzy, scope boundaries are ambiguous, or a design-consensus workflow is needed. |
| `grill-me` | `high` | Use `xhigh` only for unusually deep or high-stakes design work when budget allows. |
| `grill-with-docs` | `high` | Use `xhigh` only for hard architecture or cross-document tradeoffs when budget allows. |
| `review-pass` | `high` | Use `xhigh` for security, deep-review, final-gate, high-risk, difficult, or eval-justified review passes. |
| `review-loop` | `medium` | Use `high` for hard adjudication, design-escape-hatch calls, or same-thread orchestration and fix work after clean reviewer evidence; prescribe `review-pass` as `high` or selective `xhigh` when a separate review pass can honor it. |
| `select-issue-batch` | `medium` | Use `high` only when selection depends on unusually ambiguous dependency or parallel-safety reasoning. |
| `audit-issues` | `medium` | Use `high` only for broad, ambiguous, or high-impact reconciliation where evidence conflicts. |
| `land-github-issue` | `medium` | Use `high` only when acceptance criteria, integration proof, or human-review state is unusually ambiguous. |

### Reporting Effort

Workflow Results, Recovery Records, review packets, reports, or equivalent handoffs should include effort metadata when available and relevant:

- prescribed model and effort, if any;
- source of prescription: workflow default, Calling Workflow override, user instruction, custom-agent config, platform default, or unknown;
- Effective Effort and model actually used, when observable;
- effective source or status: explicit, inherited from current thread, platform-selected, custom-agent override, user override, unsupported or degraded, unknown, or not reported;
- any mismatch between prescribed and effective effort that matters for trust, validation, cost, or recovery.

Use `unknown` or `not reported` when the active harness does not expose exact metadata. Do not add deterministic enforcement before the convention has stable harness evidence.

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

The Calling Workflow owns the broader run state and invocation boundary. It owns integration surfaces outside the Called Workflow's contract only when the Calling Workflow's own contract and Authorization Boundary explicitly include those surfaces.

For example, `review-loop` may perform its normal PR-scoped mutations when invoked normally: fix commits on the target PR branch, consolidated Agent Review comments, and the repository's established ready-for-human marker. It still may not merge the PR, close issues, create labels, or push outside the target PR branch, because those surfaces are outside the `review-loop` contract.

If a Calling Workflow wants advisory evidence only, it should invoke a read-only mode or a narrower Called Workflow such as `review-pass`.

## Integration Ownership

**Integration Ownership** is the contract-defined responsibility to bring a workflow target to its completed, landed, closed, ready, or otherwise integrated state.

Integration Ownership is contract-defined, not role-defined. A Called Workflow may own integration of its own target when its contract and Authorization Boundary say so. A Calling Workflow may own a broader target that remains open after the Called Workflow completes.

As a directional principle, a workflow should own integration of the largest explicit target that is fully inside its contract and Authorization Boundary. It should not integrate broader parent targets merely because it completed a child target or can see the next tempting action.

Do not infer merge, closure, or branch-deletion authority from whether a workflow is currently acting as a Calling Workflow or a Called Workflow. Those actions belong only to workflows whose contracts explicitly own landing and closure. For example, `implement-github-issue` may be called by a future coordinator, but its contract still stops at reviewed PR evidence; the future coordinator may own landing only if its own contract says so.

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
- effort metadata when available and relevant, including Prescribed Effort, Effective Effort, source, and meaningful mismatches;
- open risks or unresolved decisions: especially any Blocking Human Decision;
- recommended next action.

Domain-specific result artifacts should keep their names and richer structure. For example, a `Review Packet` remains the native result artifact from `review-pass` while satisfying this convention through its target, mode, reviewer coverage, issue families, verification results, residual risks, and reporting location.

Prefer Markdown-first, field-stable results. Use predictable labels such as `Status`, `Evidence`, `Mutations performed`, `Validation`, `Open risks`, and `Recommended next action` where possible. Do not introduce JSON, YAML, or a separate schema unless a script or validator genuinely needs deterministic parsing.

## Aggregate Status

An **Aggregate Status** is the top-level `Status:` returned by a workflow that summarizes multiple child workflow results, issues, workers, PRs, landing checks, batch passes, or phases.

For aggregate workflows, top-level `Status:` means caller-facing control state: the next routing state the calling workflow or human owner must know to continue safely. It is not a complete summary of every child outcome.

Aggregate workflows should include both:

- one canonical top-level `Status:` selected by shared precedence; and
- an `Aggregate status map:` or equivalent Markdown section that preserves per-scope detail for child outcomes, issues, workers, PRs, landing, batch passes, blockers, stop reasons, and release-instruction handling as applicable.

Use this top-level precedence for mixed aggregate outcomes:

1. `failed` when the aggregate workflow itself failed, or a required child failed in a way the aggregate cannot recover from.
2. `cancelled` when the aggregate workflow or a required child was intentionally cancelled and no higher-precedence failure exists.
3. `needs-human` when safe progress now depends on a human decision or action, such as a PR merge report, scope choice, unresolved ask-user blocker, or human-owned review state.
4. `blocked` when progress is blocked by a non-human dependency, unavailable prerequisite, unresolved external state, or recoverable workflow dependency.
5. `completed` only when every required aggregate-owned unit has reached its convergence point and there are no unresolved failed, cancelled, needs-human, or blocked states.

Aggregate status maps are Markdown-first recovery surfaces, not machine-enforced schemas. Each aggregate workflow should name its required map scopes in its own contract. A typical shape is:

```md
Status: needs-human

Aggregate status map:
- batch: needs-human
- workers:
  - #158: completed
  - #162: blocked
- pull requests:
  - #201: ready-for-human-review
- landing:
  - #158: waiting-for-merge-report
- blockers:
  - Human merge report required before landing can continue.
```

Non-aggregate workflows do not need an aggregate status map.

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
- effort metadata when available and relevant, including prescribed model/effort, prescription source, effective model/effort, effective source/status, and meaningful mismatches; use `unknown` or `not reported` when unavailable;
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
- prescribed model/effort and prescription source when the caller supplies an override or wants the worker to confirm the default;
- an expected Workflow Result;
- an explicit release instruction;
- a Recovery Checkpoint before launch;
- a coordinator-owned integration or conflict-resolution step after results return.

Parallel Called Workflows must not share an uncoordinated mutable surface. They should not share the same working tree, index, branch, issue-body edit, PR comment stream, or other mutation surface unless the Calling Workflow has a designed coordination rule for that surface.

### Worker Thread Setup

When a harness supports durable worker threads or branch-backed project threads, the Calling Workflow should separate setup from execution:

1. Create or assign the worker branch, isolated worktree, and worker thread.
2. When thread renaming is supported, rename the worker thread to a public-safe, legible target-specific name before sending the `READY` signal or substantive assignment message; otherwise record why a public-safe rename was unavailable.
3. Record the worker branch, worktree, public-safe thread name when available or unavailable reason, public-safe invocation reference, Isolation Boundary, Authorization Boundary, prescribed model/effort and prescription source or explicit no-override/default statement, and expected Workflow Result in the Recovery Record.
4. Send the minimal assignment packet only after the setup checkpoint is complete.

Harness-specific invocation references can help recover a live invocation, but they are runtime references rather than reusable contract fields. Keep private or opaque references out of public issue, PR, commit, and design-doc surfaces unless repository policy explicitly allows them.

The worker's live assignment may be broader than one Called Workflow invocation. For example, a worker can run `implement-github-issue` until its PR is ready for human review, then remain assigned to the same branch and PR for human review corrections until the Calling Workflow releases it. That post-result availability is part of the Calling Workflow's worker lifecycle, not a silent expansion of the Called Workflow contract.

The Calling Workflow remains responsible for recording worker status, preserving each worker's Workflow Result, detecting branch or scope conflicts, routing blocked or needs-human results to the right decision owner, tracking post-result worker availability, and deciding any coordinator-owned integration step. Workers should not merge PRs, close issues, delete branches, mutate the integration branch, or reconcile broader batch state unless their own contract and Authorization Boundary explicitly own those actions.

## Existing Workflow Mapping

Existing AgentOS workflows keep their native contracts and artifacts:

- `review-loop` (`os/skills/review-loop/SKILL.md`) is an Orchestration Loop for PR-scoped review/fix convergence. It may own PR-scoped review mutations inside its contract, but it does not merge PRs or close issues.
- `review-pass` (`os/skills/review-pass/SKILL.md`) is a read-only Called Workflow shape. Its Review Packet can serve as a domain-specific Workflow Result.
- `ensure-implementation-readiness` (`os/skills/ensure-implementation-readiness/SKILL.md`) owns the feature-sized readiness gate and readiness-repair workflow, including consensus provenance checks, check-only invariant checks, durable design-source updates, and readiness-label hygiene when authorized.
- `audit-issues` (`os/skills/audit-issues/SKILL.md`) owns evidence-backed issue tracker reconciliation after integration evidence exists.
- `land-github-issue` (`os/skills/land-github-issue/SKILL.md`) owns one-issue acceptance-criteria reconciliation, fulfilled-checkbox updates, and authorized issue closure after integration evidence exists. It returns unmet criteria to the Calling Workflow instead of spawning workers or widening implementation scope.
- `coordinate-issue-batch` (`os/skills/coordinate-issue-batch/SKILL.md`) owns one GitHub issue batch pass: selection or accepted-batch conversion, callback-first worker launch and tracking, human merge-event handling, and eligible landing through `land-github-issue`.
- `github-loop` (`os/skills/github-loop/SKILL.md`) owns repeated GitHub issue batch-pass sequencing by invoking or resuming `coordinate-issue-batch` with callback-first batch-pass handoffs until no suitable issues remain or a stop condition halts the repository-level loop.
- `os/playbook/GITHUB_WORKFLOW.md` owns repository branch, PR, external-write, and issue-closure discipline.

Link to these contracts rather than copying their rules into every new loop.

## Skill Contract Guidance

When a skill is an Orchestration Loop or can be invoked by one, its skill contract should make the relevant boundaries clear:

- whether it is read-only, mutating, or mode-dependent;
- what target it owns;
- what external writes require additional approval;
- what it may call;
- what Workflow Result it returns;
- which canonical terminal statuses it can return, normally `completed`, `blocked`, `failed`, `cancelled`, and `needs-human` unless the skill documents a narrower set;
- for aggregate workflows, what `Aggregate status map:` scopes it returns and how its top-level `Status:` follows the shared Aggregate Status precedence;
- how it accepts and reports any caller-supplied Workflow Invocation Reference or result surface;
- how it accepts and reports caller-supplied effort prescriptions, or records that no override/default applies;
- how it follows release instructions after returning a result to a caller;
- what Minimal Assignment Packet it sends when it launches called workflows or workers, including callback/result surface, release instruction, target, boundary, prescribed effort when relevant, and expected Workflow Result ownership;
- what Recovery Record or Recovery Checkpoint it maintains;
- what Integration Ownership, if any, belongs to the skill.

Keep this proportional. A small read-only helper does not need loop-specific boilerplate.

## Validation

Before changing this convention or a loop-shaped skill that depends on it:

1. Run `scripts/run-validator`.
2. Run `git diff --check`.
3. Inspect affected skill contracts or manifest entries for clear Authorization Boundaries, Workflow Invocation References, Minimal Assignment Packets, Effort Recommendations, Workflow Results, Recovery Records, and Integration Ownership where relevant.
4. Keep deterministic validators shallow and objective until the convention matures enough to enforce mechanically.
