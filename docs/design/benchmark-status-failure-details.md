# Benchmark Status Failure Details

Design readiness: ready to implement

## Problem

`os/verification/BENCHMARK_STATUS.md` currently records the current public-safe benchmark posture, but non-passing evidence is too compressed to support later diagnosis. A future maintainer can see that a suite needs attention, but cannot quickly identify which fixture failed, what kind of failure it was, or what public-safe next step would help.

## Current Context

Raw benchmark reports and run JSON belong in the Personal Overlay. Core must not store transcripts, stdout, stderr, local paths, prompts, session details, account details, private diagnostics, or private evidence. The status file is still the right Core surface for a curated current snapshot.

## Desired Behavior

Core benchmark status entries should include compact public-safe diagnostic detail for every non-passing status-counting result:

- behavioral failures;
- fixture-stale results;
- needs-user-judgment results;
- harness or judge unavailable/error results when those are part of the reviewed evidence.

Each detail should identify the fixture and category, classify the result, summarize the public-safe diagnosis, and name a next investigation step. It must not copy raw report bodies or private evidence into Core.

## Chosen Design

Add a diagnostic detail section to `BENCHMARK_STATUS.md` entries. Use a small Markdown table under a heading such as `#### Non-Passing Details` so the status remains scan-friendly and diffable.

Update `os/skills/refresh-benchmark-status/SKILL.md` so future refreshes require those rows for eligible non-passing evidence and describe the allowed fields. The skill remains the authority for translating Personal Overlay report evidence into public-safe Core status.

## Alternatives Considered

One alternative was to keep `BENCHMARK_STATUS.md` short and require maintainers to open the raw Personal Overlay report. That preserves maximum privacy but makes Core status too weak for handoff and review.

Another alternative was to copy judge rationales or run snippets into Core. That would be more diagnostic, but it risks importing raw report content, local paths, prompts, or private context. The chosen design keeps only curated summaries.

## Non-Goals

- Do not add a deterministic parser or updater script in this change.
- Do not create append-only Core benchmark history.
- Do not copy raw report JSON, transcripts, stdout, stderr, prompts, local paths, session details, or private evidence into Core.
- Do not change benchmark pass/fail criteria.

## Acceptance Criteria

- `BENCHMARK_STATUS.md` includes fixture-level public-safe details for the current Guidance failures.
- `refresh-benchmark-status` requires public-safe details for every non-passing result in eligible evidence.
- The allowed status labels remain `passing`, `attention needed`, `not run`, and `unknown`.
- Raw report evidence remains in the Personal Overlay.
- `scripts/run-validator` passes.

## Validation Plan

- Review the status diff to confirm it contains only curated public-safe details.
- Run `scripts/run-validator`.
- Use a protected feature branch and PR for the Core change.

## Open Questions

None for this implementation scope.
