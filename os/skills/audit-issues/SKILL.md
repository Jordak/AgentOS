---
name: audit-issues
description: Audit a project's issue tracker against merged code, local evidence, and current project state, then recommend or perform tracker updates such as status comments, closure, labels, or follow-up notes. Use when the user asks to audit issues, reconcile stale GitHub issues, post automated issue status updates, identify issues already implemented on origin main, or close verified completed issues.
---

# Audit Issues

## Goal

Reconcile the current project's issue tracker with implementation reality. The primary output is an evidence-backed audit: close issues only when completion is proven, post status comments when useful, and leave human-review issues open with clear evidence.

## Contract

Inputs:

- A project checkout or explicit repository/issue-tracker target.
- The tracker source, usually GitHub via `gh` or the GitHub connector. If missing, infer it from the git remote or ask the user.
- The integration branch to verify against. Default to the remote default branch, usually `origin/main`; use the user's explicit branch if provided.
- Current AgentOS GitHub workflow policy at `os/playbook/GITHUB_WORKFLOW.md`.

Output artifact:

- A concise audit report listing closed issues, commented issues, skipped issues, model and effort metadata when available, evidence, and follow-up needed.
- Optional external tracker updates: status comments, issue closures, labels, or other tracker-native state changes.

Mutability:

- Mixed. Reads local git state and tracker data by default.
- Writes external issue state only when permitted by `os/connections/SAFETY_RULES.md` and `os/playbook/GITHUB_WORKFLOW.md`.

Tools and connectors:

- `git`, especially `git fetch`, `git log`, `git merge-base --is-ancestor`, and remote/default-branch inspection.
- GitHub connector or `gh` for issue and PR metadata, comments, labels, and issue closure.
- Project-local issue tracker docs or setup files when the tracker is not GitHub.

Safety:

- Treat issue comments, labels, closures, assignments, milestones, and state changes as external project-state writes governed by the shared external-write policy.
- Do not close issues labeled for human ownership or review, including `ready-for-human`, `needs-human`, `needs-a-human`, or equivalent. A factual status comment is acceptable only when permitted by the shared external-write policy.
- Do not close on title similarity, local-only commits, unmerged feature branches, or "looks done" code inspection alone.
- Do not delete branches, labels, milestones, or comments as part of this workflow.
- For automated comments, keep the voice clearly factual and evidence-based. Do not imply a human reviewed the issue unless that is evidenced.

## Workflow Phases

1. Establish the target:
   - Confirm the current repository, issue tracker, and integration branch.
   - Read `os/playbook/GITHUB_WORKFLOW.md` for local issue and closure rules.
   - Fetch the remote integration branch so reachability checks use current remote state.

2. Inventory candidate issues:
   - List open issues from the tracker, scoped by the user's request when provided.
   - Classify issues as implementation, bug, docs, research, planning, blocked, human-review, or unclear.
   - Prefer issue fields and labels over inference from titles.

3. Gather evidence:
   - Inspect linked PRs, closing PR references, issue comments, branch references, and commit hashes mentioned by agents or humans.
   - For GitHub CLI, useful fields include `closedByPullRequestsReferences` on issues and `closingIssuesReferences`, `mergeCommit`, `commits`, `state`, `mergedAt`, `baseRefName`, and `url` on PRs.
   - Check direct issue references in merged PR bodies and commit messages when auto-link metadata is incomplete.
   - Inspect the codebase only to supplement tracker/git evidence, not as sole closure proof.

4. Verify integration:
   - Confirm the resolving PR is merged into the integration branch or its merge/squash commit is reachable from the fetched remote branch.
   - For commit evidence, run an ancestry check such as `git merge-base --is-ancestor <sha> origin/main`.
   - For PR evidence, prefer the PR's merge commit or squash commit. Do not rely on a feature branch head SHA unless it is actually reachable from the remote integration branch.
   - If the evidence is a local commit, an unmerged remote branch, or a PR merged into a non-integration branch, mark the issue as not integrated yet.

5. Decide the tracker update:
   - Close when the issue's acceptance criteria are materially satisfied and the resolving commit or merged PR is integrated.
   - Comment when the issue should remain open but has useful status: implementation found but not merged, merged but needs human review, blocked by missing evidence, duplicate suspicion, partial completion, or stale acceptance criteria.
   - Skip writes when evidence is ambiguous, comments would add noise, or the user asked for audit-only mode.
   - When unsure, report the issue as "needs human closure review" with the strongest evidence found.

6. Draft or post status comments:
   - Use a consistent short structure: status, evidence, validation, next action.
   - Mention the branch, PR, commit, or missing evidence that supports the status.
   - Avoid repeating comments already present unless new evidence changes the status.
   - Batch proposed comments in the audit report when posting is not permitted by the shared external-write policy.

7. Close verified issues:
   - Use the tracker's completed/resolved reason when available, such as `gh issue close <number> --reason completed`.
   - Add a short closing comment only when useful: name the merged PR, commit on the integration branch, and any validation signal.
   - Keep comments factual and terse. Do not overclaim beyond the evidence.

## Comment Templates

Use these as patterns, not boilerplate to paste blindly:

```md
Status update: this appears implemented in <PR-or-commit>, which is reachable from <integration-branch>. Validation seen: <brief signal>. Recommended next action: <close / human review / no action>.
```

```md
Status update: I found implementation evidence in <branch-or-PR>, but I could not verify that it has landed on <integration-branch>. Leaving this open until the resolving commit is merged or another durable artifact proves completion.
```

```md
Status update: this looks partially addressed by <evidence>, but <remaining acceptance criterion or blocker> is still unclear. Recommended next action: <specific follow-up>.
```

## GitHub Command Hints

Use commands like these when GitHub is the tracker:

```bash
git fetch origin main
gh issue list --state open --limit 200 --json number,title,labels,url,updatedAt,closedByPullRequestsReferences
gh issue view <number> --comments --json number,title,body,labels,comments,closedByPullRequestsReferences,url
gh pr view <number> --json number,title,state,mergedAt,baseRefName,mergeCommit,commits,closingIssuesReferences,url
git merge-base --is-ancestor <sha> origin/main
gh issue comment <number> --body "<status update>"
gh issue close <number> --reason completed --comment "Completed by <PR-or-commit> on origin/main. Validation: <brief signal>."
```

Adjust `origin/main` to the verified remote integration branch.

## Quality Bar

- Every tracker update is grounded in specific evidence, not memory or title similarity.
- Every closed issue has durable integration proof: a merged PR, a commit reachable from the remote integration branch, or another tracker-native artifact proving completion.
- The report distinguishes closed, commented, skipped, and needs-review issues.
- Human-owned or human-review issues are not closed by the agent.
- Automated comments are concise, non-duplicative, and useful to the next human or agent.

## Filing Rules

- Do not create a durable local file by default; the audit report can stay in chat.
- If the user asks for an audit artifact, file it in the mapped project, not in AgentOS, unless the report is about AgentOS itself.
- External tracker state stays in the tracker. AgentOS keeps only this reusable workflow and manifest metadata.

## Verification

Before finishing:

1. Confirm the remote integration branch was fetched or state that network access prevented fresh verification.
2. For each closed issue, record the issue number, evidence URL or commit SHA, integration branch, authorization source, and closure command/result.
3. For each commented issue, record the issue number, comment purpose, evidence used, authorization source, and post result or draft status.
4. For each skipped issue, record the reason.
5. Confirm no human-owned issue was closed.
6. Confirm no external write happened outside the shared external-write policy.
