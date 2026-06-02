# AgentOS Index

This is the map for AgentOS Core, the public-safe reusable layer under `$root/os/`.

Core files describe templates, policy, routing, verification, and generic examples. They should be usable by a stranger with no private context. Private user-specific state belongs in the Personal Overlay under `$root/personal/os/`.

## Operating Principle

AgentOS is not one giant prompt. Its control plane is a stack of small Markdown files:

- Identity templates describe how to capture who the user is and how to collaborate.
- Context templates describe what matters and where real project sources live.
- Skills encode repeatable workflows.
- Memory templates describe how to record decisions, current state, and compiled truth.
- Connections describe tools, permissions, and safety boundaries.
- Agent templates define durable jobs that inherit the OS.
- Verification keeps agent output trustworthy.
- Playbooks explain operating policy and publication rules.
- Automations describe safe scheduled or event-driven work.
- Propagation review is the private pre-issue inbox for generated durable-state recommendations that are not yet public-safe actionable project work.
- The Personal Overlay rule separates publishable Core files under `$root/os/` from private user-specific files under `$root/personal/os/`.
- The publication rule explains how to create a fresh-history public repository without exposing private Git history.
- The protected-main workflow keeps AgentOS Core and publishable support-file changes on isolated feature-branch worktrees and lands them through validated pull requests.
- The implementation-readiness rule keeps feature-sized work from starting before a durable design source is complete for the requested scope; chat-only consensus must be promoted into a durable source before implementation code begins.

## How To Use This Folder

Start here after `AGENTS.md`. Read `os/playbook/PERSONAL_OVERLAY.md` before looking for or storing private state. When a task is broad or ambiguous, read `os/RESOLVER.md` after this index, then start with the smallest relevant file. Do not load everything by default.

A public clone may contain only the tracked `personal/` skeleton. That is expected. If matching Personal Overlay files are absent, continue with Core templates and ask the user for missing private facts only when the task requires them.

When updating AgentOS, prefer adding facts to the narrowest file:

- Personal preferences -> `personal/os/identity/`
- Work/project knowledge -> `personal/os/context/`
- Reusable workflow -> `os/skills/`
- Durable personal decision or memory -> `personal/os/memory/`
- Core architecture decision -> `docs/adr/` or `os/memory/DECISIONS_LOG.md`
- Generated durable-state recommendation -> classify first: GitHub issue or mapped tracker for public-safe actionable project work; `personal/os/memory/propagation-review/QUEUE.md` for private, tentative, connector-derived, personal, cross-project, or pre-issue proposals; direct edit only for exact approved changes.
- Tool access or permission -> `personal/os/connections/`
- Specific live agent behavior -> `personal/os/agents/`
- Generic agent template -> `os/agents/`
- Quality checks -> `os/verification/README.md`
- System overview -> `os/playbook/`
- Scheduled or event work -> `personal/os/automations/`
- Personal overlay load and migration rule -> `os/playbook/PERSONAL_OVERLAY.md`
- Guided first-pass setup -> `os/playbook/GETTING_STARTED.md`
- Public repository publication workflow -> `os/playbook/PUBLICATION.md`
- GitHub branch, worktree, pull request, and merge workflow -> `os/playbook/GITHUB_WORKFLOW.md`
- Feature implementation readiness and no-first-commit design gate -> `os/playbook/IMPLEMENT_FEATURES.md`
- Lookup, routing, authority, safety, and filing tie-breakers -> `os/RESOLVER.md`

## Backlog

Core backlog templates may live in `os/playbook/BACKLOG.md`. Live private backlog entries belong in `personal/os/playbook/BACKLOG.md`.
