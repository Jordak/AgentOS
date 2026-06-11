# AgentOS Skill Contract

Status: contract v1.

Use this contract when creating, upgrading, auditing, or preparing durable AgentOS skills for machine-local exposure.

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

When these facts live in a manifest, use the Markdown manifest API: exact third-level headings shaped as ``### `skill-name` `` plus exact, case-sensitive list labels shaped as `- Field name: value`. Keep long-form safety, filing, verification, provenance, and maintenance notes as readable Markdown prose. Add a structured sidecar only when scripts or validators need deterministic typed data that cannot be represented safely by the narrow Markdown convention.

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
- Project-specific implementation artifacts and public-safe actionable project work live in the mapped project or its issue tracker.
- External account artifacts stay in their source system unless AgentOS has a safe pointer or summary rule.
- Generated recommendations that would change durable AgentOS state should be classified before filing: use GitHub issues or mapped-project trackers for public-safe actionable project work, use `personal/os/memory/propagation-review/QUEUE.md` for private/tentative/connector-derived/personal/cross-project/pre-issue proposals, and edit canonical files directly only when the user explicitly asked for the exact edit in the current request or approved a specific proposal.

Do not scatter the same durable fact across multiple layers. Link instead.

## Propagation Rule

Skills with `local-write` or `mixed` mutability that produce reports, reviews, briefs, digests, or recommendations must route durable follow-up through the right inbox instead of applying generated recommendations by default. Use issue trackers for public-safe actionable project work, mapped-project destinations for project-owned work, and the propagation review queue for private/tentative/connector-derived/personal/cross-project/pre-issue AgentOS proposals.

Inline chat approval can approve an exact edit or a specific queue entry, but it should not silently become the durable record for unresolved generated recommendations. Direct canonical edits are appropriate when the user explicitly asks for the exact edit, or when applying an approved queue entry or issue-backed change.

## Verification Coverage

A skill's verification guidance should test observable behavior, not internal style. Good checks include:

- source and citation checks for current claims;
- artifact existence and path checks for generated files;
- connector safety checks before sends, uploads, labels, or permission changes;
- privacy checks before summaries, commits, public posts, or shared artifacts;
- output-format checks for HTML, DOCX/PDF, slides, sheets, or issue bodies;
- filing checks that generated state landed in the intended home.

## Orchestration Loops

Loop-shaped or mutating skills that coordinate repeated steps, call other workflows, wait on human decisions, or need safe recovery after interruption should also follow `os/skills/ORCHESTRATION_LOOPS.md`.

That convention defines AgentOS guidance for Authorization Boundaries, effort policy, Workflow Invocation References, Callback-First Invocation, Minimal Assignment Packets, Workflow Results, Recovery Records, Recovery Checkpoints, Blocking Human Decisions, parallel Called Workflows, and Integration Ownership. Do not copy the full convention into every skill; link to it when the skill's contract needs loop-specific boundaries, model or effort selection, or recovery behavior.

## Exposure Rules

Canonical public AgentOS skills live under `os/skills/`. Canonical private skills can live under `personal/os/skills/<skill-name>/SKILL.md`. Personal Overlay skills implement this same Core contract; do not fork a separate private skill contract in v1.

A Personal Overlay skill counts as a maintained canonical private skill only when `personal/os/skills/MANIFEST.md` has an entry for it with `Lifecycle status: maintained`. Directory-only private skills are drafts or ad hoc local files until the private manifest records their governance facts. Use `os/skills/PERSONAL_OVERLAY_MANIFEST.template.md` as the public-safe template when creating the ignored private manifest. Core and Personal Overlay skill manifests use the same Markdown manifest API in v1.

Private config is optional for private skills. Since `personal/os/skills/<skill-name>/SKILL.md` is already private, stable private settings may live directly in that file. Use `personal/os/skills/<skill-name>/CONFIG.md` when settings are volatile, machine-specific, generated, profile-like, useful to audit separately, or needed by scripts. Private inputs to a reusable Core skill belong in `personal/os/skills/<core-skill>/CONFIG.md`, not in the Core skill source.

The private skills manifest should reference `personal/os/context/SOURCE_MAP.md` for nontrivial private source routes and `personal/os/connections/CONNECTIONS.md` for connector/account permissions instead of duplicating their full inventories.

Installed harness adapters are current-machine artifacts, not portable AgentOS state. Do not record machine-local adapter paths or exposure state in `os/skills/MANIFEST.md` or `personal/os/skills/MANIFEST.md`.

Installed skills that adapt private live agents must route private job definitions, histories, reports, briefs, queues, and generated outputs to `personal/os/agents/`, `personal/os/automations/`, or Personal Overlay skill config. They must not route private live agent state into Core `os/agents/` or `os/automations/`.

Use `os/skills/expose-skills/SKILL.md` and its bundled script when the active machine should expose Core skills through global symlink adapters. `expose-skills` is Core-only, does not scan or expose Personal Overlay skills, and replaces existing same-name Core skill directories only through explicit backup-backed replacement.

Do not automatically create `personal/os/skills/MANIFEST.md` just because private skill directories exist. Create or update it only when the user asks, or when the current task is explicitly maintaining, importing, promoting, or governance-reviewing a private skill.

If a harness needs intentionally different skill behavior, prefer a canonical thin adapter skill under `os/skills/` or a private skill under `personal/os/skills/` rather than untracked drift in a current-machine installed skill.

When changing skill behavior:

1. Read `os/skills/MANIFEST.md`.
2. Edit the canonical source first.
3. Run or plan `expose-skills` when current-machine Core skill discoverability matters.
4. Run the skill's verification guidance or note why it was not run.

## Contract Adoption

Existing skills do not need to be fully rewritten in one pass. Use the manifest to classify each skill as:

- `full`: the skill itself clearly contains the contract facts.
- `partial`: the skill plus manifest together contain enough facts to operate.
- `needs-upgrade`: important contract facts are missing.
- `thin-adapter`: the skill intentionally routes to a fuller agent or workflow.

Prefer small upgrades made during real work over speculative rewrites.
