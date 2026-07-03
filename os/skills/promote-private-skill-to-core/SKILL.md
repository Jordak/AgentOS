---
name: promote-private-skill-to-core
description: "Design, audit, or perform an approved promotion of a maintained Personal Overlay skill into an AgentOS Core-safe skill by separating reusable workflow from private identity, account, path, project, live-agent, generated-output, and local configuration details."
---

# Promote Private Skill To Core

## Trigger

Use this when the user asks to sanitize, promote, upstream, extract, or turn a Personal Overlay skill into an AgentOS Core skill.

Also use this when a private skill has become broadly reusable but still contains private user-specific facts, local paths, account assumptions, personal examples, live agent routing, generated outputs, or Personal Overlay configuration.

Do not use this for ordinary Core skill creation from public examples. Use `skillify-agentos` for general skillification, and route here only when the candidate starts from a Personal Overlay skill or private skill config.

## Goal

Turn a private skill candidate into a Core-safe reusable workflow without leaking private state and without breaking the user's private behavior.

The workflow can stop after a read-only promotion audit. When implementation is explicitly approved, it can create or update a Core skill, Core export-map entry, validation fixtures, and the matching Personal Overlay config or private thin adapter plan.

## Contract

Inputs:

- A candidate Personal Overlay skill path, private manifest entry, private skill config overlay, or user-approved private skill content.
- `os/playbook/PERSONAL_OVERLAY.md`, `os/skills/SKILL_CONTRACT.md`, `os/skills/MANIFEST.md`, and `os/skills/PERSONAL_OVERLAY_MANIFEST.template.md`.
- The live `personal/os/skills/MANIFEST.md` only when the user or task explicitly authorizes private skill governance review.
- At least one concrete example showing repeated use, repeated requests, repeated agent failures, or another reason the workflow is reusable beyond one private situation.
- Relevant private source-map or connection references only when approved and needed to understand what must remain private.

Output artifact:

- By default, a promotion audit report with candidate status, reusable evidence, private/Core boundary map, recommended Core shape, private preservation plan, validation plan, non-goals, and blockers.
- When implementation is explicitly approved, a sanitized Core skill or skill update, `os/skills/MANIFEST.md` update, optional safe smoke fixture, and optional Personal Overlay config or private thin-adapter instructions.

Mutability:

- Read-only by default.
- Local-write only when the user explicitly approves creating or updating Core files, local design docs, safe fixtures, or Personal Overlay config.
- External-write only when permitted by the shared external-write policy for GitHub issues, PRs, comments, labels, or other external project state.

Tools and connectors:

- Local filesystem, `rg`, `git`, AgentOS validators, and privacy scanners.
- GitHub connector or `gh` reads only when issue or PR context is needed.
- `verify-privacy` for semantic privacy review.
- No connector account reads by default.

Safety:

- Do not scan, enumerate, copy, expose, or summarize Personal Overlay skills unless the user or current task explicitly authorizes that private scope.
- Do not treat a directory-only private skill as a maintained canonical private skill; first require or propose private manifest governance.
- Do not copy private examples, local paths, private project names, account IDs, connector details, live agent state, generated reports, histories, queues, or run logs into Core.
- Do not modify `expose-skills` to scan or expose Personal Overlay skills.
- Ask before external writes, current-machine skill exposure changes, connector reads, Personal Overlay writes, or destructive edits.

## Workflow Phases

1. Establish scope.
   - Identify the candidate skill, requested mode, and whether the task is audit-only or approved for implementation.
   - Read the Core skill contract, Core manifest, Personal Overlay policy, private manifest template, and any linked issue or design source.
   - If running from an isolated feature worktree, resolve Personal Overlay reads through the canonical primary AgentOS checkout unless the user assigned a different private overlay workspace.

2. Check candidate governance.
   - Prefer a `personal/os/skills/MANIFEST.md` entry with `Lifecycle status: maintained`.
   - If the candidate is directory-only or missing manifest facts, stop promotion and recommend private governance review first.
   - Confirm the private manifest entry does not duplicate source-map or connection inventories that belong in `personal/os/context/SOURCE_MAP.md` or `personal/os/connections/CONNECTIONS.md`.

