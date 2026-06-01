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
3. Run the global-instructions drift check:

   ```bash
   python3 scripts/install_global_agent_instructions.py --agentos-home <agentos-home> --check
   ```

   Replace `<agentos-home>` with the resolved path to the current AgentOS checkout. If setup used `--all-default-adapters` or custom `--adapter <path>` flags, repeat those same flags here so the check covers those managed adapter files. Confirm the canonical `<home>/.agents/AGENTS.md` file and any managed harness adapters still point to the intended AgentOS installation.
4. If any Core skills have `UPSTREAM.md` provenance files, run the vendored skill upstream freshness check:

   ```bash
   python3 os/skills/check-vendored-skill-upstreams/scripts/check_vendored_skill_upstreams.py --agentos-root <agentos-home>
   ```

   Treat update availability as report-only evidence for a separate reviewed vendoring update. Do not auto-update vendored skills during Weekly Review.
5. Identify stale state, missing templates, private-data risks, and useful follow-up work.
6. Draft a report as a private generated output under `personal/os/memory/weekly-review/`.
7. Classify generated durable-state recommendations by inbox: GitHub issue or mapped-project tracker for public-safe actionable project work; `personal/os/memory/propagation-review/QUEUE.md` for private, tentative, connector-derived, personal, cross-project, or pre-issue proposals; direct edit only for exact approved changes.
8. Ask the user to approve any durable state changes or external actions. Inline approval can approve exact requested edits or specific queue entries, but vague generated yes/no prompts are not durable decision records by themselves.

## Retrospective Checklist

Check whether the OS is still serving the user:

- Stale context: source maps, project summaries, tool notes, work boundaries, and dated context files.
- Repeated explanations: facts the user had to restate that should become context, memory, a source-map entry, or a skill.
- Unused or weak skills: skills that are never invoked, produce poor outputs, lack verification, or duplicate another workflow.
- Agent instructions: live agent roles, inputs, outputs, boundaries, and verification checklists that no longer match actual use.
- Automations: live registry entries, manual-run evidence, last verification dates, logs, run histories, review modes, and disable notes.
- Memory: decisions or lessons that should be promoted, stale working memory that should be removed, and generated reports that remain only evidence.
- Source-map drift: moved repositories, stale document links, missing canonical sources, or project work that belongs outside AgentOS.
- Propagation review: proposed durable updates that are still waiting, applied entries that need decision records, and rejected entries that should be closed.

## Safety

- Do not inspect external accounts unless the user explicitly asks.
- Do not perform external writes, delete files, or change automation state without approval.
- Treat generated durable state changes as proposals until they are filed in the right inbox, approved when needed, and applied.
