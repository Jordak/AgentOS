# Personal Overlay

Status: publishing architecture v1.

AgentOS separates publishable scaffolding from private user-specific state with two mirrored roots:

- AgentOS Core root: `$root/os/`
- Personal Overlay root: `$root/personal/os/`

`$root` means the location where AgentOS is installed.

## Load Rule

Read AgentOS Core first. Then read matching files under the Personal Overlay when present.

If both roots contain guidance for the same topic, the Personal Overlay may add private detail or override user-specific facts. It should not silently replace Core behavior unless the personal file says that it does.

## Discovery Rule

The Personal Overlay is intentionally ignored local state. Do not treat ignore-aware or git-aware discovery as evidence that Personal Overlay files are absent.

Absence must be proven with a direct filesystem read or listing of the canonical Personal Overlay root that does not apply git ignore rules. If discovery returns only tracked skeleton files such as `.gitkeep`, treat the result as inconclusive until a direct filesystem check has also found no matching private files.

Use any direct filesystem mechanism available in the current environment. Examples include reading a known expected path directly, using a filesystem API that recursively lists regular files under `personal/os/`, POSIX `find personal/os -type f`, PowerShell `Get-ChildItem -Path personal/os -File -Recurse -Force`, or ignore-including search flags such as `rg --files -uuu personal/os/` when ripgrep is installed.

Do not use default ignore-aware searches, IDE indexes, Git file APIs, or MCP/resource indexes as absence evidence unless they are known to include ignored files.

## Canonical Local Overlay

The Personal Overlay is ignored local state. In a multi-worktree setup, ignored files under `personal/os/` are not copied or synchronized into feature worktrees.

Treat the canonical Personal Overlay as the `personal/os/` directory in the primary local AgentOS checkout. The primary checkout is the long-lived local AgentOS directory that owns the user's ignored private state; it is not defined by whichever branch name the current process is on.

When an agent is running from an isolated feature worktree and is routed to a Personal Overlay path, it should resolve reads against the primary checkout's `personal/os/` unless the user or harness explicitly assigned a different private overlay workspace. If the primary checkout is unknown, ask before assuming that the current worktree's mostly empty `personal/os/` skeleton is authoritative.

Writes to the canonical Personal Overlay are allowed only when the task is Personal Overlay work and the agent has clear path ownership. Parallel agents may write different Personal Overlay subtrees, but they should not edit the same ignored file concurrently.

Do not broad-copy ignored Personal Overlay contents into feature worktrees to make paths line up. Copy only narrowly requested private inputs when a user-approved workflow requires it, and never force-add Personal Overlay files to Git.

## Directory Shape

AgentOS Core and the Personal Overlay use the same layer names:

- `identity/`
- `context/`
- `memory/`
- `connections/`
- `agents/`
- `skills/`
- `verification/`
- `playbook/`
- `automations/`

The tracked `personal/` tree keeps empty `.gitkeep` files so the public-safe directory shape is visible. Ordinary files under `personal/` are ignored by git.

Do not track `.gitkeep` files in private-specific subdirectories when the directory name itself reveals personal state, project names, account names, live agent names, or private workflow names. Keep only generic skeleton paths in Core; private-specific overlay paths can exist locally while remaining fully ignored.

AgentOS Core defines no remote versioning policy for Personal Overlay files in v1. Treat the Personal Overlay as local ignored state unless the user makes a separate private-backup decision with its own threat model.

## Core Files

Use a normal Markdown filename when a Core file is safe and useful as-is for any user.

Use `.template.md` when the file needs personal facts before it becomes real user state.

Examples:

- `$root/os/playbook/PORTABILITY.md` can be a Core Default.
- `$root/os/identity/USER.template.md` can describe the shape of a personal identity file.
- `$root/personal/os/identity/USER.md` can hold the private live identity file.

## Generated Outputs

Generated outputs derived from a real person's private data, project state, memory, interests, accounts, or work context belong in the Personal Overlay by default.

This includes reports, briefs, histories, run logs, weekly reviews, scout outputs, inbox/calendar summaries, resume/career outputs, and agent-owned generated artifacts.

AgentOS Core may contain sanitized example outputs or templates that demonstrate shape, but not generated artifacts based on real private state.

If an output path is not explicitly public-safe, route it to `personal/os/` first. Promote only sanitized examples or reusable templates into Core after review.

Examples:

- `$root/personal/os/agents/assistant-agent/reports/YYYY-MM-DD.html`
- `$root/personal/os/agents/current-awareness-agent/briefs/YYYY-MM-DD.html`
- `$root/personal/os/memory/weekly-review/YYYY-MM-DD.html`
- `$root/os/agents/example-agent/reports/example.html`

## Agent Instances

Named live agents configured around a real person's interests, routines, connected-account assumptions, private output paths, or personal project state belong in the Personal Overlay by default.

AgentOS Core may contain agent templates, contracts, and sanitized examples that demonstrate the structure of a durable role.

