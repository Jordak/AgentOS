# Personal Overlay Discovery

Design readiness: ready to implement

Implementation tracker: GitHub issue #36.

AgentOS must let external agents use AgentOS Core plus the ignored Personal Overlay as one control plane. The Personal Overlay stays ignored local state under `$root/personal/os/`, but ignored must not mean undiscoverable to the agents that are supposed to read it.

## Context

The tracked Personal Overlay skeleton contains public-safe `.gitkeep` files while real private state is ignored by git. Many common discovery paths respect ignore rules by default, including default code search, git file APIs, IDE search, and some resource indexes. When those tools are used as absence evidence, an agent can see only the skeleton and incorrectly conclude that no private context exists.

That failure is especially dangerous because it looks clean. The agent did search a plausible path, found no visible private files, and may then answer confidently from incomplete Core-only context.

## Decision

AgentOS will document a portable Personal Overlay absence-evidence rule rather than adding a helper script or validator gate.

Agents must not treat ignore-aware or git-aware discovery as evidence that Personal Overlay files are absent. Absence must be proven by a direct filesystem read or listing of the canonical Personal Overlay root that does not apply git ignore rules.

If Personal Overlay discovery returns only tracked skeleton files such as `.gitkeep`, the result is inconclusive until a direct filesystem check of the canonical Personal Overlay root has also found no matching private files.

The rule is tool-neutral. AgentOS may give examples for common environments, but no one command is canonical. Valid approaches include direct file reads when the expected path is known, ordinary filesystem APIs that list regular files under `personal/os/`, POSIX `find`, PowerShell `Get-ChildItem -Force`, or ignore-including search flags for tools that support them.

In isolated worktrees, a skeleton-only `personal/os/` can be a real local state of that worktree. Agents should resolve Personal Overlay reads against the canonical primary AgentOS checkout unless the user or harness explicitly assigns a different private overlay workspace.

## Alternatives Considered

Helper script: rejected for now. A small listing helper would create a stable affordance, but it would likely grow into a cross-platform locator with worktree resolution, privacy controls, symlink policy, JSON modes, and content-search edge cases. The failure being fixed is a rule-of-evidence problem, so the portable rule should come first.

Validator-only check: rejected for now. A validator can prove checked-in wording exists, but once the wording is committed, that does not materially improve the real failure mode. Guidance measures the agent behavior, while source-routing fixtures keep deterministic route evidence available without treating exact prose as the only acceptance signal.

Command-specific rule: rejected. Requiring one command such as `rg -uuu` would make the contract less portable across machines, shells, operating systems, and harnesses.

## Acceptance Criteria

- `os/playbook/PERSONAL_OVERLAY.md` states the portable absence-evidence rule and gives non-normative examples.
- `os/RESOLVER.md` keeps local search as the default while naming the Personal Overlay exception.
- Root and generated global adapter instructions route agents to `os/playbook/PERSONAL_OVERLAY.md` before they conclude private state is absent.
- A Guidance fixture covers the false-empty scenario where default ignored-file discovery shows only `.gitkeep`; source-routing fixtures keep the relevant Core route evidence checked by the deterministic validator.
- No helper script, validator check, copied Personal Overlay content, or tracked private filenames are added.

## Follow-Ups

If future evidence shows agents still miss ignored Personal Overlay files after this rule is documented and benchmarked, revisit whether a narrowly scoped helper script is worth the maintenance cost.
