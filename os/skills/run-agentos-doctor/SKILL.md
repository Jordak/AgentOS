---
name: run-agentos-doctor
description: Run AgentOS setup health checks using a thin deterministic fact-collector plus agent judgment for ambiguous local state. Use when the user asks to run AgentOS Doctor, audit AgentOS setup health, check whether AgentOS is wired up correctly, inspect adapters, Core skill exposure, Personal Overlay starter files, or recurring AgentOS update/drift checks.
---

# Run AgentOS Doctor

## Goal

Audit a local AgentOS installation without making changes. Treat the skill-local helper at `os/skills/run-agentos-doctor/scripts/agentos_doctor.py` as a read-only fact collector, not as the whole diagnosis: scripts gather deterministic facts, and this Markdown skill interprets those facts.

## Contract

Inputs:

- An AgentOS checkout, defaulting to the current workspace.
- Optional primary AgentOS checkout when running from a feature worktree.
- Optional adapter flags used by the installer, such as `--all-default-adapters` or repeated `--adapter <path>`.
- Optional installed-adapter smoke harness, starting with Codex.
- Optional current-machine Core skill exposure context.

Output artifact:

- A concise setup health report with script facts, interpreted risks, and approval-gated next steps.

Mutability:

- Read-only by default.
- Ask before installing adapters, applying Core skill exposure, editing Personal Overlay files, changing automations, or writing outside the checkout.

Tools and connectors:

- Local filesystem, skill-local `os/skills/run-agentos-doctor/scripts/agentos_doctor.py`, `scripts/install_global_agent_instructions.py`, `os/skills/expose-skills/scripts/expose_skills.py`, `os/playbook/GETTING_STARTED.md`, and relevant Personal Overlay automation notes when present.
- Optional Codex CLI smoke diagnostics when the user explicitly requests an installed-adapter smoke run.

Safety:

- Do not expose private file contents.
- Do not treat ambiguous automation prose as active recurring evidence.
- Do not treat the helper's automation location counts as activation proof.
- Do not run installed-adapter smoke checks by default. Real smoke runs may invoke local harnesses, auth/model paths, and model calls; require explicit user approval or explicit smoke flags.
- Ask before adapter writes, Core skill exposure changes, Personal Overlay file creation, automation changes, or current-machine setup changes.

## Workflow Phases

1. Load setup context.
   Read `AGENTS.md`, `os/INDEX.md`, `os/playbook/PERSONAL_OVERLAY.md`, and `os/playbook/GETTING_STARTED.md`. If current-machine setup boundaries are unclear, also read `os/RESOLVER.md`.

2. Choose roots.
   Use the current checkout as the Core audit root via `--agentos-home`. If running from an isolated Git worktree, find or ask for the primary checkout and pass `--primary-agentos-home <primary-agentos-home>` so private Personal Overlay automation locations refer to the canonical checkout. Core skill exposure evidence stays tied to the audited checkout. Treat missing primary-root context as a limitation, not as permission to write into the worktree.

3. Run the deterministic helper.
   Use:

   ```bash
   python3 os/skills/run-agentos-doctor/scripts/agentos_doctor.py
   ```

   Add `--agentos-home`, `--primary-agentos-home`, `--all-default-adapters`, and repeated `--adapter <path>` when needed. Repeat the same adapter flags used by installer dry-runs/checks. The helper must remain read-only: adapter check only and automation location/count facts only. It does not audit Core skill exposure, parse `os/playbook/GETTING_STARTED.md` for starter paths, or judge starter-file completeness.

4. Interpret script facts.
   Treat PASS/WARN/FAIL as facts about the helper's checks, not as final setup truth. If helper output is missing, unreadable, malformed, or ambiguous, keep the diagnosis at WARN/FAIL until a human or agent reviews the underlying facts.

