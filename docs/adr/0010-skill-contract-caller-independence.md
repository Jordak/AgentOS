# Skill Contracts Stay Caller-Independent

Design readiness: ready to implement

## Context

AgentOS skills are reusable workflow units. As skills become composable, it is tempting for a skill to explain which larger workflows might call it, which future coordinators might own neighboring steps, or which sibling skills should not call it.

That extra caller narration makes skills harder to reuse. It also lets current orchestration plans leak into the callee's contract. The result is similar to a function documenting every caller in the codebase instead of documenting its own inputs, outputs, side effects, and the functions it invokes.

ADR 0009 already says AgentOS composes loop-shaped workflows through contracts and invocation-scoped boundaries. This decision makes the local writing rule explicit for individual skill contracts.

## Decision

Skill contracts should stay caller-independent.

A skill should describe:

- the behavior it owns;
- its inputs, outputs, side effects, safety boundaries, and recovery obligations;
- the tools, playbooks, skills, or workflows it directly calls or requires;
- the Workflow Result it returns to its caller;
- the conditions under which it recommends a caller invoke another skill as a next action.

A skill should not describe or assume:

- which specific workflow, coordinator, batch runner, or human process will call it;
- which sibling workflows are not supposed to call it;
- future orchestration plans that are not required to execute the skill itself;
- caller ownership boundaries except through the generic `Calling Workflow`, `Authorization Boundary`, and `Workflow Result` interfaces.

This is the same design posture as programming a function. The function documents its own contract and the contracts it depends on. It does not hardcode assumptions about every current or future call site.

## Consequences

Skills become smaller and easier to reuse in new orchestration shapes. A future coordinator can call an existing skill without needing that skill's prose to predict or bless the coordinator.

Caller-specific sequencing belongs in the caller's contract, issue design source, handoff, or orchestration ledger. Callee skills should expose stable interfaces that callers can compose.

Skill docs may still mention another skill when that mention is operational:

- the current skill calls that skill;
- the current skill requires that skill's evidence standard or playbook;
- the current skill returns a Workflow Result that recommends invoking that skill for a specific recovery path.

Skill docs should avoid negative ownership prose such as "skill X does not call this skill" unless the statement is part of an active safety rule that cannot be expressed through the callee's own contract.

## Alternatives Considered

Document expected callers inside each skill. This was rejected because caller lists go stale and make skill contracts feel like narrow call-site appendices rather than reusable interfaces.

Keep the rule only implicit in ADR 0009. This was rejected because caller narration is a recurring writing failure mode, and the function analogy is clearer as a small standalone decision.

Ban all cross-skill mentions. This was rejected because skills need to name direct dependencies and useful recovery paths. The rule is caller independence, not isolation.

## Validation

When changing a skill contract, review whether cross-skill or workflow mentions are operational dependencies, recovery recommendations, or unnecessary caller assumptions.

Run `git diff --check` and `scripts/run-validator` after changing AgentOS Core skill or manifest surfaces.
