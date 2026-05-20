---
name: weekly-update
description: "Draft concise weekly updates, status reports, or check-ins from supplied facts and local AgentOS context without inventing progress, blockers, owners, dates, or commitments. Use when the user asks for a weekly update, weekly summary, status report, or check-in draft."
---

# Weekly Update Skill

## Trigger

Use this when the user asks for a weekly update, weekly summary, status report, or check-in draft.

## Contract

Inputs:

- Current active projects from `personal/os/context/PROJECTS.md`, using `os/context/PROJECTS.template.md` as the public-safe shape when needed.
- Recent live decisions from `personal/os/memory/DECISIONS_LOG.md`; use `os/memory/DECISIONS_LOG.md` only for publishable AgentOS architecture decisions.
- Working notes from `personal/os/memory/WORKING_MEMORY.md`, using `os/memory/WORKING_MEMORY.template.md` as the public-safe shape when needed.
- Any user-provided accomplishments, blockers, audience, tone, or next actions.

Output artifact:

- Concise weekly update, status report, or check-in draft.

Mutability:

- Read-only by default.
- No local-write, connector-write, or external-write unless the user explicitly asks to save or send the update.

Tools and connectors:

- Local AgentOS context, decisions, and working memory.
- User-provided facts.
- No external account reads unless the user explicitly requests them.

Safety:

- Do not invent progress, blockers, dates, or commitments.
- Clearly label unknowns and missing facts.
- Ask for missing facts if the update will be sent to another person.
- Treat outbound status messages as drafts until the user approves sending.

## Inputs

- Current active projects from `personal/os/context/PROJECTS.md`, using `os/context/PROJECTS.template.md` as the public-safe shape when needed.
- Recent live decisions from `personal/os/memory/DECISIONS_LOG.md`; use `os/memory/DECISIONS_LOG.md` only for publishable AgentOS architecture decisions.
- Working notes from `personal/os/memory/WORKING_MEMORY.md`, using `os/memory/WORKING_MEMORY.template.md` as the public-safe shape when needed.
- Any user-provided accomplishments, blockers, or next actions.

## Workflow Phases

1. Identify the audience and purpose: personal check-in, team status, manager update, project update, or generic weekly summary.
2. Read the relevant local AgentOS context unless the user supplied all facts in the current request.
3. Extract changes, blockers, next actions, decisions, and asks.
4. Label unknowns and ask for missing facts if the draft will be sent externally.
5. Produce a concise draft in the requested tone and format.

## Output

Produce a concise update with:

1. What changed.
2. What is blocked.
3. What is next.
4. Any decisions or asks.

## File Conventions

- Default output stays in chat.
- Save a file only when the user asks.
- Do not update memory from the weekly update skill by default; use `os/playbook/WEEKLY_REVIEW.md` when the task is AgentOS maintenance.

## Quality Bar

- The update is concise and useful to the intended audience.
- Progress is grounded in supplied facts or local AgentOS context.
- Blockers and asks are explicit.
- Unknowns are labeled rather than hidden.
- The draft is not sent externally without approval.

## Verification

Before finishing:

1. Confirm no progress, owner, date, blocker, or ask was invented.
2. Confirm unknowns are labeled.
3. If the update will be sent externally, confirm missing facts were requested or caveated.
4. Confirm no send or external write happened without approval.

## Rules

- Do not invent progress.
- Clearly label unknowns.
- Ask for missing facts if the update will be sent to other people.
