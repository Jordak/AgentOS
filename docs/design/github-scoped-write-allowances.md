# GitHub Scoped Write Allowances

Design readiness: ready to implement

## Problem

AgentOS Core currently treats external GitHub writes as approval-gated by default. Jordan's Personal Overlay also says GitHub comments, issues, PRs, pushes, repository settings, permissions, and visibility changes require explicit approval.

That default is safe, but too restrictive for Jordan-owned or Jordan-maintained repositories. It makes agents pause for routine workflow writes after the user has already assigned the task.

## Chosen Design

Keep Core conservative by default, but let matching Personal Overlay connection rules explicitly grant scoped write allowances for real accounts or repository sets.

Core should define the shape of such allowances:

- account or ownership scope;
- write types allowed without per-action approval;
- task conditions that activate the allowance;
- actions that still require explicit approval.

GitHub workflow policy should interpret those allowances for GitHub work. In a matching user-owned or maintained repository, agents may perform allowed routine writes when the current task clearly targets that repo.

## Intended Allowed Writes

A Personal Overlay GitHub allowance may permit:

- creating or updating issues;
- creating or updating pull requests;
- posting factual issue or PR comments;
- pushing commits or branches to the targeted repository.

## Required Approval Boundary

Agents should still ask before:

- merging pull requests;
- closing issues;
- creating new labels or milestones;
- changing permissions, visibility, branch protections, or repository settings;
- deleting branches, comments, labels, milestones, releases, repositories, or other nontrivial data;
- pushing outside the target repository or target branch scope;
- posting to repositories the user does not own or maintain;
- credentials/MFA, purchases, new external services, or automations that act without manual review.

## Non-goals

- Do not grant broad write permission to all GitHub repositories.
- Do not remove Core's conservative default for users without Personal Overlay allowances.
- Do not allow PR merges or issue closure without explicit approval.
- Do not change Google Drive, Gmail, Calendar, Slack, or other connector rules in this PR.
- Do not update Jordan's ignored Personal Overlay file in this Core PR.

## Acceptance Criteria

- `os/connections/SAFETY_RULES.md` says Core defaults may be superseded by explicit Personal Overlay scoped-write allowances.
- `os/playbook/GITHUB_WORKFLOW.md` defines GitHub-specific scoped write behavior and required approval boundaries.
- Feature-readiness, issue-audit, and other Core issue-write surfaces no longer contradict the Personal Overlay allowance model for routine GitHub issue/PR comments and issue creation.
- PR body includes readiness evidence pointing to this design doc.
- `scripts/run-validator` passes.

## Validation Plan

- Run `scripts/run-validator`.
- Inspect policy text for contradictions around GitHub issue creation, PR creation, comments, pushes, merges, and issue closure.
