# Guidance Benchmark Status PR Workflow

Design readiness: ready to implement

## Problem

The manual Guidance benchmark trial can now run model-backed status-eligible evidence in GitHub Actions, but it only renders a public-safe step summary. Maintainers still have to manually copy freshness facts into `os/verification/BENCHMARK_STATUS.md`, which makes the public Core snapshot lag behind the latest eligible run.

## Current Behavior

The workflow is `workflow_dispatch` only, constrained to `main`, and uses the `guidance-benchmark-trial` protected environment. It runs the Codex preflight, executes one hard-coded Guidance benchmark configuration, generates a public-safe refresh candidate in `$RUNNER_TEMP`, renders a step summary, and deletes temporary evidence JSON.

The refresh helper is intentionally read-only. It emits deterministic public-safe candidate facts and non-Core-safe private locators, but it does not write `BENCHMARK_STATUS.md`.

## Desired Behavior

Keep the workflow manual, but let an approved manual run persist the public-safe status refresh by opening a pull request that updates `os/verification/BENCHMARK_STATUS.md`.

The workflow should keep the repository `GITHUB_TOKEN` read-only and use a protected-environment status PR token for the write path. That token should have only the repository permissions needed to push the update branch and open the pull request. The workflow should not become scheduled or automatic.

## Chosen Design

Add a checked-in status applicator helper that consumes the existing refresh candidate JSON and updates only the matching status entries in `os/verification/BENCHMARK_STATUS.md`. The applicator should read only `public_safe.targets`, reject malformed or unavailable candidates, and never read or render `private_locators`.

Update the manual workflow to run the applicator after the refresh candidate is generated successfully. If the status file changes, the workflow should commit the change to a generated branch and open a pull request. The workflow should not push directly to `main`.

Keep the model-backed benchmark job read-only. Pass only compact `public_safe` candidate facts to a separate writer job. The writer job still uses read-only repository `GITHUB_TOKEN` permissions, and uses the protected `AGENTOS_STATUS_PR_TOKEN` environment secret only for pushing the generated branch and opening the pull request.

Generated PR content should stay public-safe and point back to the workflow run and step summary rather than embedding raw benchmark evidence.

The generated PR should use normal pull request validation. Because GitHub suppresses most workflow runs caused by the repository `GITHUB_TOKEN`, the generated branch push and PR creation use a dedicated protected-environment token instead.

## Alternatives Considered

Directly committing to `main` would be simpler, but it bypasses AgentOS protected-main discipline and removes human review of the public status snapshot.

Extending `refresh_benchmark_status.py` to write the status file would be convenient, but it would weaken the existing skill contract that the refresh helper is JSON-only and read-only. A separate applicator keeps the read and write boundaries explicit.

Scheduling the workflow would make freshness automatic, but the current model-backed run cost is high enough that v2 should remain manually triggered.

## Non-Goals

- No schedule, cron trigger, push trigger, or custom workflow inputs.
- No raw reports, run JSON, transcripts, stdout, stderr, local paths, prompts, private locators, or private diagnostics in Core, logs, PR bodies, or artifacts.
- No direct commits to `main`.
- No append-only benchmark history.
- No generic multi-suite status writer beyond the current Guidance target shape.

## Acceptance Criteria

- The workflow remains `workflow_dispatch` only with zero custom inputs and keeps the `main` guard.
- The workflow keeps repository `GITHUB_TOKEN` permissions read-only and uses a protected-environment status PR token for the generated branch push and PR creation.
- The workflow still runs the existing hard-coded Guidance benchmark configuration.
- A checked-in helper updates `os/verification/BENCHMARK_STATUS.md` from `public_safe.targets` in the refresh candidate.
- The helper ignores `private_locators` and rejects missing, malformed, or unavailable candidates.
- The helper removes stale `Non-Passing Details` when the new candidate is passing.
- The workflow opens a PR only when `BENCHMARK_STATUS.md` changes.
- Workflow-created status PRs are expected to run normal pull request validation and remain review-gated.
- The workflow does not upload artifacts, push directly to `main`, close issues, comment on issues, or create PRs containing raw benchmark evidence.
- Tests cover successful passing updates, non-passing detail rendering, malformed input rejection, unavailable candidate rejection, and private-locator non-leakage.

## Validation Plan

- Run the new applicator self-test.
- Run `python3 os/verification/scripts/refresh_benchmark_status.py --self-test`.
- Run `python3 os/verification/scripts/render_benchmark_step_summary.py --self-test`.
- Run `scripts/run-validator`.
- After merge, manually trigger the workflow on `main` and confirm it opens a public-safe `BENCHMARK_STATUS.md` refresh PR when the benchmark evidence is newer than the current snapshot.

## Open Questions

None for v2.
