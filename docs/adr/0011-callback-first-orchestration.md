# Callback-First Orchestration

Design readiness: ready to implement

## Context

ADR 0009 defines AgentOS orchestration loops through workflow contracts, Authorization Boundaries, Workflow Results, Recovery Records, and Integration Ownership. As batch and repository-level workflows start launching durable called workflows, the next failure mode is control-plane chatter: a Calling Workflow can keep polling worker threads for progress, copy large handoff prompts into each worker, or leave child threads with ambiguous names until after real work has already started.

Those habits make the active working state hard to recover. They also spend tokens on instructions that should live in durable sources such as GitHub issues, ADRs, playbooks, skill contracts, and Workflow Result contracts.

## Decision

AgentOS orchestration should use callback-first invocation for durable Called Workflows.

A Calling Workflow should pass a Workflow Invocation Reference to each Called Workflow when the harness or workflow surface supports it. The reference can be a callback thread id, child-thread URL, coordinator ledger location, issue or PR comment surface, or equivalent stable place where the Called Workflow can return its Workflow Result.

A Called Workflow should report completion, blocked, failed, cancelled, and needs-human states back to the Calling Workflow through that reference. After reporting, the Called Workflow should stop or wait according to the caller's explicit release instruction. It should not assume the caller will continuously poll for progress.

This ADR standardizes callback-first result surfaces and terminal status vocabulary. It does not define aggregate workflow status precedence or richer status maps for mixed child outcomes; that design is deferred to GitHub issue #158. Until that follow-up lands, aggregate workflows should keep per-worker, per-issue, or per-batch outcomes visible in their Workflow Results instead of implying a durable precedence rule.

Runtime polling of Called Workflows is not the normal orchestration pattern. Polling is allowed only as bounded bootstrap, timeout, recovery, or diagnostic behavior, and the caller should record why polling was needed in its Recovery Record.

Calling Workflows should send minimal assignment packets. The packet should point to durable task sources, issue bodies, ADRs, playbooks, skill contracts, and expected Workflow Result fields instead of copying those contracts into each launch message. Workflow-specific handoff shapes belong in the workflow that owns the launch, not in a universal reusable prompt.

When the harness supports branch-backed or durable worker threads, the orchestrator should include a setup stage before real worker execution: create or assign the worker branch and worktree, record the invocation reference, and only then send the worker the `READY` signal or assignment message. When thread renaming is supported, the orchestrator should rename the worker thread to a public-safe, legible target-specific name before `READY` or assignment; otherwise it should record why a public-safe rename was unavailable.

## Consequences

Parent workflows can go idle after launching child work and resume from returned Workflow Results instead of spending active turns monitoring every child.

Recovery records become more important. A caller must record the callback reference, expected result, worker identity, branch or worktree, and next safe action before launch or before any recovery boundary.

Worker handoffs get smaller and more durable. The caller points to the GitHub issue, skill contract, repository playbooks, and validation requirements rather than pasting a long universal runtime prompt.

Harness-specific handles remain implementation details. Public or Git-backed recovery surfaces should record only public-safe stable references, and private or opaque handles should stay on authorized private surfaces or be redacted.

## Alternatives Considered

Keep parent workflows polling worker threads until they finish. This was rejected because it wastes tokens, makes "who is currently working" ambiguous, and encourages parent threads to behave like live supervisors instead of callback consumers.

Use one universal implementation-worker handoff prompt for every orchestration workflow. This was rejected because handoff details are workflow-specific and drift from the underlying skill contracts. Minimal pointer-first packets keep the reusable rule stable while letting launch-owning workflows define their own shape.

Require a deterministic callback transport before documenting the convention. This was rejected because the workflow rule is useful across harnesses today. A callback can be a thread id, comment surface, ledger path, or equivalent invocation reference.

## Validation

The implementation for GitHub issue #156 should:

- update `os/skills/ORCHESTRATION_LOOPS.md` with callback-first invocation, anti-polling, minimal assignment, and worker-thread setup guidance;
- record that aggregate workflow status precedence and richer status maps are deferred to GitHub issue #158 while preserving detailed child outcome reporting;
- move or restate the `coordinate-issue-batch` to `implement-github-issue` worker handoff shape in `os/skills/coordinate-issue-batch/SKILL.md`;
- update `github-loop`, GitHub workflow guidance, and manifest summaries so parent workflows go idle after launch and recover through Workflow Results rather than continuous polling;
- run `git diff --check` and `scripts/run-validator`.

Readiness evidence: GitHub issue #156

Readiness verdict: Ready to Implement
