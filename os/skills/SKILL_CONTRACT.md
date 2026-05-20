# AgentOS Skill Contract

Status: contract v1.

Use this contract when creating, upgrading, auditing, or preparing durable AgentOS skills for machine-local mirroring.

This contract is not a routing catalog. Harnesses may already expose skill names, descriptions, and paths in context. The contract defines the maintenance facts AgentOS needs so skills can stay portable, safe, verifiable, and file-aware across harnesses.

## Required Shape

Durable AgentOS skills should make these facts clear, either in frontmatter, in short sections, or in the skills manifest:

- Name: stable skill identifier.
- Purpose: what repeated workflow this skill exists to perform.
- Inputs: what the user or agent must provide before the workflow can run.
- Output artifact: conversational answer, Markdown, HTML, DOCX/PDF, issue, draft, local file, external update, or another artifact.
- Mutability: read-only, local-write, connector-write, external-write, or mixed.
- Tools and connectors: local files, browser/web, GitHub, Gmail, Calendar, Drive, Documents, Spreadsheets, Presentations, or other surfaces.
- Safety: actions that require the user's approval before proceeding.
- Phases: the high-level workflow steps.
- Quality bar: what makes the output good enough.
- Verification: checks to run before trusting or delivering the result.
- Filing rules: where generated artifacts, decisions, notes, or state updates belong.

## Mutability Levels

Use the narrowest level that describes normal operation:

- `read-only`: reads context and returns an answer; does not write files or external state.
- `local-write`: may write local AgentOS files or local artifacts.
- `connector-write`: may write through a connected service after approval or an explicit pre-approved rule.
- `external-write`: may post, send, publish, change permissions, or otherwise affect people or external accounts.
- `mixed`: combines more than one level depending on mode.

If a skill can send messages, publish, delete, change sharing, upload, overwrite, label external data, or create automations, its safety section must say what requires approval.

## Filing Rules

Every durable skill should state where outputs go:

- Live agent-owned reports and run histories usually live with the relevant `personal/os/agents/` directory; `os/agents/` is for public-safe templates and examples.
- Live automation records, delivery queues, and run histories live under `personal/os/automations/` or the relevant Personal Overlay agent/memory directory; `os/automations/` is for templates, examples, and policy.
- Reusable workflow changes live under `os/skills/`.
- Live durable decisions and lessons live under `personal/os/memory/`; publishable AgentOS architecture decisions can live under `os/memory/`.
- Project-specific implementation artifacts live in the mapped project from the appropriate source map.
- External account artifacts stay in their source system unless AgentOS has a safe pointer or summary rule.
- Generated recommendations that would change durable AgentOS state go through `personal/os/memory/propagation-review/QUEUE.md` before canonical edits, unless the user explicitly asked for the exact edit in the current request.

Do not scatter the same durable fact across multiple layers. Link instead.

## Propagation Rule

Skills with `local-write` or `mixed` mutability that produce reports, reviews, briefs, digests, or recommendations must use the propagation review queue for durable AgentOS state changes. This applies to proposed updates to identity, context, memory, source-map, skills, agents, verification, playbook, backlog, or automation state.

Inline chat approval can approve a queue entry, but it should not replace the queue entry. Direct canonical edits are appropriate when the user explicitly asks for the exact edit, or when applying an approved queue entry.

## Verification Coverage

A skill's verification guidance should test observable behavior, not internal style. Good checks include:

- source and citation checks for current claims;
- artifact existence and path checks for generated files;
- connector safety checks before sends, uploads, labels, or permission changes;
- privacy checks before summaries, commits, public posts, or shared artifacts;
- output-format checks for HTML, DOCX/PDF, slides, sheets, or issue bodies;
- filing checks that generated state landed in the intended home.

## Mirror Rules

Canonical AgentOS skills live under `os/skills/`.

Installed harness mirrors are current-machine artifacts, not portable AgentOS state. Do not record machine-local mirror paths or mirror sync status in `os/skills/MANIFEST.md`.

Installed skills that adapt private live agents must route private job definitions, histories, reports, briefs, queues, and generated outputs to `personal/os/agents/`, `personal/os/automations/`, or Personal Overlay skill config. They must not route private live agent state into Core `os/agents/` or `os/automations/`.

Use `os/skills/audit-skill-mirrors/SKILL.md` and its bundled script to audit or sync mirrors for the active machine. If a harness needs intentionally different behavior, prefer a canonical thin adapter skill under `os/skills/` rather than untracked drift in a local mirror.

When changing skill behavior:

1. Read `os/skills/MANIFEST.md`.
2. Edit the canonical source first.
3. Run or plan `audit-skill-mirrors` when current-machine discoverability matters.
4. Run the skill's verification guidance or note why it was not run.

## Contract Adoption

Existing skills do not need to be fully rewritten in one pass. Use the manifest to classify each skill as:

- `full`: the skill itself clearly contains the contract facts.
- `partial`: the skill plus manifest together contain enough facts to operate.
- `needs-upgrade`: important contract facts are missing.
- `thin-adapter`: the skill intentionally routes to a fuller agent or workflow.

Prefer small upgrades made during real work over speculative rewrites.
