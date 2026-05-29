# GitHub Scoped Write Allowances

Design readiness: ready to implement

## Problem

AgentOS Core currently treats external GitHub writes as approval-gated by default. Jordan's Personal Overlay can also define narrower account- or repository-specific rules, but Core does not yet give those rules a clean way to supersede generic defaults.

That default is safe, but too restrictive when a trusted Personal Overlay has already authorized a narrow class of routine writes.

## Chosen Design

Keep Core conservative by default, but let matching Personal Overlay connection rules explicitly grant scoped write allowances for real accounts or repository sets.

Core should define the shape of such allowances:

- account or ownership scope;
- write types allowed without per-action approval;
- task conditions that activate the allowance;
- actions that still require explicit approval.

GitHub workflow policy should not define its own permission taxonomy. It should point to the central safety policy and apply any matching Personal Overlay allowance.

Skills should avoid restating Personal Overlay allowance mechanics. They should link to the central external-write policy and keep only skill-specific safety rules.

## Approval Boundary

This PR should define where approval rules live, not enumerate GitHub-specific allowances. Personal Overlay files remain responsible for naming concrete accounts, repositories, write types, activation conditions, and actions that still require approval.

## Non-goals

- Do not grant broad write permission to all GitHub repositories.
- Do not remove Core's conservative default for users without Personal Overlay allowances.
- Do not define Jordan's concrete GitHub allowance in Core.
- Do not change Google Drive, Gmail, Calendar, Slack, or other connector rules in this PR.
- Do not update Jordan's ignored Personal Overlay file in this Core PR.

## Acceptance Criteria

- `os/connections/SAFETY_RULES.md` says Core defaults may be superseded by explicit Personal Overlay scoped-write allowances.
- `os/playbook/GITHUB_WORKFLOW.md` points GitHub writes to the centralized safety policy instead of repeating allowance examples.
- Feature-readiness, issue-audit, and other Core issue-write surfaces defer to the centralized external-write policy instead of duplicating Personal Overlay allowance mechanics.
- PR body includes readiness evidence pointing to this design doc.
- `scripts/run-validator` passes.

## Validation Plan

- Run `scripts/run-validator`.
- Inspect policy text for repeated Personal Overlay allowance mechanics outside `os/connections/SAFETY_RULES.md`.
