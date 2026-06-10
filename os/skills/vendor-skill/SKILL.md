---
name: vendor-skill
description: Vendor a public GitHub skill into AgentOS Core with source-first provenance, license-first safety, honest manifest metadata, and validation. Use when importing, refreshing, or correcting a reusable Core skill from an upstream repository.
---

# Vendor Skill

## Trigger

Use this when the user wants to vendor, import, refresh, or correct a reusable skill under `os/skills/` from an upstream source.

Do not use this for private-to-Core promotion. If the candidate starts from a Personal Overlay skill or private skill config, use `promote-private-skill-to-core` first.

## Goal

Create or update an AgentOS Core skill from a real upstream source without guessing provenance, losing license obligations, over-wrapping upstream behavior, or changing validators to accommodate bad metadata.

The v1 workflow is intentionally conservative: supported upstreams are public GitHub repositories with machine-checkable paths and full commit SHAs. Private repositories, non-GitHub sources, current-machine installed/global adapters, missing licenses, ambiguous licenses, and non-machine-checkable refs are blockers or follow-up work unless a later issue expands this skill's contract.

## Contract

Inputs:

- Upstream public GitHub repository or URL.
- Path within the upstream repository.
- Target AgentOS skill name and target `os/skills/<skill-name>/` path.
- Intended vendored ref, or permission to discover the latest path-touching commit.
- List of upstream files to vendor, or permission to discover the skill directory contents.
- Mirror-vs-patch intent: exact upstream mirror by default, explicit local patches only when the user approves them.
- License location or expected license terms when known.
- `os/skills/SKILL_CONTRACT.md`, `os/skills/MANIFEST.md`, `os/skills/check-vendored-skill-upstreams/SKILL.md`, and `os/skills/expose-skills/SKILL.md`.

Output artifact:

- A Core skill directory under `os/skills/<skill-name>/`.
- `os/skills/<skill-name>/UPSTREAM.md` with source, path, vendored ref, vendored files, local patches, update procedure, and license notice.
- An `os/skills/MANIFEST.md` entry with honest contract metadata.
- Optional source-routing fixture when the new skill should be discoverable by stable prompt evidence.
- A concise report naming provenance, license status, local patches, validation, and any blocked source or license decisions.

Mutability:

- Mixed.
- Read-only while auditing source, license, provenance, and existing Core state.
- Local-write when the user asks to vendor or update a Core skill.
- External-write only under the shared GitHub/external-write policy for issue body edits, labels, PRs, comments, pushes, or other tracker/repository state.

Tools and connectors:

- Local filesystem, `rg`, `git`, `curl` or `gh` for public GitHub source reads, upstream raw file comparisons, AgentOS validators, `check-vendored-skill-upstreams`, `expose-skills` dry run, and GitHub issue/PR tooling when the work is issue-driven.

Safety:

- Start with source confirmation. Do not proceed from a current-machine installed/global adapter when a real upstream repository exists or can be requested.
- Support public GitHub upstreams only in v1. Stop for human review on private repos, non-GitHub sources, missing sources, or non-machine-checkable refs.
- Require a clear license before vendoring. Stop for human review when the license is missing, unclear, incompatible, private, or imposes obligations the workflow cannot confidently satisfy.
- Include the required license notice in `UPSTREAM.md` or another approved vendored provenance file.
- Do not broaden validators, freshness checkers, or source-routing checks to make incorrect provenance pass. Fix the provenance first.
- Do not patch upstream skill files unless local AgentOS patches are explicitly intended and documented.
- Do not copy private examples, Personal Overlay state, current-machine adapter paths, account details, local paths, or generated reports into Core.
- Ask before external writes, current-machine skill exposure changes, or destructive edits.

## Workflow Phases

1. Confirm scope and source.
   - Ask for or confirm the full initial vendoring bundle before resolving or writing files:
     upstream public GitHub repository or source URL, path within the upstream repository,
     intended full commit ref or permission to discover the latest path-touching commit,
     target skill name and target `os/skills/<skill-name>/` path, mirror-vs-patch intent,
     and known license location or expected license terms.
   - Confirm the source is a public GitHub repository and the path is inside that repository.
   - Confirm whether the user wants an exact upstream mirror or explicit local AgentOS patches.
   - If only a current-machine installed/global adapter is known, stop and ask for the real upstream source.

2. Resolve the vendored ref.
   - Use the caller-provided full commit SHA when supplied.
   - Otherwise discover the latest upstream commit that touched the vendored path.
   - Use full 40-character commit SHAs in `UPSTREAM.md`.
   - Do not use branch names, tags, short SHAs, local run markers, or machine-local adapter names as vendored refs.

3. Inventory upstream files.
   - List the upstream files to vendor.
   - Prefer mirroring the upstream skill directory exactly when the issue calls for an upstream vendored skill.
   - Record every vendored file in `UPSTREAM.md`.
   - Keep generated, private, test-only, or irrelevant upstream files out unless the user explicitly approves them and the license allows redistribution.

