# Issue 90 Guidance HUT Isolation

Design readiness: ready to implement

## Problem

Guidance builds a sanitized temporary AgentOS copy for the harness under test, but issue #90 showed that a nested HUT may still be able to read host filesystem paths outside that sanitized workspace when the surrounding runtime permits it. A diagnostic run reportedly crossed into the host Personal Overlay, while a later status-eligible run passed without doing so.

Guidance should preserve trust in status evidence without claiming a broad sandbox guarantee it does not actually provide.

## Chosen Design

Add a runner-level host-boundary sentinel as a contamination tripwire, not as proof of full isolation.

For real runs, Guidance should create a temporary host-only sentinel outside the HUT project and outside the sanitized AgentOS copy. The sentinel content must be a random, non-private marker. Guidance should inspect HUT outputs for that marker and mark the run status-ineligible when the marker is observed.

The default Guidance fixtures should not guide the HUT toward the sentinel. The sentinel is benchmark instrumentation and eligibility metadata, not an ordinary guidance scenario. The existing judge rule still fails visible reliance on private Personal Overlay files in fixture answers.

## Non-Goals

- No broad OS/container sandbox architecture.
- No claim that a clean sentinel result proves the HUT cannot access host paths.
- No real Personal Overlay reads, copies, or private markers in the sentinel.
- No default fixture that intentionally directs the HUT to probe the sentinel.
- No Codex-specific eligibility semantics beyond using the existing HUT command path.

## Acceptance Criteria

- Saved Guidance reports include host-boundary metadata that records the sentinel tripwire result without exposing private data.
- `summary.status_eligible` is false when the sentinel marker appears in HUT output, with a clear reason such as `hut_host_boundary_sentinel_observed`.
- Sentinel absence is documented as a non-observed tripwire, not proof of isolation.
- The default fixture set remains realistic and does not point at the sentinel.
- Self-tests cover observed and non-observed sentinel outcomes.

## Validation Plan

- Run `python3 os/verification/guidance/scripts/benchmark_guidance.py --self-test`.
- Run `python3 os/verification/guidance/scripts/benchmark_guidance.py --dry-run`.
- Run the relevant validator if available.

## Deferred Follow-Ups

- Future diagnostic-only probes may intentionally test host path behavior, but they should remain status-ineligible and separate from the default Guidance fixture set.
- If future evidence requires stronger guarantees, revisit a narrowly scoped sandbox strategy as a separate design.
