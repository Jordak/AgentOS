# Getting Started With AgentOS

Status: first-pass onboarding playbook.

Use this after AgentOS is installed and the global instruction adapters are current. The goal is to help the user turn a fresh AgentOS checkout into a useful personal operating layer without dumping private facts into the public Core.

## Ground Rules

- Read `AGENTS.md`, `os/INDEX.md`, and `os/playbook/PERSONAL_OVERLAY.md` first.
- Treat `$root` as the location where AgentOS is installed.
- Ask before writing private state.
- Write real user-specific facts under `$root/personal/os/`.
- Keep public-safe templates, policies, and examples under `$root/os/`.
- Prefer a few useful starter files over a giant interview.

## First Conversation

Ask enough to make the next agent session better:

1. What should future agents know about who you are and how you like to collaborate?
2. Do you plan to use AgentOS for work, personal life, or both?
3. What projects, repositories, documents, or source systems matter most right now?
4. What recurring workflows do you want agents to help with?
5. What tools, accounts, or connectors do agents need to treat carefully?
6. What boundaries should agents never cross without explicit approval?
7. What should agents remember between sessions?

After the interview, summarize proposed writes before making them. Include the target path, why it belongs there, and whether the content is private.

## Bootstrap Loop

Prefer a useful 70% first version over a perfect private profile. The fastest path is:

1. Ask the user for a rough brain dump about identity, projects, tools, workflows, and boundaries.
2. Interview them with focused follow-up questions.
3. Draft the smallest starter files that will improve the next session.
4. Ask for approval before writing private state.
5. Patch the files over the next few weeks whenever the user has to re-explain something important.

Concrete starter prompt:

```text
I'm building my AgentOS Personal Overlay. Interview me before writing anything.

Ask me about:
- who I am and how I want agents to work with me;
- how direct, detailed, skeptical, or action-oriented I want responses to be;
- what I value when making decisions;
- what frustrates me about AI assistance today;
- what agents should never do without approval;
- which projects, tools, accounts, and source systems matter now;
- which workflows I repeat often enough to deserve a skill or agent;
- what future agents should remember between sessions.

After the interview, propose a 70% first version of the starter files. Include the target path, whether the content is private, and any unanswered questions. Do not write files until I approve the paths and contents.
```

## Starter Files

Useful first Personal Overlay files include:

- `personal/os/identity/USER.md`: durable identity and collaboration context.
- `personal/os/identity/COMMUNICATION.md`: tone, formatting, and interaction preferences.
- `personal/os/identity/BOUNDARIES.md`: approval rules and sensitive areas.
- `personal/os/context/SOURCE_MAP.md`: where agents should find real project sources.
- `personal/os/context/PROJECTS.md`: active projects and why they matter.
- `personal/os/context/TOOLS.md`: real tools, harnesses, and local setup notes.
- `personal/os/memory/WORKING_MEMORY.md`: current state that should survive context resets.
- `personal/os/memory/LONG_TERM_MEMORY.md`: durable facts and decisions.
- `personal/os/connections/CONNECTIONS.md`: connected accounts and permission boundaries.

Use the matching Core templates under `os/` when the user wants structure but has not supplied private facts yet.

## Run AgentOS Doctor

Use the Run AgentOS Doctor skill when the user wants a read-only setup health check with agent judgment for ambiguous local state. The Doctor helper is skill-local and should be run as part of that workflow, not as a standalone diagnosis. The skill uses this deterministic helper script for setup facts:

```bash
python3 os/skills/run-agentos-doctor/scripts/agentos_doctor.py
```

The helper script discovers `$root` from the current directory, or accepts `--agentos-home <root>`. It reports the resolved AgentOS home, checks adapter drift through `scripts/install_global_agent_instructions.py --check`, and reports automation registry/file locations and counts only. It prints bounded facts and helper output only; it must not audit skill mirrors, parse this Markdown for starter paths, print Personal Overlay file contents, or classify automation lifecycle state.

If the installer or adapter check used `--all-default-adapters` or any custom `--adapter <path>` flags, repeat those exact flags when using Run AgentOS Doctor or the helper script so the read-only adapter drift result covers the same harness files.

If the command is running from an isolated feature worktree, pass `--primary-agentos-home <primary-agentos-home>` so Personal Overlay automation location counts refer to the canonical checkout. The helper still runs read-only checks only and suppresses feature-worktree write commands when the audit root and primary checkout differ; starter-file interpretation, skill mirror diagnosis, adapter writes, mirror syncs, Personal Overlay edits, and automation changes require the Run AgentOS Doctor skill and explicit approval.

Run AgentOS Doctor is not the installer and not mirror sync:

- Use `os/skills/run-agentos-doctor/SKILL.md` for setup-health workflow and judgment over ambiguous notes.
- Use `os/skills/run-agentos-doctor/scripts/agentos_doctor.py` for skill-local deterministic setup facts and exact read-only check commands.
- Use `scripts/install_global_agent_instructions.py` when the user has approved creating, updating, checking, or removing global instruction adapters.
- Use `os/skills/expose-skills/scripts/expose_skills.py` when the user wants AgentOS Core skills exposed to the global harness skill root with symlink adapters.
- Use `os/skills/mirror-skills/scripts/mirror_skills.py` only for the legacy copy-mirror workflow while it remains available.

## Skill Exposure

AgentOS Core skills live under `os/skills/`. Private skills can live under `personal/os/skills/<skill-name>/SKILL.md`.

When the user wants the active harness to discover AgentOS Core skills directly, run the expose-skills workflow:

```bash
python3 os/skills/expose-skills/scripts/expose_skills.py
```

Show the dry-run result before applying. If the user approves writes to the global skill root, run:

```bash
python3 os/skills/expose-skills/scripts/expose_skills.py --no-dry-run
```

Expose-skills v1 covers Core manifest skills only. It does not discover or expose Personal Overlay skills. Missing entries become symlink adapters under `~/.agents/skills`; copied mirrors, wrong-target symlinks, and blocked paths are reported but not replaced.

## Recurring Checks

Offer to set up recurring checks when the harness supports automations:

- Adapter drift: confirm global instruction adapters still point at the intended AgentOS checkout.
- Repository updates: check whether the public AgentOS repository has changed and summarize what the user may want to pull.
- Weekly AgentOS review: inspect stale state, missing templates, useful memories, and automation health.

Do not create or enable automations until the user approves the cadence, prompt, destination, and any external effects.

## Good First Prompts

Ask the user's agent:

```text
Use AgentOS to get to know me.

Read AGENTS.md, os/INDEX.md, os/playbook/PERSONAL_OVERLAY.md, and os/playbook/GETTING_STARTED.md. Interview me about identity, whether I plan to use AgentOS for work, personal life, or both, projects, tools, recurring workflows, safety boundaries, and what future agents should remember. Then propose the first Personal Overlay files to create. Do not write private state until I approve the paths and contents.
```

Or:

```text
Audit my AgentOS setup.

Use the Run AgentOS Doctor skill from my AgentOS checkout. As part of that skill workflow, run `python3 os/skills/run-agentos-doctor/scripts/agentos_doctor.py` for deterministic setup facts, then check whether the global instruction adapters point at this AgentOS checkout, whether AgentOS skills are discoverable from my harness, whether my Personal Overlay has starter identity, context, memory, tool, and boundary files, and whether automation state appears actively configured or only ambiguously mentioned. Report gaps and ask before making changes.
```
