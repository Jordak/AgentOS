# Check Vendored Skill Upstreams

Design readiness: ready to implement

## Problem

AgentOS Core can vendor upstream skills under `os/skills/<skill-name>/` with an `UPSTREAM.md` file that records the source repository, upstream path, and vendored ref. Weekly AgentOS Review now expects a freshness check for these vendored skills, but there is no reusable manual or automated workflow that finds all `UPSTREAM.md` files and compares them against upstream.

Without a reusable check, agents may either forget to check upstream drift or compare against noisy repository HEADs instead of changes to the specific vendored path.

## Desired Behavior

Add a Core skill named `check-vendored-skill-upstreams` that can be run manually or from Weekly AgentOS Review.

The skill should:

- find Core skill `UPSTREAM.md` files under `os/skills/*/UPSTREAM.md`;
- parse `Source`, `Path`, and `Vendored ref`;
- check whether the upstream path has a newer commit than the vendored ref;
- report `up-to-date`, `update-available`, or `check-failed` per skill;
- include links or commands that make the upstream diff easy to inspect;
- never auto-update vendored files.

## Chosen Design

Use a thin `SKILL.md` plus a deterministic Python helper under `os/skills/check-vendored-skill-upstreams/scripts/`.

For GitHub-backed upstreams, compare the vendored ref with the latest commit touching the upstream path, not the default branch HEAD. The initial implementation can use the public GitHub REST commits endpoint for `owner/repo`, `path`, and optional branch/ref information. Unsupported or malformed upstream metadata should be reported as `check-failed`, not treated as up-to-date.

The script should default to the current AgentOS root, support explicit `--agentos-root`, and produce both text and JSON output so weekly review can include concise summaries or structured evidence.

## Scope

In scope:

- Core skill directory and script.
- Manifest entry.
- Smoke coverage for the current two vendored skills.
- Manual and Weekly AgentOS Review instructions.

Out of scope:

- Auto-updating vendored skills.
- Opening PRs or issues.
- Supporting non-GitHub upstreams beyond reporting them as unsupported.
- Changing `UPSTREAM.md` schema beyond documenting the fields this checker reads.
- Storing run history in Core.

## Acceptance Criteria

- Running the script finds the current vendored `improve-codebase-architecture` and `thermo-nuclear-code-quality-review` skills.
- The report compares against the latest upstream commit for each vendored path.
- The report is useful when run manually and safe for Weekly AgentOS Review.
- Network or upstream failures are visible as `check-failed` rows.
- The skill is listed in `os/skills/MANIFEST.md`.
- `scripts/run-validator` passes.
- `mirror-skills` can mirror the new skill to the current-machine skill root.

## Validation Plan

- Run the helper with `--format text` against the AgentOS root.
- Run the helper with `--format json` and inspect parseability.
- Run a failure smoke check with a synthetic malformed `UPSTREAM.md` fixture or invalid path when practical.
- Run Codex skill validation for the new skill.
- Run `scripts/run-validator`.
- Run scoped `mirror-skills` audit/sync for `check-vendored-skill-upstreams`.
