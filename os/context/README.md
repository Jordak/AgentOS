# Context Resolver

Status: directory resolver v1.

Use `os/context/` for public-safe, relatively stable context templates and Core routing that help agents avoid generic answers without storing live private state. Live user, project, account, interest, tool, and source-location facts belong in matching Personal Overlay files under `personal/os/context/`.

## Belongs Here

- Public-safe project and role context templates that can be reused across AgentOS instances.
- Core/default source-map schema and public-safe source routing.
- Public-safe work descriptions and durable constraints such as a generic work firewall.
- Public-safe tool inventory templates and known connection-surface categories, when the fact is contextual rather than a permission rule.
- Glossary terms that help agents use AgentOS language consistently.

## Does Not Belong Here

- Durable decisions or lessons: use `personal/os/memory/` for live/private decisions, or `os/memory/` and `docs/adr/` for publishable AgentOS architecture decisions.
- Reusable procedures: use `os/skills/`.
- Generic agent contracts and templates: use `os/agents/`. Live agent run instructions, private job context, and agent-owned reports: use `personal/os/agents/`.
- Account permissions, connector write rules, and account-specific connection safety: use `personal/os/connections/`. Core keeps public-safe connection templates and safety policy under `os/connections/`.
- Live project and work context, private interests, account-specific tool inventory, and private source pointers: use `personal/os/context/`.
- Substantial implementation notes, research artifacts, code, datasets, documents, or publishable reports: use the mapped project in the appropriate source map.

## Common Tie-Breakers

- Context vs memory: context is the stable map of what matters; memory is the record of what changed, what was decided, or what matters this week.
- Context vs source map: if the fact tells agents where to inspect a public-safe Core/project artifact, put it in `os/context/SOURCE_MAP.md`. If it points to a live, private, local, or account-specific source, put it in `personal/os/context/SOURCE_MAP.md`. If it summarizes why that project matters, put it in the relevant context file.
- Context vs connections: if the fact says "this public-safe tool category exists" or "this project uses this public-safe source," context is fine. If it says what an agent may read, write, send, delete, or change for a real account, use `personal/os/connections/`; keep generic approval policy in `os/connections/SAFETY_RULES.md`.
- Context vs mapped project: keep summary and routing here; keep the actual domain work in the mapped project.

## Update Rules

- Prefer public-safe, stable summaries over detailed raw notes.
- Inspect mapped project sources before changing project-specific context.
- Keep stale context honest with dates, status markers, or TODOs instead of silently rewriting history.
- User corrections outrank older context. Preserve the correction in the narrowest relevant file.

## Provenance

For project and career facts, note the source when it is not obvious from the file itself. For external or fast-moving facts, prefer current official or primary sources.

## Handoff Rules

- If a context update implies a durable decision, also update or point to `personal/os/memory/DECISIONS_LOG.md`; use `os/memory/DECISIONS_LOG.md` only for publishable AgentOS architecture decisions.
- If a new external account capability or permission appears, update `personal/os/connections/CONNECTIONS.md` and keep public-safe policy in `os/connections/SAFETY_RULES.md`.
- If a new public-safe Core/project source becomes canonical, update `os/context/SOURCE_MAP.md`.
- If a new live, private, local, or account-specific project source becomes canonical, update `personal/os/context/SOURCE_MAP.md`.
