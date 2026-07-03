---
name: github-issue-lifecycle
description: Route GitHub issue lifecycle work from issue selection through batch coordination, one-issue implementation, PR review handoff, and authorized issue landing using private lifecycle modules.
---

# GitHub Issue Lifecycle

## Goal

Route GitHub issue lifecycle work through one exported skill while keeping the workflow leaves private until a local routing decision selects them.

This skill is the harness-visible entry point for the GitHub issue lifecycle family. It does not duplicate the full procedures for issue selection, batch coordination, repeated batch loops, one-issue implementation, or issue landing. It chooses the right private module, then loads only the selected module's implementation.

## Contract

Inputs:

- A GitHub issue, pull request, repository, batch goal, issue-selection question, merge report, or landing request.
- Current repository checkout and local instructions when the work concerns the current project.
- Applicable GitHub workflow policy, especially `os/playbook/GITHUB_WORKFLOW.md`.
- Applicable orchestration-loop policy from `os/skills/ORCHESTRATION_LOOPS.md` for repeated, delegated, or recoverable work.

Output artifact:

- A selected private module invocation, recommendation, Workflow Result, pull request, issue update, or landing result, depending on the selected module.

Mutability:

- Mixed.
- Read-only when selecting issues, explaining routing, or auditing available lifecycle paths.
- Local-write or external-write only when the selected private module's contract and the current Authorization Boundary permit it.

Tools and connectors:

- Local filesystem, `git`, `rg`, GitHub connector or `gh`, and repository validators as required by the selected module.

Safety:

- Do not treat this exported routing skill as permission to merge PRs, close issues, delete branches, create labels, change repository settings, grant permissions, handle credentials, or post outside the selected module's Authorization Boundary.
- Ask before any external write not already covered by the selected module and current user request.
- Preserve branch/worktree discipline from `os/playbook/GITHUB_WORKFLOW.md`.
- Keep Personal Overlay state out of public issue, PR, and review surfaces unless a separate private workflow explicitly owns it.

## Routing

Read these private module interfaces first:

- `os/skills/github-issue-lifecycle/batch-orchestration/INTERFACE.md`
- `os/skills/github-issue-lifecycle/issue-execution/INTERFACE.md`

Choose `batch-orchestration` when the user wants to select what to work on, coordinate a batch pass, launch or track workers, resume a batch, or repeatedly run issue batches.

Choose `issue-execution` when the user names one issue to implement, one merged issue to reconcile or close, or one issue's acceptance criteria to verify against integration evidence.

After choosing a mid-level module, read that module's `IMPLEMENTATION.md`. The mid-level implementation may read child `INTERFACE.md` files to choose a leaf. Load the selected child `IMPLEMENTATION.md` only after the leaf has been selected.

## Workflow Phases

1. Establish the target repository, issue or batch target, current branch/worktree, and requested mode.
2. Read local instructions plus `os/playbook/GITHUB_WORKFLOW.md` and `os/skills/ORCHESTRATION_LOOPS.md` when the request is mutating, repeated, delegated, or PR-bound.
3. Read the two mid-level `INTERFACE.md` files and choose the smallest matching module.
4. Read the selected mid-level `IMPLEMENTATION.md`.
5. Let the selected mid-level module choose and invoke the leaf module by reading child interfaces before child implementations.
6. Return the selected module's native report, Workflow Result, PR, or issue-state evidence.

## Quality Bar

- The exported skill answers the top-level routing question without loading every leaf implementation.
- Parent routing uses `INTERFACE.md` files, not child `IMPLEMENTATION.md` files.
- The selected module's Authorization Boundary, mutability, recovery, and validation rules are preserved.
- The result clearly names the selected module and any external writes or blockers.

## Filing Rules

- GitHub issue lifecycle procedure lives under this exported skill.
- Private modules live under `batch-orchestration/` and `issue-execution/`.
- Issue-specific readiness evidence, PR review evidence, merge reports, and closure evidence stay on their issue/PR surfaces or in the selected module's approved result surface.
- Reusable lifecycle policy shared across modules may live under `references/`.

## Verification

Before finishing changes to this skill or its private modules:

1. Confirm `os/skills/MANIFEST.md` exports `github-issue-lifecycle` rather than the private leaf modules.
2. Confirm parent files route through child `INTERFACE.md` files before child `IMPLEMENTATION.md` files.
3. Run `git diff --check`.
4. Run `scripts/run-validator`.
