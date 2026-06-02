# Propagation Review Queue

Status: manual pattern v1.

Use this pattern when a generated report, review, brief, digest, workflow, or agent output discovers a likely durable AgentOS update that is private, tentative, connector-derived, personal, cross-project, or not yet ready for a project issue.

The queue is a private pre-issue triage inbox. It is not a replacement for GitHub issues, mapped-project trackers, or direct current-thread approval of an exact edit.

Use GitHub issues or mapped-project trackers for public-safe, actionable project work. Use direct canonical edits when the user explicitly asks for the exact edit in the current request, or when applying an already approved queue entry or issue-backed change. Use the propagation queue for generated recommendations that need human review before they should become durable AgentOS state.

Queue entries are evidence and recommendations. They are not canonical context, memory, source-map, skill, agent, verification, or backlog state until the user approves them and an agent applies them under an explicit instruction.

Inline chat questions are useful as a human review surface. They can approve an exact current-thread edit or a specific queue entry, but they should not become the durable record for unresolved generated recommendations.

Live queue:

`personal/os/memory/propagation-review/QUEUE.md`

## Choose The Inbox

Use a GitHub issue or mapped-project tracker when the recommendation is public-safe, actionable, repo-scoped, and likely to become a PR or project task.

Use the propagation queue when the recommendation is private, tentative, connector-derived, personal, cross-project, low-confidence, or still needs triage before it belongs in an issue tracker.

Use a direct canonical edit only when the user explicitly requests the exact edit in the current thread, or when applying a specific approved queue entry or issue-backed change.

## When To Queue Instead Of Edit

Create a queue entry instead of directly editing canonical state when:

- the source is an agent report, brief, digest, weekly review, or generated recommendation rather than the user's direct instruction, and the recommendation is not yet a public-safe actionable issue;
- the proposed update touches private personal preferences, career framing, local project routing, private source-map entries, recurring workflows, live agent behavior, connector-derived facts, or automations;
- the evidence is useful but confidence is mixed or future relevance is unclear;
- the update touches private connector output, contact details, calendar/email interpretations, or anything governed by a safety boundary;
- applying the update would change how future agents act across more than one run, but the destination and approval are not yet clear;
- the workflow wants to ask the user whether to promote generated findings into private AgentOS context, memory, source-map, skill config, agent, backlog, or automation state.

Do not queue public-safe, actionable project work merely because it originated in a generated report. File that work in the relevant GitHub issue tracker or mapped project instead.

Directly edit canonical state only when the user explicitly asks for the exact canonical edit in the current request, or when applying an approved queue entry or issue-backed change under the relevant apply rules. Do not treat a generated workflow's vague inline yes/no question as a durable decision record.

## Operational Migrations And Direct Approval

Operational migrations, cleanup runs, and other step-by-step actions may proceed by explicit human approval in the active thread without first creating a queue entry. That approval authorizes the named action sequence; it does not by itself promote lessons, summaries, or inline discussion into canonical AgentOS state.

Do not retroactively create queue entries merely because a user-approved operation already happened. Queue follow-up changes when the operation produces a durable lesson or policy recommendation that would alter Core guidance, personal memory, playbooks, skills, verification, automations, or other canonical state. The queue remains the review path for generated or inferred propagation unless the user explicitly asks for the exact canonical edit to make.

Inline chat approval can approve operational actions, applying a specific queue entry, or an exact canonical edit. It should not silently become durable state for unresolved generated recommendations; capture those through the queue, an issue tracker, or the exact canonical edit the user requested.

## Candidate Producers

These outputs may produce queue entries, GitHub issues, mapped-project tasks, or exact user-approved edits depending on the inbox classification above. They must not auto-apply generated recommendations by default:

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
