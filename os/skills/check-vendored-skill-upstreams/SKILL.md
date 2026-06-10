---
name: check-vendored-skill-upstreams
description: Check AgentOS Core skills with `UPSTREAM.md` provenance files against their upstream GitHub sources. Use when manually auditing vendored skill freshness, preparing Weekly AgentOS Review, or deciding whether vendored skills need a reviewed update PR.
---

# Check Vendored Skill Upstreams

## Goal

Report whether AgentOS Core vendored skills are current with their upstream sources. This is a freshness check only: never auto-update vendored files.

## Contract

Inputs: an AgentOS checkout, defaulting to the current workspace, with vendored Core skills under `os/skills/<skill-name>/UPSTREAM.md`.

Output artifact: a text or JSON freshness report with one row per vendored skill.

Mutability: read-only for the AgentOS checkout and upstream sources. The normal helper reads local files and public upstream metadata only; `--self-test` writes temporary fixtures under the system temporary directory.

Tools and connectors: local filesystem, Python helper `scripts/check_vendored_skill_upstreams.py`, sidecar no-network self-test module, and public GitHub HTTP API for supported upstreams.

Safety: do not edit vendored skills, open PRs/issues, post comments, change automations, or write external state. Treat update availability as a prompt for a reviewed vendoring PR, not as approval to apply upstream changes.

Workflow Phases:

1. Read `os/skills/*/UPSTREAM.md`.
2. Parse `Source`, `Path`, and `Vendored ref`.
3. For GitHub sources, compare the vendored ref with the latest upstream commit touching the vendored path.
4. Report `up-to-date`, `update-available`, or `check-failed`.
5. If an update is available, link to the upstream compare view and recommend a reviewed vendoring update.

Quality Bar:

- Compare against the latest commit touching the upstream path, not the repository's default-branch HEAD.
- Treat a vendored repository snapshot as current when it already contains the latest path-touching commit.
- Make network and metadata failures explicit as `check-failed`.
- Keep manual and Weekly AgentOS Review output concise.

Filing Rules:

- Default output stays in chat or the weekly review report.
- Do not write run history to Core.
- Weekly AgentOS Review may summarize results in `personal/os/memory/weekly-review/`.

## Usage

Run from the AgentOS root:

```bash
python3 os/skills/check-vendored-skill-upstreams/scripts/check_vendored_skill_upstreams.py
```

Use JSON for automation or weekly review ingestion:

```bash
python3 os/skills/check-vendored-skill-upstreams/scripts/check_vendored_skill_upstreams.py --format json
```

Use `--strict` only when update availability should make the command fail.

## Verification

Before trusting changes to this skill:

1. Run the helper with `--self-test` to cover parser discovery, status classification, malformed metadata, strict exits, directory-style upstream paths, and text/JSON report shape without network access.
2. Run the helper against the AgentOS root with `--format text`.
3. Run the helper against the AgentOS root with `--format json`.
4. Run Codex skill validation for this skill.
5. Run `scripts/run-validator`.
6. Before review or merge, run `expose-skills` in dry-run mode when current-machine discoverability matters; apply exposure changes only after explicit user approval or after the reviewed PR lands.
