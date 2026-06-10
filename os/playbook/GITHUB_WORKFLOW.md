# GitHub Workflow

Status: operational policy v2.

Use this file when drafting GitHub issues, PRDs, pull requests, pull request descriptions, branch handoffs, merge/landing notes, or issue closure comments.

Also use this file when another workflow produces a report, candidate list, branch, or implementation slice and the next user request asks to draft, open, create, or retry a pull request. The earlier workflow supplies context; this workflow owns GitHub routing, branch/PR discipline, and GitHub CLI authentication handling.

Use the branch/worktree checkpoint in this file before the first tracked-file edit when AgentOS Core or an AgentOS-backed mapped project change is meant to land through a pull request.

## Workflow Skill Routing

When the active agent harness exposes these skills or equivalent workflows, prefer the narrowest one that matches the job:

- Use `/to-prd` when the user wants to turn the current conversation context into a PRD and publish it to the project issue tracker.
- Use `/to-issues` when the user wants to break a plan, spec, or PRD into independently grabbable implementation issues. Publish issues only after the breakdown is approved, and do not close or modify any parent issue as part of that workflow.
- Use `/triage` for issue intake, classification, readiness checks, label/state transitions, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`, and agent brief comments.

Do not use these skills or equivalent workflows as the default for simple PR descriptions, branch integration, merge verification, or post-implementation issue closure unless the work also needs PRD generation, issue breakdown, or triage/state changes.

When using `/triage`, follow its posting rules, including the AI-generated triage disclaimer. If the repository's issue-tracker or triage-label mapping is missing, run `/setup-matt-pocock-skills` or ask the user for the mapping.

## GitHub Write Permissions

GitHub writes follow `os/connections/SAFETY_RULES.md` plus any matching Personal Overlay connection allowances. If no allowance or current user request covers the target repository, account, action, and task scope, ask before writing externally.

## Issue and PR Writing

When drafting GitHub issues, PRDs, or pull request descriptions, make the contrast explicit before describing the desired change:

- Start with the current or previous behavior/design.
- Explain why that behavior/design should not remain as-is.
- Then describe the desired behavior/design and how it will be validated.

Use snapshot language to avoid staleness in issues. Prefer phrases like "As of this issue being written, ..." or "Currently, ..." rather than presenting the state of the system as permanent fact. For PRs, use "Previously, ..." because the PR itself changes the baseline.

This convention helps future agents understand not only what to build, but why the old shape was insufficient.

When writing PR bodies, issue comments, commit messages, or other GitHub text that references issues without resolving them, avoid phrases that combine GitHub auto-closing keywords with an issue reference, even in negated sentences. For example, do not write non-closing phrases like `does not close #123` or `does not fix #123`; GitHub can still interpret the keyword-plus-reference pattern as a closing reference. Prefer wording such as `GitHub issue #123 remains open`, `tracked in GitHub issue #123`, or `related to GitHub issue #123`. Use closing keywords only when the workflow intentionally resolves the issue and the integration evidence supports closure.

## PR Readiness Fields

For feature-sized implementation PRs, include these fields in the PR body:

```md
Readiness evidence: <GitHub issue, PRD, ADR, local design doc, or gate-skip reason>
Readiness verdict: Ready to Implement
```

Prefer a GitHub issue as the readiness evidence for issue-driven work. The issue can contain the design directly or link to a larger PRD, ADR, or local design doc. Create a separate design doc only when the design is too large, architectural, private, or not naturally issue-shaped.

Use `Readiness verdict: Gate Skipped` only when the implementation-readiness gate is exempt or intentionally bypassed, and put the reason in `Readiness evidence:`. A `ready-for-agent` label or a confident implementation prompt is not a substitute for these fields.

Before opening, updating, or merging a feature PR, check that the body still points to current readiness evidence and does not contain stale paths, obsolete commands, or an old readiness verdict. Treat these fields as non-canonical documentation that still matters because future agents read PR bodies.

## GitHub CLI Auth In Sandboxed Harnesses

