# AgentOS Verification

Status: maintainer guidance.

Use this when changing AgentOS Core, reviewing a pull request, or preparing a public-safe release. User-facing setup should usually ask an agent to run these checks rather than asking the user to run them directly.

## Default Validator

Run the local validator:

```bash
python3 os/verification/scripts/validate_agentos.py
```

The default validator reads local files only and runs structural checks plus deterministic publication/privacy checks.

## Benchmark Evidence

AgentOS uses a hybrid benchmark-evidence model:

- Private raw reports stay in the Personal Overlay, usually under `personal/os/verification/<suite>/reports/`. Saved runs may include `report.md`, `run.json`, harness diagnostics, local paths, and other private run evidence.
- Core benchmark history lives in `os/verification/BENCHMARK_HISTORY.md`. It contains only curated public-safe fields: date, commit/PR reference, suite, pass/fail or hit-rate summary, interpretation, and caveats such as `dry-run only` or `no real harness run`.

Do not paste raw report dumps, transcripts, local machine paths, account/session details, private prompts, or generated report payloads into Core history. If a private run produces an insight worth preserving publicly, summarize the result by hand and keep the raw evidence in the Personal Overlay.

The default validator lints Core benchmark history for public-safe shape and raw-report leakage.

Check saved raw harness report freshness during Weekly Review:

```bash
python3 os/verification/scripts/check_benchmark_harness_freshness.py
```

When reviewing whether the curated Core history has caught up with private raw runs, include the history check:

```bash
python3 os/verification/scripts/check_benchmark_harness_freshness.py --check-history
```

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
