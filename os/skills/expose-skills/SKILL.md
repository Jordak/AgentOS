---
name: expose-skills
description: Expose AgentOS Core skills to the global harness skill root with symlink adapters. Use when checking, planning, or applying discoverable skill exposure for AgentOS skills, especially replacing copy-based mirror thinking with adapter links.
---

# Expose Skills

## Goal

Expose canonical AgentOS Core skills to the current machine's global harness skill root with per-skill symlink adapters.

This skill is not a copy mirror workflow. Canonical skill behavior stays under `os/skills/`; exposed entries under `~/.agents/skills` are current-machine adapters.

## Contract

Inputs:

- AgentOS root, defaulting to the current workspace.
- `os/skills/MANIFEST.md` as the Core skill list.
- Current-machine global skill root: `~/.agents/skills`.
- Optional repeated `--skill <name>` filter.
- Optional apply flag: `--no-dry-run`.

Output artifact:

- Dry-run or apply report listing adapter status for Core skills.
- Optional symlink adapters under `~/.agents/skills` when `--no-dry-run` is used.

Mutability:

- Read-only by default.
- Current-machine local-write only with `--no-dry-run`.

Tools and connectors:

- Local filesystem and bundled script `scripts/expose_skills.py`.
- No external connectors or network access.

Safety:

- Ask before applying writes to `~/.agents/skills` unless the user explicitly requested `--no-dry-run` or equivalent apply behavior.
- Do not expose Personal Overlay skills in v1.
- Do not copy skills, create Windows junctions, delete global skill dirs, replace copied mirrors, or overwrite wrong-target symlinks.
- If symlink creation is blocked by OS, filesystem, sandbox, or permission policy, stop and report the fix.
- Do not record global adapter status in `os/skills/MANIFEST.md`.

## Workflow Phases

1. Confirm scope:
   - Default: all Core manifest skills.
   - Use `--skill <name>` for named subsets.
   - Personal Overlay is doc-only in v1 and not scanned by the script.
   - Target is always global `~/.agents/skills`.

2. Run dry run:
   - Use `python3 os/skills/expose-skills/scripts/expose_skills.py`.
   - Report missing adapters, already-linked adapters, wrong-target symlinks, existing copied mirrors, blocked paths, missing sources, and extras.

3. Apply only when approved:
   - Use `python3 os/skills/expose-skills/scripts/expose_skills.py --no-dry-run`.
   - Use repeated `--skill <name>` with apply only when the user approved that subset.
   - Missing entries become directory symlinks to canonical Core skill directories.
   - Existing copied mirrors and wrong-target symlinks are reported, not changed.

4. Verify:
   - Re-run dry run after applying.
   - Expected successful exposure state is `already-linked`.
   - Run `scripts/run-validator` only when Core skill, script, manifest, or docs changed.

## Script Examples

Dry run all Core skills:

```bash
python3 os/skills/expose-skills/scripts/expose_skills.py
```

Dry run one Core skill:

```bash
python3 os/skills/expose-skills/scripts/expose_skills.py --skill research-brief
```

Apply all missing Core skill adapters:

```bash
python3 os/skills/expose-skills/scripts/expose_skills.py --no-dry-run
```

Apply one missing Core skill adapter:

```bash
python3 os/skills/expose-skills/scripts/expose_skills.py --skill research-brief --no-dry-run
```

## Personal Overlay V1

Private skills may live under `personal/os/skills/<skill-name>/SKILL.md`, but v1 does not discover, scan, or expose them. Future Personal Overlay exposure must be explicit because private skill names and content can leak into global harness context.

## Quality Bar

- Dry run is the default and shows planned global adapter changes before writes.
- Apply mode creates only missing symlink adapters for Core manifest skills.
- Existing copied mirrors, wrong-target symlinks, blocked paths, and extras are visible in the report and are not modified.
- Unknown skills fail with the available Core skill list.
- Permission-style symlink failures stop with OS-appropriate remediation and no fallback.
- Personal Overlay skills are documented but not scanned or exposed in v1.

## Filing Rules

- Keep this skill under `os/skills/expose-skills/`.
- Keep canonical skill behavior in each source skill directory under `os/skills/`.
- Keep global adapter state out of `os/skills/MANIFEST.md` and other portable Core metadata.
- Keep dry-run and apply reports in chat by default unless the user asks for a local report.
- Track Mirror Skills retirement separately after `expose-skills` validates through one migration cycle.

## Mirror Skills Retirement

`mirror-skills` is the legacy copy-mirror workflow. Build and validate `expose-skills` first, then delete `mirror-skills` in a follow-up PR after one successful migration and validation cycle.

## Verification

Before finishing changes to this skill:

1. Run default dry run with a temporary `HOME`.
2. Run `--no-dry-run` with a temporary `HOME` and confirm symlinks are created.
3. Run scoped dry run and apply with repeated `--skill` where possible.
4. Confirm existing copied mirrors are reported but not changed.
5. Confirm wrong-target symlinks are reported but not changed.
6. Confirm unknown skills fail clearly.
7. Confirm permission-style symlink failures fail with remediation.
8. Run `scripts/run-validator`.
