# Decisions Log

Status: Core architecture decisions.

This Core log records publishable AgentOS architecture decisions. Live personal decisions belong in `personal/os/memory/DECISIONS_LOG.md`.

## 2026-05-23

- AgentOS-managed files and directories should not use symlinks; repository paths outside `personal/` and public exports reject symlinks, and scripts must fail closed instead of following symlinks during managed reads or writes, including when the relevant managed path is in Personal Overlay. See `docs/adr/0005-no-symlinks-in-agentos-managed-files.md`.
- AgentOS executable scripts should stay thin, deterministic, and easy to audit across personal and work machines; ambiguous judgment, prose interpretation, and remediation orchestration belong in Markdown skills and playbooks unless executable complexity provides narrowly scoped deterministic value. See `docs/adr/0003-thin-trusted-scripts.md`.

## 2026-05-18

- AgentOS publishing architecture uses AgentOS Core under `$root/os/` plus a Personal Overlay under `$root/personal/os/`, with Core read first and matching Personal Overlay files read after it.
- AgentOS uses layer parity plus content residency: Core and Personal Overlay keep the same layer shape, while individual files decide whether they are publishable scaffolding or private user-specific state.
- Personal Overlay v1 uses the fixed overlay root `$root/personal/os/`; optional external overlay discovery is deferred until there is a real need.
- Generated outputs derived from real private data, project state, memory, interests, accounts, or work context belong in the Personal Overlay by default; AgentOS Core may contain only sanitized examples or templates.
- Named live agents configured around a real person's interests, routines, connected-account assumptions, private output paths, or personal project state belong in the Personal Overlay by default; AgentOS Core may contain only agent templates, contracts, and sanitized examples.
- Reusable skill procedures may remain in AgentOS Core, while private live inputs for those skills belong in Personal Overlay skill config files such as `$root/personal/os/skills/<skill-name>/CONFIG.md`; thin adapters to private agents or personal-artifact workflows belong in the Personal Overlay by default.
- Personal Overlay config is Markdown-first, with structured sidecars such as JSON or YAML only when scripts or validators need deterministic parsing.
- Live `context`, `identity`, `memory`, `connections`, `automations`, and verification report files belong in the Personal Overlay by default; AgentOS Core keeps templates, generic policy, schemas, reusable checks, and sanitized examples.
- Root adapter files such as `AGENTS.md` and `CLAUDE.md` may live in AgentOS Core only as generic launchers into Core and optional Personal Overlay.
- Private live files should move mostly as-is into the Personal Overlay first, while Core replacements are sanitized or rewritten separately.
- Public AgentOS publication must use a sanitized public export and fresh Git history rather than making a formerly private GitHub repository public.
