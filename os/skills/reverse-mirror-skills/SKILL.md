---
name: reverse-mirror-skills
description: Audit local skill mirrors for skills missing from AgentOS, recommend Core vs Personal Overlay homes or local cleanup, and apply approved imports. Use when the user asks to reverse mirror skills, promote local skill directories into AgentOS, reconcile local-only skills, or decide whether local skills belong in AgentOS Core or the Personal Overlay.
---

# Reverse Mirror Skills

## Goal

Review locally installed skills as untrusted inputs, recommend what should happen to each one, and apply only the user-approved actions that make a skill canonical in AgentOS or clean up local skill clutter.

This complements `mirror-skills`: `mirror-skills` pushes canonical AgentOS skills out to the local harness, while this workflow reviews local harness skills before pulling selected ones back into AgentOS.

## Contract

Inputs:

- AgentOS root, defaulting to the current workspace.
- Local skill mirror root, defaulting to the user's current-machine skill mirror directory.
- `os/skills/MANIFEST.md`, `os/skills/SKILL_CONTRACT.md`, `os/skills/README.md`, `os/playbook/PERSONAL_OVERLAY.md`, and `os/skills/mirror-skills/SKILL.md`.
- Local skill directories containing `SKILL.md`.
- Local skill metadata that may indicate third-party origin, such as package manager metadata, source URLs, author/license fields, upstream README text, or install-tool markers.
- User approval for each import, replacement, archive, deletion, or follow-up issue.

Output artifact:

- A full prioritized recommendation table for local skills.
- A separate excluded list for local skills that appear to be externally sourced or not owned by the user.
- Optional canonical skill files under `os/skills/<skill-name>/` or `personal/os/skills/<skill-name>/`.
- Optional Core manifest updates for Core imports.
- Optional local or Personal Overlay backup directories.
- Optional follow-up issue drafts or created issues only when the user explicitly asks.

Mutability:

- Read-only in audit and recommendation mode.
- Local-write after approval when importing skills, updating Core manifest metadata, backing up local or Personal Overlay skills, archiving local skills, generating active-harness metadata, or syncing mirrors through `mirror-skills`.
- External-write only when the user explicitly asks to create or update GitHub issues.

Tools and connectors:

- Local filesystem tools such as `find`, `rg`, `sed`, and file reads.
- `git` for Core protected-main state and diff checks.
- The `mirror-skills` workflow for local mirror refresh after approved changes.
- Skill validation helpers such as `skill-creator` when available.
- GitHub only when the user explicitly asks to create tracking issues.

Safety:

- Treat every local skill as potentially private until inspected.
- Do not import, overwrite, archive, delete, permanently delete, prune, sync, or create issues until the user approves the relevant action.
- Do not overwrite existing Core or Personal Overlay canonical skill directories automatically.
- Default `delete-local` behavior archives or moves the local skill; permanent deletion requires explicit permanent-deletion wording.
- Back up a local mirror skill before any local mirror change.
- Back up an existing Personal Overlay skill before overwriting it.
- Use timestamped backup directories that include time of day, such as `<mirror-root>/.archive/YYYY-MM-DD-HHMMSS/<skill-name>/` for local mirrors and `personal/os/skills/.archive/YYYY-MM-DD-HHMMSS/<skill-name>/` for Personal Overlay skills.
- Do not clean up, delete, or prune local mirror or Personal Overlay backups until the user explicitly confirms the applied actions were intended and approves backup cleanup.
- Follow the protected-main workflow for Core changes.
- Do not record machine-local mirror paths or mirror state in `os/skills/MANIFEST.md`.
- Do not record provenance unless it changes future maintenance behavior.
- Do not import externally sourced skills into AgentOS Core or the Personal Overlay unless the user explicitly asks to vendor or fork that upstream skill and approves provenance/license review.

Filing Rules:

- Core imports live under `os/skills/<skill-name>/` and must be listed in `os/skills/MANIFEST.md`.
- Personal Overlay imports live under `personal/os/skills/<skill-name>/` and must not be listed in the Core manifest.
- Recommendation reports stay in chat unless the user asks for a durable artifact.
- Follow-up issue creation is recommended in the report when useful, but issue writes happen only after explicit user approval.
- Local mirrors remain install artifacts, not canonical source of truth.

## Workflow Phases

