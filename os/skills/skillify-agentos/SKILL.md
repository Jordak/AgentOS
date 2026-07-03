---
name: skillify-agentos
description: "Turn repeated AgentOS tasks, repeated agent failures, or recurring manual checks into durable skills, resolver guidance, deterministic validators, and smoke examples. Use when the user asks to skillify a workflow, encode a repeated miss, make a reusable AgentOS behavior, or stop relying on memory/discipline for a recurring pattern."
---

# Skillify AgentOS

## Trigger

Use this when the user asks to "skillify" something, when the same AgentOS task has appeared more than once, when an agent repeats a correctable miss, or when a manual verification chore should become reusable behavior.

Do not use this for one-off preferences, speculative abstractions, or project implementation details that belong in a mapped project.

When the candidate starts as a Personal Overlay skill or private skill config that may need sanitizing into Core, use `promote-private-skill-to-core` for the private/Core boundary workflow instead of handling promotion as ordinary skillification.

## Goal

Turn real repeated work into durable AgentOS behavior with the smallest stable artifact that will prevent the repeated cost or failure.

The output may be a skill update, a new exported skill, a private module inside an exported skill, resolver guidance, export-map maintenance, a deterministic validator, a routing fixture, or a propagation queue proposal. The default is the least machinery that makes the future run better.

## Contract

Inputs:

- At least one concrete example of the repeated task, repeated failure, or manual check. If no example exists, ask for one or stop with a proposed observation to watch.
- The current AgentOS resolver, skills resolver, skill contract, skills export map, verification checklist, and relevant existing skill or agent files.
- Any issue, report, transcript, failed run, validator output, or user correction that shows the pattern.

Output artifact:

- A new or updated AgentOS skill, private module, resolver entry, export-map entry, deterministic validator, source-routing fixture, smoke example, or review-queue proposal.
- A short implementation summary naming what changed and how it was verified.

Mutability:

- Local-write. This workflow may edit AgentOS Markdown files and local scripts.
- External-write only when permitted by the applicable external-write policy.

Tools and connectors:

- Local filesystem for AgentOS files.
- `rg`, `git`, and local validators for inspection and verification.
- GitHub issue context only when the skillification is issue-driven.
- No external account data is needed by default.

Safety:

- Follow the applicable external-write policy before external sends, public posts, permission changes, or connector writes. Ask before automation activation or destructive edits.
- Do not copy private connector data into skills, smoke examples, validators, or memory.
- Do not apply current-machine skill exposure unless the issue or the user explicitly asks for discoverability outside the AgentOS workspace.
- Use a propagation queue entry instead of canonical edits when the durable change is private, tentative, connector-derived, personal, cross-project, or not yet ready for an issue tracker.

## Workflow Phases

1. Gather examples: capture at least one concrete prompt, failure, report, diff, validator output, or manual checklist step. Prefer two examples before adding broad abstractions.
2. Classify the pattern:
   - repeated task -> skill or existing skill update;
   - repeated failure -> skill/resolver/checklist update plus smoke example;
   - exact manual check -> deterministic validator;
   - ambiguous filing/routing miss -> resolver, directory resolver, or routing
     eval fixture;
   - public-safe actionable project work -> GitHub issue or mapped-project tracker;
   - private/tentative/pre-issue durable state proposal -> propagation review queue.
3. Choose the smallest durable artifact. Update an existing skill before adding a new one when the trigger, workflow, and output are already owned by that skill.
   - Private-to-Core skill promotion -> use `promote-private-skill-to-core` for candidate governance, sanitization, private behavior preservation, and privacy validation.
4. Decide code vs Markdown:
   - use deterministic code when the check is exact, repeated, and cheaply
     machine-verifiable;
   - use Markdown process guidance when judgment, context, or user preference is
     central;
   - use both when a validator should enforce the mechanical parts and a skill
     should explain the judgment.
5. Apply the AgentOS skill contract. New or materially changed skills must name inputs, output artifact, mutability, tools/connectors, safety, phases, quality bar, verification, and filing rules.
6. Update maintenance surfaces:
   - `os/skills/MANIFEST.md` when adding, removing, renaming, deprecating, or changing export status for an exported Core skill;
   - `os/skills/expose-skills/SKILL.md` when current-machine Core skill
     exposure behavior changes;
   - `os/RESOLVER.md` only when lookup, routing, authority, safety, or filing
     tie-breakers change;
   - `os/verification/scripts/validate_agentos.py` when a deterministic invariant should be
     checked locally;
   - `os/verification/source-routing/fixtures.json` when route coverage or a
     source-routing smoke example should be replayable.
7. Add or update a smoke example. It must be safe, local, and specific enough for a future agent to tell whether the new behavior still routes and behaves.
8. Verify. Run the relevant local validator and any skill-specific checks before calling the workflow complete.

## Code Vs Markdown Decision

Extract deterministic code when all are true:

- the input shape is stable enough to parse;
- the expected outcome is objective;
- a script would fail faster and more reliably than model reasoning;
- the check can run without network calls or private external account reads.

Keep the behavior as Markdown guidance when:

- the decision depends on taste, user preference, prioritization, or context;
- examples are too few to justify a rigid check;
- the right behavior is to ask the user before acting;
- the failure is about judgment rather than exact state.

## File Conventions

- Exported Core skills live under `os/skills/<skill-name>/SKILL.md` and appear in `os/skills/MANIFEST.md`.
- Private modules inside an exported skill use `INTERFACE.md` and `IMPLEMENTATION.md` when they need a caller-visible contract separate from execution details.
- Skill contract metadata lives with the skill or a skill-local provenance/governance file; current-machine Core skill exposure checks live in `os/skills/expose-skills/`.
- Resolver changes live in `os/RESOLVER.md` or the narrow directory resolver.
- Deterministic local checks live in `os/verification/scripts/validate_agentos.py` unless a separate script is clearly warranted.
- Source-routing and smoke fixtures live under `os/verification/source-routing/`.
- Private, tentative, or pre-issue durable update proposals live in `personal/os/memory/propagation-review/QUEUE.md`; public-safe actionable project work belongs in the relevant issue tracker or mapped project.

Do not duplicate the same rule across layers. Put the canonical rule in the narrowest stable home and link to it elsewhere.

## Quality Bar

- The workflow is grounded in at least one concrete example.
- The resulting artifact is narrower than the repeated problem, not a generic framework for its own sake.
- Deterministic checks cover exact invariants and avoid external network calls.
- Skill and export-map updates remain consistent with `os/skills/SKILL_CONTRACT.md`.
- Smoke examples are safe to run locally and do not contain private data.
- Resolver edits stay small and preserve the resolver's role as a policy spine, not a skill catalog.

## Verification

Before finishing:

1. Confirm the concrete example is named in the work summary or encoded in a smoke fixture.
2. Confirm `os/skills/MANIFEST.md` reflects any exported skill set changes.
3. Confirm resolver or directory-resolver edits were made only for real tie-breakers.
4. Run `scripts/run-validator`.
5. If the validator changed, also run `scripts/run-validator --self-test`.
6. Run any skill-specific verification named by the changed skill.
7. Confirm no private connector data, literal private contact details, or external write happened outside the applicable external-write policy.
