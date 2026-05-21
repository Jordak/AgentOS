# GitHub Workflow

Status: operational policy v2.

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

## GitHub CLI Auth In Sandboxed Harnesses

Some agent harnesses run shell commands in a sandbox that cannot read the system keyring correctly. In that context, `gh auth status` may report "the token is invalid" even when the user's GitHub CLI credential is valid in the normal shell.

When an authenticated `gh` command is needed and sandboxed `gh auth status` reports an invalid token:

- Do not immediately ask the user to reauthenticate.
- First retry the exact auth check or GitHub CLI command with the harness's approved elevation path so `gh` can access the system keyring.
- Treat the credential as actually broken only if the elevated `gh auth status -h github.com` also fails.
- Never use `gh auth status --show-token`, `gh auth token`, or other token-printing commands unless the user explicitly asks and the risk is necessary.
- Prefer GitHub connector reads when they are sufficient, but use elevated `gh` for CLI-only actions such as PR creation when connector permissions are read-only.

Concrete example: in Codex Desktop, an unelevated `gh auth status` can report an invalid token while elevated `gh auth status -h github.com` succeeds with a keyring-backed token. The correct repair is to rerun the needed `gh` operation with keyring access, not to send the user through a redundant `gh auth login` flow.

## Branch and Integration Discipline

When implementation work is meant to land in a repository, the durable artifact is integrated code, not a local commit or unmerged branch.

- Treat `main` as protected. Do not commit or push AgentOS Core/public changes directly to `main`.
- Make Core/public changes on a feature branch in an isolated worktree, open a pull request, wait for required validators, and squash merge the PR through GitHub.
- Use the harness-provided worktree when one exists. Otherwise create an external Git worktree under `$CODEX_HOME/worktrees/`, not inside the AgentOS repository.
- If the work is on a pushed feature branch and is meant to land, open a pull request. Do not treat a pushed branch as the final artifact unless the user explicitly asked only for a branch.
- When updating a feature branch with newer integration-branch changes, prefer rebasing the feature branch onto `main` and force-pushing with lease when the branch is yours to rewrite.
- Do not merge `main` into a feature branch. The PR branch hygiene check rejects merge commits in PR branches.
- Use `scripts/agent-push` for feature-branch pushes. Use `scripts/agent-push --force-with-lease` only after rebasing the current non-main branch.

If `main` was accidentally merged into a feature branch, recover by backing up and rebasing:

```bash
git switch <feature-branch>
git branch backup/<feature-branch>-before-rebase
git fetch origin
git rebase origin/main
python3 os/verification/scripts/validate_agentos.py
scripts/agent-push --force-with-lease origin <feature-branch>
```

Resolve conflicts during the rebase if prompted. If the rebase becomes unclear, abort it and create a clean branch from `origin/main`, then cherry-pick only the real feature commits.

## Personal Overlay and Worktrees

Git worktrees isolate tracked Core/public edits. They do not isolate or synchronize ignored Personal Overlay state.

When work is routed to `personal/os/`, use `os/playbook/PERSONAL_OVERLAY.md` as the authority. A feature worktree's `personal/os/` directory may contain only the tracked public-safe skeleton. It should not be treated as the live Personal Overlay unless the user explicitly assigned that worktree as a private overlay workspace.

For Personal Overlay reads from a feature worktree, inspect the canonical primary AgentOS checkout's `personal/os/`. For Personal Overlay writes, use the primary checkout only when the task is personal-state work and the agent has clear path ownership.

Personal-only ignored-file edits may happen in the primary checkout even when it is on `main`, because they are not Git commits. If the task also requires a Core/public change, split the work: edit ignored Personal Overlay files in the primary checkout, and make tracked Core changes on a feature branch in an isolated worktree with a pull request.

Do not broad-copy `personal/os/` into feature worktrees, and do not use `git add -f personal/...` unless the user explicitly approves a narrow, public-safe skeleton or template change.

## Subagent / Feature Branch Delegation

When delegating implementation issues to subagents on feature branches, make worktree isolation explicit, and make issue closure an integration responsibility, not a branch-worker responsibility.

- Give each subagent its own isolated worktree and feature branch. Prefer `git worktree` checkouts rooted from the current integration branch.
- Preserve Codex-managed worktrees when Codex creates them; for manual AgentOS worktrees, use `$CODEX_HOME/worktrees/`.
- Do not have multiple subagents share the same checkout, working tree, index, or feature branch.
- Record each worker's worktree path, branch name, assigned issue, and owned files or responsibility before starting parallel work.
- Before integrating results, inspect the worktree list and each worker branch status to confirm workers did not step on each other's branches or local changes.
- Instruct workers to commit, push their feature branch, and comment evidence on the issue.
- Do not instruct feature-branch workers to close the issue.
- Issue closure belongs to the integration step, after the resolving commit has landed on `main` or the pull request has merged.
- Avoid wording such as "close after the commit is pushed" unless the push is directly to the integration branch.

Standard worker handoff language:

> Work only in your assigned isolated worktree and feature branch. Do not reuse
> or switch another worker's branch. Do not commit directly to `main`. Rebase
> on `origin/main` instead of merging `main` into your branch. Push with
> `scripts/agent-push` and comment on the issue with branch, commit,
> validation, and smoke-trial evidence. If you need Personal Overlay state,
> read it from the canonical primary AgentOS checkout, not from this feature
> worktree's ignored-file skeleton. Write Personal Overlay files only when
> explicitly assigned a non-overlapping path. Do not close the issue. The
> integrator will close it after the resolving PR is squash-merged into `main`.

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
