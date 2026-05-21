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
2. What projects, repositories, documents, or source systems matter most right now?
3. What recurring workflows do you want agents to help with?
4. What tools, accounts, or connectors do agents need to treat carefully?
5. What boundaries should agents never cross without explicit approval?
6. What should agents remember between sessions?

After the interview, summarize proposed writes before making them. Include the target path, why it belongs there, and whether the content is private.

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

## Skill Mirrors

AgentOS Core skills live under `os/skills/`. Private skills can live under `personal/os/skills/<skill-name>/SKILL.md`.

When the user wants the active harness to discover AgentOS skills directly, run the mirror-skills workflow:

```bash
python3 os/skills/mirror-skills/scripts/mirror_skills.py
```

Show the audit result before syncing. If the user approves writes to the current-machine mirror root, run:

```bash
python3 os/skills/mirror-skills/scripts/mirror_skills.py --sync
```

The mirror audit includes Core skills and Personal Overlay skills. Use `--core-only` only when the user explicitly wants to skip private Personal Overlay skills.

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

Read AGENTS.md, os/INDEX.md, os/playbook/PERSONAL_OVERLAY.md, and os/playbook/GETTING_STARTED.md. Interview me about identity, projects, tools, recurring workflows, safety boundaries, and what future agents should remember. Then propose the first Personal Overlay files to create. Do not write private state until I approve the paths and contents.
```

Or:

```text
Audit my AgentOS setup.

Check whether the global instruction adapters point at this AgentOS checkout, whether AgentOS skills are discoverable from my harness, and whether my Personal Overlay has starter identity, context, memory, tool, and boundary files. Report gaps and ask before making changes.
```
