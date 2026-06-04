---
name: run-benchmarks
description: "Run AgentOS benchmark scripts from the benchmark manifest, save status-eligible evidence for current status targets when possible, and route the result through `refresh-benchmark-status`. Use when the user asks to run AgentOS benchmarks, run all benchmarks, produce fresh benchmark evidence, or run benchmarks and refresh Core benchmark status."
---

# Run Benchmarks

## Goal

Run AgentOS benchmarks end to end without embedding benchmark-specific internals: discover configured scripts from `os/verification/BENCHMARKS.json`, classify manifest entries as current status-refresh targets or diagnostic/historical runnable suites, run only scripts that expose the expected CLI contract, save raw reports in the configured Personal Overlay report directories, and then invoke or follow `refresh-benchmark-status` for eligible current status targets. External/model-call harnesses either run from a clean git checkout whose script owns HUT sanitization, or from a sanitized Core-only checkout/export when the suite is diagnostic and export-compatible.

## Contract

Inputs:

- `os/verification/BENCHMARKS.json`.
- Configured benchmark scripts named by the manifest.
- User intent: deterministic/local checks only, model-call harnesses, or full benchmark-plus-status-refresh workflow.
- The current AgentOS checkout and its Git state.

Output artifact:

- A concise benchmark run report with commands, saved report directories, incompatible scripts, pass/fail/unavailable posture when safely visible, and status-refresh outcome.
- Optional update or proposed update to `os/verification/BENCHMARK_STATUS.md` through `refresh-benchmark-status`.

Mutability:

- Mixed. Reads Core benchmark configuration and runs local scripts.
- Local-write when benchmark scripts save reports under configured Personal Overlay report directories, and when `refresh-benchmark-status` updates Core status after the user requested or approved the refresh.
- No external-write behavior.

Tools and connectors:

- Local `git`, filesystem reads, and configured benchmark scripts.
- `os/verification/BENCHMARKS.json`.
- `os/skills/refresh-benchmark-status/SKILL.md` for status interpretation and updates.
- `os/verification/scripts/refresh_benchmark_status.py` through `refresh-benchmark-status` for deterministic status candidate facts after saved runs.
- `os/playbook/PERSONAL_OVERLAY.md` for report location boundaries.

Safety:

- Ask before running external harnesses, model-call benchmarks, or any command that may spend credits or require authenticated CLIs.
- Run current status-refresh targets from a clean, remote-fresh git checkout when the suite depends on Git metadata or the Git index. Guidance status-eligible runs use the runner's internal HUT sanitization and host-boundary sentinel tripwire and are not raw-export-compatible.
- Run diagnostic external/model-call harnesses from a sanitized Core-only checkout or export when the suite supports that shape, not from a primary checkout that has a live Personal Overlay nearby, unless the user explicitly accepts that risk for a diagnostic run.
- Do not copy raw reports, `run.json` bodies, transcripts, stdout, stderr, local paths, prompts, session details, account details, private diagnostics, or private evidence into Core.
- Do not update `os/verification/BENCHMARK_STATUS.md` directly; route all status interpretation and edits through `refresh-benchmark-status`.
- If the checkout is not clean, current `main`, do not produce status-eligible evidence. Offer diagnostic/non-eligible runs only when useful and clearly label them.

## Workflow Phases

1. Inspect the benchmark surface.
   Read `os/verification/BENCHMARKS.json`, `os/playbook/PERSONAL_OVERLAY.md`, and `os/skills/refresh-benchmark-status/SKILL.md`. Resolve each manifest `reports_dir` through the Personal Overlay rule before any saved run. Classify entries with `weekly_review.check_freshness: true` as current status-refresh targets; entries with `check_freshness: false` are runnable diagnostic/historical suites unless the manifest is explicitly changed. For each manifest entry, resolve the script path and run its help output, usually `python3 <script> --help`.

2. Check the script contract.
   Treat a script as compatible only when its help exposes the flags needed for the requested mode:
   - status-eligible saved evidence: `--save-report` and `--check-remote-main`;
   - deterministic validation: `--self-test`;
   - diagnostic preview: `--dry-run` when the script can avoid external harness calls;
   - external/model-call harnesses: `--no-dry-run`, plus `--harness all` only when the help advertises that option;
   - log-sensitive public CI trials: `--quiet` when the script may otherwise print rendered reports, progress lines, generated paths, raw evidence, or other non-Core-safe run details.

   Report incompatible scripts instead of carrying benchmark-specific command knowledge. Do not infer suite-specific flags or fixture names in this skill. Treat dry-run output as diagnostic and ineligible for Core status updates, even when it is saved with Git metadata.

