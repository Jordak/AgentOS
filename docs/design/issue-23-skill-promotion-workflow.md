# Issue 23 Skill Promotion Workflow

Design readiness: ready to implement

## Context

GitHub issue #23 asks AgentOS to define a safe workflow for turning a maintained Personal Overlay skill into an AgentOS Core skill. The workflow depends on the now-closed prerequisite decisions from #19 and #74:

- Personal Overlay skills use the same Core skill contract as public Core skills.
- A private skill is maintained canonical state only when `personal/os/skills/MANIFEST.md` has an entry with `Lifecycle status: maintained`.
- Core and Personal Overlay skill manifests remain Markdown-first, but they now serve different jobs: the Core manifest is an export map, while the Personal Overlay manifest is an ignored private governance registry.
- `expose-skills` remains Core-only and must not scan or expose Personal Overlay skills.

## Chosen Design

Add a new Core skill for private-to-Core skill promotion. The likely skill name is `promote-private-skill-to-core`.

The new skill should be read-only by default, local-write only after explicit implementation approval, and external-write only through the shared GitHub/external-write policy. It should produce either a promotion audit report or, when approved, a sanitized Core skill plus the required maintenance updates.

The workflow starts from a governed private candidate instead of raw directory discovery. A directory-only private skill should first go through private manifest/governance review before Core promotion.

## Workflow Shape

1. Candidate gate: verify that the private skill is actively being evaluated for promotion and, preferably, has a maintained entry in `personal/os/skills/MANIFEST.md`.
2. Reusability gate: require evidence that the workflow is useful without the original user's private identity, projects, accounts, local paths, live agents, or generated reports.
3. Boundary map: classify private skill content into Core-safe behavior, private config, private examples, live private state, and discard.
4. Sanitized Core draft: write the reusable workflow as a Core skill under `os/skills/`, applying `os/skills/SKILL_CONTRACT.md` and the Core Markdown manifest API.
5. Private preservation: keep private behavior usable through `personal/os/skills/<core-skill>/CONFIG.md` when private inputs are enough, or through a private thin-adapter skill when the old behavior still depends on private agents, account assumptions, generated histories, or live artifact routing.
6. Validation and privacy gate: run AgentOS validators, privacy checks, and a semantic crawl before proposing or landing Core changes through the protected-main workflow.

## Reusable Evidence

Promotion requires at least one concrete example and should prefer two or more. Good evidence includes repeated successful use, repeated user requests, repeated agent failures that the skill prevents, a stable workflow contract, safe smoke examples, public-safe validation behavior, and a clear explanation of why the workflow helps a stranger who lacks the original Personal Overlay.

Private convenience, one-off preferences, live personal agent behavior, account-specific operating assumptions, and generated reports are not enough by themselves.

## Mandatory Privacy And Sanitization Checks

The workflow must check both paths and content for private leakage:

- personal identity, preferences, biographical facts, routines, handles, and contact details;
- private project names, private repository names, client/workplace facts, and private source-map entries;
- absolute local paths, machine-specific tool paths, current-machine adapter paths, and connector locations;
- account IDs, calendar IDs, Drive URLs, private GitHub URLs, connector assumptions, and permissions;
- live agent jobs, prompts, histories, reports, briefs, queues, run logs, and generated outputs;
- examples that appear sanitized but still encode real private facts;
- private filenames or directory names that would leak state even if contents are rewritten.

Core may receive reusable procedure, public-safe safety policy, sanitized examples, validators, fixtures, and export-map membership. Private live inputs stay in the Personal Overlay.

## Alternatives Considered

- Mode of `skillify-agentos`: rejected as the primary shape because promotion has its own privacy boundary, manifest-governance gate, and preservation workflow. `skillify-agentos` should route to the new skill when promotion is requested.
- Playbook-only note: too passive for a workflow agents need to execute repeatedly and carefully.
- Private manifest promotion field: rejected as a default because #19 says to add promotion notes only when a user or workflow is actively evaluating promotion.
- `expose-skills` support for Personal Overlay skills: out of scope for v1 and contrary to existing Core-only exposure guidance.

## Acceptance Criteria

- AgentOS includes a Core skill that documents the private-to-Core promotion workflow.
- The workflow distinguishes maintained private skills from drafts or ad hoc private directories.
- The workflow defines evidence required to prove a private skill is reusable enough for Core.
- The workflow separates Core-safe behavior from private config, private examples, live state, generated outputs, and discarded content.
- The workflow preserves private behavior after promotion through Personal Overlay config or a private thin adapter.
- The workflow requires privacy validation and protected-main PR discipline before Core changes land.
- `skillify-agentos` routes private-to-Core promotion requests to the new skill.
- `os/skills/MANIFEST.md` records the new skill using the Markdown manifest API.

## Non-Goals

- Do not implement automatic scanning, importing, or exposing of Personal Overlay skills.
- Do not modify `expose-skills` to read Personal Overlay skills.
- Do not migrate manifests to YAML, JSON, or structured sidecars.
- Do not add a default Core-promotion status field to private manifests.
- Do not promote generated private reports, live agent state, account-specific rules, or private examples into Core.
- Do not update GitHub issues, create PRs, commit, push, or change external state as part of this implementation unless separately approved.

## Validation Plan

- Run `scripts/run-validator`.
- Run `git diff --check`.
- Inspect the diff semantically for private leakage, especially paths, examples, manifest notes, and any mention of Personal Overlay behavior.
- Confirm no live `personal/os/` files were created, modified, copied, or tracked.

## PR Readiness Fields

```md
Readiness evidence: docs/design/issue-23-skill-promotion-workflow.md and GitHub issue #23
Readiness verdict: Ready to Implement
```