Some agent harnesses run shell commands in a sandbox that cannot read the system keyring correctly. In that context, `gh auth status` may report "the token is invalid" even when the user's GitHub CLI credential is valid in the normal shell.

When an authenticated `gh` command is needed and sandboxed `gh auth status` reports an invalid token:

- Do not immediately ask the user to reauthenticate.
- Make the immediate next step a retry of the exact auth check or needed GitHub CLI command with the harness's approved elevation path so `gh` can access the system keyring. Do not substitute environment diagnosis, connector fallback, or general troubleshooting for this keyring-capable retry.
- Treat the credential as actually broken only if the elevated `gh auth status -h github.com` also fails.
- Do not inspect token-valued environment variables as the first response to this mismatch. If environment-variable diagnosis is still needed after the elevated keyring-capable retry, check only variable presence or names and do not print values.
- Never use or suggest `gh auth status --show-token`, `gh auth token`, `env | rg TOKEN`, or other token-printing commands unless the user explicitly asks and the risk is necessary.
- Prefer GitHub connector reads when they are sufficient, but use elevated `gh` for CLI-only actions such as PR creation when connector permissions are read-only.

Response shape for this mismatch: identify likely sandbox/keyring isolation, retry through the approved elevated path, and wait for that result before any other diagnosis. A response that mentions token-printing commands or makes environment inspection the first step is wrong for this case.

Concrete example: in Codex Desktop, an unelevated `gh auth status` can report an invalid token while elevated `gh auth status -h github.com` succeeds with a keyring-backed token. The correct repair is to rerun the needed `gh` operation with keyring access, not to send the user through a redundant `gh auth login` flow.

## Branch and Integration Discipline

When implementation work is meant to land in a repository, the durable artifact is integrated code, not a local commit or unmerged branch.

- Before tracked-file edits, inspect the current branch and working-tree state, for example with `git status --short --branch`.
- Treat `main` as protected for PR-bound work. Do not start tracked-file edits directly on `main` when the change is meant to land through a pull request.
- Use the harness-provided worktree and feature branch when they exist. Otherwise create or switch to a feature branch or isolated worktree according to the repository's local policy before tracked-file edits.
- If the checkout is already dirty on `main`, stop before adding more edits. Preserve existing changes, identify whether they are yours, and move only the owned or approved work to the proper feature branch or worktree.
- For AgentOS Core or publishable support-file changes, use an isolated feature-branch worktree, open a pull request, wait for required validators, and squash merge the PR through GitHub.
- If the work is on a pushed feature branch and is meant to land, open a pull request. Do not treat a pushed branch as the final artifact unless the user explicitly asked only for a branch.
- When updating a feature branch with newer integration-branch changes, prefer rebasing the feature branch onto `main` and force-pushing with lease when the branch is yours to rewrite.
- Do not merge `main` into a feature branch. The PR branch hygiene check rejects merge commits in PR branches.
- For AgentOS public repository persistence, use `scripts/agent-push` for feature-branch pushes. Use `scripts/agent-push --force-with-lease` only after rebasing the current non-main branch.

If `main` was accidentally merged into a feature branch, recover by backing up and rebasing:

```bash
git switch <feature-branch>
git branch backup/<feature-branch>-before-rebase
git fetch origin
git rebase origin/main
scripts/run-validator
scripts/agent-push --force-with-lease origin <feature-branch>
```

Resolve conflicts during the rebase if prompted. If the rebase becomes unclear, abort it and create a clean branch from `origin/main`, then cherry-pick only the real feature commits.

## Personal Overlay and Worktrees

Git worktrees isolate tracked AgentOS Core and publishable support-file edits. They do not isolate or synchronize ignored Personal Overlay state.

When work is routed to `personal/os/`, use `os/playbook/PERSONAL_OVERLAY.md` as the authority. A feature worktree's `personal/os/` directory may contain only the tracked public-safe skeleton. It should not be treated as the live Personal Overlay unless the user explicitly assigned that worktree as a private overlay workspace.

