# AgentOS Verification

Status: maintainer guidance.

Use this when changing AgentOS Core, changing publishable support files, reviewing a pull request, or preparing a public-safe release. User-facing setup should usually ask an agent to run these checks rather than asking the user to run them directly.

## Default Validator

Run the local validator:

```bash
scripts/run-validator
```

The default validator reads local files only and runs structural checks plus deterministic publication/privacy checks.

## Benchmark Status

Core benchmark posture lives in `os/verification/BENCHMARK_STATUS.md`. That file is a current public-safe snapshot for humans and agents, not raw evidence, a run log, or append-only history.

Raw benchmark reports and run histories belong outside Core, usually under the Personal Overlay report directories configured in `os/verification/BENCHMARKS.json`. Use `os/skills/refresh-benchmark-status/SKILL.md` to refresh the Core snapshot from eligible local evidence without copying private or raw run details into Core.

## Benchmark Script CLI Contract

Every benchmark script listed in `os/verification/BENCHMARKS.json` must expose a small common CLI surface so `run-benchmarks` can inspect and run scripts from the manifest without benchmark-specific command knowledge.

Required behavior:

- `--help` exits successfully, performs no writes, makes no network calls, spends no model calls, and advertises the orchestration flags the script supports.
- `--self-test` runs deterministic local script or grader checks, writes no benchmark reports, spends no model calls, and exits nonzero when local benchmark invariants fail.
- `--save-report` writes both `report.md` and `run.json` to one timestamped directory under the manifest `reports_dir`; `--no-save-report` must be available for boolean-option symmetry.
- `--check-remote-main` records remote `origin/main` freshness metadata for status-eligible evidence. If remote freshness cannot be proven, the saved evidence remains ineligible for Core benchmark status updates.
- Harness-capable scripts expose `--harness`, `--dry-run`, `--no-dry-run`, `--model`, and `--effort`. Dry-run mode is the safe default for external or model-call harness work; `--no-dry-run` is the explicit real-run mode.
- Unsupported harness names fail as usage or configuration errors. Supported harnesses with missing local dependencies should be represented as unavailable harness evidence, not as behavioral benchmark failures.

Saved `run.json` reports intended for `refresh-benchmark-status` must include current-schema Git metadata, a manifest-resolvable summary object, behavior totals, unavailable harness counts when applicable, and mode metadata sufficient to reject dry-run, transcript, saved-response, stale, dirty-worktree, non-main, or non-remote-fresh evidence.

The default validator enforces the mechanical CLI surface and deterministic self-tests. It intentionally does not run real harnesses, inspect saved report directories, simulate missing dependencies, or parse raw benchmark reports.

## Commit And Tree Scans

For shell-backed publication safety scans, run:

```bash
scripts/check_staged_publication_secrets.sh
scripts/check_publication_tree_secrets.sh HEAD
```

Use `scripts/check_working_tree_secrets.sh` as an advisory day-to-day scan of the mixed working tree.

## Hooks

Install the included hooks to validate and scan commits and pushes:

```bash
scripts/install_agentos_hooks.sh
```

## Publication

For public repository publication, follow `os/playbook/PUBLICATION.md`. Do not make a formerly private AgentOS repository public after private files have existed in its history.
