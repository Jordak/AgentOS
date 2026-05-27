# AgentOS

AgentOS is a portable Markdown control plane for agentic tools. It gives agents a stable way to find operating instructions, routing rules, reusable skills, memory templates, safety policies, verification checks, and publication workflows without requiring any one agent harness or private account.

This public repository is built from the publishable AgentOS file set and centers on AgentOS Core: the reusable, public-safe scaffolding described in [os/INDEX.md](os/INDEX.md). It also includes public-safe support files such as root adapters, docs, scripts, GitHub metadata, and the tracked Personal Overlay skeleton. A real local installation is meant to grow a Personal Overlay for private user-specific state.

This project started as an implementation of [aidbagentos.ai](https://aidbagentos.ai/).

## Core And Overlay

- AgentOS Core lives under `$root/os/`; start with [os/INDEX.md](os/INDEX.md).
- The Personal Overlay lives under `$root/personal/os/`; read the [Personal Overlay playbook](os/playbook/PERSONAL_OVERLAY.md) for the load rule.
- `$root` means the location where AgentOS is installed.

Core files are meant to be shareable. They describe templates, policy, validation, routing, and generic examples. They should not contain a real person's private identity, account data, live agent histories, generated briefs, run logs, or private project state.

Personal Overlay files are local-only state. They can hold the real user's identity, context, memory, connections, live automations, live agent definitions, reports, histories, queues, and generated outputs. The public repository contains only empty placeholders under `personal/` so agents can see where local private files should go. Normal AgentOS publication excludes anything you write there; see [os/playbook/PUBLICATION.md](os/playbook/PUBLICATION.md).

Agents should read Core first. Then, when present and relevant, they should read matching files under the Personal Overlay. A fresh public clone can explain the system, but AgentOS becomes useful as your operating layer after an agent helps you fill in approved private context under `$root/personal/os/`.

See [os/playbook/PERSONAL_OVERLAY.md](os/playbook/PERSONAL_OVERLAY.md) for the full load and migration rule.

## Quickstart

Copy this prompt into your agent:

```text
Install AgentOS for me.

1. Ask me where AgentOS should live. If I do not have a preference, suggest a conventional local development path that is not inside iCloud Drive, OneDrive, Dropbox, Google Drive, or another cloud-synced folder. Do not assume or require a default path.
2. Clone https://github.com/Jordak/AgentOS.git into my chosen path.
3. From that AgentOS checkout, run the installer self-test:
   python3 scripts/install_global_agent_instructions.py --self-test
   Confirm the self-test uses temporary directories and does not touch my real home directory.
4. Run the installer dry-run:
   python3 scripts/install_global_agent_instructions.py --agentos-home <resolved-agentos-home>
   Ask me which agent harnesses I use, meaning the tools I use to run agents, such as Codex, Claude Code, Google Antigravity, OpenClaw, Hermes, or something else. If CODEX_HOME, CLAUDE_CONFIG_DIR, or GEMINI_CLI_HOME is set, confirm the dry-run targets those harness homes. If I use Google Antigravity and GEMINI_CLI_HOME is set, explain that current official Antigravity docs still name <home>/.gemini/GEMINI.md as the default global rules/context path; ask whether to include --adapter <home>/.gemini/GEMINI.md so that default Antigravity file is managed explicitly. For harnesses outside the defaults, ask me for the current instruction-file path before adding any --adapter <path> flags. Include the same --adapter <path> flags in this dry-run and every later write/check/remove command.
5. Show me exactly which files would be created, backed up, or changed. Do not run the write command until I explicitly approve.
6. After I approve, run:
   python3 scripts/install_global_agent_instructions.py --agentos-home <resolved-agentos-home> --no-dry-run
7. Run the drift check:
   python3 scripts/install_global_agent_instructions.py --agentos-home <resolved-agentos-home> --check
   If extra --adapter <path> flags were used above, repeat those exact flags here.
8. Run the Run AgentOS Doctor skill. As part of that skill workflow, use its deterministic helper script for setup facts:
   python3 os/skills/run-agentos-doctor/scripts/agentos_doctor.py --agentos-home <resolved-agentos-home>
   If extra --all-default-adapters or --adapter <path> flags were used above, repeat those exact flags here. Treat script warnings as facts or next-step recommendations, then use agent judgment for ambiguous setup notes such as automation drafts or disabled notes. Do not make changes without approval.
9. Summarize what changed, where backups were written, whether the adapter check passed, and what Run AgentOS Doctor recommends.
10. Ask me whether I want AgentOS skills to be discoverable from my harnesses. If I do, use the mirror-skills workflow to check Core skills and Personal Overlay skills, show me the audit result, and ask before syncing any files outside this checkout.
11. Ask me if I want to hear how to get the most out of AgentOS.
```

Use the Python 3 command that works on your machine. On some systems that is `python3`; on others it may be `python` or `py -3`.

<details>
<summary>Manual setup commands</summary>

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
python3 os/skills/run-agentos-doctor/scripts/agentos_doctor.py --agentos-home <agentos-home>
```

If you use `--all-default-adapters` or any custom `--adapter <path>` flags, repeat those same flags on the dry-run, write, check, and remove commands.
Repeat those same flags when using Run AgentOS Doctor, because its helper script passes them through to the read-only adapter drift check.

</details>

For installer adapter details, see the [portability playbook](os/playbook/PORTABILITY.md). The [glossary](os/context/GLOSSARY.md) defines AgentOS terms such as harness, adapter, Core, Personal Overlay, and drift.

## Run AgentOS Doctor

Use the [Run AgentOS Doctor skill](os/skills/run-agentos-doctor/SKILL.md) when you want a read-only setup-health audit with agent judgment for ambiguous local state. The Doctor helper is skill-local and should be run as part of that workflow, not as a standalone diagnosis. The skill uses this deterministic helper script for facts:

```bash
python3 os/skills/run-agentos-doctor/scripts/agentos_doctor.py
```

The helper script discovers the AgentOS checkout from the current directory, or you can pass `--agentos-home <agentos-home>`. It always prints the resolved home, runs the installer drift check in read-only `--check` mode, and reports automation registry/file locations and counts only. It does not remediate, install, sync, delete, audit skill mirrors, parse getting-started Markdown for starter paths, classify automation lifecycle state, or print private file contents.

When your setup uses `--all-default-adapters` or custom `--adapter <path>` targets, pass those same flags to Run AgentOS Doctor or the helper script so the adapter drift result covers the same harness instruction files as your installer check.

When running the doctor from an isolated feature worktree, pass `--primary-agentos-home <primary-agentos-home>` so Personal Overlay automation location counts refer to the canonical checkout. The helper still runs read-only checks only; it suppresses feature-worktree write commands when the audit root and primary checkout differ. Any adapter writes, mirror syncs, Personal Overlay edits, starter-file interpretation, skill mirror diagnosis, or automation changes belong to the Run AgentOS Doctor skill after explicit approval.

Use the tools this way:

- `os/skills/run-agentos-doctor/SKILL.md`: read-only setup-health workflow with agent judgment for ambiguous local state.
- `os/skills/run-agentos-doctor/scripts/agentos_doctor.py`: skill-local deterministic setup facts and exact read-only check commands.
- `scripts/install_global_agent_instructions.py`: dry-run, install, check, or remove global instruction adapters after review.
- `os/skills/mirror-skills/scripts/mirror_skills.py`: audit skill mirrors by default; sync only after approving current-machine writes.

## Getting The Most Out Of AgentOS

AgentOS works best when you treat it as a living operating layer, not a one-time prompt paste. Let agents load the smallest relevant files, then ask them to improve the system when a repeated workflow, preference, boundary, or lesson should become durable.

Useful first moves:

- Ask your agent to get to know you, whether you plan to use AgentOS for work, personal life, or both, your projects, your tools, your recurring workflows, and your safety boundaries, then propose approved facts to write into the [Personal Overlay](os/playbook/PERSONAL_OVERLAY.md) under `$root/personal/os/`.
- When a task reveals a reusable workflow, ask whether it should become a skill, playbook entry, memory entry, verification check, or Personal Overlay note.
- Keep private state in `$root/personal/os/`; keep public-safe templates, policies, and examples in [AgentOS Core](os/INDEX.md) under `$root/os/`.
- Ask your agent to occasionally check whether the global instruction adapters still point at the right AgentOS installation, especially after moving the checkout or changing agent harnesses.
- Ask your agent to run the mirror-skills workflow when you want AgentOS skills to be discoverable from your harness.
- Ask your agent to set up a recurring reminder or automation to check this repository for AgentOS updates, if your agent harness supports automations.

For a guided first pass, use the [getting started playbook](os/playbook/GETTING_STARTED.md), or ask your agent:

```text
Help me get the most out of AgentOS.

Read os/playbook/GETTING_STARTED.md and guide me through the first-pass setup. Interview me about whether I plan to use AgentOS for work, personal life, or both, plus my projects, preferences, recurring workflows, tools, and safety boundaries. Recommend the first Personal Overlay files or AgentOS updates that would make future agent sessions more useful. Do not write private state until I approve the proposed files and locations. Ask whether I want a recurring check for AgentOS repository updates and adapter drift, meaning local instruction files no longer pointing at the intended AgentOS checkout.
```

## First Read Sequence

For an agent or human using an AgentOS checkout for the first time:

1. Read [AGENTS.md](AGENTS.md).
2. Read [os/INDEX.md](os/INDEX.md).
3. Read [os/playbook/PERSONAL_OVERLAY.md](os/playbook/PERSONAL_OVERLAY.md) before storing or looking for private state.
4. For broad routing, authority, safety, or filing questions, read [os/RESOLVER.md](os/RESOLVER.md).
5. Use the narrowest relevant Core file for the task.

## Entry Points

- [AGENTS.md](AGENTS.md): agent adapter entry point.
- [CLAUDE.md](CLAUDE.md): Claude Code adapter.
- [DOMAIN.md](DOMAIN.md): domain language for the publishing architecture.
- [os/INDEX.md](os/INDEX.md): Core map.
- [os/RESOLVER.md](os/RESOLVER.md): routing, authority, safety, and filing tie-breakers.
- [os/playbook/AGENTOS_PLAYBOOK.md](os/playbook/AGENTOS_PLAYBOOK.md): operating manual.
- [os/playbook/GETTING_STARTED.md](os/playbook/GETTING_STARTED.md): guided first-pass setup.
- [os/playbook/PERSONAL_OVERLAY.md](os/playbook/PERSONAL_OVERLAY.md): Core/Overlay load and migration rules.
- [os/playbook/PORTABILITY.md](os/playbook/PORTABILITY.md): harness adapter and portability guidance.
- [os/verification/README.md](os/verification/README.md): maintainer validation guidance.
- [os/playbook/PUBLICATION.md](os/playbook/PUBLICATION.md): publication safety workflow.
