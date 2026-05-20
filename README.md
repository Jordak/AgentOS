# AgentOS

AgentOS is a portable Markdown control plane for agentic tools. It gives agents a stable way to find operating instructions, routing rules, reusable skills, memory templates, safety policies, verification checks, and publication workflow without requiring any one agent harness or private account.

This public repository contains AgentOS Core: the reusable, public-safe scaffolding. A real local installation may also have a Personal Overlay for private user-specific state.

## Core And Overlay

- AgentOS Core lives under `$root/os/`.
- The Personal Overlay lives under `$root/personal/os/`.
- `$root` means the AgentOS repository root.

Core files are meant to be shareable. They describe templates, policy, validation, routing, and generic examples. They should not contain a real person's private identity, account data, live agent histories, generated briefs, run logs, or private project state.

Personal Overlay files are local ignored state. They can hold the real user's identity, context, memory, connections, live automations, live agent definitions, reports, histories, queues, and generated outputs. The tracked `personal/` tree contains only public-safe empty `.gitkeep` files so the generic shape is visible.

Agents should read `$root/os/` first. Then, when present and relevant, they should read matching files under `$root/personal/os/`. A public clone is still usable without private context; the Personal Overlay is optional.

See `os/playbook/PERSONAL_OVERLAY.md` for the full load and migration rule.

## How To Start

For an agent or human landing here for the first time:

1. Read `AGENTS.md`.
2. Read `os/INDEX.md`.
3. Read `os/playbook/PERSONAL_OVERLAY.md` before storing or looking for private state.
4. For broad routing, authority, safety, or filing questions, read `os/RESOLVER.md`.
5. Use the narrowest relevant Core file for the task.

## Publication Safety

Do not make a formerly private AgentOS repository public after private files have existed in its history.

The publication path is to validate the migrated working tree, confirm private overlay files are ignored, run staged and tree privacy scans against the publishable file set, and create a fresh-history public repository. Keep old private Git history out of the public repository.

See `os/playbook/PUBLICATION.md` for the publication workflow.

## Entry Points

- `AGENTS.md`: agent adapter entry point.
- `CLAUDE.md`: Claude Code adapter.
- `DOMAIN.md`: domain language for the publishing architecture.
- `os/INDEX.md`: Core map.
- `os/RESOLVER.md`: routing, authority, safety, and filing tie-breakers.
- `os/playbook/AGENTOS_PLAYBOOK.md`: operating manual.
- `os/playbook/PERSONAL_OVERLAY.md`: Core/Overlay load and migration rules.
- `os/playbook/PUBLICATION.md`: fresh-history publication workflow.

## Validation

Run the local validator:

```bash
python3 os/verification/scripts/validate_agentos.py
```

The default validator reads local files only and runs structural checks plus deterministic publication/privacy checks.

For shell-backed publication safety scans, run:

```bash
scripts/check_staged_publication_secrets.sh
scripts/check_publication_tree_secrets.sh HEAD
```

Use `scripts/check_working_tree_secrets.sh` as an advisory day-to-day scan of the mixed working tree. Install the included hooks to validate and scan commits and pushes:

```bash
scripts/install_agentos_hooks.sh
```
