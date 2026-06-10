---
name: select-issue-batch
description: "Select and explain the next high-leverage GitHub issue or small issue batch without mutating tracker state or starting workers. Use when the user asks what issue to do next, wants a batch recommendation, or needs a read-only planner before coordinate-issue-batch."
---

# Select Issue Batch

## Goal

Recommend the next issue or small batch of issues to work on by inspecting tracker state, blocker relationships, readiness evidence, labels, and the user's current selection goal. The planner is read-only: it selects and explains. It does not coordinate execution, spawn workers, create branches, edit issues, change labels, close issues, or mutate GitHub by default.

This skill is the selection layer between single-issue execution and future batch coordination:

- `implement-github-issue` owns one issue through readiness, implementation, PR creation, review-loop convergence, and final reporting while stopping before merge and issue closure.
- `select-issue-batch` recommends which issue or batch should be considered next and explains the next workflow for each candidate.
- `coordinate-issue-batch` may later consume a selected or user-provided batch and coordinate Called Workflows that run `implement-github-issue` after explicit authorization.

## Contract

Inputs:

- A target repository or issue tracker, inferred from the current checkout when possible.
- Optional selection goal, such as "what should we do next?", "find high-leverage issues", "find only ready issues", "find parallel-safe work", or "choose a batch for a coordinator".
- Optional scope filters such as labels, milestones, projects, issue numbers, area, recent updates, or maximum batch size.
- Tracker issue data, usually open GitHub issues with titles, bodies, labels, comments when needed, URLs, and update times.
- Current AgentOS GitHub workflow policy at `os/playbook/GITHUB_WORKFLOW.md` and orchestration vocabulary at `os/skills/ORCHESTRATION_LOOPS.md` when batch, worker, or parallel-safety reasoning is relevant.

Output artifact:

- A Markdown recommendation report with ranked issues, rationale, readiness/blocker state, recommended next workflow, parallel-safety assessment, rejected or deferred candidates, assumptions, and useful handoff instructions for `implement-github-issue` or a future `coordinate-issue-batch` caller.

Mutability:

- Read-only by default for local files, GitHub, branches, worktrees, issues, labels, and PRs.
- No local-write, connector-write, or external-write behavior by default.
- If the user asks to turn the recommendation into tracker updates, worker launch, branch creation, issue comments, labels, or PR work, stop and route that action to the appropriate mutating workflow.

Tools and connectors:

- Local filesystem and `git` for repository identity and local policy files.
- GitHub connector or `gh` for read-only issue and PR metadata.
- `os/playbook/GITHUB_WORKFLOW.md` for issue, branch, worker, and closure discipline.
- `os/skills/ORCHESTRATION_LOOPS.md` for Workflow Result, Blocking Human Decision, Isolation Boundary, and parallel Called Workflow vocabulary.
- `os/skills/implement-github-issue/SKILL.md` when recommending the single-issue execution path.
- Future `os/skills/coordinate-issue-batch/SKILL.md` when it exists and the user wants execution coordination after selection.

Safety:

- Do not mutate GitHub by default: no issue comments, issue edits, labels, milestones, assignments, closures, PR comments, PR state changes, or repository settings.
- Do not create or switch branches, create worktrees, spawn workers, call subagents, or start `implement-github-issue` by default.
- Treat `blocked`, `HITL`, `ready-for-human`, `needs-human`, `needs-a-human`, and similar labels conservatively. They may still be high-leverage candidates, but the recommendation must name the blocker or human decision and choose the smallest safe next workflow.
- Do not treat `ready-for-agent` as the primary ranking signal. It is evidence that execution may be possible, not evidence that the issue is the best next move.
- Ask before any external write or any transition from selection into execution or coordination.

## Ranking Policy

Optimize primarily for future leverage: work that, if done next, makes later work easier, safer, or more valuable. Readiness is a modifier that affects the recommended next workflow; it is not the first ranking gate.

Default ranking posture:

1. Prefer high-leverage issues that unlock, de-risk, or increase the value of follow-on work.
2. Prefer ready high-leverage issues when leverage is otherwise comparable.
3. Prefer high-leverage issues that need design consensus over low-leverage issues that are already ready, because `implement-github-issue` starts with `ensure-implementation-readiness` and can handle design consensus before implementation.
4. Recommend low-leverage ready issues as quick wins or filler only when they do not displace higher-leverage work.
5. Treat blocked, HITL, and human-review issues conservatively by explaining the blocker and recommending the smallest next safe action.

If the user gives a narrower selection goal, honor it explicitly. For example, "find only issues that can be implemented immediately" may filter out not-ready high-leverage work; "find design work worth doing next" may elevate issues that need consensus.

## Workflow Phases

1. Establish the target:
   - Identify the repository, tracker, base branch if relevant, and issue scope.
   - Read local instructions and relevant policy files, especially `os/playbook/GITHUB_WORKFLOW.md`.
   - If batch or parallel reasoning is requested, read `os/skills/ORCHESTRATION_LOOPS.md`.
   - Infer the selection goal from the user request or state the default high-leverage goal.

