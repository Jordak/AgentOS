# Memory Resolver

Status: directory resolver v1.

Use `os/memory/` for public-safe memory mechanics, templates, and publishable AgentOS Core architecture memory. Live state about a real person, private projects, current priorities, personal decisions, compiled truth, propagation queues, and weekly review reports belongs in matching Personal Overlay files under `personal/os/memory/`.

## Belongs Here

- Memory templates and public-safe example shapes.
- Publishable AgentOS Core architecture decisions and lessons.
- Compaction rules and memory-maintenance practices.
- Propagation review mechanics and templates.

## Does Not Belong Here

- Current short operating state, this-week priorities, live long-term memory, confirmed personal preferences, and private decisions: use `personal/os/memory/`.
- Live compiled-truth pages that preserve current synthesis plus timeline evidence: use `personal/os/memory/compiled-truth/`; Core keeps only the template shape.
- Propagation review proposals that are waiting for approval before becoming canonical state: use `personal/os/memory/propagation-review/QUEUE.md`; Core keeps only the template shape.
- Weekly review reports and review history: use `personal/os/memory/weekly-review/`.
- Stable project and career context that is more map than history: use `personal/os/context/` for live/private context, or `os/context/` for public-safe templates and Core routing.
- Reusable workflow instructions: use `os/skills/`.
- Generic agent scaffolding: use `os/agents/`. Live agent definitions, operating instructions, and agent-owned brief/report histories: use `personal/os/agents/`.
- Verification checklists: use `os/verification/`.
- Substantial project artifacts, research notes, datasets, or implementation records: use the mapped project from the appropriate source map.

## Common Tie-Breakers

- Working memory vs long-term memory: `personal/os/memory/WORKING_MEMORY.md` is short and current; `personal/os/memory/LONG_TERM_MEMORY.md` is for durable facts that should survive beyond the week. Core keeps `os/memory/WORKING_MEMORY.template.md` and `os/memory/LONG_TERM_MEMORY.template.md` as public-safe shapes.
- Compiled truth vs ordinary memory: use `personal/os/memory/compiled-truth/` when future agents need both the current private synthesis and the evidence timeline that produced it. Core keeps the public-safe template shape.
- Decisions log vs context: if the value is "we decided X on this date," use `personal/os/memory/DECISIONS_LOG.md` for live personal state. Use `os/memory/DECISIONS_LOG.md` only for publishable AgentOS architecture decisions. If the value is "future agents need to know X about the world/project," use `os/context/` for public-safe context or `personal/os/context/` for private context.
- Memory vs agent history: if it is specific to one agent's runs, keep it with that agent unless it affects the whole OS.
- Memory vs backlog: if it is a candidate action rather than a fact or decision, use `personal/os/playbook/BACKLOG.md` for live private backlog state, `os/playbook/BACKLOG.md` for public-safe Core templates, or the relevant issue tracker.
- Memory vs propagation queue vs issue tracker: if an agent output proposes a private or tentative durable update but approval, confidence, or target placement is still unresolved, add it to `personal/os/memory/propagation-review/QUEUE.md` instead of editing canonical state directly. If it is public-safe actionable project work, use the relevant issue tracker or mapped project.

## Update Rules

- Keep live working memory short in `personal/os/memory/WORKING_MEMORY.md`. Remove or move stale items instead of letting it become a journal.
- Append durable personal decisions with concrete dates when possible; use Core memory only for publishable AgentOS architecture decisions.
- For live compiled-truth pages under `personal/os/memory/compiled-truth/`, update the current synthesis while preserving the timeline as append-only evidence. Core keeps only the template shape.
- Do not overwrite user corrections with weaker generated reports.
- Preserve the difference between evidence and canonical state: generated reports are evidence until filed in the right inbox, promoted into the appropriate Personal Overlay file, Core architecture file, mapped project, issue tracker, or another canonical layer.
- Treat propagation queue entries as non-canonical until approved and applied.

## Provenance

Record enough source context for future agents to tell whether a memory came from the user, a local artifact, a mapped project, a connector, or an external source. Use dates for decisions and time-sensitive memories.

## Handoff Rules

- If a memory changes public-safe Core/project routing, update `os/context/SOURCE_MAP.md`; if it changes live, private, local, or account-specific routing, update `personal/os/context/SOURCE_MAP.md`.
- If a memory changes how a workflow should run, update `os/skills/` or `os/playbook/` instead of leaving the rule only in memory.
- If a memory implies a new recurring job, update `personal/os/agents/` or `personal/os/automations/` after the workflow has a verified manual run; use `os/agents/` only for reusable public-safe templates or examples.
