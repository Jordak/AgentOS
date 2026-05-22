---
name: run-agentos-doctor
description: Run AgentOS setup health checks using the deterministic doctor script plus agent judgment for ambiguous local state. Use when the user asks to run AgentOS Doctor, audit AgentOS setup health, check whether AgentOS is wired up correctly, inspect adapters, skill mirrors, Personal Overlay starter files, or recurring AgentOS update/drift checks.
---

# Run AgentOS Doctor

## Goal

Audit a local AgentOS installation without making changes. Use the deterministic script for facts, then apply agent judgment to ambiguous setup notes and ask the user before any remediation.

## Contract

Inputs:

- An AgentOS checkout, defaulting to the current workspace.
- Optional primary AgentOS checkout when running from a feature worktree.
- Optional adapter flags used by the installer, such as `--all-default-adapters` or repeated `--adapter <path>`.
- Optional current-machine mirror root.

Output artifact:

- A concise setup health report with PASS/WARN/FAIL style findings, interpreted risks, and next steps.
- No durable artifact by default.

Mutability:

- Read-only by default.
- Ask before installing adapters, syncing mirrors, editing Personal Overlay files, changing automations, or writing outside the checkout.

Tools and connectors:

- Local filesystem.
- `scripts/agentos_doctor.py`.
- `scripts/install_global_agent_instructions.py`.
- `os/skills/mirror-skills/scripts/mirror_skills.py`.
- `os/playbook/GETTING_STARTED.md`.
- Relevant Personal Overlay automation notes when present.

Safety:

- Do not expose private file contents.
- Do not treat ambiguous automation prose as active recurring evidence.
- Ask before adapter writes, mirror syncs, Personal Overlay file creation, automation changes, or current-machine setup changes.

## Workflow Phases

1. Load setup context.
   Read `AGENTS.md`, `os/INDEX.md`, `os/playbook/PERSONAL_OVERLAY.md`, and `os/playbook/GETTING_STARTED.md`. If you need current-machine setup boundaries, also read `os/RESOLVER.md`.

2. Choose roots.
   Use the current checkout as the Core audit root via `--agentos-home`. If running from an isolated Git worktree, find or ask for the primary checkout and pass `--primary-agentos-home <primary-agentos-home>` so adapter setup checks and remediation recommendations target the canonical installation, while Personal Overlay reads come from `<primary-agentos-home>/personal/os`. Skill mirror audits compare Core skills from `--agentos-home` plus private skills from the primary overlay; mirror sync recommendations are suppressed while those roots differ.

3. Run the deterministic helper.
   Use:

   ```bash
   python3 scripts/agentos_doctor.py
   ```

   Add `--agentos-home`, `--primary-agentos-home`, `--mirror-root`, `--all-default-adapters`, and repeated `--adapter <path>` when needed. Repeat the same adapter flags used by installer dry-runs/checks.

4. Interpret results.
   Treat script output as checked facts, not the whole diagnosis. For automation evidence, inspect relevant local notes only as needed:

   - Codex automation metadata under the current harness automation directory, when present.
   - `personal/os/automations/AUTOMATIONS.md`, when present.
   - Nearby Personal Overlay automation notes when the registry points to them.

   Do not quote private contents. Summarize only the minimum needed: active, scheduled/enabled, possible/ambiguous, disabled/retired/draft, missing, or unreadable.

5. Classify automation state conservatively.
   Active/scheduled/enabled evidence can support PASS. Vague prose, drafts, retired notes, disabled notes, or negative statements should produce WARN and a recommendation to confirm with the user. If judgment is uncertain, say so and ask.

6. Recommend next steps.
   Separate deterministic commands from judgment calls. Ask before adapter writes, mirror syncs, Personal Overlay file creation, or automation changes. Prefer the lower-level tools for approved remediation:

   - `scripts/install_global_agent_instructions.py` for global instruction adapters.
   - `os/skills/mirror-skills/scripts/mirror_skills.py` for skill mirror audits/syncs.
   - `os/playbook/GETTING_STARTED.md` for first-pass Personal Overlay setup.

## Quality Bar

- The report distinguishes script facts from agent interpretation.
- Feature worktree runs do not recommend writing durable setup state to the worktree.
- Ambiguous automation prose is not treated as active recurring evidence.
- Private file contents are not exposed.
- No writes occur without explicit user approval.

## Filing Rules

- Default output stays in chat.
- The deterministic helper stays at `scripts/agentos_doctor.py`.
- Private setup notes and automation state stay in the Personal Overlay.
- Current-machine mirror state is not recorded in the Core manifest.

## Verification

Before finishing, confirm:

1. The doctor script ran, or explain why it could not.
2. Any feature-worktree run used `--primary-agentos-home` or clearly warned that adapter write and mirror sync recommendations are limited.
3. Automation evidence was classified conservatively.
4. Recommended writes were framed as requests for approval, not actions already authorized.
