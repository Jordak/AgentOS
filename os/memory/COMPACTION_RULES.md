# Memory Compaction Rules

## Working Memory

- Keep only current priorities, blockers, and next actions.
- Remove stale notes once they are captured in durable files.

## Long-Term Memory

- Store stable facts, recurring preferences, and durable lessons.
- Avoid raw transcripts, duplicate notes, and temporary implementation details.

## Decisions

- Live personal decisions belong in `personal/os/memory/DECISIONS_LOG.md`.
- Publishable AgentOS architecture decisions belong in `os/memory/DECISIONS_LOG.md` or `docs/adr/`.
- Context-facing decisions that affect private work should be summarized in `personal/os/memory/DECISIONS_LOG.md` and reflected in `personal/os/context/` when they become durable context.
