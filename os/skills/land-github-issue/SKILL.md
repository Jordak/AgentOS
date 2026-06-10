---
name: land-github-issue
description: Verify a GitHub issue's acceptance criteria against remote integration-branch evidence, update fulfilled Markdown checklist criteria, and close the issue only when closure is authorized and fully evidenced.
---

# Land GitHub Issue

## Goal

Own the approval-gated issue-landing step after integration evidence exists for one GitHub issue.

This skill is for a landing-capable Calling Workflow, such as a future `coordinate-issue-batch`, to reconcile an issue after implementation work has landed on the remote integration branch. It verifies the issue's acceptance criteria, checks off fulfilled Markdown checklist items, closes the issue only when all closure gates pass, and returns unmet criteria to the caller when more implementation work is needed.

`implement-github-issue` does not call or own this skill. Implementation workers stop at reviewed PR evidence. Coordinators or human-supervised landing actions decide whether and when to invoke this skill.

## Contract

Inputs:

- A GitHub issue URL or issue number plus the target repository, inferred from the current checkout when possible.
- The remote integration branch to verify against, defaulting to `origin/main` unless the caller specifies another branch.
- Optional evidence from a Calling Workflow, such as merged PR URLs, merge or squash commit SHAs, validation results, worker Workflow Results, or issue comments.
- Current local agent instructions and project guidance, including `AGENTS.md`.
- Current GitHub workflow and closure discipline at `os/playbook/GITHUB_WORKFLOW.md`.
- `os/skills/audit-issues/SKILL.md` for reusable post-integration closure evidence rules.
- `os/skills/ORCHESTRATION_LOOPS.md` for Authorization Boundary, Workflow Result, Recovery Record, and Calling Workflow vocabulary.
- Optional explicit mode: read-only by default, checklist-update-only, or authorized landing mode when the caller's Authorization Boundary explicitly allows checklist edits and issue closure.

Output artifact:

- A Workflow Result naming the issue URL, labels, integration branch, evidence checked, fulfilled acceptance criteria, unmet or ambiguous acceptance criteria, checklist mutations, closure decision, validation, open risks, and recommended next action for the Calling Workflow.
- Optional issue-body update that checks off fulfilled Markdown acceptance criteria.
- Optional issue closure with a factual evidence comment when all closure gates pass and closure is authorized.

Mutability:

- Read-only by default. Inspect the issue, labels, integration branch, linked PRs, commits, acceptance criteria, and evidence, then return a landing recommendation without mutating issue state.
- Checklist-update-only when the caller explicitly authorizes issue-body checkbox updates but not closure.
- Authorized landing mode when the caller explicitly authorizes both issue-body checkbox updates and issue closure for the target issue. In this mode, the skill may update fulfilled acceptance-criteria checkboxes and close the issue only after all closure gates pass.

Tools and connectors:

- Local filesystem and `git`, especially `git fetch`, `git merge-base --is-ancestor`, and inspection of the fetched remote integration branch.
- GitHub connector or `gh` for issue body, labels, comments, linked PRs, PR merge metadata, issue edits, issue comments, and issue closure when authorized.
- `os/playbook/GITHUB_WORKFLOW.md` for GitHub write policy, PR and issue wording, branch discipline, and issue closure rules.
- `os/skills/audit-issues/SKILL.md` for closure evidence standards.
- `os/skills/ORCHESTRATION_LOOPS.md` for recovery and Workflow Result conventions.

Safety:

- Ask or stop unless the current Authorization Boundary explicitly allows the requested issue-body edits and issue closure for this issue.
- Do not merge PRs, squash merge, push branches, delete branches, spawn implementation workers, create labels, change permissions, or mutate issues outside the target issue.
- Do not close issues labeled for human ownership or human review, including `ready-for-human`, `needs-human`, `needs-a-human`, or equivalent labels, unless the caller provides a resolved human decision and repository policy permits closure.
- Do not close issues based on local commits, unmerged feature branches, title similarity, local-only code inspection, unchecked assumptions, or a worker's confidence alone.
- Do not treat checked Markdown boxes as proof. Verify the acceptance criteria against integration-branch evidence; content and evidence win over checkbox state.
- Do not uncheck previously checked acceptance criteria unless the caller explicitly asks for a corrective issue-body edit and the evidence shows the checkbox is wrong.
- Keep issue comments factual and evidence-backed. Avoid GitHub auto-closing keywords in comments unless the skill is intentionally closing the target issue in the same authorized operation.

## Workflow Phases

1. Establish the target:
   - Identify the issue, repository, remote, integration branch, checkout path, current branch, and Authorization Boundary.
   - Read local instructions, `os/playbook/GITHUB_WORKFLOW.md`, `os/skills/audit-issues/SKILL.md`, and `os/skills/ORCHESTRATION_LOOPS.md`.
   - Inspect the issue body, labels, comments, linked PRs, and caller-provided evidence.
   - Record the initial Recovery Record: issue URL, repository, integration branch, current phase, Authorization Boundary, known human-review or closure blockers, and next action.

2. Verify integration evidence:
   - Fetch or otherwise refresh the remote integration branch before deciding closure.
   - For each PR or commit offered as evidence, verify that its merge, squash, or resolving commit is reachable from the remote integration branch.
   - Treat feature branch heads, local-only commits, unmerged PRs, and unknown SHAs as insufficient closure evidence.
   - Record the exact PR URLs, commit SHAs, integration branch, and reachability checks used.

