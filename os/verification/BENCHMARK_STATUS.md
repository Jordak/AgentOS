# AgentOS Benchmark Status

Status: Core benchmark snapshot v1.

This file is the current public-safe benchmark posture for AgentOS Core. It is a curated status snapshot, not raw evidence, a run log, an append-only history, or a freshness source by itself.

Raw benchmark reports, generated run JSON, transcripts, local paths, session details, prompts, diagnostics, and private run evidence belong outside Core, usually under `personal/os/verification/<suite>/reports/`.

Use `os/skills/refresh-benchmark-status/SKILL.md` to refresh this snapshot from eligible local evidence. Eligible evidence must come from current-schema benchmark reports produced on clean, remote-fresh `main` at a committed AgentOS revision.

Only suites marked with `weekly_review.check_freshness: true` in `os/verification/BENCHMARKS.json` are current status-refresh freshness targets. Older retrieval and playbook-activation entries remain historical benchmark posture until they are explicitly revived or replaced. This does not delete those suites or make them unrunnable; it narrows which benchmark evidence is allowed to refresh current Core status.

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

## Playbook Activation

### Codex

- Status: `passing`
- Reviewed Core revision: `36c707b40428033510432c921feeec5e4c9827df`
- Last reviewed evidence: `2026-05-22 20:35 PDT`
- Evidence scope: `playbook-activation Codex harness; 10 fixtures; gpt-5.5 xhigh`
- Summary: Codex accessed the required guidance for all 10 playbook-activation fixtures, covering programming CLI, artifact format selection, GitHub workflow, implementation readiness, propagation review, weekly review, portability, Markdown style, and skill contract upgrade routing.
- Caveats: Claude is not currently a configured playbook-activation harness, so there is no Claude playbook-activation entry in this snapshot.

## Guidance Eval

### Codex

- Status: `not run`
- Reviewed Core revision: `not reviewed`
- Last reviewed evidence: `none`
- Evidence scope: `guidance-eval Codex harness; judge-assisted AgentOS guidance scenarios`
- Summary: No status-eligible Guidance Eval evidence has been reviewed yet.
- Caveats: This entry is initialized with the new `guidance-eval` suite and should be refreshed only from eligible saved evidence produced on clean, remote-fresh `main`.