Core `os/agents/` is not a live job registry. It must not contain private named agent histories, queues, brief archives, report archives, account-specific instructions, or generated outputs.

Examples:

- `$root/personal/os/agents/current-awareness-agent/`
- `$root/personal/os/agents/project-scout-agent/`
- `$root/personal/os/agents/assistant-agent/`
- `$root/personal/os/agents/learning-companion-agent/`
- `$root/os/agents/AGENT_TEMPLATE.md`
- `$root/os/agents/example-agent/`

## Skills

Reusable skill procedures, safety contracts, and verification workflows may live in AgentOS Core when they are useful without private user-specific state.

Personal Overlay skills implement the Core skill contract in `$root/os/skills/SKILL_CONTRACT.md`; AgentOS does not define a separate private skill contract in v1.

A maintained canonical private skill needs an ignored manifest entry under `$root/personal/os/skills/MANIFEST.md` with `Lifecycle status: maintained`. Directory-only private skill folders are drafts or ad hoc local files until the manifest records their governance facts. Use the public-safe template at `$root/os/skills/PERSONAL_OVERLAY_MANIFEST.template.md` when creating the ignored private manifest.

Private config is optional for private skills. Since `$root/personal/os/skills/<skill-name>/SKILL.md` is already private, stable private settings can live directly in the private skill. Use a separate config file when settings are volatile, machine-specific, generated, profile-like, useful to audit separately, or when a reusable Core skill needs private inputs without changing the Core source.

Personal Overlay skill config may include local paths, account IDs, artifact roots, user-specific defaults, private examples, and current-machine adapter locations.

Core skills that support private configuration should name the optional config path they read, usually:

`$root/personal/os/skills/<skill-name>/CONFIG.md`

Personal Overlay config is Markdown-first. Use clear labels and fenced or inline code for paths and identifiers so agents can read it naturally.

Add a structured sidecar such as `CONFIG.json` or `CONFIG.yaml` only when scripts or validators need deterministic parsing.

Do not make `$root/personal/os/skills/MANIFEST.md` the source map or connection inventory. Stable project directories, repositories, document folders, account workspaces, connector maturity, and account-specific approval allowances belong in `$root/personal/os/context/SOURCE_MAP.md` or `$root/personal/os/connections/CONNECTIONS.md`; manifest entries should reference those files for nontrivial dependencies.

Skills that are thin adapters to live private agents or workflows centered on private artifacts belong in the Personal Overlay by default.

Examples:

- `$root/os/skills/research-brief/SKILL.md`
- `$root/os/skills/expose-skills/SKILL.md`
- `$root/personal/os/skills/current-awareness-agent/CONFIG.md`
- `$root/personal/os/skills/current-awareness-agent/SKILL.md`
- `$root/personal/os/skills/private-document-maintenance/SKILL.md`

## Context

Live context files usually describe a real person's projects, career, source map, tools, interests, work boundaries, and account-specific constraints. These belong in the Personal Overlay by default.

AgentOS Core may keep context structure, templates, public-safe examples, and generic AgentOS glossary terms.

Sensitive-boundary patterns belong in Core as templates. The live boundary itself belongs in the Personal Overlay.

Examples:

- `$root/os/context/README.md`
- `$root/os/context/SOURCE_MAP.template.md`
- `$root/os/context/PROJECTS.template.md`
- `$root/os/context/TOOLS.template.md`
- `$root/os/context/WORK_FIREWALL.template.md`
- `$root/personal/os/context/SOURCE_MAP.md`
- `$root/personal/os/context/CAREER.md`
- `$root/personal/os/context/CV.md`
- `$root/personal/os/context/INTERESTS.md`
- `$root/personal/os/context/PROJECTS.md`
- `$root/personal/os/context/WORK.md`
- `$root/personal/os/context/TOOLS.md`
- `$root/personal/os/context/WORK_FIREWALL.md`

## Identity

Live identity files describe a real person, their preferences, boundaries, communication style, and unanswered personal questions. These belong in the Personal Overlay by default.

AgentOS Core may keep identity templates and public-safe collaboration guidance that explain what to capture without containing a real person's private details.

Examples:

- `$root/os/identity/README.md`
- `$root/os/identity/USER.template.md`
- `$root/os/identity/COMMUNICATION.template.md`
- `$root/os/identity/BOUNDARIES.template.md`
- `$root/os/identity/QUESTIONS.template.md`
- `$root/personal/os/identity/USER.md`
- `$root/personal/os/identity/COMMUNICATION.md`
- `$root/personal/os/identity/BOUNDARIES.md`
- `$root/personal/os/identity/QUESTIONS.md`

## Memory

Live memory files record what changed, what was decided, what should persist, and what needs to be remembered across future runs for a real person or private AgentOS instance. These belong in the Personal Overlay by default.

AgentOS Core may keep memory mechanics, templates, propagation rules, compaction guidance, and Core architecture ADRs.

