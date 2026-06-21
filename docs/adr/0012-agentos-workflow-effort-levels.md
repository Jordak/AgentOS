# AgentOS Workflow Effort Levels

Design readiness: ready to implement
Consensus provenance: Human-attested GitHub approval from repository owner Jordak: https://github.com/Jordak/AgentOS/issues/144#issuecomment-4699349113
Gate skipped: not applicable

## Context

AgentOS workflows increasingly compose other workflows. A repository-level loop may invoke a batch coordinator, which may launch issue workers, which may run readiness checks, design-consensus workflows, implementation, and review loops.

As of this decision, AgentOS has reusable conventions for Authorization Boundaries, Callback-First Invocation, Workflow Results, Recovery Records, and Integration Ownership. It does not yet have a durable rule for choosing or reporting model effort. That creates ambiguity: a future agent cannot tell whether an observed effort level was a workflow default, a Calling Workflow override, a user budget choice, custom-agent configuration, a platform default, or an unreported fallback.

The convention must stay portable. Model effort is not a universal capability across all agentic harnesses, and even harnesses with effort controls may not support switching effort repeatedly inside one live thread or one turn.

## Decision

AgentOS treats workflow effort recommendations as invocation-level intentions, not hard intra-thread controls.

The durable lookup home for named workflow defaults is `os/skills/ORCHESTRATION_LOOPS.md`. AgentOS-owned skill contracts may mention local effort guidance when useful, but cross-workflow defaults belong in the orchestration convention so callers can find them without scanning every skill.

Calling Workflows may prescribe effort for Called Workflow invocations. When the harness can create a separate run, thread, worker, subagent, custom agent, or model request, it should apply the prescribed effort when supported. When multiple skills run in the same live thread and the harness cannot reliably switch effort mid-turn, the current thread effort is the effective effort and the workflow should report the prescribed/effective mismatch.

Workflow Results, Recovery Records, review packets, reports, or equivalent handoffs should report prescribed model/effort, the prescription source, effective model/effort when observable, effective source or status, and meaningful mismatches. `unknown` and `not reported` are valid values when the harness does not expose exact metadata.

Vendored upstream skill bodies should not be edited solely to add AgentOS effort policy. AgentOS-specific effort recommendations for vendored workflows belong in AgentOS-owned caller instructions, wrapper workflows, routing/manifest metadata when appropriate, or the reusable orchestration convention.

## Assignment Logic

Use `low` for mechanical, low-risk, deterministic checks with little interpretation.

Use `medium` for workflow coordination, tracker reconciliation, issue selection, closure judgment, recovery ledgers, and routine orchestration where evidence must be weighed but new design or code is not the main task.

Use `high` for implementation, design consensus, difficult prose-contract edits, substantive adjudication, and reviewer quality.

Use `xhigh` selectively for security, deep review, final-gate review, unusually high-stakes design, long asynchronous work, or cases where evaluation evidence shows the extra cost and latency are worthwhile.

Higher outer-loop scope does not automatically imply higher effort. Coordinators often default to `medium` because their job is routing, recovery, ledger management, and evidence handling. The deeper design, implementation, or review work may happen in called workflows with their own prescribed effort.

## Initial Defaults

- `github-loop`: `medium` for repository-level pass sequencing, callback handling, stop-condition judgment, and recovery.
- `coordinate-issue-batch`: `medium` for batch coordination, worker ledger management, parallel-safety checks, and landing queue judgment.
- `implement-github-issue`: `high` for same-thread end-to-end runs across readiness, implementation, validation, PR creation, and review-loop orchestration.
- `ensure-implementation-readiness`: `medium`, escalating to `high` when consensus is fuzzy, scope boundaries are ambiguous, or design-consensus work is needed.
- `grill-me`: `high`, with selective `xhigh` for unusually deep or high-stakes design work.
- `grill-with-docs`: `high`, with selective `xhigh` for hard architecture or cross-document tradeoffs.
- `review-pass`: `high`, with selective `xhigh` for security, deep-review, final-gate, high-risk, difficult, or eval-justified passes.
- `review-loop`: `medium`, escalating to `high` for hard adjudication, design-escape-hatch calls, or same-thread orchestration and fix work after clean reviewer evidence.
- `select-issue-batch`: `medium` for issue-state interpretation, dependency judgment, and parallel-safety reasoning.
- `audit-issues`: `medium` for evidence-backed issue tracker reconciliation.
- `land-github-issue`: `medium` for integration proof, acceptance-criteria reconciliation, and human-review label judgment.

## Consequences

Calling Workflows can be explicit about desired quality, latency, and cost posture without pretending every harness can enforce effort at fine granularity.

Same-thread fallback remains valid for orchestration, fixing, reporting, and other non-review-evidence work, but it cannot satisfy `review-pass` or `review-loop` clean-context reviewer evidence; reports must distinguish prescribed effort from effective inherited effort when that matters.

Workflow Results and Recovery Records become more useful for later review, reruns, and cost-quality diagnosis.

Vendored skills can remain upstream-aligned while AgentOS still records local orchestration policy for invoking them.

The convention remains prose-first. Deterministic enforcement should wait until harness behavior and metadata surfaces are stable enough to validate objectively.

## Alternatives Considered

Use one global effort level for every workflow. This was rejected because issue selection, implementation, design consensus, review, and landing have different cost-quality tradeoffs.

Make all review-related workflows `xhigh`. This was rejected because `xhigh` can be costly and slow; it is better reserved for high-risk, deep, final-gate, difficult, or eval-justified review passes.

Make outer orchestration loops default to `high` or `xhigh` because they own larger scopes. This was rejected because coordination is often evidence management rather than deep reasoning; called workflows can prescribe higher effort for deeper work.

Patch vendored upstream `SKILL.md` files with AgentOS effort policy. This was rejected because it creates unnecessary upstream divergence for policy that belongs to AgentOS invocation guidance.

Assume every harness can switch effort phase-by-phase inside one thread. This was rejected because effort control is harness-specific; AgentOS should record effective behavior instead of relying on unportable assumptions.

## Validation

The implementation for GitHub issue #144 should:

- update `os/skills/ORCHESTRATION_LOOPS.md` with the effort convention, reporting guidance, and named workflow lookup table;
- add or update only small cross-references in skill contracts or manifests when needed;
- avoid naming one specific agentic tool or model provider in reusable policy logic;
- preserve upstream-vendored skill bodies;
- run `git diff --check` and `scripts/run-validator`.
