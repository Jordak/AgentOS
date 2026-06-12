# PR Readiness Evidence Tripwire

Design readiness: ready to implement

## Context

The AgentOS Doctor work initially moved in the wrong implementation direction before the design boundary was fully agreed. Review-loop later caught and corrected the shape, but that was too late: the first implementation should not be where design consensus is discovered.

AgentOS already has an implementation-readiness playbook and skill, and the resolver points feature-sized implementation requests at them. That guidance is useful when an agent remembers to apply it, but it did not leave a visible PR-surface tripwire. A feature PR could still be opened with no visible readiness evidence or verdict in the PR body, and review-loop could spend time reviewing implementation symptoms before pausing on missing design consensus.

## Decision

AgentOS feature PRs should expose readiness evidence and a readiness verdict in the PR body.

The visible fields are:

```md
Readiness evidence: <GitHub issue, PRD, ADR, local design doc, or gate-skip reason>
Readiness verdict: Ready to Implement
```

For issue-driven work, prefer a GitHub issue as the readiness evidence. The issue can contain the agreed design directly or link to a larger PRD, ADR, or local design doc. Create a separate design document only when the design is too large, architectural, private, or not naturally issue-shaped.

`Readiness verdict: Gate Skipped` is allowed for exempt work or an intentional bypass, but the reason belongs in `Readiness evidence:`. A `ready-for-agent` label, confident prompt, branch name, or PR existence is not a substitute for readiness evidence.

The CI check should remain shallow. It verifies that PR bodies contain the fields and that the readiness verdict is one of the allowed visible states. It must not parse design prose or judge whether the design is good. Humans and agents still apply `os/playbook/IMPLEMENT_FEATURES.md` and `os/skills/ensure-implementation-readiness/SKILL.md`.

Review-loop should treat readiness as a check-only preflight invariant. Before spawning reviewers for feature-sized PRs, it should invoke or follow `ensure-implementation-readiness` in check-only mode and proceed only when that check returns `Ready to Implement` or `Gate Skipped`; if it returns `Needs Design Consensus`, review-loop should return `blocked` before spawning reviewers with the missing evidence recorded. The first review panel should compare the implementation shape against the durable design source so early design drift is surfaced as design risk, not only as isolated code findings.

## Alternatives Considered

Requiring every feature to start with a separate design document was rejected because it would pollute the project with stale planning artifacts. GitHub issues are a better default for issue-driven work.

Building a semantic validator for design quality was rejected because scripts would start judging fuzzy prose, recreating the same design creep this decision is meant to prevent.

Detecting feature-sized PRs from changed paths in CI was rejected as brittle. It would push policy judgment into a shell check and create edge cases around documentation-only, mechanical, and follow-up PRs.

Adding a new skill was rejected because the existing implementation-readiness skill and playbook already own the gate. The missing piece was visibility and enforcement at the PR surface.

## Consequences

PR bodies become slightly more structured, and small exempt changes may need an explicit gate-skip line. That is acceptable because the field can be short, such as `Readiness evidence: Gate skipped - typo fix`.

The check can produce false WARN-style friction when a PR omitted the fields even though the design was discussed elsewhere. That friction is intentional: the durable evidence should be visible to future agents and reviewers.

The check can still produce false confidence if the fields are present but the evidence is weak. That is why the check stays shallow and the playbook/skill remain responsible for judgment.

## Acceptance Criteria

- `IMPLEMENT_FEATURES.md` says no feature implementation commit should happen before `Ready to Implement` or an explicit `Gate Skipped` verdict.
- `ensure-implementation-readiness` says that chat-only consensus must be promoted into a durable source before implementation.
- GitHub workflow guidance and the PR template use `Readiness evidence:` and `Readiness verdict:`.
- CI fails pull requests whose body is missing those fields or uses an unsupported readiness verdict.
- `review-loop` preflights readiness before spawning reviewers and asks reviewers to compare implementation shape against the durable design source in the first pass.
- The checks are deterministic and shallow; scripts do not parse design prose for quality.