5. Run optional installed-adapter smoke diagnostics when requested.
   Static adapter drift remains part of the normal helper run. The installed-adapter smoke check is stronger: it starts a harness from a temporary external project with no project-local adapter and checks whether the real installed global adapter makes AgentOS setup facts visible.

   Dry-run planning is safe and does not invoke the harness:

   ```bash
   python3 os/skills/run-agentos-doctor/scripts/agentos_doctor.py --installed-adapter-smoke codex
   ```

   A real smoke run is opt-in and may use local harness auth/model paths:

   ```bash
   python3 os/skills/run-agentos-doctor/scripts/agentos_doctor.py --installed-adapter-smoke codex --run-installed-adapter-smoke
   ```

   The smoke prompt must not include the expected AgentOS path, `personal/**`, `os/verification/**`, benchmark fixtures, judge assets, answer keys, saved reports, or raw private state. The helper reports parsed setup facts only; it does not print raw harness output. Default output stays diagnostic-only and does not update `os/verification/BENCHMARK_STATUS.md`.

6. Audit Core skill exposure when requested.
   When the user wants Core skill discoverability or exposure diagnosis, use the expose-skills skill in its default dry-run mode:

   ```bash
   python3 os/skills/expose-skills/scripts/expose_skills.py --agentos-root <agentos-root>
   ```

   Do not use `--no-dry-run` or `--replace-existing-copy --no-dry-run` without explicit approval.

7. Interpret starter setup.
   When the user wants Personal Overlay starter-file diagnosis, this skill reads `os/playbook/GETTING_STARTED.md` and reasons about the relevant starter guidance. Keep that judgment in the agent layer: summarize gaps without quoting private contents, and ask before creating or editing Personal Overlay files.

8. Interpret automation state.
   The helper reports automation registry/file/directory presence and counts only. When the user wants automation diagnosis, inspect relevant local notes only as needed:

   - Codex automation metadata under the current harness automation directory, when present.
   - `personal/os/automations/AUTOMATIONS.md`, when present.

   Do not quote private contents. Summarize only the minimum needed: active, scheduled/enabled, possible/ambiguous, disabled/retired/draft, missing, or unreadable. Vague prose, drafts, retired notes, disabled notes, negative statements, malformed metadata, or uncertainty should remain WARN and prompt confirmation.

9. Recommend next steps.
   Separate deterministic commands from judgment calls. Ask before adapter writes, Core skill exposure changes, Personal Overlay file creation, automation edits, or current-machine setup changes. Prefer the lower-level tools only after approval:

   - `scripts/install_global_agent_instructions.py` for global instruction adapters.
   - `os/skills/expose-skills/scripts/expose_skills.py` for Core skill exposure dry runs, approved symlink adapter applies, and approved backup-backed same-name Core skill directory replacement.
   - `os/playbook/GETTING_STARTED.md` for first-pass Personal Overlay setup.

## Quality Bar

- The report distinguishes script facts from agent interpretation.
- Feature-worktree runs do not recommend writing durable setup state to the worktree.
- Split-root runs keep Core audit evidence tied to `--agentos-home` and Personal Overlay evidence tied to `--primary-agentos-home`.
- Installed-adapter smoke checks are optional, diagnostic-only, and do not print raw harness output by default.
- Core skill exposure checks use `expose-skills`.
- Ambiguous automation prose or metadata is not treated as active recurring evidence.
- Private file contents are not exposed.
- No writes occur without explicit user approval.

## Filing Rules

- Default output stays in chat; the deterministic helper and its tests stay under `os/skills/run-agentos-doctor/scripts/`; private setup notes, optional raw installed-adapter smoke evidence, and automation state stay in the Personal Overlay; current-machine adapter state is not recorded in the Core manifest or benchmark status.

## Verification

Before finishing, confirm:

1. The doctor script ran, or explain why it could not.
2. Any feature-worktree run used `--primary-agentos-home` or clearly warned that private/setup interpretation is limited.
3. Any real installed-adapter smoke run was explicitly requested or approved, and raw harness output was not copied into Core.
4. Core skill exposure was audited through expose-skills when requested, not inferred from Doctor helper output.
5. Automation evidence was classified conservatively by the agent, not by assuming helper counts imply active setup.
6. Recommended writes were framed as requests for approval, not actions already authorized.
