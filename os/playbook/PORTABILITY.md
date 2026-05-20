# AgentOS Portability Guide

Status: first pass.

The AgentOS should stay useful even if the user stops using Codex and moves to Claude Code, Google Antigravity, ChatGPT Projects, Cursor, or another agentic tool.

## Principle

Keep the canonical OS control plane as plain Markdown under:

`os/`

Tool-specific files are adapters, not the source of truth.

Unless otherwise stated, local file paths in AgentOS Markdown are relative to the AgentOS repository root. Do not use hardcoded user-specific checkout paths for files that live inside AgentOS; use root-relative paths like `os/skills/MANIFEST.md`.

Static HTML is the preferred format for substantial human-facing artifacts, but those artifacts are outputs, not the portable control plane. Keep Markdown indexes or pointers where needed so other tools can discover the HTML files.

## Reusable Project Code

- Do not hard-code machine-specific app bundle paths, user directories, or local install locations into reusable project code.
- Prefer stable command names on `PATH`, configuration, environment variables, or explicit user-supplied flags.
- Treat absolute local paths and tool-specific flags as escape hatches, not shared defaults.
- Put general behavior in shared/base layers before adding child or adapter-specific logic.

## Portable Core

These folders should remain tool-agnostic:

- `os/identity/`
- `os/context/`
- `os/skills/`
- `os/memory/`
- `os/connections/`
- `os/agents/`
- `os/verification/`
- `os/playbook/`
- `os/automations/`

## Tool Adapters

Tool-specific adapter state belongs in the Personal Overlay when it contains current-machine paths or account-specific setup.

Common adapter surfaces:

- Global instructions in the tool's home directory.
- Workspace instructions such as `AGENTS.md`.
- Discoverable skill mirrors.
- Automation definitions.

Claude Code adapter:

- Workspace instructions: `CLAUDE.md`

Other tools should get small adapter files that point back to the portable core. Do not copy the whole OS into every adapter unless the tool cannot read local files.

Possible future adapters:

- Claude Code: create `CLAUDE.md` that imports `AGENTS.md`, then add Claude-specific notes below the import only when needed. Claude Code's current docs say it reads `CLAUDE.md`, not `AGENTS.md`, and supports imports with `@AGENTS.md`.
- Google Antigravity: create a project instruction/context adapter that points to `os/INDEX.md`. Verify current Antigravity docs before relying on any exact file convention; Google's current public codelab emphasizes artifacts and verification, but does not settle the full portable-instructions story for this OS.
- ChatGPT Projects: project instructions plus selected uploaded/attached Markdown files, because ChatGPT Projects may not automatically read this local filesystem.
- Cursor: project rules/instructions that point to `os/INDEX.md` and project-specific `AGENTS.md` files.

## Migration Checklist

When moving AgentOS to a new tool:

1. Check that tool's current official docs for persistent instructions, project context, skills, memory, connections, and automations.
2. Create a small adapter file for that tool.
3. Point the adapter to `os/INDEX.md`.
4. Confirm the tool can read local files under the AgentOS repository root.
5. If it cannot, upload or copy only the minimal relevant Markdown files.
6. Recreate discoverable skills only when the tool has a real skill/plugin mechanism.
7. Recreate automations only after one manual run and verification.
8. Keep the source map updated so project-specific work still routes to the right place.

## Avoid Drift

- Do not maintain duplicate global instruction mirrors.
- Keep reusable knowledge in `os/`.
- Keep installed tool-specific copies as thin as possible.
- When installed skill mirrors are needed, keep the source copy in `os/skills/` and run `audit-skill-mirrors` on the current machine instead of storing mirror state in portable AgentOS metadata.

## What Is Not Portable

- Auth state and connected accounts.
- Codex-specific automation definitions.
- Tool-specific slash/skill discovery metadata.
- Browser sessions.
- Local absolute paths if this workspace moves to another machine.

## Current Source Notes

Checked on 2026-05-07:

- Codex: OpenAI's AGENTS.md docs say Codex reads global guidance from the user-level Codex `AGENTS.md` file and project guidance from `AGENTS.md` files in the workspace path.
- Claude Code: Anthropic's memory docs say Claude Code reads `CLAUDE.md`, can import `AGENTS.md`, and supports user/project/local scopes.
- Google Antigravity: Google's public codelab emphasizes artifact-based verification for plans, screenshots, recordings, diffs, and reports. Treat exact instruction-file conventions as migration-time research.

Sources:

- https://developers.openai.com/codex/guides/agents-md
- https://code.claude.com/docs/en/memory
- https://codelabs.developers.google.com/getting-started-google-antigravity

## If The Workspace Moves

Update:

- Personal Overlay source-map entries.
- Local adapter installation notes.
- Installed skill paths.
- Automation prompts that reference absolute paths.
