# Agents Resolver

Status: directory resolver v1.

Use `os/agents/` for publishable reusable agent scaffolding: templates, public-safe example contracts, and generic guidance for durable roles.

Live named agents with personal cadence, private inputs, operating history, reports, or job-specific continuity belong in `personal/os/agents/`.

This directory is not a live agent registry. Core agent folders must be templates, public-safe examples, or policy-only scaffolding.

## Belongs Here

- Generic agent job templates and public-safe example instructions.
- Public-safe boundaries, source discipline, and verification patterns.
- Reusable report-pointer patterns that do not disclose live state.
- Templates for creating new agents.

## Does Not Belong Here

- Generic reusable workflows without a durable role: use `os/skills/`.
- Cross-cutting AgentOS policy: use `os/playbook/`.
- Stable project/career context shared across agents: use `personal/os/context/` for live/private context, or `os/context/` for public-safe templates and Core routing.
- Durable decisions or lessons that affect the whole OS: use `personal/os/memory/` for live/private decisions, or `os/memory/` for publishable AgentOS architecture decisions.
- Live named agent definitions, private operating instructions, histories, reports, brief archives, or job-specific continuity: use `personal/os/agents/`.
- Live queues, run logs, generated outputs, and delivery records: use `personal/os/agents/` or the narrowest matching Personal Overlay directory.
- Substantial domain work products, datasets, code, notes, decks, or publishable reports that have value outside the agent: use the mapped project from the appropriate source map.

## Common Tie-Breakers

- Agent vs skill: an agent owns a recurring job and may use many skills; a skill is a callable procedure that may be used by many agents.
- Agent report vs mapped project artifact: keep OS-level advisory reports with the agent; move growing standalone corpora or publishable products to a mapped project.
- Agent memory vs global memory: keep live agent-specific continuity with the agent under `personal/os/agents/`; promote public-safe architecture decisions or lessons that affect all AgentOS work to `os/memory/`, and private live decisions to `personal/os/memory/`.
- Agent vs automation: the agent defines the job; `personal/os/automations/` records live schedules, triggers, destinations, and runtime automation details. Core keeps public-safe automation templates and policy under `os/automations/`.

## Update Rules

- Use `AGENT_TEMPLATE.md` for new agents unless an existing agent provides a clearer local pattern.
- Each durable agent should have a job definition, operating instructions, inputs, outputs, boundaries, and verification guidance.
- Keep live agent histories compact under `personal/os/agents/`. Link to reports rather than duplicating report content into summaries.
- Do not route installed skill adapters or automations for private live agents into `os/agents/`; point them at `personal/os/agents/` or a Personal Overlay skill config.
- Do not add a new installed skill adapter for every agent by default. Add one only when the user should invoke the agent from arbitrary projects.

## Provenance

Agent outputs should identify their inputs and source discipline when the output will guide future work. Treat reports as evidence until their claims are promoted into context, memory, source map, playbook, skills, verification, or automation files.

When an agent output proposes a durable OS update but should not apply it directly, classify the right inbox first. Use GitHub issues or mapped-project trackers for public-safe actionable project work, and use `personal/os/memory/propagation-review/QUEUE.md` with `os/playbook/PROPAGATION_REVIEW_QUEUE.md` for private, tentative, connector-derived, personal, cross-project, or pre-issue proposals. Such proposals are not canonical until approved and applied.

## Handoff Rules

- If an agent starts producing artifacts in a new location, update `os/context/SOURCE_MAP.md` for public-safe routing or `personal/os/context/SOURCE_MAP.md` for private/local routing.
- If an agent becomes scheduled or event-driven, update `personal/os/automations/` for live schedules or `os/automations/` for public-safe templates.
- If an agent discovers a reusable procedure, add or update a skill rather than burying the method in agent-only instructions.
