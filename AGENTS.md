# AgentOS Adapter

This workspace is an AgentOS checkout. Treat it as a portable Markdown control plane for agentic tools.

AgentOS Core is the public-safe, reusable layer under `os/`. The Personal Overlay is ignored local state under `personal/os/` for private identity, context, memory, live automations, live agents, generated reports, histories, queues, and account-specific details.

## Path Convention

Unless otherwise stated, local file paths in AgentOS Markdown are relative to the AgentOS repository root. Use `os/...`, `personal/os/...`, `AGENTS.md`, or another root-relative path for files inside this workspace. Use absolute paths only for explicitly machine-local adapters, external project checkouts, or connector/tool locations outside AgentOS.

## Load Order

At the start of work in this workspace:

1. Read this file.
2. Read `os/INDEX.md`.
3. Read `os/playbook/PERSONAL_OVERLAY.md`.
4. If `personal/os/` contains matching files for the task, read those after the Core files. Use the Personal Overlay discovery rule before concluding ignored private files are absent.
5. For broad or ambiguous AgentOS routing, source authority, safety, or durable state placement, read `os/RESOLVER.md`.
6. Read the narrowest relevant files for the user's request.

## Current-Docs Rule

Before answering questions about Codex, ChatGPT, OpenAI APIs, Cursor, Claude Code, OpenClaw, GitHub Copilot, MCP, or any fast-moving tool feature, check current official docs or primary sources. State when guidance is based on a current source versus local workspace instructions.

## Working Rules

- Build in small, usable increments.
- Treat `main` as protected. Do not commit or push Core/public AgentOS changes directly to `main`.
- Make Core/public changes on a feature branch in an isolated worktree, open a pull request, wait for required validators, and squash merge through GitHub.
- Use the harness-provided worktree when one exists. Otherwise create an external Git worktree under `$CODEX_HOME/worktrees/`; do not create worktrees inside this repository.
- When running from a feature worktree, do not assume ignored `personal/os/` files exist there. For Personal Overlay reads or approved writes, use the canonical primary AgentOS checkout's `personal/os/` unless the user explicitly assigns a different private overlay workspace.
- For AgentOS public repository persistence, use `scripts/agent-push` instead of raw `git push` when that helper is available. If the helper is missing or unsuitable, pause and ask before pushing.
- Prefer plain Markdown for the AgentOS control plane so it can move between tools.
- Prefer static HTML for substantial human-facing reports, reviews, plans, explainers, and briefs. Use `os/playbook/ARTIFACTS.md` for output-format decisions.
- Keep global identity and preferences separate from project-specific instructions.
- Preserve user agency around credentials, account actions, external posts, and write-access connections.
- When a template asks for personal knowledge that is missing, create a clearly marked placeholder and a short question list.
- Keep this adapter lean. When adding guidance, link to the narrowest playbook, skill, or layer file unless the instruction applies to nearly every AgentOS task.

## Publication Safety

Do not make a formerly private AgentOS repository public. Follow `os/playbook/PUBLICATION.md`: migrate private live state into `personal/os/`, generate a sanitized public export, validate the export, and create the public repository from fresh Git history.

Live named agents, live automations, reports, briefs, histories, queues, run logs, and generated outputs default to `personal/os/`. Core `os/agents/` and `os/automations/` are for templates, examples, schemas, and policy only.
