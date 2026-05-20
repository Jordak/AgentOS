# AgentOS Playbook

Status: operating manual v1.

This playbook explains how to use and maintain AgentOS Core.

## Purpose

AgentOS is a portable Markdown-based operating layer for agentic tools.

AgentOS Core lives under `$root/os/`. Private user-specific state lives under `$root/personal/os/` as a Personal Overlay. Read Core first, then matching Personal Overlay files when present. See `os/playbook/PERSONAL_OVERLAY.md`.

Do not make a formerly private AgentOS GitHub repository public after private files have existed in its history. Public AgentOS publication uses a sanitized export and a fresh initial commit. See `os/playbook/PUBLICATION.md`.

## Core Principle

Do not turn AgentOS into one giant prompt.

Use small files with clear jobs:

- Identity templates describe who the user is and how to collaborate.
- Context templates describe what matters and where real sources live.
- Skills describe reusable workflows.
- Memory templates record decisions, current state, and compiled truth.
- Connections describe tools, accounts, and safety rules.
- Agents define durable jobs.
- Verification describes quality checks.
- Artifact policy explains output formats.
- Programming playbooks route durable coding, CLI, interface-design, and Markdown authoring preferences.
- Automations describe scheduled or trigger-based work.
- The source map tells agents where to inspect real project state.
- The resolver gives brain-first lookup, routing, authority, safety, and filing tie-breakers.

## Domain Language

Use `DOMAIN.md` for repository domain language: canonical terms, relationships, example dialogue, and flagged ambiguities.

Do not create new `CONTEXT.md` files for this purpose. In AgentOS, `context` already names the `os/context/` layer for stable project, source-routing, and tool knowledge. Legacy repositories may still have `CONTEXT.md`; read and update those when they are the existing domain file, but prefer `DOMAIN.md` for new work and migrations.

## Load Order

For broad AgentOS work, read:

1. `AGENTS.md`
2. `os/INDEX.md`
3. `os/playbook/PERSONAL_OVERLAY.md`
4. `os/RESOLVER.md`
5. This playbook.
6. The narrowest relevant Core files and matching Personal Overlay files.

For project-specific advice, always check:

1. `os/context/SOURCE_MAP.md`
2. `personal/os/context/SOURCE_MAP.md` when present
3. The mapped project source
4. The relevant agent or skill files

Do not load every file by default.

## Routing Rules

Use the narrowest path that can answer the request.

- Personal preferences: `personal/os/identity/`
- Live project and work context: `personal/os/context/`
- Current project source locations: `personal/os/context/SOURCE_MAP.md`
- Repeatable workflow: `os/skills/`
- Private skill config: `personal/os/skills/<skill-name>/CONFIG.md`
- Current state and personal decisions: `personal/os/memory/`
- Core architecture decisions: `docs/adr/` or `os/memory/DECISIONS_LOG.md`
- Connected tools and safety: `personal/os/connections/`
- Live agent roles: `personal/os/agents/`
- Generic agent templates: `os/agents/`
- Quality checks: `os/verification/`
- Private run evidence: `personal/os/verification/`
- Live schedules and recurring jobs: `personal/os/automations/`
- Tool portability: `os/playbook/PORTABILITY.md`
- Personal overlay load and migration rule: `os/playbook/PERSONAL_OVERLAY.md`
- Public repository publication workflow: `os/playbook/PUBLICATION.md`
- Output artifact policy: `os/playbook/ARTIFACTS.md`
- GitHub issue, PR, branch, and closure workflow: `os/playbook/GITHUB_WORKFLOW.md`
- Programming preferences: `os/playbook/programming/README.md`
- Propagation review queue: `os/playbook/PROPAGATION_REVIEW_QUEUE.md`
- Weekly AgentOS review template: `os/playbook/WEEKLY_REVIEW.md`; private generated reports and live review state: `personal/os/memory/weekly-review/`

When a request belongs in another project, do not duplicate that project's context here. Inspect the mapped source, then produce a handoff for the right project.

## State Placement

AgentOS Core stores:

- templates;
- reusable workflows;
- cross-cutting operating policy;
- validation code and schemas;
- sanitized examples;
- Core architecture decisions.

Personal Overlay stores:

- real identity, preferences, and boundaries;
- live project and source-map state;
- account and connector state;
- live agents, automations, reports, and run histories;
- private generated outputs;
- personal decisions and memories.

## Artifact Formats

Use `os/playbook/ARTIFACTS.md` before deciding the output format for a substantial report, brief, plan, review, explainer, or design artifact.

Production rule:

- Keep the AgentOS control plane in Markdown.
- Use static HTML as the preferred output for substantial human-facing artifacts.
- Store private generated outputs in the Personal Overlay by default.

## Safety Rules

Ask before:

- sending email or messages;
- posting publicly;
- changing sharing permissions;
- entering credentials or handling MFA;
- deleting nontrivial data;
- installing software;
- granting external write access;
- taking actions with external consequences;
- deleting, replacing, archiving, or changing visibility of a repository.

## Skills

Canonical reusable skill sources live under `os/skills/`.

Before changing skill behavior, read:

- `os/skills/MANIFEST.md`
- `os/skills/SKILL_CONTRACT.md`

Private live inputs for Core skills belong in `personal/os/skills/<skill-name>/CONFIG.md`.

## Agents

Generic agent scaffolding lives under `os/agents/`. Named live agents belong in `personal/os/agents/` by default.

Use `os/agents/AGENT_TEMPLATE.md` for new reusable templates. Use the Personal Overlay for real recurring jobs.

## Automations

Automation patterns and safety policy may live in Core. Live schedules, prompts, destinations, accounts, and activation state belong in `personal/os/automations/`.

Do not create automations that act without manual review unless the user explicitly approves.

## Publication

Follow `os/playbook/PUBLICATION.md`.

Do not delete, archive, replace, make public, or recreate a formerly private GitHub repository until the local migration, export script, privacy validation, secret scan, and manual public-export inspection are complete.
