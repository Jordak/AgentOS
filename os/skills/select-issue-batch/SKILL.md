---
name: select-issue-batch
description: "Select and explain the next high-leverage GitHub issue or small issue batch without mutating tracker state or starting workers. Use when the user asks what issue to do next, wants a batch recommendation, or needs a read-only planner for coordinate-issue-batch."
---

# Select Issue Batch

## Goal

Recommend the next issue or small batch of issues to work on by inspecting tracker state, blocker relationships, readiness evidence, labels, and the user's current selection goal. The planner is read-only: it selects and explains. It does not coordinate execution, spawn workers, create branches, edit issues, change labels, close issues, or mutate GitHub by default.

This skill is the selection layer in the issue-batch workflow stack:

- Single-issue execution workflows own readiness repair, implementation, PR creation, review convergence, and final reporting for one issue.
- `select-issue-batch` recommends which issue or batch should be considered next and explains why those issues belong together or should be sequenced.
- `coordinate-issue-batch` consumes a selected or user-provided batch and owns execution coordination after explicit authorization.

## Contract

Inputs:

- A target repository or issue tracker, inferred from the current checkout when possible.
- Optional selection goal, such as "what should we do next?", "find high-leverage issues", "find only ready issues", "find parallel-safe work", or "choose a batch for a coordinator".
- Optional scope filters such as labels, milestones, projects, issue numbers, area, recent updates, or maximum batch size.
- Tracker issue data, usually open GitHub issues with titles, bodies, labels, comments when needed, URLs, and update times.
- Current AgentOS GitHub workflow policy at `os/playbook/GITHUB_WORKFLOW.md` and orchestration vocabulary at `os/skills/ORCHESTRATION_LOOPS.md` when batch, worker, or parallel-safety reasoning is relevant.

Output artifact:

- A Markdown recommendation report with ranked issues, rationale, readiness/blocker evidence, parallel-safety assessment, rejected or deferred candidates, assumptions, and useful handoff notes for `coordinate-issue-batch`.

Mutability:

- Read-only by default for local files, GitHub, branches, worktrees, issues, labels, and PRs.
- No local-write, connector-write, or external-write behavior by default.
- If the user asks to turn the recommendation into tracker updates, worker launch, branch creation, issue comments, labels, or PR work, stop after the recommendation and tell the caller or user to explicitly invoke `coordinate-issue-batch` or another authorized mutating workflow in a separate step.

Tools and connectors:

- Local filesystem and `git` for repository identity and local policy files.
- GitHub connector or `gh` for read-only issue and PR metadata.
- `os/playbook/GITHUB_WORKFLOW.md` for issue, branch, worker, and closure discipline.
- `os/skills/ORCHESTRATION_LOOPS.md` for Workflow Result, Blocking Human Decision, Isolation Boundary, and parallel Called Workflow vocabulary.
- The `coordinate-issue-batch` contract when the user wants execution coordination after selection.

Safety:

- Do not mutate GitHub by default: no issue comments, issue edits, labels, milestones, assignments, closures, PR comments, PR state changes, or repository settings.
- Do not create or switch branches, create worktrees, spawn workers, call subagents, or start execution workflows by default.
- Treat labels as evidence, not truth. Labels such as `blocked`, `HITL`, `ready-for-agent`, `ready-for-human`, `needs-human`, and `needs-a-human` can be stale or incomplete, so verify them against issue bodies, dependencies, comments when needed, and current tracker state before using them as selection reasons.
- Treat current blocker or human-review evidence conservatively. A candidate may still be high leverage, but the recommendation must name what needs verification or resolution before coordination starts.
- Do not treat `ready-for-agent` as the primary ranking signal. It is evidence that execution may be possible, not evidence that the issue is the best next move.
- Ask before any external write request, and do not perform the write from this skill. For execution or coordination requests, stop after the recommendation and tell the caller or user to explicitly invoke `coordinate-issue-batch` or another authorized mutating workflow in a separate step.

## Ranking Policy

Optimize primarily for future leverage: work that, if done next, makes later work easier, safer, or more valuable. Readiness is a modifier that affects sequencing and coordination risk; it is not the first ranking gate.

Default ranking posture:

