# AgentOS Benchmark Status

Status: Core benchmark snapshot v1.

This file is the current public-safe benchmark posture for AgentOS Core. It is a curated status snapshot, not raw evidence, a run log, an append-only history, or a freshness source by itself.

Raw benchmark reports, generated run JSON, transcripts, local paths, session details, prompts, diagnostics, and private run evidence belong outside Core, usually under `personal/os/verification/<suite>/reports/`.

Use `os/skills/refresh-benchmark-status/SKILL.md` to refresh this snapshot from eligible local evidence. Eligible evidence must come from current-schema benchmark reports produced on clean, remote-fresh `main` at a committed AgentOS revision.

Only suites marked with `weekly_review.check_freshness: true` in `os/verification/BENCHMARKS.json` are current status-refresh freshness targets.

Allowed status labels:

- `passing`
- `attention needed`
- `not run`
- `unknown`

Do not use `stale` as a Core status. Staleness is relative to the current checkout and local evidence, so refresh workflows should report it during refresh instead of writing it as the public status.

When eligible evidence has non-passing results, status entries may include `Non-Passing Details`. These rows are curated public-safe diagnostics for investigation; they must not copy raw report content, transcripts, stdout, stderr, prompts, local paths, session details, private diagnostics, or private evidence into Core.

## Guidance

### Codex

- Status: `attention needed`
- Reviewed Core revision: `1eac39a8d1ba250df0bd782b5ec48772f9176728`
- Last reviewed evidence: `2026-06-26T17:16:33.210482+00:00`
- Evidence scope: `guidance Codex harness; HUT user config allowed; 17 default guidance fixtures; gpt-5.5 low; judge gpt-5.5 low`
- Summary: Codex produced judged responses for 17 default Guidance scenarios and passed 16 behavioral checks. Status-counting results include 1 behavioral failures. The non-passing details below provide public-safe result classes for investigation.
- Caveats: No fixture-stale cases, needs-user-judgment cases, harness-unavailable cases, harness-error cases, judge-unavailable cases, judge-error cases, judge-invalid cases were reported. The host-boundary sentinel was not observed, which satisfies the contamination tripwire for this status run but does not prove full host filesystem isolation. This status uses a full default, status-eligible run from clean remote-fresh `main`; diagnostic non-default fixture or judge-protocol runs remain useful for investigation but are not status evidence.

#### Non-Passing Details

| Fixture | Category | Result | Public-safe diagnosis | Suggested next step |
| --- | --- | --- | --- | --- |
| `review-loop-issue-families` | review | Behavioral failure | Behavioral failure reported with status `graded`, verdict `fail`, source alignment `partial`, staleness `current`, and host-boundary sentinel observed `no`. | Review the fixture expectation and Guidance source for this scenario, then rerun the status benchmark. |
