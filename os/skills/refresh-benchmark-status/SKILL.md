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
- A concise refresh report naming eligible evidence, ineligible evidence, stale status entries, every public-safe non-passing detail included in Core status, and any entries left unchanged.

Mutability:

- Mixed. Read-only when inspecting evidence or reporting status.
- Local-write when updating `os/verification/BENCHMARK_STATUS.md` after evidence is eligible and the user requested the refresh or approved the proposed update.
- No external-write behavior.

Tools and connectors:

- Local filesystem reads for Core files and Personal Overlay benchmark reports.
- Local `git` for branch, commit, upstream, remote `origin/main`, and dirty-state checks.
- `os/verification/scripts/refresh_benchmark_status.py` for deterministic evidence discovery, eligibility checks, freshness comparison, public-safe fact extraction, and private result locators.
- `os/verification/scripts/apply_benchmark_status_candidate.py` for approved write-side application of public-safe candidate facts to `os/verification/BENCHMARK_STATUS.md`.
- `os/verification/BENCHMARKS.json` for benchmark suite configuration.
- `os/playbook/PERSONAL_OVERLAY.md` for resolving local Personal Overlay report locations from a feature worktree.
- No external connectors are needed. Use saved remote-freshness metadata from benchmark reports rather than making network calls unless the user asks to rerun benchmarks.

Safety:

- Do not copy raw benchmark reports, `run.json` bodies, transcripts, stdout, stderr, local paths, prompts, session details, account details, private diagnostics, or private evidence into Core.
- Do not copy judge rationales verbatim into Core. Translate non-passing results into short public-safe diagnostic summaries and next steps.
- Do not compare private raw evidence against curated Core prose. Compare only structured provenance fields such as report mode, suite sections, reviewed Core revision, Git metadata, and evidence timestamp.
- Do not mutate Core status from missing, stale, incompatible, dirty-worktree, non-main, or non-fresh-main evidence by default.
- Do not mark a status as `passing` unless eligible evidence was produced from clean, remote-fresh `main` at a committed AgentOS revision.
- Do not treat local upstream parity alone as proof of fresh `main`; eligible evidence must prove remote `origin/main` freshness or remain ineligible.
- Ask before applying a caveated update when evidence is technically present but ambiguous.

## Workflow Phases

1. Inspect policy and targets.
   Read `os/verification/BENCHMARKS.json`, `os/verification/BENCHMARK_STATUS.md`, and `os/playbook/PERSONAL_OVERLAY.md`. Resolve report directories relative to the AgentOS root, using the canonical primary checkout's Personal Overlay when running from a feature worktree.

   Treat only manifest entries with `weekly_review.check_freshness: true` as current status-refresh freshness targets. Entries with `check_freshness: false` are diagnostic or historical suites; they can remain runnable, but missing or stale evidence from those suites must not block a benchmark status refresh. Reducing a legacy suite's status-refresh surface is different from deleting or disabling that suite.

2. Generate deterministic candidate facts.
   Run `python3 os/verification/scripts/refresh_benchmark_status.py`, passing `--personal-root <canonical AgentOS checkout>` when working from a feature worktree whose ignored `personal/os/` skeleton is not authoritative. Use `--report <path>` only when the user asks whether one explicit saved report counts.

   The helper is read-only and JSON-only. It never writes `os/verification/BENCHMARK_STATUS.md`, never emits Markdown patches, and never returns raw HUT output, judge rationales, prompts, stdout, stderr, transcripts, raw report bodies, local absolute paths, or private diagnostics in `public_safe`.

   Treat the helper's `public_safe` object as deterministic evidence facts. Treat `private_locators` as non-Core-safe pointers for targeted private inspection only; do not copy them into Core.

   Helper exit codes distinguish outcomes:
   - `0`: candidate generated for all current status-refresh targets.
   - `1`: no eligible or fresh-enough evidence found, or evidence is older than current status.
   - `2`: invalid manifest/config/schema/unsupported target.
   - `3`: public-safe output invariant failed.

