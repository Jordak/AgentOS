# Review Loop Conservative Autopilot

Design readiness: ready to implement

## Problem

`review-loop` automates review-panel cycles, fixes, validation, comments, and reporting, but its adjudication policy still leaves too much implicit judgment in the parent agent. In practice, agents can either ask the user to adjudicate issue families manually or accept too many reviewer suggestions and make the implementation more complex than the original brief required.

The missing behavior is not another heavy workflow. The loop needs a conservative default policy for deciding what it can fix without the user, what it should decline, and when it must stop for design judgment.

## Chosen Design

Add a `Conservative Autopilot` policy to `review-loop`.

The parent agent should classify every issue family into one of three buckets:

- `auto-fix`: evidenced, in scope, localized, follows existing patterns, has a clear validation signal, and does not add meaningful concepts.
- `auto-decline`: speculative, stylistic, duplicate, clearly out of scope, a low-value scope expansion, or more complex than the risk justifies.
- `ask-user`: an evidenced in-scope finding whose fix would change product behavior, change scope, add durable workflow semantics, introduce new abstractions or parser/schema/lifecycle/synchronization logic, or trigger the design escape hatch.

Completion should be based on parent adjudication, not raw reviewer recommendation labels: the loop is clean only when no unresolved `auto-fix` or `ask-user` blockers remain, and any remaining reviewer concerns are recorded as `auto-decline` with rationale. After a lazy-human brief, an `ask-user` family is resolved only by an explicit user decision: `user-approved-fix` enters the normal fix and verification path, `user-declined/accepted-risk` is recorded as residual risk, and `unresolved` blocks readiness.

For accepted fixes, the loop should apply a complexity governor before editing. It should choose the smallest closing move in this order:

1. Delete, simplify, narrow, split, or scope-reduce.
2. Use an existing helper, contract, module, or documented pattern.
3. Tighten the current code or prose locally.
4. Add narrow validation or tests around existing behavior.
5. Add a new abstraction, schema, parser, lifecycle rule, synchronization mechanism, or reusable contract only when the original brief or a P0/P1 risk requires it.

When user judgment is required, the interruption should use a short lazy-human brief:

- what the user needs to decide exactly;
- what the loop can confidently do without the user;
- what the loop is declining to avoid complexity;
- the recommended default.

## Scope

In scope:

- Update `os/skills/review-loop/SKILL.md` with the conservative autopilot policy.
- Update the loop ledger, adjudication, fix, quality, and verification guidance to record autopilot decisions and complexity posture.
- Encourage simplicity/code-judo attention when requesting review-pass panels for targets where complexity creep is the known risk.

Out of scope:

- Changing `review-pass` packet schema.
- Adding new scripts, validators, durable ledgers, or generated artifacts.
- Changing GitHub comment/report templates unless they become inconsistent with the revised loop contract.
- Running an actual review loop as part of this implementation.

## Acceptance Criteria

- `review-loop` says what the parent agent can confidently do without user input.
- `review-loop` says what must be brought to the user before fixing.
- The default fix policy prefers simplification and scope reduction over added machinery.
- The loop records auto-fix, auto-decline, and ask-user decisions in its ledger/reporting trail.
- User-approved ask-user fixes re-enter fix and verification, while unresolved ask-user blockers prevent ready marking.
- Final convergence is based on no unresolved auto-fix or ask-user blockers after parent adjudication, not on raw reviewer labels alone.
- User interruptions use the lazy-human brief shape instead of dumping raw issue-family adjudication on the user.
- Existing safety boundaries for PR comments, pushes, ready markers, and non-PR writes remain intact.

## Validation Plan

- Run `scripts/run-validator`.
- Run `git diff --check`.
- Inspect the diff to confirm it does not add new durable state, scripts, schemas, or review-pass packet fields.

## PR Readiness Fields

```md
Readiness evidence: docs/design/review-loop-conservative-autopilot.md
Readiness verdict: Ready to Implement
```
