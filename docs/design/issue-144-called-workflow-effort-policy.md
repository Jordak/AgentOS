# Issue 144 Called Workflow Effort Policy

Design readiness: ready to implement

## Problem

AgentOS now composes loop-shaped workflows through Calling Workflow and Called Workflow roles. That composition has made model and reasoning-effort selection part of the workflow contract surface: a parent loop may be cheap ledger management, while the reviewer or design-consensus workflow it calls may need higher effort.

Previously, AgentOS had only scattered effort guidance. Without a convention, future agents cannot tell whether a Called Workflow's effort was selected by the workflow contract, inherited from the harness, overridden by the Calling Workflow, set by a custom agent, chosen by the user for latency or budget, or simply unknown.

This is also a vendored-skill problem. Some skills, such as `grill-me` and `grill-with-docs`, are mirrored from upstream sources. AgentOS should not edit those vendored `SKILL.md` bodies solely to add local model or effort policy.

## Current Platform Facts Checked

As of this issue implementation, current official OpenAI docs show that model and effort controls are surface-specific and model-dependent:

- OpenAI Responses API exposes a `reasoning.effort` option for supported reasoning models, with values such as `minimal`, `low`, `medium`, `high`, and model-dependent higher settings. The docs describe lower effort as a latency and reasoning-token tradeoff and state that defaults vary by model family.
- Codex configuration exposes local `model` and `model_reasoning_effort` settings, while Codex cloud tasks currently do not expose a user-selectable default model in the same way.

Therefore AgentOS should recommend effort in workflow language, not hardcode one platform field as universally available. Workflow Results and Recovery Records must allow values such as `unknown`, `not reported`, `platform-selected`, and `not applicable`.

Sources checked:

- OpenAI API reference, Responses `reasoning.effort`: https://platform.openai.com/docs/api-reference/responses/create
- OpenAI Codex configuration reference, `model` and `model_reasoning_effort`: https://developers.openai.com/codex/config-reference
- OpenAI Codex models docs, local and cloud model selection notes: https://developers.openai.com/codex/models

## Chosen Design

Use `os/skills/ORCHESTRATION_LOOPS.md` as the canonical AgentOS convention for model and effort selection in workflow composition.

AgentOS-owned workflow `SKILL.md` contracts may include local effort recommendations when the recommendation is stable and belongs to that workflow. They should still link to `ORCHESTRATION_LOOPS.md` for the shared vocabulary and result metadata.

For vendored skills, do not patch upstream `SKILL.md` bodies solely to add AgentOS effort policy. Use AgentOS-owned caller instructions, wrapper workflows, `os/skills/MANIFEST.md` metadata, or the orchestration convention instead. The Calling Workflow can prescribe effort for that invocation without creating upstream drift.

Effort recommendations are defaults, not mandates. User instructions about budget, latency, rate limits, or quality override AgentOS defaults when they do not conflict with safety or the workflow's minimum quality bar. Platform, harness, model, or custom-agent configuration can also override or ignore the requested effort. The workflow must record that distinction when it can observe it.

## Invocation Policy

A Calling Workflow may specify an effort policy when invoking a Called Workflow. The policy should name:

- requested effort: `low`, `medium`, `high`, `xhigh`, another harness-native value, or `harness default`;
- reason: why that level is appropriate for the called task;
- override source: `contract default`, `calling workflow override`, `user budget override`, `user latency override`, `custom agent config`, `platform selected`, or `unknown`;
- fallback rule: what to do if the platform cannot honor or report the requested value.

If no invocation-specific effort is supplied, the Called Workflow uses its own contract or AgentOS manifest recommendation when one exists. If no recommendation exists, the harness default applies.

Effort policy does not widen the Authorization Boundary. A high-effort review still cannot mutate a PR unless the called workflow's contract and invocation boundary allow that mutation.

## Workflow Result Metadata

Workflow Results and equivalent handoffs should report model and effort metadata when available:

- requested model and requested effort;
- actual model and actual effort, if reported by the harness;
- selection source, such as contract default, Calling Workflow override, user override, custom agent config, platform default, or unknown;
- override or mismatch notes, including budget or latency constraints;
- unknown/not-reported values rather than invented precision.

This metadata is evidence for the caller and coordinator. It is not a deterministic validation requirement in v1.

## Initial Effort Defaults

Use these initial defaults when the harness exposes effort controls and no user or platform override applies:

| Workflow type | Default effort | Escalate when | De-escalate when |
| --- | --- | --- | --- |
| Parent orchestration loops such as `implement-github-issue`, `coordinate-issue-batch`, and `github-loop` | `medium` | Design adjudication, recovery from ambiguity, or cross-workflow risk is substantial | The loop is only bookkeeping, status polling, or handoff packaging |
| `ensure-implementation-readiness` | `medium` | Readiness repair is fuzzy, architectural, or requires `grill-with-docs` | The gate is a mechanical marker or source-shape check |
| `grill-me` | `high` when invoked for design consensus | The decision is hard to reverse or spans multiple domains | The session is a small read-only sanity check |
| `grill-with-docs` | `high` when invoked for readiness repair or ADR-worthy design | Domain terms conflict, durable docs need careful edits, or the decision is hard to reverse | The update is a narrow glossary clarification |
| `review-pass` | `high` for normal reviewer panels | Security, publication safety, broad contract changes, or deeply ambiguous design drift may justify `xhigh` when the user budget allows it | Tiny docs-only or formatting-only review can use `medium` |
| `review-loop` parent orchestrator | `medium` | Ambiguous adjudication, repeated findings, or design-escape-hatch decisions need deeper judgment | Routine ledger management and PR-comment packaging can use `low` or `medium` |
| Simple audit or closure workflows such as `audit-issues` and `land-github-issue` | `medium` | Acceptance criteria, human-review labels, or integration evidence are ambiguous | The check is purely mechanical and already backed by integration-branch evidence |

## Non-Goals

- Do not edit upstream-vendored `SKILL.md` files solely to add AgentOS effort policy.
- Do not require one universal effort level for every Called Workflow.
- Do not require deterministic enforcement before the convention is stable.
- Do not assume every Codex or agent surface exposes exact effort metadata.
- Do not turn effort policy into authorization for extra mutations.

## Acceptance Criteria

- `os/skills/ORCHESTRATION_LOOPS.md` defines where defaults, Calling Workflow overrides, user overrides, and result metadata belong.
- Vendored skills remain policy-aligned with upstream; AgentOS-specific effort guidance lives in AgentOS-owned surfaces.
- Workflow Result and Recovery Record guidance includes model and effort metadata with unknown/not-reported fallbacks.
- Initial default effort recommendations cover parent loops, `ensure-implementation-readiness`, `grill-me`, `grill-with-docs`, `review-pass`, `review-loop`, and simple audit/closure workflows.
- The convention is ready to inform future implementation-loop work without adding deterministic enforcement in this issue.

## Validation Plan

- Run `git diff --check`.
- Run `scripts/run-validator`.
- Inspect changed orchestration, skill-contract, and manifest surfaces for consistency with this design.

## PR Readiness Fields

```md
Readiness evidence: docs/design/issue-144-called-workflow-effort-policy.md and GitHub issue #144
Readiness verdict: Ready to Implement
```
