# Verification Checklist

Status: first real pass.

Use this before trusting agent output.

## General Checks

1. Does the output answer the actual request?
2. Are assumptions stated?
3. Are facts, dates, names, and links verified when they matter?
4. Is any private or sensitive information handled safely?
5. Is there a clear next action?
6. If fixing a local failure, was the root cause diagnosed before adding app-level workarounds? Environment and configuration failures should usually be fixed in the environment or configuration.
7. For AgentOS maintenance changes, run the deterministic local validator: `scripts/run-validator`.

## AgentOS Maintenance Checks

For AgentOS maintenance validation, use:

`scripts/run-validator`

This includes structural retrieval fixtures under `os/verification/retrieval/`. They check route evidence, not final model prose.

For Core/Personal Overlay guidance, push-safety, and stale installed-instruction checks, also run:

`scripts/audit_agentos_leak_paths.sh`

This audit checks `os/`, `personal/os/`, installed skill adapters, and Codex automation mirrors for suspicious Core generated-output paths, live history/queue/report routing, raw Git persistence instructions, and private live-agent adapters that still point into Core.

Safe smoke fixture:

`scripts/run-validator --self-test`

## High-Risk Work

For legal, medical, financial, security, account, permissions, external messages, or public publishing work:

- Verify current sources.
- Ask before taking external action.
- Prefer drafts and review steps.
