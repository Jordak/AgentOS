---
name: run-benchmarks
description: "Run AgentOS benchmark scripts from the benchmark manifest, save status-eligible evidence when possible, and route the result through `refresh-benchmark-status`. Use when the user asks to run AgentOS benchmarks, run all benchmarks, produce fresh benchmark evidence, or run benchmarks and refresh Core benchmark status."
---

# Run Benchmarks

## Goal

Run AgentOS benchmarks end to end without embedding benchmark-specific internals: discover configured scripts from `os/verification/BENCHMARKS.json`, run only scripts that expose the expected CLI contract, save raw reports in the Personal Overlay, and then invoke or follow `refresh-benchmark-status` so Core status is not left behind the evidence.

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
- `os/playbook/PERSONAL_OVERLAY.md` for report location boundaries.

Safety:

- Ask before running external harnesses, model-call benchmarks, or any command that may spend credits or require authenticated CLIs.
- Do not copy raw reports, `run.json` bodies, transcripts, stdout, stderr, local paths, prompts, session details, account details, private diagnostics, or private evidence into Core.
- Do not update `os/verification/BENCHMARK_STATUS.md` directly; route all status interpretation and edits through `refresh-benchmark-status`.
- If the checkout is not clean, current `main`, do not produce status-eligible evidence. Offer diagnostic/non-eligible runs only when useful and clearly label them.

## Workflow Phases

1. Inspect the benchmark surface.
   Read `os/verification/BENCHMARKS.json`, `os/playbook/PERSONAL_OVERLAY.md`, and `os/skills/refresh-benchmark-status/SKILL.md`. For each manifest entry, resolve the script path and run its help output, usually `python3 <script> --help`.

2. Check the script contract.
   Treat a script as compatible only when its help exposes the flags needed for the requested mode:
   - status-eligible saved evidence: `--save-report` and `--check-remote-main`;
   - deterministic validation: `--self-test`;
   - safe preview: `--dry-run` when the script can avoid external harness calls;
   - external/model-call harnesses: `--no-dry-run`, plus `--harness all` only when the help advertises that option.

   Report incompatible scripts instead of carrying benchmark-specific command knowledge. Do not infer suite-specific flags or fixture names in this skill.

3. Preflight Git state.
   Before status-eligible saved runs, confirm the checkout is on `main`, clean, and aligned with `origin/main` after fetching when network is available. The scripts' own `--check-remote-main` metadata remains the evidence of remote freshness at run time.

4. Run safe checks first.
   Default to deterministic/local-safe work: run compatible scripts' `--self-test`, then run safe saved reports with `--dry-run --check-remote-main --save-report` when supported. If a script has no safe preview flag, ask before running it.

5. Ask before model-call harnesses.
   If the user explicitly asked for model-call harnesses or all external benchmarks, summarize the commands and ask for confirmation unless the current request clearly approved spending model calls. For approved harness runs, use the compatible script contract, usually `python3 <script> --no-dry-run --check-remote-main --save-report`, adding `--harness all` only when advertised.

6. Refresh status.
   After scripts finish, run or follow `refresh-benchmark-status`. If the user asked for "run benchmarks and refresh status", continue through eligible updates allowed by that skill. If the user only asked to "run benchmarks", state that the benchmark process is not complete until `refresh-benchmark-status` has run, then offer the refresh or run it in proposal/report mode when write authorization is unclear.

## Filing Rules

- Raw reports and run histories stay in the Personal Overlay report directories configured by `os/verification/BENCHMARKS.json`.
- Core benchmark status lives only in `os/verification/BENCHMARK_STATUS.md` and is changed only through `refresh-benchmark-status`.
- Benchmark CLI standardization is deferred to GitHub Issue #33.
- Deterministic refresh-helper work is deferred to GitHub Issue #30.

## Quality Bar

- The run plan comes from the manifest and script help, not benchmark-specific internals.
- Model-call or external harness work is explicitly approved.
- Every saved report path is named in the final report without copying raw/private report contents.
- Incompatible scripts are reported clearly.
- The final response says whether `refresh-benchmark-status` ran, updated Core status, proposed changes, or remains the next step.

## Verification

Before finishing:

1. Confirm `os/verification/BENCHMARKS.json`, `os/playbook/PERSONAL_OVERLAY.md`, and `refresh-benchmark-status` were read.
2. Confirm configured script help was inspected and compatibility was reported.
3. Confirm Git preflight was performed before status-eligible saved runs.
4. Confirm no model-call harness ran without approval.
5. Confirm raw report content was not copied into Core.
6. Confirm `refresh-benchmark-status` ran, was offered, or was explicitly left as the next step.