1. Inspect policy and roots:
   - Read the Core skills manifest, skill contract, skills README, Personal Overlay playbook, and `mirror-skills`.
   - Confirm whether the current checkout is a feature worktree. If Personal Overlay writes are possible, resolve the canonical primary checkout's `personal/os/skills/` unless the user assigns a different private overlay workspace.
   - Confirm the local skill mirror root. Use the current-machine default unless the user provides another root.

2. Inventory all local skills:
   - List direct child skill directories under the local mirror root that contain `SKILL.md`.
   - Exclude dot/control directories such as `.archive` and any backup/archive roots from live-skill discovery.
   - For each skill, inspect the directory name, `SKILL.md`, any files under `agents/`, and filenames under `scripts/`, `references/`, and `assets/`.
   - Look for third-party origin signals before judging AgentOS ownership: package manager metadata, upstream source URLs, author or license fields, README/install text, generated package markers, external repository names, or content that describes an ecosystem package rather than a user-authored workflow.
   - Use targeted `rg` searches for obvious private, local-path, account, live-agent, generated-output, or credential markers when Core promotion is plausible.
   - Deep-read bundled scripts, references, or assets when a skill is a likely Core candidate, high risk, duplicate, stale, or approved for import.

3. Classify canonicality:
   - `canonical-core`: listed in `os/skills/MANIFEST.md`.
   - `canonical-personal-overlay`: `personal/os/skills/<skill-name>/SKILL.md` exists.
   - `external-origin-local`: credible evidence indicates the skill was downloaded from, generated by, or copied from an external upstream that the user does not own.
   - `local-only`: neither canonical source exists.
   - Do not treat local mirror state as canonical.
   - If external origin is ambiguous, report the evidence and classify the skill as `local-only-needs-owner-check` instead of recommending import.

4. Recommend dispositions:
   - Produce a full table in one pass.
   - Exclude `external-origin-local` skills from reverse-mirror import candidacy by default. List them in an `excluded external-origin` section with recommendation `exclude-external-origin`.
   - Use these recommendations for owned or ambiguous local skills: `delete-local`, `replace-with-existing-agentos-skill`, `promote-to-personal-overlay`, `promote-to-core`, and `leave-local`.
   - Order rows by priority: excluded external-origin skills, local deletion candidates, replacement/refresh candidates, Personal Overlay candidates, Core candidates, then leave-local entries.
   - Include columns: `skill`, `status`, `recommendation`, `reason`, `risk`, `follow-up`, and `next action`.
   - Use follow-up values such as `none`, `owner-check`, `upstream-update`, `vendor-fork-review`, `core-sanitization-issue`, `manifest-design-blocked`, and `manual-review-issue`.

5. Normalize approval:
   - Bulk approval is allowed.
   - Convert the user's approval into an explicit action plan before mutating files.
   - For each action, name the skill, action, destination if importing, source path, target or archive path, whether Core manifest changes, backup paths, whether `mirror-skills` will run afterward, and which AgentOS root `mirror-skills` should use.
   - For Personal Overlay imports, use the primary checkout's AgentOS root for the follow-up `mirror-skills` run, or pass that root explicitly through the `mirror-skills` workflow, so feature-worktree skeleton overlays are not treated as authoritative.
   - If approval is vague or the action plan is ambiguous, pause and confirm.

6. Apply approved actions:
   - Use ordinary file operations. Do not rely on a bundled reverse mirror script.
   - For Core imports, work in an isolated feature branch or worktree and update `os/skills/<skill-name>/` plus `os/skills/MANIFEST.md`.
   - For Personal Overlay imports, write to the canonical primary checkout's `personal/os/skills/<skill-name>/`, backing up any existing target before overwrite to `personal/os/skills/.archive/YYYY-MM-DD-HHMMSS/<skill-name>/`.
   - For `delete-local`, archive by default to `<mirror-root>/.archive/YYYY-MM-DD-HHMMSS/<skill-name>/`.
   - Before any local mirror change, back up the affected local skill to a timestamped archive path under the mirror root.
   - After applying approved actions, keep all backup/archive directories until the user confirms the results and approves cleanup.
   - Preserve existing harness metadata files under `agents/`; generate or refresh active-harness metadata when local conventions call for it.

