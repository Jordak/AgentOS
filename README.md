# AgentOS

AgentOS is a portable Markdown control plane for agentic tools. It separates reusable operating scaffolding from private user-specific state.

## Core And Personal Overlay

- AgentOS Core lives under `$root/os/`.
- The Personal Overlay lives under `$root/personal/os/`.
- `$root` means the AgentOS repository root.

Read `$root/os/` first. Then read matching files under `$root/personal/os/` when present. Personal Overlay files can add private detail or override user-specific facts.

The tracked `personal/` tree keeps public-safe empty `.gitkeep` files so the generic directory shape is visible, while ordinary files under `personal/` are ignored by git.

Generated reports, histories, logs, briefs, and other outputs derived from real private state belong in `$root/personal/os/` by default. AgentOS Core may keep only sanitized examples or templates.

See `os/playbook/PERSONAL_OVERLAY.md` for the full load and migration rule.

## Publication Safety

Do not make a formerly private AgentOS repository public after private files have existed in its history.

The publication path is to validate the migrated working tree, confirm private overlay files are ignored, run a staged-snapshot privacy scan against the Git index, and create a fresh-history public repository from the prechecked publishable file set.

See `os/playbook/PUBLICATION.md` for the publication workflow.

## Entry Points

- `AGENTS.md`: generic adapter entry point.
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

The validator reads local files only. Publication checks are separate from normal maintenance validation and are described in `os/playbook/PUBLICATION.md`.

For publication safety, run:

```bash
python3 os/verification/scripts/validate_agentos.py --publication-precheck
scripts/check_staged_publication_secrets.sh
```

Use `scripts/check_working_tree_secrets.sh` as an advisory day-to-day scan of the mixed working tree. Install the included pre-commit hook to validate and scan the staged snapshot before commits:

```bash
pre-commit install
```