3. Find local evidence manually when needed.
   For each current status-refresh freshness target, inspect saved `run.json` files under the configured report directory and `run_glob`. Consider only current-schema reports that include Git state metadata.

   If eligible evidence is missing and the user asks to rerun benchmarks, run them from a clean `main` checkout with `--check-remote-main` and `--save-report`. Ordinary local, dry-run, transcript, or diagnostic reports may avoid remote network checks; those reports remain ineligible when remote freshness is unknown.

4. Check evidence eligibility.
   Evidence is eligible only when the report mode and suite section represent status-counting benchmark evidence for the target status entry, and its Git metadata shows:
   - branch `main`;
   - upstream `origin/main`;
   - clean worktree;
   - no ahead/behind drift from the local upstream tracking ref at run time;
   - remote `origin/main` was checked and matched the reviewed commit at run time;
   - a committed AgentOS revision.

   Treat dry-run plans, saved-response regrades, transcript regrades, reports with `status_eligible: false`, and reports without remote-freshness proof as ineligible. They may be useful diagnostics, but they are not enough to mark Core status as `passing` or `attention needed`.

   For Guidance reports, `summary.status_eligible` includes fixture-scope checks for the default canonical fixture file, the full default fixture set, and no selected `--fixture-id` subset. It also includes judge-protocol checks for default judge prompt, default judge schema, and default judge batch size, plus a host-boundary sentinel tripwire check that rejects runs where the non-private sentinel marker appeared in captured HUT output. A non-observed sentinel does not prove full host filesystem isolation; it is only a contamination tripwire. Raw fixture, judge-protocol, and host-boundary provenance remain report metadata for auditability. `fixture_stale` is allowed in eligible evidence and should be reported separately from behavioral pass/fail counts. `fixture_stale` means the fixture expectation needs review against the current guidance source; it does not by itself make the run ineligible. `needs_user_judgment` remains ineligible until resolved by a later workflow.

   Freshness thresholds use status-counting totals, not only behavioral pass/fail totals. For Guidance, derive the status-counting total from `behavioral_total + fixture_stale`; do not rely on a saved derived total in the report.

5. Compare provenance.
   Compare eligible evidence to the matching status entry by `Reviewed Core revision` and `Last reviewed evidence`, not by prose. A later local run against an older commit does not refresh current Core status.

6. Summarize public-safe posture.
   Produce only the minimum public-safe summary needed to explain what kinds of benchmark tasks are passing, failing, unavailable, or unknown. Use the allowed status labels:
   - `passing`;
   - `attention needed`;
   - `not run`;
   - `unknown`.

   For eligible evidence with any non-passing status-counting result, include a `#### Non-Passing Details` section in the matching status entry. The section should use a compact Markdown table with these columns:
   - `Fixture`: the fixture or scenario identifier, or `n/a` when the evidence is suite-level rather than fixture-level;
   - `Category`: the public-safe benchmark category or suite area;
   - `Result`: one of `Behavioral failure`, `Fixture stale`, `Needs user judgment`, `Harness unavailable`, `Harness error`, `Judge unavailable`, `Judge error`, `Judge invalid`, or another concise public-safe result class present in the structured evidence;
   - `Public-safe diagnosis`: a curated explanation of what went wrong, stated without raw transcript text, stdout, stderr, prompts, local paths, private facts, or private diagnostics;
   - `Suggested next step`: the next investigation or repair action a maintainer can take without needing raw evidence in Core.

   Include one row for every behavioral failure, fixture-stale result, needs-user-judgment result, harness unavailable/error result, and judge unavailable/error/invalid result that affects the reviewed status evidence. It is acceptable to omit the section when the entry is `passing` and there are no non-passing details. When the only issue is suite-level ambiguity or malformed metadata, use `n/a` for the fixture and make the diagnosis explain the suite-level blocker.

   For Guidance reports, derive rows from structured result fields where possible:
   - behavioral failures from graded results whose verdict is not `pass`;
   - fixture-stale rows from graded results marked stale;
   - needs-user-judgment rows from results requiring unresolved judgment;
   - harness or judge availability/error rows from result status and summary counts.

   Fixture identifiers, categories, verdict classes, staleness labels, and availability/error classes are public-safe structured provenance. Judge rationales, HUT answers, prompts, command shapes, stdout, stderr, local paths, and raw report excerpts are not public-safe Core content.

