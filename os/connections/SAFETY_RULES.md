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

- Prefer drafts and local artifacts before external writes.
- Treat connector reads as scoped to the user's explicit request.
- Report partial connector availability rather than pretending unavailable data was checked.

## Connection Maturity Ladder

Use the least capable connection level that can complete the job.

1. Read-only: the agent may inspect explicitly relevant data and report back.
2. Draft-to-user: the agent may prepare local drafts, summaries, or proposed updates for review.
3. Draft-to-system: the agent may create drafts or private notes inside a connected system when the user has approved that connector behavior.
4. Scoped write: the agent may make narrow, reversible writes after the workflow has been observed and verified.
5. External effect: the agent may send, post, publish, change permissions, delete, purchase, or commit externally only after explicit approval for that action or a previously approved automation path.

Before raising a connector above read-only, record what manual runs were observed, what verification passed, and what approval gate still applies.
