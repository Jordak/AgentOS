# AgentOS Adapter

This workspace is an AgentOS checkout. Treat it as a portable Markdown control plane that can guide the active agent harness and be reused by other agentic tools.

## Path Convention

Unless otherwise stated, local file paths in AgentOS Markdown are relative to the AgentOS repository root. Use `os/...`, `personal/os/...`, `AGENTS.md`, or another root-relative path for files inside this workspace. Use absolute paths only for explicitly machine-local adapters, external project checkouts, or connector/tool locations outside AgentOS.

## Load Order

At the start of work in this workspace:

1. Read this file.
2. Read `os/INDEX.md`.
3. Read `os/playbook/PERSONAL_OVERLAY.md`.
4. If `personal/os/` contains matching files for the task, read those after the Core files.
5. For broad or ambiguous AgentOS routing, source authority, safety, or durable state placement, read `os/RESOLVER.md`.
6. Read the narrowest relevant files for the user's request.

## Current-Docs Rule

Before answering questions about Codex, ChatGPT, OpenAI APIs, Cursor, Claude Code, OpenClaw, GitHub Copilot, MCP, or any fast-moving tool feature, check current official docs or primary sources. State when guidance is based on a current source versus local workspace instructions.

## Working Rules

- Build in small, usable increments.
- Prefer plain Markdown for the AgentOS control plane so it can move between tools.
- Prefer static HTML for substantial human-facing reports, reviews, plans, explainers, and briefs. Use `os/playbook/ARTIFACTS.md` for output-format decisions.
- Keep global identity and preferences separate from project-specific instructions.
- Preserve user agency around credentials, account actions, external posts, and write-access connections.
- When a template asks for personal knowledge that is missing, create a clearly marked placeholder and a short question list.

## Publication Safety

Do not make a formerly private AgentOS repository public. Follow `os/playbook/PUBLICATION.md`: migrate private live state into `personal/os/`, generate a sanitized public export, validate the export, and create the public repository from fresh Git history.