3. Prove reusable value.
   - Require at least one concrete example and prefer two or more.
   - Good evidence includes repeated successful use, repeated user requests, repeated agent failures the skill prevents, a stable workflow contract, safe smoke examples, and usefulness for a stranger without the original Personal Overlay.
   - Reject promotion when the only evidence is private convenience, one-off preference, live personal agent behavior, account-specific operating assumptions, or generated reports.

4. Build a boundary map.
   Classify every meaningful part of the private skill:
   - Core-safe workflow behavior;
   - Core-safe safety or filing policy;
   - private config for `personal/os/skills/<core-skill>/CONFIG.md`;
   - private examples or smoke trials that must remain private;
   - live agent, automation, report, queue, or run-history state that belongs elsewhere in the Personal Overlay;
   - content to discard instead of preserving.

5. Draft the sanitized Core shape.
   - Rewrite the workflow from the reusable behavior instead of copying the private skill.
   - Apply `os/skills/SKILL_CONTRACT.md`: inputs, output artifact, mutability, tools/connectors, safety, phases, quality bar, verification, and filing rules.
   - Use the Markdown manifest API in `os/skills/MANIFEST.md`.
   - Add deterministic validation only for exact, stable invariants. Keep judgment-heavy privacy separation in Markdown guidance.

6. Preserve private behavior.
   - Use `personal/os/skills/<core-skill>/CONFIG.md` when the Core workflow only needs private inputs, defaults, paths, account references, or private examples.
   - Keep or create a private thin-adapter skill when behavior still routes to private agents, live automations, connected-account assumptions, generated histories, or private artifact roots.
   - Do not force the old private skill to disappear just because a Core-safe version exists.

7. Validate before delivery.
   - Run AgentOS validators and diff checks for approved Core edits.
   - Use `verify-privacy` or its checklist for semantic privacy review.
   - Confirm no live `personal/os/` files were copied into Core or accidentally tracked.
   - For PR-bound Core changes, follow `os/playbook/GITHUB_WORKFLOW.md` and include readiness evidence in the PR body.

## Mandatory Sanitization Checklist

Before proposing a Core promotion as safe, inspect paths and content for:

- personal identity, preferences, routines, handles, emails, and biographical facts;
- private project, repository, client, workplace, and source-map references;
- absolute local paths, machine-specific tool paths, adapter paths, and artifact roots;
- account IDs, calendar IDs, Drive URLs, private GitHub URLs, connector names, and permission assumptions;
- live agent jobs, automation schedules, prompts, generated outputs, briefs, reports, histories, queues, and run logs;
- private filenames or directory names that leak state even when file contents are rewritten;
- examples that look sanitized but still encode real private facts;
- private marker hits from the local privacy marker list when available.

## Filing Rules

- Core-safe promoted skill sources live under `os/skills/<skill-name>/`.
- Core export membership lives in `os/skills/MANIFEST.md`; skill maintenance facts live in the promoted skill, its provenance files, or generated audit evidence.
- Private inputs for reusable Core skills live in `personal/os/skills/<skill-name>/CONFIG.md` when a separate config is warranted.
- Private skill governance facts live in ignored `personal/os/skills/MANIFEST.md`.
- Private examples, reports, run histories, live agent state, live automation state, and generated outputs remain in the relevant Personal Overlay layer.
- Promotion audit reports stay in chat by default. Save them only when the user asks; private audits belong in the Personal Overlay.

## Quality Bar

- The candidate was governed or clearly blocked on governance.
- Reusability evidence is named and specific.
- The boundary map separates Core-safe behavior from private config and private state.
- The Core draft is rewritten as public-safe workflow guidance, not copied from private source.
- Private behavior has a preservation plan.
- Privacy review includes semantic inspection, not only secret scanning.
- The workflow does not change external state or current-machine skill exposure without approval.

## Verification

Before finishing:

1. Confirm whether the run was audit-only or implementation-approved.
2. Confirm the candidate governance status and reusable evidence.
3. Confirm the boundary map was created.
4. Confirm all mandatory sanitization categories were considered.
5. Confirm the private preservation plan.
6. If Core files changed, run `scripts/run-validator` and `git diff --check`.
7. If validator behavior changed, run `scripts/run-validator --self-test`.
8. Confirm no unapproved Personal Overlay writes, external writes, connector reads, or current-machine exposure changes happened.
9. Confirm no private examples, paths, account details, live agent state, generated outputs, or run histories were copied into Core.
