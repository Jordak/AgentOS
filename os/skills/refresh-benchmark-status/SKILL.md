---
name: refresh-benchmark-status
description: "Refresh AgentOS Core's public-safe benchmark status snapshot from eligible local Personal Overlay benchmark evidence. Use when the user asks to refresh, update, compare, or inspect Core benchmark status, or asks whether local benchmark runs mean `os/verification/BENCHMARK_STATUS.md` should change."
---

# Refresh Benchmark Status

## Goal

Refresh `os/verification/BENCHMARK_STATUS.md` from eligible local benchmark evidence while preserving the boundary between Core's public-safe current status and private raw run evidence.

This workflow exists because AgentOS benchmarks measure AgentOS Core capabilities. Core should expose enough current benchmark posture for a human or agent to understand whether Core is operating according to spec, without storing raw run reports, generated JSON, transcripts, local paths, session details, prompts, diagnostics, or append-only history in Core.

## Contract

Inputs:

- `os/verification/BENCHMARKS.json`.
- `os/verification/BENCHMARK_STATUS.md`.
- Local saved benchmark reports under the report directories named in `BENCHMARKS.json`, usually `personal/os/verification/<suite>/reports/`.
- The current Git state of the AgentOS checkout.
- User approval before writing Core status when evidence is missing, stale, ineligible, ambiguous, or would require judgment beyond the current public-safe summary.

Output artifact:

- An updated or proposed update to `os/verification/BENCHMARK_STATUS.md`.
- A concise refresh report naming eligible evidence, ineligible evidence, stale status entries, and any entries left unchanged.

Mutability:

- Mixed. Read-only when inspecting evidence or reporting status.
- Local-write when updating `os/verification/BENCHMARK_STATUS.md` after evidence is eligible and the user requested the refresh or approved the proposed update.
- No external-write behavior.

Tools and connectors:

- Local filesystem reads for Core files and Personal Overlay benchmark reports.
- Local `git` for branch, commit, upstream, and dirty-state checks.
- `os/verification/BENCHMARKS.json` for benchmark suite configuration.
- `os/playbook/PERSONAL_OVERLAY.md` for resolving local Personal Overlay report locations from a feature worktree.
- No network or external connectors are needed.

Safety:

- Do not copy raw benchmark reports, `run.json` bodies, transcripts, stdout, stderr, local paths, prompts, session details, account details, private diagnostics, or private evidence into Core.
- Do not compare private raw evidence against curated Core prose. Compare only structured provenance fields such as reviewed Core revision and evidence timestamp.
- Do not mutate Core status from missing, stale, incompatible, dirty-worktree, non-main, or non-fresh-main evidence by default.
- Do not mark a status as `passing` unless eligible evidence was produced from clean, fresh `main` at a committed AgentOS revision.
- Ask before applying a caveated update when evidence is technically present but ambiguous.

## Workflow Phases

1. Inspect policy and targets.
   Read `os/verification/BENCHMARKS.json`, `os/verification/BENCHMARK_STATUS.md`, and `os/playbook/PERSONAL_OVERLAY.md`. Resolve report directories relative to the AgentOS root, using the canonical primary checkout's Personal Overlay when running from a feature worktree.

2. Find local evidence.
   For each benchmark suite, inspect saved `run.json` files under the configured report directory and `run_glob`. Consider only current-schema reports that include Git state metadata.

3. Check evidence eligibility.
   Evidence is eligible only when its Git metadata shows:
   - branch `main`;
   - upstream `origin/main`;
   - clean worktree;
   - no ahead/behind drift from upstream at run time;
   - a committed AgentOS revision.

4. Compare provenance.
   Compare eligible evidence to the matching status entry by `Reviewed Core revision` and `Last reviewed evidence`, not by prose. A later local run against an older commit does not refresh current Core status.

5. Summarize public-safe posture.
   Produce only the minimum public-safe summary needed to explain what kinds of benchmark tasks are passing, failing, unavailable, or unknown. Use the allowed status labels:
   - `passing`;
   - `attention needed`;
   - `not run`;
   - `unknown`.

6. Update or report.
   Update `os/verification/BENCHMARK_STATUS.md` only when the user requested the refresh and evidence is eligible, or after the user approves a proposed update. If evidence is missing, stale, incompatible, dirty, not from fresh `main`, or otherwise ineligible, leave Core unchanged and explain what to rerun.

## Status Rules

- `passing`: eligible evidence exists from clean, fresh `main`; behavioral checks meet the suite's pass criteria; and no caveat changes the reader's interpretation.
- `attention needed`: eligible evidence exists, but behavior failed, degraded, partially passed meaningfully, or has a maintainer-relevant caveat.
- `not run`: no eligible evidence has been reviewed for the suite/harness entry.
- `unknown`: evidence exists but cannot be interpreted confidently, such as malformed metadata, unsupported report version, unclear harness availability, or missing Git-state fields.

Do not use `stale` as a Core status. Report staleness in the refresh report because it depends on current repo state and local evidence.

## Filing Rules

- Core benchmark status lives only in `os/verification/BENCHMARK_STATUS.md`.
- Raw reports and run histories stay in the Personal Overlay report directories configured by `os/verification/BENCHMARKS.json`.
- Deterministic refresh-helper design is deferred to GitHub Issue #30. Do not add a parser/updater script as part of this skill.
- Do not create append-only Core benchmark history.

## Quality Bar

- Every proposed Core status entry uses only public-safe fields: `Status`, `Reviewed Core revision`, `Last reviewed evidence`, `Evidence scope`, `Summary`, and `Caveats`.
- Evidence eligibility is checked before any `passing` or `attention needed` update.
- Missing or incompatible evidence prompts a rerun instead of a Core mutation.
- Summaries describe what kinds of tasks are affected without copying raw evidence.
- The workflow leaves unrelated status entries unchanged.

## Verification

Before finishing:

1. Confirm `os/verification/BENCHMARKS.json` and `os/verification/BENCHMARK_STATUS.md` were read.
2. Confirm local report paths were resolved through the Personal Overlay rule.
3. Confirm each used report had current-schema Git metadata.
4. Confirm no raw report body, run JSON, transcript, stdout, stderr, local path, prompt, session detail, or private diagnostic was copied into Core.
5. Confirm status labels are limited to `passing`, `attention needed`, `not run`, and `unknown`.
6. Run `python3 os/verification/scripts/validate_agentos.py` after skill or status-file changes.