For Personal Overlay reads from a feature worktree, inspect the canonical primary AgentOS checkout's `personal/os/`. For Personal Overlay writes, use the primary checkout only when the task is personal-state work and the agent has clear path ownership.

Personal-only ignored-file edits may happen in the primary checkout even when it is on `main`, because they are not Git commits. If the task also requires an AgentOS Core or publishable support-file change, split the work: edit ignored Personal Overlay files in the primary checkout, and make tracked public-safe changes on a feature branch in an isolated worktree with a pull request.

Do not broad-copy `personal/os/` into feature worktrees, and do not use `git add -f personal/...` unless the user explicitly approves a narrow, public-safe skeleton or template change.

## Subagent / Feature Branch Delegation

When delegating implementation issues to subagents on feature branches, make worktree isolation explicit, and make landing and issue closure an integration responsibility, not a branch-worker responsibility.

- Give each subagent its own isolated worktree and feature branch. Prefer `git worktree` checkouts rooted from the current integration branch.
- Preserve Codex-managed worktrees when Codex creates them; for manual AgentOS worktrees, use `$CODEX_HOME/worktrees/`.
- Do not have multiple subagents share the same checkout, working tree, index, or feature branch.
- Record each worker's worktree path, branch name, assigned issue, and owned files or responsibility before starting parallel work.
- Before integrating results, inspect the worktree list and each worker branch status to confirm workers did not step on each other's branches or local changes.
- Instruct workers to commit, push their feature branch, open or update their PR when their contract owns that step, and return evidence through their Workflow Result or issue/PR comments.
- Do not instruct feature-branch workers to merge PRs, close issues, or delete branches.
- Landing, issue closure, and branch deletion belong to a workflow or human integration step whose contract explicitly owns those surfaces.
- Issue closure belongs after the resolving commit has landed on `main` or the pull request has merged and the integration owner has reconciled the issue acceptance criteria.
- Avoid wording such as "close after the commit is pushed" unless the push is directly to the integration branch.

Standard worker handoff language:

> Work only in your assigned isolated worktree and feature branch. Do not reuse
> or switch another worker's branch. Do not commit directly to `main`. Rebase
> on `origin/main` instead of merging `main` into your branch. Push with
> `scripts/agent-push` and report branch, PR, commit, validation, and
> review evidence in your Workflow Result. If you need Personal Overlay state,
> read it from the canonical primary AgentOS checkout, not from this feature
> worktree's ignored-file skeleton. Write Personal Overlay files only when
> explicitly assigned a non-overlapping path. Do not merge PRs, close issues,
> or delete branches. The integration owner will decide landing and closure
> after the resolving PR is merged and the issue acceptance criteria are reconciled.

## GitHub Issue Closure Discipline

Closing a GitHub issue is an external project-state action, not just a local bookkeeping step.

Before closing an implementation issue:

- Ensure the resolving commit or commits have landed on the repository's integration branch, usually `main`, either by pushing directly to that branch or by merging a pull request/feature branch into it.
- A pushed feature branch is not enough. A comment that references only a local commit hash or an unmerged remote branch is not enough.
- Verify the remote integration branch contains the resolving commit before closing the issue.
- Reconcile the issue acceptance criteria against the merged PR or integration commit evidence.
- Confirm no human-review label such as `ready-for-human`, `needs-human`, `needs-a-human`, or equivalent still requires a human closure decision.
- Then close the issue with a factual comment that references the integration branch, the commit on `main`, the merged PR or another durable integration artifact, and relevant validation evidence when available.

## Workflow Labels

Respect workflow labels as authority:

- `ready-for-agent` means an agent may implement the issue when the instructions are clear.
- For feature-sized implementation work, `ready-for-agent` is not a substitute for implementation readiness; the work must also pass or intentionally skip `os/playbook/IMPLEMENT_FEATURES.md`, and the PR body should expose readiness evidence and the readiness verdict.
- `ready-for-human`, `needs-human`, `needs-a-human`, or equivalent labels mean a human must do the work or make the closure decision. Do not close these issues as an agent, even if local work appears complete. Instead, leave an evidence comment and ask the user or the human owner to review and close.