3. Extract acceptance criteria:
   - Identify issue acceptance criteria from the issue body, especially Markdown checklist items under headings such as `Acceptance criteria`.
   - Preserve checklist text exactly unless checking off a verified item.
   - If the issue has no clear acceptance criteria, classify closure as ambiguous and return a Blocking Human Decision or caller action instead of guessing.

4. Reconcile acceptance criteria:
   - For each criterion, decide one of: fulfilled, unmet, ambiguous, or out of scope.
   - Use integration-branch evidence as the closure standard. Code inspection, tests, comments, and worker Workflow Results may support the decision, but they do not replace integration proof.
   - Keep criteria unmet or ambiguous when evidence is missing, partial, contradicted, or not reachable from the integration branch.
   - If any criterion is unmet or ambiguous, prepare a Workflow Result that names the exact criteria and evidence gaps. Recommend that the Calling Workflow restart an `implement-github-issue` Called Workflow, create a follow-up issue, or request a human decision depending on scope.

5. Update fulfilled checklist items:
   - If issue-body edits are authorized, update fulfilled Markdown acceptance-criteria checkboxes from `[ ]` to `[x]`.
   - Leave unmet and ambiguous checkboxes unchecked.
   - Do not rewrite non-acceptance checklists unless the caller explicitly scoped them into the landing check.
   - If issue-body edits are not authorized, include the proposed checkbox diff or item list in the Workflow Result instead of mutating the issue.
   - Create or update a Recovery Checkpoint before the issue-body edit.

6. Decide closure:
   - Close only when all acceptance criteria are fulfilled or explicitly out of scope, all integration evidence is reachable from the remote integration branch, no human-review or human-owned label blocks closure, and the Authorization Boundary explicitly allows closure.
   - If closure is blocked, return a Workflow Result with the reason and recommended next action.
   - If closure is authorized, close with a factual comment that cites the merged PR or integration commit, the remote integration branch, fulfilled acceptance criteria, and validation evidence when available.
   - Create or update a Recovery Checkpoint before closure.

7. Report the Workflow Result:
   - Include issue URL and final labels, integration branch, evidence checked, acceptance-criteria reconciliation, checklist edits made or proposed, closure action or blocker, validation signals, open risks, and recommended next action.
   - When unmet criteria remain, recommend that the Calling Workflow restart or request an `implement-github-issue` Called Workflow only if the remaining work is implementation-shaped and inside that workflow's contract.
   - State clearly that merge, branch deletion, worker spawning, and broader batch integration remain outside this skill.

## Recovery Record

Maintain enough state to resume safely after compaction, interruption, or handoff. Recover at least:

- issue URL and repository;
- integration branch and fetched remote state when available;
- Authorization Boundary, including whether checklist edits and closure are authorized;
- issue labels and any human-review or human-owned blocker;
- acceptance criteria with fulfilled, unmet, ambiguous, or out-of-scope classification;
- evidence PRs, commits, merge commits, reachability checks, and validation results;
- checklist mutations performed or proposed;
- closure action performed or blocker;
- current phase and next safe action;
- open risks and recommended action for the Calling Workflow.

Create a Recovery Checkpoint before issue-body edits, issue comments, issue closure, yielding for a Blocking Human Decision, or ending with incomplete landing work. Use the narrowest authorized surface, such as a caller ledger, issue comment, final Workflow Result, or local note.

## Filing Rules

- Canonical reusable workflow guidance lives in this skill.
- Issue-specific closure evidence and checklist state stay on the GitHub issue.
- Coordinator ledgers and batch-level decisions belong to the Calling Workflow, not this skill.
- Broader stale-issue sweeps belong to `audit-issues`; this skill handles one assigned issue at a time.
- Implementation recovery belongs to `implement-github-issue` or a follow-up issue when the caller decides more work is needed.

## Quality Bar

- The remote integration branch was fetched or the report explains why fresh verification was unavailable.
- Every closure decision is grounded in integration-branch reachability and acceptance-criteria reconciliation.
- Fulfilled Markdown checkbox criteria are checked off only when evidence supports them.
- Unmet or ambiguous criteria remain unchecked and are returned to the Calling Workflow.
- Human-owned or human-review issues are not closed without a resolved human decision.
- Issue-body edits and issue closure happen only inside the explicit Authorization Boundary.
- No PR merge, branch deletion, worker spawning, label creation, permission change, or out-of-target issue mutation happens through this skill.
- The Workflow Result is recoverable and names all mutations, evidence, validation, risks, and recommended next action.

## Verification

Before finishing:

1. Confirm local instructions, GitHub workflow policy, `audit-issues`, and orchestration-loop guidance were read or honored.
2. Confirm the target issue, repository, integration branch, and Authorization Boundary.
3. Confirm the remote integration branch was fetched or record why fresh verification was unavailable.
4. Confirm each evidence PR or commit was checked for reachability from the remote integration branch.
5. Confirm acceptance criteria were extracted from the issue body and classified.
6. Confirm fulfilled checkbox criteria were updated or proposed, while unmet and ambiguous criteria stayed unchecked.
7. Confirm no issue closure happened while any criterion was unmet or ambiguous.
8. Confirm human-review and human-owned labels were treated as closure blockers unless a resolved human decision was provided.
9. Confirm closure, if performed, used an evidence-backed factual comment and stayed inside the Authorization Boundary.
10. Confirm the Workflow Result names fulfilled criteria, unmet criteria, checklist mutations, closure state, validation, open risks, and recommended Calling Workflow action.
11. If this skill or its manifest entry changed, run `git diff --check` and `scripts/run-validator`.