7. Normalize imported skills:
   - Ensure folder name matches skill name.
   - Ensure `SKILL.md` frontmatter has `name` and a clear trigger-oriented `description`.
   - Ensure contract fields are present: inputs, output artifact, mutability, tools/connectors, safety, phases, quality bar, verification, and filing rules.
   - Remove or relocate private/local-only facts before Core import.
   - Avoid broad prose rewrites, speculative abstractions, or changes to workflow intent.

8. Verify and mirror:
   - Run skill validation when available for imported or changed skill directories.
   - Run `scripts/run-validator` after Core changes.
   - Run the `mirror-skills` workflow scoped to the imported or changed skill names after approval.
   - For Personal Overlay imports made from a feature worktree, run `mirror-skills` from the primary checkout or with the primary checkout as the AgentOS root.
   - Report validation status, mirror status, and backup paths.

## Recommendation Rules

Recommend `promote-to-core` only when the skill is reusable for a stranger and contains no user-specific identity, account, project, path, preference, history, live-agent state, generated output, queue, report, or private example assumptions.

Recommend `promote-to-personal-overlay` when the skill depends on private identity, account state, local paths, personal projects, live agents, automations, preferences, or user-specific defaults.

Recommend `replace-with-existing-agentos-skill` when a local skill is a stale, drifted, or equivalent copy of an existing canonical skill and should be refreshed from AgentOS rather than imported.

Recommend `delete-local` when a local skill is clearly obsolete, duplicated, superseded, broken, or stale. Archive by default.

Recommend `exclude-external-origin` when a local skill appears to come from an external upstream that the user does not own. Do not promote, normalize, or delete it as part of reverse mirroring. If it is stale, recommend updating or removing it through the original install mechanism. If the user wants AgentOS to own it, require an explicit vendor/fork decision, provenance and license review, and a tracking issue before import.

Recommend `leave-local` when a local skill is experimental, harness-specific, not worth canonicalizing, or lacks enough signal for a durable AgentOS home.

If a skill seems private but could become broadly reusable after sanitization, recommend `promote-to-personal-overlay` now and use the `follow-up` column to suggest a Core-sanitization tracking issue.

## Collision Rules

- If a local skill is equivalent to canonical behavior, recommend `leave-local` or `replace-with-existing-agentos-skill` depending on mirror state.
- If it is an older version of a canonical skill, recommend `delete-local`, archive, or refresh through `mirror-skills`.
- If a local skill is equivalent to an external upstream package, recommend `exclude-external-origin` and upstream update/removal rather than AgentOS import.
- If it has intentional local differences, recommend a new canonical skill name or moving private configuration into `personal/os/skills/<core-skill>/CONFIG.md`.
- Never overwrite canonical Core or Personal Overlay skill directories unless the user explicitly approves replacing that named canonical skill and backups/diff safeguards are in place.

## Quality Bar

- The report covers all local skills in one prioritized table.
- Externally sourced skills are detected, separated from owned local skills, and excluded from import recommendations unless the user explicitly asks to vendor or fork them.
- Recommendations are evidence-backed and separate Core-safe reusable behavior from private or local-only state.
- Bulk approvals become an explicit action plan before mutation.
- Core imports are contract-complete, manifest-listed, portable, and privacy-reviewed.
- Personal Overlay imports keep private behavior out of Core and out of the Core manifest.
- Local mirrors are refreshed only through `mirror-skills` after canonical changes.
- Timestamped backups are created before local mirror changes and Personal Overlay overwrites.
- Backup cleanup happens only after explicit user confirmation.

## Verification

Before finishing:

1. Confirm no bundled `reverse-mirror-skills` script was added.
2. Run skill validation for `reverse-mirror-skills` when available.
3. Run `scripts/run-validator` after Core changes.
4. Run `mirror-skills` scoped to `reverse-mirror-skills`.
5. Run a scoped `mirror-skills` regression check on at least one existing Core skill.
6. Confirm `os/skills/MANIFEST.md` includes `reverse-mirror-skills` and no machine-local mirror state.
7. Confirm no Personal Overlay import, local archive/delete, GitHub issue write, or permanent deletion happened without explicit approval.
8. Confirm any local mirror or Personal Overlay backup cleanup was separately approved, or report remaining backup paths.
9. Confirm externally sourced local skills were excluded from import recommendations, or record the user's explicit vendor/fork approval.
