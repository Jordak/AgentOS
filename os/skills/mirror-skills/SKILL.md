---
name: mirror-skills
description: Audit and sync current-machine discoverable mirrors for canonical AgentOS skills without storing machine-local mirror state in the portable manifest. Use when the user asks to mirror skills, check skill mirrors, install missing .agents skill mirrors, sync AgentOS skills to the current machine, or verify that Core or Personal Overlay skills are discoverable locally.
---

# Mirror Skills

## Goal

Keep AgentOS skill sources portable while making the current machine usable. The Core manifest lists public canonical skills, and the Personal Overlay may contain private canonical skills under `personal/os/skills/<skill-name>/SKILL.md`. This skill checks whether the current machine has discoverable mirrors, usually under the user's `.agents/skills` directory, and can sync missing or stale mirrors from those canonical sources.

## Contract

Inputs:

- AgentOS root, defaulting to the current workspace for Core-only audits. When including Personal Overlay skills from a feature worktree, run from the canonical primary AgentOS checkout or pass `--agentos-root <primary AgentOS checkout>` so the feature worktree's ignored-file skeleton is not treated as authoritative.
- `os/skills/MANIFEST.md` with canonical skill entries and `Canonical source` fields.
- Personal Overlay skill directories under `personal/os/skills/<skill-name>/SKILL.md`, when present.
- A current-machine mirror root, defaulting to the user's `.agents/skills` directory.
- Optional private config at `personal/os/skills/mirror-skills/CONFIG.md` for current-machine mirror roots or validator paths.
- Optional skill filter: one or more canonical skill names to audit or sync.
- Optional mode: audit-only by default, or sync when the user asks to create/update mirrors.

Output artifact:

- A concise mirror audit report listing in-sync, missing, stale, extra-file, and source-missing skills.
- Optional local mirror directories/files under the chosen mirror root.

Mutability:

- Read-only in audit mode.
- Local-write in sync mode; writes to the current machine's configured mirror root.

Tools and connectors:

- Local filesystem and bundled script `scripts/mirror_skills.py`.
- No external connectors or network access.

Safety:

- Do not record machine-local mirror paths or mirror state in `os/skills/MANIFEST.md`.
- Ask before writing outside the workspace unless the active harness has already approved that mirror root.
- Default to audit-only. Show the user exactly which mirrors would be created, updated, or left with extra files before syncing.
- Do not delete extra mirror files by default. Use destructive pruning only if the user explicitly asks and the script option makes the deletion visible.

## Workflow Phases

1. Inspect policy:
   - Read `os/skills/MANIFEST.md`, `os/skills/README.md`, `os/skills/SKILL_CONTRACT.md`, and `os/playbook/PERSONAL_OVERLAY.md`.
   - Confirm the manifest remains portable and contains canonical skill metadata only.
   - Check for Personal Overlay skills under `personal/os/skills/<skill-name>/SKILL.md`. These are private canonical sources for the current user and should be mirrored alongside Core skills when present.
   - If running from a feature worktree and the audit includes Personal Overlay skills, resolve the canonical primary checkout's `personal/os/skills/` by running this skill from that checkout or by passing `--agentos-root <primary AgentOS checkout>`. Use the current feature worktree root only for Core-only audits, or when the user explicitly assigned that worktree as the private overlay workspace.

2. Run an audit:
   - Use `python3 os/skills/mirror-skills/scripts/mirror_skills.py`.
   - From a feature worktree, pass `--agentos-root <primary AgentOS checkout>` unless using `--core-only`.
   - Pass `--mirror-root <path>` if checking somewhere other than the default current-machine mirror root.
   - Pass repeated `--skill <name>` arguments to check only a named subset of canonical skills.
   - Report missing, stale, and extra-file mirrors before syncing.

3. Sync when requested:
   - Use the same script with `--sync` to create missing mirrors and copy changed canonical files.
   - Use `--skill <name>` with `--sync` when the user only approved syncing specific canonical skills.
   - Ask for confirmation before syncing unless the user has already explicitly approved the exact mirror root and write scope in the current thread.
   - Use `--prune-extra` only after explicit approval, because it deletes mirror files that are not present in the canonical skill source.
   - Re-run audit after sync.

4. Preserve source-of-truth boundaries:
   - Edit canonical skills in `os/skills/` first.
   - Treat mirrors as install artifacts for the current machine.
   - If a mirror intentionally differs from canonical behavior, prefer creating a thin adapter skill with its own canonical source instead of hiding drift in a machine-local copy.

## Script Examples

Audit the default current-machine mirror root:

```bash
python3 os/skills/mirror-skills/scripts/mirror_skills.py
```

Create or update mirrors under the default current-machine mirror root:

```bash
python3 os/skills/mirror-skills/scripts/mirror_skills.py --sync
```

Audit or sync only a named canonical skill:

```bash
python3 os/skills/mirror-skills/scripts/mirror_skills.py --skill mirror-skills
python3 os/skills/mirror-skills/scripts/mirror_skills.py --skill mirror-skills --sync
```

Audit Personal Overlay skills from a feature worktree by pointing at the primary AgentOS checkout:

```bash
python3 os/skills/mirror-skills/scripts/mirror_skills.py --agentos-root <primary-agentos-root>
```

Test against a temporary mirror root:

```bash
python3 os/skills/mirror-skills/scripts/mirror_skills.py --mirror-root <mirror-root> --sync
```

## Quality Bar

- The audit derives canonical skills from the manifest, Personal Overlay skill paths, and canonical source paths, not from machine-local mirror records.
- The audit includes both Core manifest skills and Personal Overlay skills, unless `--core-only` is used.
- Skill filters only select from canonical skills discovered in the selected scope and fail clearly when a requested skill is unknown or directly collides between Core and the Personal Overlay.
- Scoped skill filters should not fail because of unrelated Personal Overlay collisions outside the requested skill names.
- Personal Overlay skill names must not collide with Core skill names; use `personal/os/skills/<core-skill>/CONFIG.md` for private inputs to a Core skill.
- Sync mode copies all required canonical skill files for directory-backed skills, including `os/agents/`, `scripts/`, `assets/`, and `references/` when present.
- The report clearly separates missing/stale mirrors from extra mirror files.
- No external account or network state is touched.

## Filing Rules

- Keep this skill and its script under `os/skills/mirror-skills/`.
- Keep mirror audit results in chat by default.
- Do not add current-machine mirror paths or mirror state to `os/skills/MANIFEST.md`; rerun the script on each machine instead.

## Verification

Before finishing:

1. Run the script in audit mode.
2. Run a sync smoke test against a temporary mirror root.
3. Run scoped audit and sync smoke tests with `--skill <name>`, including repeated `--skill` arguments when more than one canonical skill is available.
4. Run an unknown-skill failure check and confirm it fails clearly.
5. Run any private validator path named in `personal/os/skills/mirror-skills/CONFIG.md` when available.
6. Run `scripts/run-validator`.
7. Confirm no machine-local mirror state was added to the manifest.