7. Update or report.
   Update `os/verification/BENCHMARK_STATUS.md` only when the user requested the refresh and evidence is eligible, or after the user approves a proposed update. Apply approved updates through `python3 os/verification/scripts/apply_benchmark_status_candidate.py <refresh-json>` so the write path consumes only `public_safe.targets` and keeps `private_locators` out of Core. If evidence is missing, stale, incompatible, dirty, not from fresh `main`, or otherwise ineligible, leave Core unchanged and explain what to rerun.

## Status Rules

- `passing`: eligible evidence exists from clean, remote-fresh `main`; behavioral checks meet the suite's pass criteria; and no caveat changes the reader's interpretation. Guidance `fixture_stale` counts are a reported fixture-maintenance signal, not a harness behavior failure.
- `attention needed`: eligible evidence exists, but behavior failed, degraded, partially passed meaningfully, or has a maintainer-relevant caveat.
- `not run`: no eligible evidence has been reviewed for the suite/harness entry.
- `unknown`: evidence exists but cannot be interpreted confidently, such as malformed metadata, unsupported report version, unclear harness availability, or missing Git-state fields.

Do not use `stale` as a Core status. Report staleness in the refresh report because it depends on current repo state and local evidence.

## Filing Rules

- Core benchmark status lives only in `os/verification/BENCHMARK_STATUS.md`.
- Raw reports and run histories stay in the Personal Overlay report directories configured by `os/verification/BENCHMARKS.json`.
- Deterministic refresh-helper behavior lives in `os/verification/scripts/refresh_benchmark_status.py`. The helper emits JSON candidate facts and private locators only; it is not a Core status writer.
- Approved Core status writes use `os/verification/scripts/apply_benchmark_status_candidate.py`, which consumes only public-safe candidate facts and must not read or render private locators.
- Do not create append-only Core benchmark history.

## Quality Bar

- Every proposed Core status entry uses only public-safe fields: `Status`, `Reviewed Core revision`, `Last reviewed evidence`, `Evidence scope`, `Summary`, `Caveats`, and optional `Non-Passing Details`.
- Every non-passing status-counting result in eligible evidence is represented in `Non-Passing Details` unless the entry is left unchanged with an explicit reason.
- Evidence eligibility is checked before any `passing` or `attention needed` update.
- Missing or incompatible evidence prompts a rerun instead of a Core mutation.
- Summaries describe what kinds of tasks are affected without copying raw evidence.
- Non-passing detail rows are diagnostic enough to guide investigation without opening the raw report first.
- The workflow leaves unrelated status entries unchanged.
- Approved status-file writes are applied through the write-side applicator, not by hand-editing raw reports or private locators into Core.

## Verification

Before finishing:

1. Confirm `os/verification/BENCHMARKS.json` and `os/verification/BENCHMARK_STATUS.md` were read.
2. Confirm local report paths were resolved through the Personal Overlay rule.
3. Confirm `os/verification/scripts/refresh_benchmark_status.py` ran or explain why manual inspection was needed instead.
4. Confirm each used report had current-schema Git metadata.
5. Confirm no raw report body, run JSON, transcript, stdout, stderr, local path, prompt, session detail, or private diagnostic was copied into Core.
6. Confirm each non-passing status-counting result in eligible evidence has a public-safe detail row or that the status entry was intentionally left unchanged.
7. Confirm status labels are limited to `passing`, `attention needed`, `not run`, and `unknown`.
8. Run `python3 os/verification/scripts/refresh_benchmark_status.py --self-test` after refresh-helper changes.
9. Run `python3 os/verification/scripts/apply_benchmark_status_candidate.py --self-test` after status-applicator changes.
10. Run `scripts/run-validator` after helper, skill, or status-file changes.
