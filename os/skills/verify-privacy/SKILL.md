---
name: verify-privacy
description: Audit a repository, project directory, publishable file set, or release candidate for private, personal, secret, machine-local, or otherwise nonpublishable content. Use when preparing AgentOS or another repo for publication, reviewing Core/Personal Overlay separation, checking whether private facts leaked into publishable files, validating privacy markers, or producing a privacy findings report before commit or release.
---

# Verify Privacy

## Purpose

Use this skill to perform a human-in-the-loop privacy audit of publishable files. Do not treat Gitleaks or deterministic validators as enough by themselves; they catch credentials and configured markers, while this skill also looks for semantic personal leakage.

## Contract

Inputs: repository root, project directory, publishable file set, or release-candidate path; optional scope; and optional private marker list.

Output artifact: concise privacy audit report with verdict, commands run, reviewed scope, findings, warnings, marker recommendations, and exact next fixes.

Mutability: read-only by default; local-write only when the user asks to add markers, fix leaks, update docs, or save a report.

Tools and connectors: local filesystem reads, `git`, `rg`, AgentOS validators, Gitleaks, and optionally TruffleHog. No connector data unless the user explicitly asks and approves the privacy risk.

Safety: never delete, publish, change repository visibility, alter external GitHub state, or expose private marker contents without explicit approval.

Verification: run the precheck and scanner checks when available, then do a semantic crawl of high-risk Core areas before reporting.

## Inputs

- Repository root, project directory, publishable file set, or release-candidate path. Default to the current working directory.
- Optional scope: working tree, staged diff, tracked file set, release candidate, or specific directories.
- Optional private marker list. For AgentOS, default to `personal/os/verification/privacy-markers.txt` when present.

## Output Artifact

Return a concise privacy audit report with:

- verdict: `pass`, `pass-with-warnings`, or `block`;
- commands run;
- files or path classes reviewed;
- blocker findings with file paths and line numbers when possible;
- warnings and marker-list recommendations;
- exact next fixes.

Do not save a report unless the user asks. If saving a report, follow the file conventions below.

## Mutability

Default to read-only. Local writes are allowed only when the user asks to add markers, fix leaks, update docs, or save a report. Never delete, publish, change repository visibility, or alter external GitHub state without explicit approval.

## Tools

Use local filesystem reads, `git`, `rg`, AgentOS validators, Gitleaks, and optionally TruffleHog. Do not use connector data unless the user explicitly asks and approves the privacy risk.

## Workflow Phases

1. Establish scope.
   - Identify the repository root or directory under review.
   - For AgentOS, read `DOMAIN.md`, `os/playbook/PERSONAL_OVERLAY.md`, and `os/playbook/PUBLICATION.md` when present.
   - Decide whether the audit target is the mixed working tree, Git's publishable file set, staged diff, or a generated release candidate.
   - If AgentOS publication or commit safety is in scope, treat the staged snapshot as the main gate and the generated candidate as an optional final dry run.

2. Run deterministic gates.
   - For AgentOS, run `scripts/run-validator --publication-precheck` for advisory working-tree migration checks.
   - Run the repo's staged snapshot privacy scan when publication or commit safety is in scope, such as `scripts/check_staged_publication_secrets.sh`.
   - Run the repo's working-tree secret scan only as an advisory mixed-working-tree sweep, such as `scripts/check_working_tree_secrets.sh`.
   - If auditing an AgentOS candidate, run `scripts/check_public_export_secrets.sh` or validate the candidate directly.
   - Record warnings separately from blockers. Unstaged deletion warnings are blockers only when the user is about to publish or commit the publication state.

3. Build the review set.
   - Prefer `git ls-files` for a repo's publishable tracked set.
   - Include untracked but unignored files because they could be accidentally added.
   - Include path names as well as file contents; private directory names can leak.
   - Exclude ignored private overlays or local-only data directories, except to verify they are actually ignored.

4. Crawl for semantic privacy leaks.
   Look for content that is not necessarily a secret but should not be in publishable files:
   - real personal names, handles, emails, calendar IDs, account IDs, private repository names, private project names, workplace/client names, resume facts, biographical facts, or current routines;
   - absolute local paths, machine-specific tool paths, connector locations, private checkout paths, and account-specific URLs;
   - live agent instances, generated reports, dated briefs, real memory, live automations, or private verification outputs;
   - examples that appear sanitized but still encode real private facts;
   - private-specific directory names under tracked skeleton or placeholder paths.

5. Use privacy markers, then improve them.
   - Load the project's marker file when present. For AgentOS, use `personal/os/verification/privacy-markers.txt`.
   - Search flexible variants: spaces, hyphens, underscores, case changes, and common slug forms.
   - When a new private-looking term is found, recommend adding it to the marker file unless it is intentionally public-safe.
   - Keep marker files in private/local state, not in publishable Core or public source.

6. Inspect representative high-risk files.
   - For AgentOS, review root docs, `DOMAIN.md`, `AGENTS.md`, `README.md`, `docs/adr/`, `os/RESOLVER.md`, `os/INDEX.md`, `os/playbook/`, `os/context/`, `os/identity/`, `os/memory/`, `os/connections/`, `os/automations/`, `os/agents/`, `os/skills/`, `os/verification/`, and `scripts/`.
   - For other repositories, review root docs, configuration, examples, generated outputs, fixtures, tests, scripts, and any publishable docs or templates.
   - For large trees, combine broad `rg` searches with targeted reads of high-risk files and changed files from `git diff --name-only`.

7. Classify findings.
   - Blocker: tracked/unignored private content, secrets, private generated output in publishable areas, non-skeleton private files under a tracked private overlay, or anything that would make the public repo unsafe.
   - Warning: ambiguous personal-looking text, missing marker coverage, or stale docs that imply candidate-only publication.
   - Pass: no blockers after deterministic checks and semantic review.

## Quality Bar

- Do not equate "no Gitleaks findings" with privacy-safe.
- Check both path names and file contents.
- Separate deterministic evidence from judgment calls.
- Prefer exact file/line evidence over vague concern.
- Explain why each blocker belongs in Core, Personal Overlay, or neither.
- Leave the user with a short, actionable fix list.

## File Conventions

- Default output stays in chat.
- Saved privacy reports live under `personal/os/verification/privacy/` because findings can reveal private state.
- For AgentOS, saved privacy reports live under `personal/os/verification/privacy/` because findings can reveal private state.
- Proposed durable marker additions go in a private marker file; for AgentOS, use `personal/os/verification/privacy-markers.txt`.
- Public-safe validator or skill improvements live in the project only when they do not include private examples.

## Verification

Before finishing:

1. Confirm the publication precheck result.
2. Confirm the staged snapshot privacy scan result when publication or commit safety is in scope, or say why it was unavailable.
3. Confirm any advisory working-tree Gitleaks result separately from the staged gate.
4. Confirm whether ignored private overlay files were excluded from review and whether ignore coverage was checked.
5. Confirm at least one semantic crawl was performed over high-risk Core areas.
6. Confirm any proposed durable marker additions or file moves are listed separately from findings.
