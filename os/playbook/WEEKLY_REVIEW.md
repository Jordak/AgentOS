# Weekly Review

Status: Core template.

Use this as a starting point for a Personal Overlay weekly review workflow.

## Purpose

Review whether AgentOS state is current, useful, and safely filed.

## Inputs

- `AGENTS.md`
- `os/INDEX.md`
- `os/RESOLVER.md`
- `os/playbook/AGENTOS_PLAYBOOK.md`
- Matching Personal Overlay files when present

## Procedure

1. Inspect current Core and Personal Overlay state.
2. Run relevant local validators.
3. Check saved benchmark freshness when local raw reports exist:

   ```bash
   python3 os/verification/scripts/check_benchmark_harness_freshness.py --check-history
   ```

   Use `os/verification/BENCHMARK_HISTORY.md` only for curated public-safe summaries. Keep raw benchmark reports, diagnostics, and generated run files in the Personal Overlay.
4. Run the global-instructions drift check:

   ```bash
   python3 scripts/install_global_agent_instructions.py --agentos-home <agentos-home> --check
   ```

   Replace `<agentos-home>` with the resolved path to the current AgentOS checkout. If setup used `--all-default-adapters` or custom `--adapter <path>` flags, repeat those same flags here so the check covers those managed adapter files. Confirm the canonical `<home>/.agents/AGENTS.md` file and any managed harness adapters still point to the intended AgentOS installation.
5. Identify stale state, missing templates, private-data risks, and useful follow-up work.
6. Draft a report as a private generated output under `personal/os/memory/weekly-review/`.
7. Ask the user to approve any durable state changes or external actions.

## Safety

- Do not inspect external accounts unless the user explicitly asks.
- Do not perform external writes, delete files, or change automation state without approval.
- Treat generated durable state changes as proposals until approved.
