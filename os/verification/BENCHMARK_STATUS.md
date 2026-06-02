# AgentOS Benchmark Status

Status: Core benchmark snapshot v1.

This file is the current public-safe benchmark posture for AgentOS Core. It is a curated status snapshot, not raw evidence, a run log, an append-only history, or a freshness source by itself.

Raw benchmark reports, generated run JSON, transcripts, local paths, session details, prompts, diagnostics, and private run evidence belong outside Core, usually under `personal/os/verification/<suite>/reports/`.

Use `os/skills/refresh-benchmark-status/SKILL.md` to refresh this snapshot from eligible local evidence. Eligible evidence must come from current-schema benchmark reports produced on clean, remote-fresh `main` at a committed AgentOS revision.

Only suites marked with `weekly_review.check_freshness: true` in `os/verification/BENCHMARKS.json` are current status-refresh freshness targets. The older retrieval entries remain historical benchmark posture until they are explicitly revived, replaced, or removed. This does not delete retrieval or make it unrunnable; it narrows which benchmark evidence is allowed to refresh current Core status.

Allowed status labels:

- `passing`
- `attention needed`
- `not run`
- `unknown`

Do not use `stale` as a Core status. Staleness is relative to the current checkout and local evidence, so refresh workflows should report it during refresh instead of writing it as the public status.

## Retrieval

### Local Lexical

- Status: `attention needed`
- Reviewed Core revision: `36c707b40428033510432c921feeec5e4c9827df`
- Last reviewed evidence: `2026-05-22 19:33 PDT`
- Evidence scope: `retrieval local lexical suite; 10 lookup questions; section-index and keyword hit@5`
- Summary: Section-index retrieval found an expected canonical path within the top 5 for all 10 lookup tasks. The simpler keyword baseline found expected paths for 8 of 10 tasks.
- Caveats: Keyword search missed two lookup categories even though section-index retrieval succeeded for both. No model-call harness evidence is included in this local lexical entry.

### Codex

- Status: `attention needed`
- Reviewed Core revision: `36c707b40428033510432c921feeec5e4c9827df`
- Last reviewed evidence: `2026-05-22 19:45 PDT`
- Evidence scope: `retrieval Codex harness; 10 lookup questions; gpt-5.5 xhigh`
- Summary: Codex produced graded responses for all 10 retrieval tasks and passed 5. It succeeded on context projects, skills contract, agent templates, Personal Overlay routing, and benchmark status lookup.
- Caveats: Five tasks failed, mostly because evidence quotes did not support the cited source strongly enough or the expected source path was missed. The failing categories included identity defaults, memory/current state, publication safety, mapped projects, and run-benchmarks routing.

### Claude

- Status: `attention needed`
- Reviewed Core revision: `36c707b40428033510432c921feeec5e4c9827df`
- Last reviewed evidence: `2026-05-22 19:45 PDT`
- Evidence scope: `retrieval Claude harness; 10 lookup questions; gpt-5.5 xhigh`
- Summary: Claude produced graded responses for all 10 retrieval tasks but passed only the context-projects lookup.
- Caveats: Nine tasks failed primarily on schema-shape, source-path, and evidence-support requirements. This indicates a harness/response-format alignment problem as much as a retrieval problem.

## Guidance Eval

### Codex

- Status: `passing`
- Reviewed Core revision: `d277d122dd043f63deb490b96394422a40de0798`
- Last reviewed evidence: `2026-06-02 08:48 PDT`
- Evidence scope: `guidance-eval Codex harness; 14 default guidance fixtures; gpt-5.5 low; judge gpt-5.5 low`
- Summary: Codex produced judged responses for all 14 default Guidance Eval scenarios and passed every behavioral check. The covered scenarios include GitHub CLI sandbox auth, implementation readiness, artifact format routing, Personal Overlay discovery, generated preference propagation, public project issue routing, programming CLI contracts, Markdown style, portability, review workflows, weekly-review storage, and skill-contract upgrade routing.
- Caveats: No behavioral failures, fixture-stale cases, or needs-user-judgment cases were reported. This status uses a full default, status-eligible run from clean remote-fresh `main`; diagnostic non-default fixture or judge-protocol runs remain useful for investigation but are not status evidence.
