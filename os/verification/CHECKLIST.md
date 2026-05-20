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
7. For AgentOS maintenance changes, run the deterministic local validator: `python3 os/verification/scripts/validate_agentos.py`.

## AgentOS Maintenance Checks

For AgentOS maintenance validation, use:

`python3 os/verification/scripts/validate_agentos.py`

This includes structural retrieval fixtures under `os/verification/retrieval/`. They check route evidence, not final model prose.

Safe smoke fixture:

`python3 os/verification/scripts/validate_agentos.py --self-test`

## High-Risk Work

For legal, medical, financial, security, account, permissions, external messages, or public publishing work:

- Verify current sources.
- Ask before taking external action.
- Prefer drafts and review steps.
