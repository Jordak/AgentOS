# Issue 13 AgentOS Doctor Thin Boundary

Design readiness: ready to implement

## Problem

PR #17 proved many setup-health edge cases, but the Doctor helper grew into a large judgment-heavy script. That makes it harder for a cautious person to audit before running on a work computer.

## Chosen Design

Use this boundary:

**Scripts gather deterministic facts. Markdown skills interpret those facts.**

`scripts/agentos_doctor.py` should be a thin read-only helper. It may discover/report roots, confirm required Core entry files, run helper commands in audit/check mode, count automation locations, print bounded helper output, and return conservative WARN/FAIL when evidence is missing, unreadable, malformed, or ambiguous.

`os/skills/run-agentos-doctor/SKILL.md` owns fuzzy judgment: starter-file interpretation from getting-started guidance, automation lifecycle interpretation, deciding whether prose mentions are meaningful, comparing Personal Overlay notes with Codex metadata, recommending remediation from ambiguous local state, and asking before writes or current-machine changes.

## Non-Goals

- No install, sync, remediation, delete, or write behavior in the Doctor helper.
- No custom Markdown/TOML-ish automation lifecycle parser in the Doctor helper.
- No deterministic PASS for automation activation state from prose or local metadata.
- No broad standalone diagnosis when agent interpretation is needed.
- No attempt to preserve all edge-case tests from the earlier large implementation.

## Acceptance Criteria

- The Doctor helper is small enough to audit directly and remains obviously read-only.
- The helper runs `install_global_agent_instructions.py --check` only and reports command/output/exit status without applying remediation.
- The Doctor helper does not run or parse mirror-skills; the Run AgentOS Doctor skill delegates mirror diagnosis to the mirror-skills audit-only workflow.
- The Doctor helper does not parse getting-started Markdown or judge Personal Overlay starter completeness; the skill handles starter interpretation without quoting private file contents.
- Feature-worktree checks keep Core evidence tied to the audited checkout and Personal Overlay evidence tied to the primary checkout.
- Automation checks report registry/file/directory presence, counts, and locations only.
- Ambiguous or missing evidence produces WARN/FAIL rather than false PASS.
- The Run AgentOS Doctor skill explains how agents interpret ambiguous facts and ask before writes.

## Validation Plan

- Run `python3 scripts/agentos_doctor.py --self-test`.
- Run Python compilation for the Doctor helper and test module.
- Run AgentOS validator and validator self-test.
- Run skill validation for `os/skills/run-agentos-doctor`.
- Smoke-run Doctor against the PR worktree and canonical primary checkout, verifying it exits read-only and does not print private file contents.

## Deferred Follow-Ups

- Broader mirror-skills hardening can be reviewed separately if it remains larger than Doctor needs.
- A future validator may check that Doctor-like scripts stay within a read-only/no-remediation contract.
