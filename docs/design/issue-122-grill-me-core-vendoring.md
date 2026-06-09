# Issue 122 Grill Me Core Vendoring

Design readiness: ready to implement

## Problem

As of this design being written, `grill-me` exists as a current-machine installed/global skill instead of a portable AgentOS Core skill. `check-implementation-readiness` can mention design-interview workflows such as `grill-me`, but AgentOS Core cannot depend on a Core source for that workflow.

## Decision

Vendor `grill-me` as a Core skill under `os/skills/grill-me/` while preserving the upstream behavior and name.

The Core skill should keep the installed/global trigger name `grill-me`, stay read-only by default, and remain aligned with the upstream source. AgentOS may add contract, safety, filing, verification, provenance, and manifest metadata around the behavior, but should not extend the workflow into document mutation, issue mutation, code mutation, or external writes.

The behavior contract is intentionally small:

- interview the user about a plan or design until shared understanding is reached;
- walk the design tree one question at a time;
- recommend a default answer for each question;
- inspect local code or docs instead of asking when local evidence can answer safely;
- stop when shared understanding is reached or remaining unknowns are explicitly deferred.

## Alternatives Considered

Rename the Core skill to a more generic design-consensus name. Rejected because the installed/global trigger and issue title already use `grill-me`, and keeping the name preserves current workflow alignment.

Expand the Core skill into a mutating readiness workflow that updates design docs or GitHub issues. Rejected because mutation belongs to the calling workflow, such as `check-implementation-readiness`, after the applicable local-write or external-write policy is satisfied.

Treat the current-machine installed skill as private-owned behavior and fork it. Rejected because the user decision for issue #122 is to keep `grill-me` aligned with upstream.

## Scope

In scope:

- Add `os/skills/grill-me/SKILL.md` following `os/skills/SKILL_CONTRACT.md`.
- Add `os/skills/grill-me/UPSTREAM.md` provenance for the installed/global source.
- Add a `grill-me` entry to `os/skills/MANIFEST.md`.
- Add narrow source-routing smoke coverage if it remains public-safe and stable.
- Allow the vendored upstream freshness checker to report intentionally unsupported non-GitHub sources as manual-check items instead of metadata failures.
- Run AgentOS validation and diff checks.

Out of scope:

- Updating the GitHub issue body or labels without explicit external-write approval.
- Adding document, issue, PR, code, or external mutation to `grill-me`.
- Replacing `check-implementation-readiness`.
- Creating a deterministic validator for the conversation quality of a grill session.
- Exposing the new Core skill to current-machine global adapters without separate approval.

## Acceptance Criteria

- `os/skills/grill-me/SKILL.md` exists and follows the Core skill contract.
- The skill remains read-only by default and does not write docs, issues, comments, or external state.
- The skill says to ask one question at a time and recommend a default answer.
- The skill says to inspect local code/docs instead of asking when local evidence can answer.
- `UPSTREAM.md` records the source/provenance of the imported skill without storing machine-local adapter paths in Core.
- `os/skills/MANIFEST.md` includes a `grill-me` entry using the Markdown manifest API.
- AgentOS validation passes after the change.

## Validation Plan

- Run `scripts/run-validator`.
- Run `git diff --check`.
- Inspect `os/skills/grill-me/SKILL.md` against the installed/global upstream behavior.
- Inspect the manifest entry against the Markdown manifest API.
- Run the vendored upstream freshness checker self-test when its manual-check handling changes.
- Confirm no current-machine adapter paths, private examples, Personal Overlay state, or external-write permissions were copied into Core.

## PR Readiness Fields

```md
Readiness evidence: GitHub issue #122 and docs/design/issue-122-grill-me-core-vendoring.md
Readiness verdict: Ready to Implement
```