Decisions about AgentOS Core architecture may live in Core docs or ADRs. Decisions about a real person's personal state, projects, preferences, automations, or private migration history belong in the Personal Overlay.

Examples:

- `$root/os/memory/README.md`
- `$root/os/memory/COMPACTION_RULES.md`
- `$root/os/memory/WORKING_MEMORY.template.md`
- `$root/os/memory/LONG_TERM_MEMORY.template.md`
- `$root/os/memory/DECISIONS_LOG.template.md`
- `$root/os/memory/compiled-truth/TEMPLATE.md`
- `$root/os/memory/propagation-review/QUEUE.template.md`
- `$root/personal/os/memory/WORKING_MEMORY.md`
- `$root/personal/os/memory/LONG_TERM_MEMORY.md`
- `$root/personal/os/memory/DECISIONS_LOG.md`
- `$root/personal/os/memory/compiled-truth/*.md`
- `$root/personal/os/memory/propagation-review/QUEUE.md`
- `$root/personal/os/memory/weekly-review/*.html`

## Connections

Live connection files describe real accounts, connectors, calendars, repositories, permissions, and account-specific safety constraints. These belong in the Personal Overlay by default.

AgentOS Core may keep connection schemas, safety categories, and generic approval patterns.

Core can say to ask before sends, posts, deletes, permission changes, credential handling, MFA, purchases, external writes, and other external consequences. The Personal Overlay says which real accounts and connectors exist and what their account-specific constraints are.

Examples:

- `$root/os/connections/CONNECTIONS.template.md`
- `$root/os/connections/SAFETY_RULES.md`
- `$root/personal/os/connections/CONNECTIONS.md`
- `$root/personal/os/connections/GMAIL.md`
- `$root/personal/os/connections/GOOGLE_CALENDAR.md`
- `$root/personal/os/connections/GITHUB.md`

## Automations

Live automation files describe real schedules, prompts, destinations, accounts, delivery paths, activation state, and current runtime choices. These belong in the Personal Overlay by default.

AgentOS Core may keep automation schemas, safety policy, reusable activation standards, and sanitized examples.

Even when an automation pattern is reusable, the live schedule, destination, account, delivery path, and activation state are personal.

Core `os/automations/` is not a live automation registry. It may describe the registry shape and activation policy, but live jobs, run histories, queues, delivery records, and generated artifacts belong in `personal/os/automations/` or the relevant Personal Overlay agent/memory directory.

Examples:

- `$root/os/automations/AUTOMATIONS.md`
- `$root/os/automations/AUTOMATIONS.template.md`
- `$root/personal/os/automations/AUTOMATIONS.md`
- `$root/personal/os/automations/weekly-agentos-review.md`
- `$root/personal/os/automations/current-awareness-email-brief.md`

## Verification

Reusable validators, schemas, sanitized fixtures, and sanitized example reports may live in AgentOS Core.

Live verification reports and benchmark results belong in the Personal Overlay by default when they reflect a real private AgentOS instance, private project state, local paths, account availability, or harness-specific run evidence.

Fixtures are Core-safe only when they contain no private facts, local paths, private reports, private project state, or user-specific expectations.

Examples:

- `$root/os/verification/scripts/validate_agentos.py`
- `$root/os/verification/retrieval/fixtures.json`
- `$root/os/verification/retrieval/questions.json`
- `$root/os/verification/playbook-activation/fixtures.json`
- `$root/os/verification/*/README.md`
- `$root/personal/os/verification/retrieval/reports/`
- `$root/personal/os/verification/playbook-activation/reports/`
- `$root/personal/os/verification/markdown-audit/`

## Root Adapters

Root adapter files such as `$root/AGENTS.md` and `$root/CLAUDE.md` are publishable repository support files, not files under the Core Root. They may live at repository root when they are generic launchers into AgentOS Core and the optional Personal Overlay.

Publishable root adapters must not contain private identity, private absolute paths, private repository URLs, installed adapter paths, account identifiers, or local machine setup state.

Local adapter install state belongs in the Personal Overlay.

Root adapter pattern:

```md
Read `$root/os/INDEX.md`.
If `$root/personal/os/` exists, apply `os/playbook/PERSONAL_OVERLAY.md`.
```

Examples:

- `$root/AGENTS.md`
- `$root/CLAUDE.md`
- `$root/personal/os/playbook/LOCAL_ADAPTERS.md`
- `$root/personal/os/context/SOURCE_MAP.md`
- `$root/personal/os/skills/<skill-name>/CONFIG.md`

## Migration Rule

Migrate private files atomically:

1. Move the private live file to the matching path under `$root/personal/os/`.
2. Add or preserve the Core Default or `.template.md` file under `$root/os/`.
3. Update references or loader documentation if the file path changed.

Do not leave duplicate private live files in both roots as a long-lived state.

Move private files mostly as-is into the Personal Overlay first. Sanitize or rewrite the Core replacement separately.

Do not mix private-content cleanup with the move unless the cleanup is required to preserve the file's meaning after relocation.
