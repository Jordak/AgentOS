# Source Map

Status: Core default.

Use this file to decide where an agent should look before making claims about a project, artifact, or body of work.

This Core default contains only AgentOS Core routing. Live user/project/account source maps belong in `personal/os/context/SOURCE_MAP.md`.

## Rules

- Inspect the mapped source before giving project-specific advice.
- Prefer local project files for implementation state.
- Prefer external sources only when the source map says they are canonical or current facts are required.
- If a source is stale or missing, say so and ask whether to update the map.

## AgentOS Core

Purpose: publishable reusable AgentOS framework.

Primary source:

- Local directory: repository root.
- Core root: `os/`.
- Personal Overlay root: `personal/os/`.

Tool adapters:

- Codex workspace adapter: `AGENTS.md`
- Claude Code workspace adapter: `CLAUDE.md`

Publication:

- Overlay rule: `os/playbook/PERSONAL_OVERLAY.md`
- Publication workflow: `os/playbook/PUBLICATION.md`