2. Inventory candidates:
   - List open issues in scope.
   - Gather labels, title, body, URL, updated time, and linked PR or dependency evidence when readily available.
   - Read comments only when the body and labels leave blocker, ownership, or recency state ambiguous enough to affect the recommendation.
   - Keep candidate reads proportional to the requested batch size and risk.

3. Classify readiness and blockers:
   - Inspect labels such as `needs design consensus`, `ready-for-agent`, `ready-for-human`, `blocked`, `AFK`, and `HITL`.
   - Read issue bodies for readiness markers, acceptance criteria, `Blocked by` relationships, linked design sources, and explicit non-goals.
   - Classify each relevant issue as one of:
     - `ready for implement-github-issue`;
     - `implement-github-issue should start with readiness repair`;
     - `blocked on dependency`;
     - `blocked on human decision`;
     - `triage or design clarification needed before selection`;
     - `closure audit or no action candidate`.
   - Remember that `implement-github-issue` can handle readiness repair before coding, so `needs design consensus` does not automatically make an issue lower priority than ready low-leverage work.

4. Score by leverage, not only readiness:
   - Identify issues that unblock other issues, establish reusable workflow conventions, reduce integration risk, remove repeated manual work, or improve the value of future agent runs.
   - Consider immediacy, but do not let ready low-leverage work outrank high-leverage work merely because it is ready.
   - Prefer smaller batches when dependency or surface overlap is uncertain.

5. Assess parallel safety:
   - For each selected issue, name the likely Isolation Boundary: issue, branch/worktree, PR, artifact, domain/module area, read-only lane, or explicit non-overlap assumption.
   - Mark a batch as likely parallel-safe only when selected issues appear independent enough that separate `implement-github-issue` runs would not share an uncoordinated mutable surface.
   - Mark a batch as sequential when one issue depends on another, shares unclear files or workflow state, or needs a human/design decision before safe parallel work.
   - If uncertain, recommend a coordinator or human validate the boundary before worker launch.

6. Recommend the next workflow:
   - Use `implement-github-issue` for selected issues that should proceed through readiness, design repair, implementation, PR creation, and review-loop.
   - Use `implement-github-issue` even when the issue needs design consensus if the issue is high-leverage and the next move is to resolve readiness and then implement inside that workflow.
   - Recommend triage when the issue lacks enough tracker information to choose a next workflow.
   - Recommend closure audit when the issue appears already implemented or stale against integration evidence.
   - Recommend no action when the issue is blocked, low leverage, out of scope, or unsafe to start.
   - Recommend future `coordinate-issue-batch` only after the user has an approved batch and wants execution coordination; do not start it from this skill.

7. Return a selection report:
   - Include the selection goal, inspected scope, selected issue or batch, ranked rationale, recommended next workflow, readiness/blocker state, parallel-safety conclusion, rejected or deferred candidates, assumptions, and next handoff instructions.
   - For a future coordinator, include issue URLs, recommended sequencing, Isolation Boundary notes, and why each selected issue belongs in or outside the same batch.

## Output Shape

Use this structure unless the user requested a smaller answer:

```md
## Selection Goal

<goal and scope>

## Recommended Batch

1. #<issue> <title> — <recommended workflow>
   - Why this now: <future-leverage rationale>
   - Readiness/blockers: <state>
   - Parallel-safety notes: <Isolation Boundary or sequencing reason>

## Parallel-Safety Assessment

<likely parallel-safe / sequential / uncertain, with reason>

## Deferred Or Rejected Candidates

- #<issue> <title> — <reason>

## Handoff Instructions

<instructions for implement-github-issue or a future coordinator>

## Assumptions And Limits

<what was not inspected or what could change the ranking>
```

## Filing Rules

- Default output stays in chat.
- Do not create durable AgentOS state by default.
- If the recommendation becomes an approved execution plan, the next workflow owns its own filing, recovery, issue/PR comments, branch/worktree state, or coordinator ledger.
- If selection discovers a reusable workflow gap outside the requested scope, recommend a follow-up issue rather than expanding this skill's output into execution.

## Quality Bar

- The recommendation optimizes for future leverage unless the user gave a narrower goal.
- Readiness state affects the recommended workflow, not just the ranking.
- Blocked and human-review issues are handled conservatively and never silently selected for implementation without naming the blocker.
- Each selected issue has a clear next workflow.
- Batch recommendations include a parallel-safety assessment and any sequencing constraints.
- The output separates selection from execution coordination.
- The skill performs no external writes, local edits, branch/worktree actions, worker spawning, or issue state changes by default.

## Verification

Before finishing:

1. Confirm the target repository and inspected issue scope.
2. Confirm GitHub and local reads were read-only.
3. Confirm labels, blocker relationships, readiness evidence, and acceptance criteria were considered for selected issues.
4. Confirm the ranking rationale names future leverage, not only readiness.
5. Confirm blocked, HITL, and human-review candidates are not treated as silently executable.
6. Confirm each selected issue has a recommended next workflow.
7. Confirm batch output states whether the set appears parallel-safe and why.
8. Confirm no branches, worktrees, workers, issue comments, labels, PRs, or other external state were changed.
9. If this skill or its manifest entry changed, run `git diff --check` and `scripts/run-validator`.
