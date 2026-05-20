# Weekly Review

Status: Core template.

Use this as a starting point for a Personal Overlay weekly review workflow.

## Purpose

Review whether AgentOS state is current, useful, and safely filed.

## Inputs

- `AGENTS.md`
- `os/INDEX.md`
- `os/RESOLVER.md`
- `os/playbook/AGENTOS_PLAYBOOK.md`
- Matching Personal Overlay files when present

## Procedure

1. Inspect current Core and Personal Overlay state.
2. Run relevant local validators.
3. Identify stale state, missing templates, private-data risks, and useful follow-up work.
4. Draft a report as a private generated output under `personal/os/memory/weekly-review/`.
5. Ask the user to approve any durable state changes or external actions.

## Safety

- Do not inspect external accounts unless the user explicitly asks.
- Do not perform external writes, delete files, or change automation state without approval.
- Treat generated durable state changes as proposals until approved.
