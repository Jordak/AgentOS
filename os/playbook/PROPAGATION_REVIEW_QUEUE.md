# Propagation Review Queue

Status: manual pattern v1.

Use this pattern when a generated report, review, brief, digest, workflow, or agent output discovers a likely durable AgentOS update.

The queue is the canonical proposal and approval path for generated recommendations that would change durable AgentOS state. Queue entries are evidence and recommendations. They are not canonical context, memory, source-map, skill, agent, verification, or backlog state until the user approves them and an agent applies them under an explicit instruction.

Inline chat questions are still useful as a human review surface, but they should summarize or request approval for queue entries rather than replacing the queue.

Live queue:

`personal/os/memory/propagation-review/QUEUE.md`

## When To Queue Instead Of Edit

Create a queue entry instead of directly editing canonical state when:

- the source is an agent report, brief, digest, weekly review, or generated recommendation rather than the user's direct instruction;
- the proposed update touches personal preferences, career framing, project routing, source-map entries, recurring workflows, agent behavior, verification rules, or automations;
- the evidence is useful but confidence is mixed or future relevance is unclear;
- the update touches private connector output, contact details, calendar/email interpretations, or anything governed by a safety boundary;
- applying the update would change how future agents act across more than one run;
- the workflow wants to ask the user whether to promote generated findings into AgentOS context, memory, source-map, skill, agent, verification, playbook, backlog, or automation state.

Directly edit canonical state only when the user explicitly asks for the exact canonical edit in the current request, or when applying an approved queue entry under the apply rules below. Do not treat a generated workflow's inline yes/no question as a substitute for a queue entry.

## Operational Migrations And Direct Approval

Operational migrations, cleanup runs, and other step-by-step actions may proceed by explicit human approval in the active thread without first creating a queue entry. That approval authorizes the named action sequence; it does not by itself promote lessons, summaries, or inline discussion into canonical AgentOS state.

Do not retroactively create queue entries merely because a user-approved operation already happened. Queue follow-up changes when the operation produces a durable lesson or policy recommendation that would alter Core guidance, personal memory, playbooks, skills, verification, automations, or other canonical state. The queue remains the review path for generated or inferred propagation unless the user explicitly asks for the exact canonical edit to make.

Inline chat approval can approve operational actions and can approve applying a specific queue entry. It should not silently become canonical durable state; capture the resulting policy or memory through the queue, or through the exact canonical edit the user requested.

## Candidate Producers

These outputs may propose propagation entries, but must not auto-apply them by default:

- Current-awareness agents: durable interests, project ideas, source-map suggestions, weak-signal watchlist items, and verification lessons from current-awareness briefs.
- Portfolio or project-scout agents: context updates, project gaps, handoffs, and public-proof backlog candidates.
- Assistant agents: personal workflow lessons, recurring admin patterns, automation candidates, and agent-continuity updates.
- Weekly Review: stale-file decisions, memory promotions, source-map fixes, backlog changes, automation changes, and AgentOS cleanup proposals that need a human decision.

## Entry Shape

Each queue entry must include:

- ID: `PRQ-YYYY-MM-DD-##`.
- Status: `proposed`, `approved`, `applied`, `rejected`, or `superseded`.
- Producer: agent, skill, report, or workflow that created the proposal.
- Proposed target: one of `context`, `memory`, `source-map`, `skill`, `agent`, `verification`, `playbook`, `automation`, `backlog`, or `mapped project`.
- Summary: the exact durable update being proposed.
- Source evidence: links or paths to the report, brief, connector-safe summary, GitHub issue, mapped project file, or user thread that supports the proposal.
- Confidence: high, medium, low, or mixed.
- Privacy and safety notes: whether the proposal touches private data, external accounts, connector output, personal contact details, deletion, permissions, automations, or public posting.
- Recommended action: apply, reject, ask the user, inspect more evidence, or move to an issue tracker.
- Decision record: who approved or rejected it, when, and what happened.

## Status Rules

- `proposed`: waiting for review; not canonical.
- `approved`: the user or an approved workflow accepted the proposal, but it has not been applied yet.
- `applied`: the target canonical file, issue, or mapped project was updated.
- `rejected`: the proposal should not be applied. Keep the entry for traceability unless the user asks to remove it.
- `superseded`: a newer queue entry or canonical update replaced this proposal.

## Apply Rules

Before applying a proposal:

1. Re-read the source evidence.
2. Re-read the target file's local resolver or nearest instructions.
3. Confirm no higher-priority instruction or privacy boundary blocks the edit.
4. Apply the smallest canonical update that captures the durable value.
5. Mark the queue entry `applied` with the user's approval, target path, date, and commit or issue reference when available.

If the proposal touches external account behavior, public posting, deletion, permissions, credentials, automations, or private connector data, ask the user before applying it.

## Minimal Entry Template

```markdown
### PRQ-YYYY-MM-DD-##

- Status: proposed
- Producer:
- Proposed target:
- Summary:
- Source evidence:
- Confidence:
- Privacy and safety notes:
- Recommended action:
- Decision record:
```
