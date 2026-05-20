---
name: meeting-notes
description: "Turn user-provided notes, transcripts, or rough bullets into faithful meeting notes with decisions, action items, open questions, and optional follow-up drafts. Use when the user asks to summarize meeting material, extract decisions, or prepare meeting follow-up without inventing owners, dates, or commitments."
---

# Meeting Notes Skill

## Trigger

Use this when the user asks to turn notes, a transcript, or rough bullets into meeting notes.

## Contract

Inputs:

- User-provided notes, transcript, rough bullets, or meeting context.
- Optional user-provided desired audience, tone, format, follow-up recipient, or decision/action emphasis.
- Existing AgentOS context only when the user asks to connect the meeting to durable AgentOS state.

Output artifact:

- Conversational or Markdown meeting notes with summary, decisions, action items, open questions, and optional follow-up draft.

Mutability:

- Read-only by default.
- Local-write only when the user explicitly asks to record durable decisions in AgentOS.
- No connector-write or external-write by default.

Tools and connectors:

- User-provided content in the current thread.
- Local AgentOS files only when the user asks to record durable decisions.
- No calendar, email, transcript service, or external account reads unless the user explicitly supplies or requests them.

Safety:

- Preserve uncertainty from incomplete notes.
- Do not invent owners, deadlines, decisions, attendees, or commitments.
- Ask before sending, posting, emailing, or writing to any external system.
- Do not copy sensitive meeting details into durable AgentOS memory unless the user explicitly asks.

## Workflow Phases

1. Identify the input type and intended output: notes, transcript, rough bullets, summary, action list, or follow-up draft.
2. Extract facts, decisions, action items, owners, dates, and open questions from the supplied material.
3. Mark uncertainty where the source is ambiguous or incomplete.
4. Produce the meeting notes in the requested format, defaulting to concise Markdown.
5. If the user asks for durable recording, add only confirmed live decisions to `personal/os/memory/DECISIONS_LOG.md`; use `os/memory/DECISIONS_LOG.md` only for publishable AgentOS architecture decisions.

## Output

Produce:

1. Summary.
2. Decisions.
3. Action items with owners and dates when known.
4. Open questions.
5. Follow-up draft if requested.

## File Conventions

- Default output stays in chat unless the user asks for a file.
- Durable live decisions go only to `personal/os/memory/DECISIONS_LOG.md` when the user asks; Core architecture decisions go to `os/memory/DECISIONS_LOG.md` only when they are public-safe.
- Follow-up drafts remain drafts until the user approves sending.

## Quality Bar

- The notes are faithful to the supplied material.
- Owners and dates are present only when supplied or confirmed.
- Decisions are separated from discussion.
- Open questions remain visible rather than being smoothed over.
- Follow-up drafts are clearly drafts, not sent messages.

## Verification

Before finishing:

1. Check every owner, date, decision, and action item against the supplied notes.
2. Confirm unknowns are labeled instead of invented.
3. Confirm no external message was sent.
4. If durable decisions were recorded, confirm the user asked for that and the update landed in `personal/os/memory/DECISIONS_LOG.md` or, for public-safe Core architecture decisions, `os/memory/DECISIONS_LOG.md`.

## Rules

- Preserve uncertainty.
- Do not assign owners or deadlines unless present or confirmed.
- Add durable live decisions to `personal/os/memory/DECISIONS_LOG.md` when the user asks.
