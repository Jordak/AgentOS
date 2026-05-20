---
name: audit-skill-mirrors
description: Audit and sync current-machine discoverable mirrors for canonical AgentOS skills without storing machine-local mirror state in the portable manifest. Use when the user asks to check skill mirrors, install missing .agents skill mirrors, sync AgentOS skills to the current machine, or verify that manifest-listed skills are discoverable locally.
---

# Audit Skill Mirrors

## Goal

Keep AgentOS skill sources portable while making the current machine usable. The manifest lists canonical skills; this skill checks whether the current machine has discoverable mirrors, usually under the user's `.agents/skills` directory, and can sync missing or stale mirrors from the canonical sources.

## Contract

Inputs:

- AgentOS root, defaulting to the current workspace.
- `os/skills/MANIFEST.md` with canonical skill entries and `Canonical source` fields.
- A current-machine mirror root, defaulting to the user's `.agents/skills` directory.
- Optional private config at `personal/os/skills/audit-skill-mirrors/CONFIG.md` for current-machine mirror roots or validator paths.
- Optional mode: audit-only by default, or sync when the user asks to create/update mirrors.

Output artifact:

- A concise mirror audit report listing in-sync, missing, stale, extra-file, and source-missing skills.
- Optional local mirror directories/files under the chosen mirror root.

Mutability:

- Read-only in audit mode.
- Local-write in sync mode; writes to the current machine's configured mirror root.

Tools and connectors:

- Local filesystem and bundled script `scripts/audit_skill_mirrors.py`.
- No external connectors or network access.

Safety:

- Do not record machine-local mirror paths or mirror state in `os/skills/MANIFEST.md`.
- Ask before writing outside the workspace unless the active harness has already approved that mirror root.
- Do not delete extra mirror files by default. Use destructive pruning only if the user explicitly asks and the script option makes the deletion visible.

## Workflow Phases

1. Inspect policy:
   - Read `os/skills/MANIFEST.md`, `os/skills/README.md`, and `os/skills/SKILL_CONTRACT.md`.
   - Confirm the manifest remains portable and contains canonical skill metadata only.

2. Run an audit:
   - Use `python3 os/skills/audit-skill-mirrors/scripts/audit_skill_mirrors.py`.
   - Pass `--mirror-root <path>` if checking somewhere other than the default current-machine mirror root.
   - Report missing, stale, and extra-file mirrors before syncing unless the user already asked to sync.

3. Sync when requested:
   - Use the same script with `--sync` to create missing mirrors and copy changed canonical files.
   - Use `--prune-extra` only after explicit approval, because it deletes mirror files that are not present in the canonical skill source.
   - Re-run audit after sync.

4. Preserve source-of-truth boundaries:
   - Edit canonical skills in `os/skills/` first.
   - Treat mirrors as install artifacts for the current machine.
   - If a mirror intentionally differs from canonical behavior, prefer creating a thin adapter skill with its own canonical source instead of hiding drift in a machine-local copy.

## Script Examples

Audit the default current-machine mirror root:

```bash
python3 os/skills/audit-skill-mirrors/scripts/audit_skill_mirrors.py
```

Create or update mirrors under the default current-machine mirror root:

```bash
python3 os/skills/audit-skill-mirrors/scripts/audit_skill_mirrors.py --sync
```

Test against a temporary mirror root:

```bash
python3 os/skills/audit-skill-mirrors/scripts/audit_skill_mirrors.py --mirror-root <mirror-root> --sync
```

## Quality Bar

- The audit derives canonical skills from the manifest and canonical source paths, not from machine-local mirror records.
- Sync mode copies all required canonical skill files for directory-backed skills, including `os/agents/`, `scripts/`, `assets/`, and `references/` when present.
- The report clearly separates missing/stale mirrors from extra mirror files.
- No external account or network state is touched.

## Filing Rules

- Keep this skill and its script under `os/skills/audit-skill-mirrors/`.
- Keep mirror audit results in chat by default.
- Do not add current-machine mirror paths or mirror state to `os/skills/MANIFEST.md`; rerun the script on each machine instead.

## Verification

Before finishing:

1. Run the script in audit mode.
2. Run a sync smoke test against a temporary mirror root.
3. Run any private validator path named in `personal/os/skills/audit-skill-mirrors/CONFIG.md` when available.
4. Run `python3 os/verification/scripts/validate_agentos.py`.
5. Confirm no machine-local mirror state was added to the manifest.