1. Prefer high-leverage issues that unlock, de-risk, or increase the value of follow-on work.
2. Prefer ready high-leverage issues when leverage is otherwise comparable.
3. Prefer high-leverage issues that need design consensus over low-leverage issues that are already ready, because readiness repair belongs downstream and should not cause the selector to discard leverage.
4. Recommend low-leverage ready issues as quick wins or filler only when they do not displace higher-leverage work.
5. Treat blocker, HITL, and human-review signals as stale until verified; explain whether the evidence appears current and what makes the candidate safe or unsafe for the selected batch.

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
   - Treat labels as potentially stale. Verify `blocked` against open dependencies, `HITL` or human-review labels against the issue body and recent comments when needed, and `ready-for-agent` against durable readiness evidence.
   - Classify each relevant issue as one of:
     - `appears ready for coordination`;
     - `needs readiness or design repair before execution`;
     - `appears blocked on dependency`;
     - `appears blocked on human decision`;
     - `triage or design clarification needed before selection`;
     - `closure audit or no action candidate`.
   - Remember that `needs design consensus` does not automatically make an issue lower priority than ready low-leverage work.

4. Score by leverage, not only readiness:
   - Identify issues that unblock other issues, establish reusable workflow conventions, reduce integration risk, remove repeated manual work, or improve the value of future agent runs.
   - Consider immediacy, but do not let ready low-leverage work outrank high-leverage work merely because it is ready.
   - Prefer smaller batches when dependency or surface overlap is uncertain.

5. Assess parallel safety:
   - For each selected issue, name the likely Isolation Boundary: issue, branch/worktree, PR, artifact, domain/module area, read-only lane, or explicit non-overlap assumption.
   - Mark a batch as likely parallel-safe only when selected issues appear independent enough that coordinated workers would not share an uncoordinated mutable surface.
   - Mark a batch as sequential when one issue depends on another, shares unclear files or workflow state, or needs a human/design decision before safe parallel work.
   - If uncertain, recommend a coordinator or human validate the boundary before worker launch.

6. Select the batch:
   - Choose the next 1-N issues that best match the selection goal and future-leverage ranking.
   - Include readiness, blocker, and stale-label evidence as risk notes for the selected batch, not as workflow commands.
   - Leave execution, worker assignment, issue comments, label hygiene, branches, PRs, and implementation workflow invocation to `coordinate-issue-batch` or another explicitly authorized mutating workflow.
   - Recommend no selection for issues that are low leverage, out of scope, or unsafe to include in the batch after current evidence is checked.

7. Return a selection report:
   - Include the selection goal, inspected scope, selected issue or batch, ranked rationale, readiness/blocker evidence, parallel-safety conclusion, rejected or deferred candidates, assumptions, and coordinator handoff notes.
   - Include issue URLs, recommended sequencing, Isolation Boundary notes, and why each selected issue belongs in or outside the same batch.

## Output Shape

Use this structure unless the user requested a smaller answer:

```md
## Selection Goal

<goal and scope>

## Recommended Batch

1. #<issue> <title>
   - Why this now: <future-leverage rationale>
   - Readiness/blockers: <evidence and stale-label check>
   - Parallel-safety notes: <Isolation Boundary or sequencing reason>

## Parallel-Safety Assessment

<likely parallel-safe / sequential / uncertain, with reason>

## Deferred Or Rejected Candidates

- #<issue> <title> — <reason>

## Coordinator Handoff Notes

<batch sequencing, risk, and Isolation Boundary notes for coordinate-issue-batch>

## Assumptions And Limits

<what was not inspected or what could change the ranking>
```

## Filing Rules

- Default output stays in chat.
- Do not create durable AgentOS state by default.
- If the recommendation becomes an approved execution plan, the downstream coordinator or approved mutating workflow owns its own filing, recovery, issue/PR comments, branch/worktree state, or coordinator ledger.
- If selection discovers a reusable workflow gap outside the requested scope, recommend a follow-up issue rather than expanding this skill's output into execution.

## Quality Bar

- The recommendation optimizes for future leverage unless the user gave a narrower goal.
- Readiness state affects sequencing and risk notes, not just the ranking.
- Blocked and human-review labels are checked as potentially stale signals, and current blocker evidence is never silently ignored.
- Each selected issue has a clear reason for being in the batch.
- Batch recommendations include a parallel-safety assessment and any sequencing constraints.
- The output separates selection from execution coordination.
- The skill performs no external writes, local edits, branch/worktree actions, worker spawning, or issue state changes by default.

## Verification

Before finishing:

1. Confirm the target repository and inspected issue scope.
2. Confirm GitHub and local reads were read-only.
3. Confirm labels, blocker relationships, readiness evidence, and acceptance criteria were considered for selected issues.
4. Confirm the ranking rationale names future leverage, not only readiness.
5. Confirm blocked, HITL, ready, and human-review labels were treated as potentially stale signals and checked against available evidence.
6. Confirm each selected issue has a rationale for inclusion in the batch.
7. Confirm batch output states whether the set appears parallel-safe and why.
8. Confirm no branches, worktrees, workers, issue comments, labels, PRs, or other external state were changed.
9. If this skill or its manifest entry changed, run `git diff --check` and `scripts/run-validator`.