3. Preflight Git state.
   Before status-eligible saved runs, confirm the checkout is on `main`, clean, aligned with `origin/main` after fetching when network is available, and using the canonical or user-assigned Personal Overlay report directories. If the current checkout would save into a feature worktree's ignored `personal/os/` skeleton, switch to the clean current `main` checkout that owns the canonical Personal Overlay or label the run diagnostic/ineligible. The scripts' own `--check-remote-main` metadata remains the evidence of remote freshness at run time.

4. Run safe checks first.
   Default to deterministic/local-safe work: run compatible scripts' `--self-test`, then run diagnostic previews with `--dry-run` when supported. Save status-eligible evidence only for current status-refresh targets, from behavior-bearing local runs advertised by the script help or from approved real harness runs. Runs for diagnostic/historical suites may still save reports, but those reports do not refresh current Core status while `check_freshness` is false. If the next useful command could call external harnesses or spend credits, ask before running it.

5. Ask before model-call harnesses.
   If the user explicitly asked for model-call harnesses or all external benchmarks, summarize the commands, the compatible harness choices advertised by each script's help, and any spending/authentication risk. Ask for confirmation unless the current request clearly approved spending model calls. Interpret `--harness all` as all configured harnesses advertised by that script, not every conceivable harness.

   For approved external/model-call harness runs that are current status-refresh targets, use a clean, remote-fresh `main` git checkout or clone at the reviewed commit. Do not use a raw file export for Guidance status-eligible runs; the runner uses the Git index as its source snapshot, builds its own sanitized HUT workspace, and records a passive host-boundary sentinel tripwire. The sentinel not being observed does not prove full host filesystem isolation; an observed sentinel makes the run status-ineligible. For approved diagnostic suites that are export-compatible, create or use a sanitized Core-only checkout or export at the same commit and verify it contains no live Personal Overlay files beyond tracked skeleton/placeholders before running commands. Run the compatible script contract from the selected root, usually `python3 <script> --no-dry-run --check-remote-main --save-report`, adding `--harness all` only when advertised and adding `--quiet` for log-sensitive public CI trials. After the run, copy generated report directories back into the canonical or user-assigned Personal Overlay only after confirming the reports derive from public Core inputs.

6. Refresh status.
   After scripts finish, run or follow `refresh-benchmark-status` in update, proposal, or report mode as allowed by the user's request and the available evidence. Treat `os/verification/scripts/refresh_benchmark_status.py` as the deterministic helper used inside that workflow, not as the user-facing workflow boundary. If the user asked for "run benchmarks and refresh status", continue through eligible updates for current status-refresh targets. Diagnostic/historical suite reports can be summarized, but they do not drive current Core status while their manifest entries have `check_freshness: false`. If write authorization is unclear, run the refresh workflow in proposal/report mode rather than stopping at an offer. Leave refresh as a next step only when blocked, declined, or impossible; in that case state that the benchmark process is not complete until `refresh-benchmark-status` has run.

## Filing Rules

- Raw reports and run histories stay in the canonical or user-assigned Personal Overlay report directories configured by `os/verification/BENCHMARKS.json`.
- Core benchmark status lives only in `os/verification/BENCHMARK_STATUS.md` and is changed only through `refresh-benchmark-status`.
- Benchmark CLI standardization is deferred to GitHub Issue #33.
- Deterministic status-refresh candidate generation lives in `os/verification/scripts/refresh_benchmark_status.py` and is used through `refresh-benchmark-status`.

## Quality Bar

- The run plan comes from the manifest and script help, not benchmark-specific internals.
- Model-call or external harness work is explicitly approved.
- Every saved report path is named in the final report without copying raw/private report contents.
- Incompatible scripts are reported clearly.
- The final response says whether `refresh-benchmark-status` ran, updated Core status, proposed changes, or remains the next step.

## Verification

Before finishing:

1. Confirm `os/verification/BENCHMARKS.json`, `os/playbook/PERSONAL_OVERLAY.md`, and `refresh-benchmark-status` were read.
2. Confirm configured report directories were resolved through the Personal Overlay rule, script help was inspected, and compatibility was reported.
3. Confirm Git preflight was performed before status-eligible saved runs.
4. Confirm no model-call harness ran without approval.
5. Confirm external/model-call harnesses ran from the required root shape: clean git checkout for current status-refresh targets that need Git metadata/index state, sanitized checkout/export only for export-compatible diagnostic runs, or explicitly did not run.
6. Confirm the configured harness choices were reported per script before any `--harness all` run.
7. Confirm raw report content was not copied into Core.
8. Confirm `refresh-benchmark-status` ran or was followed in proposal/report mode, or that a blocked/declined refresh was labeled incomplete with the next action.
9. After helper changes, run `python3 os/verification/scripts/refresh_benchmark_status.py --self-test`.
