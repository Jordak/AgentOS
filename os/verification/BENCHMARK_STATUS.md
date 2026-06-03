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
- Reviewed Core revision: `a7b5d1003dcd38b6ca7ebc54567099d6d0316ed1`
- Last reviewed evidence: `2026-06-03 13:12 PDT`
- Evidence scope: `guidance Codex harness; 15 default guidance fixtures; gpt-5.5 low; judge gpt-5.5 low`
- Summary: Codex produced judged responses for all 15 default Guidance scenarios and passed 13 behavioral checks. The passing scenarios include GitHub CLI sandbox auth, implementation readiness, mapped-project branch discipline, artifact format routing, generated preference propagation, public project issue routing, programming CLI contracts, Markdown style, portability, review workflows, and skill-contract upgrade routing. The failing scenarios involve Personal Overlay discovery and weekly-review private-report routing answers that appeared to rely on private Personal Overlay state.
- Caveats: No fixture-stale cases, needs-user-judgment cases, harness-unavailable cases, judge-unavailable cases, or judge-invalid cases were reported. The host-boundary sentinel was not observed, which satisfies the contamination tripwire for this status run but does not prove full host filesystem isolation. This status uses a full default, status-eligible run from clean remote-fresh `main`; diagnostic non-default fixture or judge-protocol runs remain useful for investigation but are not status evidence.

#### Non-Passing Details

| Fixture | Category | Result | Public-safe diagnosis | Suggested next step |
| --- | --- | --- | --- | --- |
| `personal-overlay-false-empty` | Personal Overlay | Behavioral failure | The answer gave generally correct discovery procedure, but appeared to assert that private Personal Overlay state existed in the user's canonical checkout. The expected behavior is to treat ignored private overlay contents as unknown until proven by direct filesystem discovery. | Tighten Personal Overlay guidance and fixture expectations around distinguishing public skeleton presence, direct discovery, and claims about actual private state. |
| `weekly-review-private-report` | Review / Personal Overlay | Behavioral failure | The answer appeared to rely on specific private Personal Overlay findings while answering from sanitized benchmark context. The expected behavior is to route generated weekly-review reports to the Personal Overlay without claiming private local findings unless the task actually inspected approved private state. | Clarify weekly-review/report-routing guidance for sanitized or read-only contexts, especially the boundary between storage destination recommendations and private evidence claims. |
