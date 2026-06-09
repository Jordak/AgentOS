---
name: grill-me
description: "Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when the user wants to stress-test a plan, get grilled on their design, or mentions \"grill me\"."
---

# Grill Me Skill

## Trigger

Use this when the user wants to stress-test a plan, get grilled on a design, resolve design consensus before implementation, or explicitly says "grill me".

## Upstream Alignment

This Core skill vendors the current-machine installed/global `grill-me` behavior. Keep the name and behavior aligned with upstream unless a future vendoring update deliberately accepts an upstream change and reapplies the AgentOS contract wrapper.

The portable behavior is intentionally small:

- interview the user about every aspect of a plan until shared understanding is reached;
- walk down the design tree one branch and dependency at a time;
- ask one question at a time;
- provide a recommended answer for each question;
- inspect local code or docs instead of asking when local evidence can answer safely.

## Contract

Inputs:

- A plan, design, implementation issue, architecture choice, product decision, or other proposal to stress-test.
- Any durable design source, repository context, issue, PRD, ADR, code, docs, or acceptance criteria relevant to the proposal.
- The caller's scope boundary, non-goals, and any required readiness or decision artifact when this skill is invoked by another workflow.

Output artifact:

- A conversational design-consensus interview by default.
- A concise final summary of resolved decisions, remaining unknowns, explicit deferrals, and recommended next action when the grill session reaches shared understanding or must stop.
- No document, issue, PR, code, or external-state mutation by default.

Mutability:

- Read-only.
- No local-write, connector-write, or external-write behavior by default.
- Durable writes belong to the calling workflow after the applicable local-write or external-write policy is satisfied.

Tools and connectors:

- User-provided plan or design context.
- Local repository files, docs, issues exported into the workspace, and `rg`/local search when codebase evidence can answer a question safely.
- Read-only connector or GitHub issue/PR reads only when explicitly relevant and authorized by the caller or user.
- No connector writes or external writes.

Safety:

- Ask one question at a time so the user can answer deliberately.
- Recommend a default answer for each question, but do not present the recommendation as user consent.
- Inspect local code or docs instead of asking when local evidence can answer safely.
- Do not invent missing facts, hidden preferences, private context, or external constraints.
- Do not edit files, update design docs, post comments, change labels, create issues, commit, push, merge, close issues, or change external state.
- When invoked by a calling workflow, stay inside the caller-provided scope and authorization boundary.

## Workflow Phases

1. Establish the target. Identify the plan or design under discussion, the decision being grilled, the caller's scope boundary, and any durable design source that should anchor the session.

2. Explore available evidence. Read local code, docs, issues, ADRs, acceptance criteria, and relevant project instructions when they can answer a question safely. Do not ask the user for facts that are discoverable from the authorized local context.

3. Build the decision tree. Name the main branches, dependencies, constraints, non-goals, and risks that need resolution before implementation or commitment can proceed.

4. Ask one question. Ask the next highest-leverage unresolved question only. Include why it matters and the recommended default answer.

5. Carry answers forward. Treat the user's answer as the current decision for the session. Update the working understanding, prune resolved branches, and use the answer to choose the next question.

6. Stop at convergence. End when shared understanding is reached, when remaining unknowns are explicitly deferred, or when a blocking human decision remains unresolved and the caller must decide how to record or escalate it.

7. Summarize the result. Return resolved decisions, recommended defaults accepted or rejected, deferred questions, remaining risks, and the next safe action for the caller.

## Output

During the interview, default to this shape:

- One question.
- Why it matters.
- Recommended default.

At the end, default to this shape:

- Resolved decisions.
- Explicit deferrals.
- Remaining risks or blockers.
- Recommended next action.

## Filing Rules

- Default output stays in chat or in the calling workflow's result artifact.
- `grill-me` does not create durable AgentOS state by itself.
- If a calling workflow needs durable design evidence, that workflow owns the write under its contract, such as updating a design doc, GitHub issue, PRD, ADR, readiness report, or local follow-up artifact after the applicable write policy is satisfied.
- Private or personal design context belongs in the Personal Overlay when durable filing is approved.

## Quality Bar

- The session asks one question at a time.
- Each question has a recommended default answer.
- The skill uses local evidence instead of asking when the answer can be discovered safely.
- The interview follows dependencies between decisions rather than asking disconnected questions.
- The final summary distinguishes resolved decisions, explicit deferrals, and unresolved blockers.
- The skill remains read-only and does not imply approval for writes owned by another workflow.

## Verification

Before finishing:

1. Confirm the target plan or design was identified.
2. Confirm local evidence was inspected for questions that could be answered safely from the codebase or docs.
3. Confirm only one question was asked at a time.
4. Confirm each question included a recommended default answer.
5. Confirm the session stopped only after shared understanding, explicit deferral, or a clearly reported unresolved blocker.
6. Confirm no local files, connector state, GitHub issues, comments, labels, branches, commits, or external state were changed by this skill.
7. After changing this Core skill or its manifest entry, run `scripts/run-validator` and `git diff --check`.

## Rules

- Keep the Core behavior aligned with upstream `grill-me`.
- Preserve the read-only default.
- Keep document or tracker mutation in the calling workflow, not in this skill.
- Prefer direct local evidence over asking the user to restate facts already present in the authorized workspace.
