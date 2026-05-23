# AgentOS Benchmark Status

Status: Core benchmark snapshot v1.

This file is the current public-safe benchmark posture for AgentOS Core. It is a curated status snapshot, not raw evidence, a run log, an append-only history, or a freshness source by itself.

Raw benchmark reports, generated run JSON, transcripts, local paths, session details, prompts, diagnostics, and private run evidence belong outside Core, usually under `personal/os/verification/<suite>/reports/`.

Use `os/skills/refresh-benchmark-status/SKILL.md` to refresh this snapshot from eligible local evidence. Eligible evidence must come from current-schema benchmark reports produced on clean, remote-fresh `main` at a committed AgentOS revision.

Allowed status labels:

- `passing`
- `attention needed`
- `not run`
- `unknown`

Do not use `stale` as a Core status. Staleness is relative to the current checkout and local evidence, so refresh workflows should report it during refresh instead of writing it as the public status.

## Retrieval

### Local Lexical

- Status: `not run`
- Reviewed Core revision: `not reviewed`
- Last reviewed evidence: No eligible evidence reviewed as of `2026-05-22 17:07 PDT`
- Evidence scope: `none`
- Summary: No current-schema clean, remote-fresh main local lexical retrieval evidence has been reviewed for this snapshot.
- Caveats: Run the current retrieval benchmark on clean, remote-fresh `main` before marking this entry as `passing` or `attention needed`.

### Codex

- Status: `not run`
- Reviewed Core revision: `not reviewed`
- Last reviewed evidence: No eligible evidence reviewed as of `2026-05-22 17:07 PDT`
- Evidence scope: `none`
- Summary: No current-schema clean, remote-fresh main Codex retrieval harness evidence has been reviewed for this snapshot.
- Caveats: Run the current retrieval harness benchmark on clean, remote-fresh `main` before marking this entry as `passing` or `attention needed`.

### Claude

- Status: `not run`
- Reviewed Core revision: `not reviewed`
- Last reviewed evidence: No eligible evidence reviewed as of `2026-05-22 17:07 PDT`
- Evidence scope: `none`
- Summary: No current-schema clean, remote-fresh main Claude retrieval harness evidence has been reviewed for this snapshot.
- Caveats: Run the current retrieval harness benchmark on clean, remote-fresh `main` before marking this entry as `passing` or `attention needed`.

## Playbook Activation

### Codex

- Status: `not run`
- Reviewed Core revision: `not reviewed`
- Last reviewed evidence: No eligible evidence reviewed as of `2026-05-22 17:07 PDT`
- Evidence scope: `none`
- Summary: No current-schema clean, remote-fresh main Codex playbook-activation evidence has been reviewed for this snapshot.
- Caveats: Run the current playbook-activation benchmark on clean, remote-fresh `main` before marking this entry as `passing` or `attention needed`.
