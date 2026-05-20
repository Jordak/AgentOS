# GitHub Workflow

Status: operational policy v1.

Use this file when drafting GitHub issues, PRDs, pull request descriptions, branch handoffs, merge/landing notes, or issue closure comments.

## Workflow Skill Routing

When the active agent harness exposes these skills or equivalent workflows, prefer the narrowest one that matches the job:

- Use `/to-prd` when the user wants to turn the current conversation context into a PRD and publish it to the project issue tracker.
- Use `/to-issues` when the user wants to break a plan, spec, or PRD into independently grabbable implementation issues. Publish issues only after the breakdown is approved, and do not close or modify any parent issue as part of that workflow.
- Use `/triage` for issue intake, classification, readiness checks, label/state transitions, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`, and agent brief comments.

Do not use these skills or equivalent workflows as the default for simple PR descriptions, branch integration, merge verification, or post-implementation issue closure unless the work also needs PRD generation, issue breakdown, or triage/state changes.

When using `/triage`, follow its posting rules, including the AI-generated triage disclaimer. If the repository's issue-tracker or triage-label mapping is missing, run `/setup-matt-pocock-skills` or ask the user for the mapping.

## Issue and PR Writing

When drafting GitHub issues, PRDs, or pull request descriptions, make the contrast explicit before describing the desired change:

- Start with the current or previous behavior/design.
- Explain why that behavior/design should not remain as-is.
- Then describe the desired behavior/design and how it will be validated.

Use snapshot language to avoid staleness in issues. Prefer phrases like "As of this issue being written, ..." or "Currently, ..." rather than presenting the state of the system as permanent fact. For PRs, use "Previously, ..." because the PR itself changes the baseline.

This convention helps future agents understand not only what to build, but why the old shape was insufficient.

## Branch and Integration Discipline

When implementation work is meant to land in a repository, the durable artifact is integrated code, not a local commit or unmerged branch.

- If the work is on a pushed feature branch and is meant to land, either open a pull request or explicitly merge the branch yourself when the workflow and permissions allow it.
- Do not leave the branch as the final artifact unless the user asked only for a branch.
- When updating a feature branch with newer integration-branch changes, prefer rebasing the feature branch onto `main` and force-pushing with lease when the branch is yours to rewrite.
- Do not merge `main` into a feature branch unless the user or the repository workflow explicitly asks for merge commits.

## Subagent / Feature Branch Delegation

When delegating implementation issues to subagents on feature branches, make worktree isolation explicit, and make issue closure an integration responsibility, not a branch-worker responsibility.

- Give each subagent its own isolated worktree and feature branch. Prefer `git worktree` checkouts rooted from the current integration branch.
- Do not have multiple subagents share the same checkout, working tree, index, or feature branch.
- Record each worker's worktree path, branch name, assigned issue, and owned files or responsibility before starting parallel work.
- Before integrating results, inspect the worktree list and each worker branch status to confirm workers did not step on each other's branches or local changes.
- Instruct workers to commit, push their feature branch, and comment evidence on the issue.
- Do not instruct feature-branch workers to close the issue.
- Issue closure belongs to the integration step, after the resolving commit has landed on `main` or the pull request has merged.
- Avoid wording such as "close after the commit is pushed" unless the push is directly to the integration branch.

Standard worker handoff language:

> Work only in your assigned isolated worktree and feature branch. Do not reuse
> or switch another worker's branch. Push your feature branch and comment on the
> issue with branch, commit, validation, and smoke-trial evidence. Do not close
> the issue. The integrator will close it after the resolving commit lands on
> `main`.

## GitHub Issue Closure Discipline

Closing a GitHub issue is an external project-state action, not just a local bookkeeping step.

Before closing an implementation issue:

- Ensure the resolving commit or commits have landed on the repository's integration branch, usually `main`, either by pushing directly to that branch or by merging a pull request/feature branch into it.
- A pushed feature branch is not enough. A comment that references only a local commit hash or an unmerged remote branch is not enough.
- Verify the remote integration branch contains the resolving commit before closing the issue.
- Then close the issue with a comment that references the commit on `main`, the merged PR, or another durable artifact that proves the work is integrated.

## Workflow Labels

Respect workflow labels as authority:

- `ready-for-agent` means an agent may implement the issue when the instructions are clear.
- `ready-for-human`, `needs-human`, `needs-a-human`, or equivalent labels mean a human must do the work or make the closure decision. Do not close these issues as an agent, even if local work appears complete. Instead, leave an evidence comment and ask the user or the human owner to review and close.
