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

## Guidance

### Codex

- Status: `passing`
- Reviewed Core revision: `d277d122dd043f63deb490b96394422a40de0798`
- Last reviewed evidence: `2026-06-02 08:48 PDT`
- Evidence scope: `guidance Codex harness; 14 default guidance fixtures; gpt-5.5 low; judge gpt-5.5 low`
- Summary: Codex produced judged responses for all 14 default Guidance scenarios and passed every behavioral check. The covered scenarios include GitHub CLI sandbox auth, implementation readiness, artifact format routing, Personal Overlay discovery, generated preference propagation, public project issue routing, programming CLI contracts, Markdown style, portability, review workflows, weekly-review storage, and skill-contract upgrade routing.
- Caveats: No behavioral failures, fixture-stale cases, or needs-user-judgment cases were reported. This status uses a full default, status-eligible run from clean remote-fresh `main`; diagnostic non-default fixture or judge-protocol runs remain useful for investigation but are not status evidence.
