# Connection Safety Rules

Status: Core default.

Use this file for generic safety rules around external accounts and real-world effects.

## Approval Required

Ask before:

- sending email, chat, social, issue, or PR messages;
- posting publicly;
- changing sharing permissions;
- granting write access;
- entering credentials or handling MFA;
- deleting nontrivial data;
- changing account settings;
- making purchases or commitments;
- connecting new external services;
- creating automations that act without manual review.

## Defaults

- These Core defaults apply unless a matching Personal Overlay connection rule explicitly grants a narrower scoped-write allowance for a real account, workspace, repository set, or automation path.
- Prefer drafts and local artifacts before external writes.
- Treat connector reads as scoped to the user's explicit request.
- Report partial connector availability rather than pretending unavailable data was checked.

## Personal Overlay Allowances

A Personal Overlay allowance may loosen approval requirements only for named, scoped, reversible writes. The allowance must name:

- the account, workspace, repository set, or ownership scope;
- the write types allowed without per-action approval;
- the task or request conditions that activate the allowance;
- actions that still require approval.

Keep asking before high-risk actions unless the Personal Overlay explicitly names the action and its guardrails. High-risk actions include merges, issue closure, repository visibility changes, permission changes, deletes, credentials or MFA, purchases, new external services, and automations that act without manual review.

## Connection Maturity Ladder

Use the least capable connection level that can complete the job.

1. Read-only: the agent may inspect explicitly relevant data and report back.
2. Draft-to-user: the agent may prepare local drafts, summaries, or proposed updates for review.
3. Draft-to-system: the agent may create drafts or private notes inside a connected system when the user has approved that connector behavior.
4. Scoped write: the agent may make narrow, reversible writes after the workflow has been observed and verified.
5. External effect: the agent may send, post, publish, change permissions, delete, purchase, or commit externally only after explicit approval for that action, a previously approved automation path, or a specific Personal Overlay allowance for that account and write type.

Before raising a connector above read-only, record what manual runs were observed, what verification passed, and what approval gate still applies.