4. Run the license gate.
   - Locate the upstream license from the repository root, vendored path, package metadata, or upstream docs.
   - Decide whether the license is clear and usable for AgentOS redistribution.
   - MIT-style permissive licenses can usually proceed when the notice is included.
   - Stop for human review when the license is absent, ambiguous, conflicting, copyleft/reciprocal in a way that needs project policy, proprietary, private, or otherwise uncertain.
   - Copy the required notice into `UPSTREAM.md` or the approved provenance location.

5. Write the Core files.
   - Create or update `os/skills/<skill-name>/`.
   - Mirror upstream files exactly unless an approved local patch is in scope.
   - Add `UPSTREAM.md`.
   - For exact mirrors, keep AgentOS-specific governance in `UPSTREAM.md`, `os/skills/MANIFEST.md`, calling workflow guidance, or a separate approved patch rather than silently editing upstream files.

6. Update the manifest honestly.
   - Add or update an exact ``### `skill-name` `` entry in `os/skills/MANIFEST.md`.
   - Use `partial` for exact upstream mirrors that rely on the manifest for AgentOS contract facts.
   - Use `full` only when the skill source itself clearly carries the Core contract facts.
   - State mutability, tools/connectors, output artifact, filing rule, safety posture, verification coverage, and upgrade notes.
   - Do not record current-machine exposure state or adapter paths in the manifest.

7. Add route or smoke coverage when useful.
   - Add a source-routing fixture when the skill should be discoverable from stable Core evidence.
   - Keep fixtures public-safe and based on stable text in Core files.
   - Avoid brittle fixtures that depend on private examples, external network state, or generated artifacts.

8. Validate.
   - Run `git diff --check`.
   - Run `scripts/run-validator`.
   - Run `python3 os/skills/check-vendored-skill-upstreams/scripts/check_vendored_skill_upstreams.py --self-test` when upstream metadata or related expectations are part of the change.
   - Diff vendored upstream files against raw upstream files at the recorded ref.
   - Run the vendored upstream checker when the upstream is supported and network/auth/rate limits allow it; record rate-limit caveats separately from provenance failures.
   - Run `expose-skills` dry run when current-machine discoverability matters, and apply exposure only after explicit approval.

9. Publish through the repository workflow when requested.
   - Follow `os/playbook/GITHUB_WORKFLOW.md`.
   - Use issue body/readiness evidence for issue-driven work.
   - Avoid accidental close keywords in PR or issue text.
   - Do not close the issue until the resolving PR is merged and integration evidence is verified.

## UPSTREAM.md Format

Use this shape for vendored skills:

```md
# Upstream Provenance

Source: `owner/repo`

Path: `path/within/repo/`

Vendored ref: `full-40-character-commit-sha`

Files vendored:

- `SKILL.md`

Local AgentOS patches:

- Add this provenance file.

Update procedure:

1. Fetch the upstream directory at the new ref.
2. Diff against this vendored copy.
3. Accept upstream changes deliberately.
4. Reapply local AgentOS patches above.
5. Run skill validation, `scripts/run-validator`, and an `expose-skills` dry run when current-machine discoverability matters.

## License

<required upstream license notice>
```

## Filing Rules

- Vendored Core skill files live under `os/skills/<skill-name>/`.
- Vendored source provenance and license notices live in `os/skills/<skill-name>/UPSTREAM.md`.
- Core maintenance metadata lives in `os/skills/MANIFEST.md`.
- Source-routing and smoke fixtures live under `os/verification/source-routing/` only when they add stable public-safe route evidence.
- Current-machine adapter state stays out of Core files and is handled by `expose-skills`.
- External issue, label, PR, and review state stays in GitHub.
- Private source details, private examples, Personal Overlay state, current-machine adapter paths, and generated reports must not be filed in Core.
- Unresolved source, license, or provenance questions belong in the issue tracker or calling workflow as blockers, not in guessed `UPSTREAM.md` metadata.

## Quality Bar

- The real upstream source is public, GitHub-backed, and named.
- The path and full vendored commit ref are recorded.
- The vendored files are listed and match upstream unless local patches are explicitly documented.
- The license was located, judged usable, and included.
- Manifest metadata is honest about whether the skill source is a full AgentOS contract or an upstream mirror plus manifest metadata.
- The workflow did not broaden validators or freshness checks to hide provenance uncertainty.
- The issue or PR body records readiness evidence and validation when this is issue-driven.

## Verification

Before finishing:

1. Confirm the upstream source, path, and full commit SHA.
2. Confirm the license source, compatibility/usability decision, and included notice.
3. Confirm every vendored file is listed in `UPSTREAM.md`.
4. Confirm exact upstream mirrors still diff cleanly against raw upstream at the recorded ref.
5. Confirm local patches are documented and intentionally accepted.
6. Confirm `os/skills/MANIFEST.md` uses the Markdown manifest API and honest contract status.
7. Run `git diff --check`.
8. Run `scripts/run-validator`.
9. Run upstream-checker self-test when relevant.
10. Run upstream freshness check when supported and not blocked by network/auth/rate limits.
11. Run `expose-skills` dry run when current-machine discoverability matters.
12. Confirm no private state, current-machine adapter paths, Personal Overlay files, or unapproved external writes entered Core.
