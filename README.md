# AgentOS

AgentOS is a portable Markdown control plane for agentic tools. It gives agents a stable way to find operating instructions, routing rules, reusable skills, memory templates, safety policies, verification checks, and publication workflow without requiring any one agent harness or private account.

This public repository contains AgentOS Core: the reusable, public-safe scaffolding. A real local installation may also have a Personal Overlay for private user-specific state.

This project started as an implementation of [aidbagentos.ai](https://aidbagentos.ai/).

## Core And Overlay

- AgentOS Core lives under `$root/os/`.
- The Personal Overlay lives under `$root/personal/os/`.
- `$root` means the AgentOS repository root.

Core files are meant to be shareable. They describe templates, policy, validation, routing, and generic examples. They should not contain a real person's private identity, account data, live agent histories, generated briefs, run logs, or private project state.

Personal Overlay files are local ignored state. They can hold the real user's identity, context, memory, connections, live automations, live agent definitions, reports, histories, queues, and generated outputs. The tracked `personal/` tree contains only public-safe empty `.gitkeep` files so the generic shape is visible.

Agents should read `$root/os/` first. Then, when present and relevant, they should read matching files under `$root/personal/os/`. A public clone is still usable without private context; the Personal Overlay is optional.

See `os/playbook/PERSONAL_OVERLAY.md` for the full load and migration rule.

## Quickstart

Install AgentOS wherever you want it to live. Common choices are a folder under the current user's home directory, but AgentOS does not require or assume a default path. In the examples below, replace `<agentos-home>` with the resolved path to your chosen checkout.

Prefer a local directory that is not cloud-synced. Avoid placing AgentOS inside folders managed by iCloud Drive, OneDrive, Dropbox, Google Drive, or similar sync tools; AgentOS can contain ignored private overlay state, Git metadata, generated reports, and agent-written files that are better kept in a normal local development directory.

Portable path notation:

- macOS/Linux: `<home>/.agents/AGENTS.md`
- Windows: `<home>\.agents\AGENTS.md`

That file is the canonical global instruction file. Harness-specific instruction files keep their own locations and receive a small managed adapter block that points to the canonical file.

The default adapter targets are:

- Codex: `<home>/.codex/AGENTS.md`
- Claude Code: `<home>/.claude/CLAUDE.md`
- Gemini CLI: `<home>/.gemini/GEMINI.md`

By default, the installer updates default adapters only when their harness directory already exists. Use `--all-default-adapters` to create all default adapter files, and repeat `--adapter <path>` for extra harnesses such as OpenClaw, Hermes, Antigravity, or another tool with a known instruction-file path.

### Agent-Assisted Setup

Give this prompt to your agent:

```text
Install AgentOS for me.

1. Ask me where AgentOS should live. If I do not have a preference, suggest a conventional local development path that is not inside iCloud Drive, OneDrive, Dropbox, Google Drive, or another cloud-synced folder. Do not assume or require a default path.
2. Clone https://github.com/Jordak/AgentOS.git into my chosen path.
3. From that AgentOS checkout, run the installer self-test:
   python3 scripts/install_global_agent_instructions.py --self-test
   Confirm the self-test uses temporary directories and does not touch my real home directory.
4. Run the installer dry-run:
   python3 scripts/install_global_agent_instructions.py --agentos-home <resolved-agentos-home>
5. Show me exactly which files would be created, backed up, or changed. Do not run the write command until I explicitly approve.
6. After I approve, run:
   python3 scripts/install_global_agent_instructions.py --agentos-home <resolved-agentos-home> --no-dry-run
7. Run the drift check:
   python3 scripts/install_global_agent_instructions.py --agentos-home <resolved-agentos-home> --check
8. Summarize what changed, where backups were written, and whether the check passed.
```

Use the Python 3 command that works on your machine. On some systems that is `python3`; on others it may be `python` or `py -3`.

### Manual Setup

```bash
git clone https://github.com/Jordak/AgentOS.git <agentos-home>
cd <agentos-home>
python3 scripts/install_global_agent_instructions.py --self-test
python3 scripts/install_global_agent_instructions.py --agentos-home <agentos-home>
```

Review the dry-run output. It should tell you which global instruction files would be created, backed up, or changed. Only after you approve those changes, run:

```bash
python3 scripts/install_global_agent_instructions.py --agentos-home <agentos-home> --no-dry-run
python3 scripts/install_global_agent_instructions.py --agentos-home <agentos-home> --check
```

## First Read Sequence

For an agent or human using an AgentOS checkout for the first time:

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
