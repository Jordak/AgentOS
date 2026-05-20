# Programming Playbook Resolver

Status: directory resolver v1.

Use this directory for durable programming preferences that should shape code, CLI, and documentation edits across AgentOS and mapped projects.

## Routes

- CLI design, command-line option names, dry-run or write-mode semantics, report flags, and machine-readable output: `CLI.md`.
- Markdown prose/source style, soft wrapping, reflow scope, and Markdown formatting churn: `MARKDOWN.md`.

## Tie-Breakers

- Follow coherent project-local style when it conflicts with these global preferences.
- Prefer stable, familiar conventions over new AgentOS-specific option shapes unless the local project has a clear reason.
- Keep root adapter instructions lean; add durable programming preferences here rather than expanding `AGENTS.md`.

## Update Rules

- Add a new file in this directory only for a repeated programming preference that is stable across projects.
- Keep each preference file narrow enough that agents can load only the relevant one.
- When a preference affects activation behavior, add or update a playbook activation fixture under `os/verification/playbook-activation/`.
