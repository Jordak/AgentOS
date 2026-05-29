---
name: skillify-agentos
description: "Turn repeated AgentOS tasks, repeated agent failures, or recurring manual checks into durable skills, resolver guidance, deterministic validators, and smoke examples. Use when the user asks to skillify a workflow, encode a repeated miss, make a reusable AgentOS behavior, or stop relying on memory/discipline for a recurring pattern."
---

# Skillify AgentOS

## Trigger

Use this when the user asks to "skillify" something, when the same AgentOS task has appeared more than once, when an agent repeats a correctable miss, or when a manual verification chore should become reusable behavior.

Do not use this for one-off preferences, speculative abstractions, or project implementation details that belong in a mapped project.

## Goal

Turn real repeated work into durable AgentOS behavior with the smallest stable artifact that will prevent the repeated cost or failure.

The output may be a skill update, a new skill, resolver guidance, manifest maintenance, a deterministic validator, a routing fixture, or a propagation queue proposal. The default is the least machinery that makes the future run better.

## Contract

Inputs:

- At least one concrete example of the repeated task, repeated failure, or manual check. If no example exists, ask for one or stop with a proposed observation to watch.
- The current AgentOS resolver, skills resolver, skill contract, skills manifest, verification checklist, and relevant existing skill or agent files.
- Any issue, report, transcript, failed run, validator output, or user correction that shows the pattern.

Output artifact:

- A new or updated AgentOS skill, resolver entry, manifest entry, deterministic validator, retrieval fixture, smoke example, or review-queue proposal.
- A short implementation summary naming what changed and how it was verified.

Mutability:

- Local-write. This workflow may edit AgentOS Markdown files and local scripts.
- External-write only if the user explicitly asks for GitHub issue edits, comments, labels, or other external state changes, approves the proposed write, or a matching Personal Overlay GitHub allowance permits the specific write type for the target repository.

Tools and connectors:

- Local filesystem for AgentOS files.
- `rg`, `git`, and local validators for inspection and verification.
- GitHub issue context only when the skillification is issue-driven.
- No external account data is needed by default.

Safety:

- Ask before external sends, public posts, permission changes, automation activation, destructive edits, or connector writes not already authorized by the current request, approved by the user, or covered by a matching Personal Overlay GitHub allowance.
- Do not copy private connector data into skills, smoke examples, validators, or memory.
- Do not install a harness mirror unless the issue or the user explicitly asks for discoverability outside the AgentOS workspace.
- Use a propagation queue entry instead of canonical edits when the durable change is plausible but not approved.

## Workflow Phases

1. Gather examples: capture at least one concrete prompt, failure, report, diff, validator output, or manual checklist step. Prefer two examples before adding broad abstractions.
2. Classify the pattern:
   - repeated task -> skill or existing skill update;
   - repeated failure -> skill/resolver/checklist update plus smoke example;
   - exact manual check -> deterministic validator;
   - ambiguous filing/routing miss -> resolver, directory resolver, or routing
     eval fixture;
   - unapproved durable state proposal -> propagation review queue.
3. Choose the smallest durable artifact. Update an existing skill before adding a new one when the trigger, workflow, and output are already owned by that skill.
4. Decide code vs Markdown:
   - use deterministic code when the check is exact, repeated, and cheaply
     machine-verifiable;
   - use Markdown process guidance when judgment, context, or user preference is
     central;
   - use both when a validator should enforce the mechanical parts and a skill
     should explain the judgment.
5. Apply the AgentOS skill contract. New or materially changed skills must name inputs, output artifact, mutability, tools/connectors, safety, phases, quality bar, verification, and filing rules.
6. Update maintenance surfaces:
   - `os/skills/MANIFEST.md` for any skill add/update;
   - `os/skills/mirror-skills/SKILL.md` when current-machine mirror
     audit or sync behavior changes;
   - `os/RESOLVER.md` only when lookup, routing, authority, safety, or filing
     tie-breakers change;
   - `os/verification/scripts/validate_agentos.py` when a deterministic invariant should be
     checked locally;
   - `os/verification/retrieval/fixtures.json` when route coverage or a
     retrieval smoke example should be replayable.
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

- Canonical skills live under `os/skills/`.
- Skill contract metadata lives in `os/skills/MANIFEST.md`; current-machine mirror checks live in `os/skills/mirror-skills/`.
- Resolver changes live in `os/RESOLVER.md` or the narrow directory resolver.
- Deterministic local checks live in `os/verification/scripts/validate_agentos.py` unless a separate script is clearly warranted.
- Retrieval and smoke fixtures live under `os/verification/retrieval/`.
- Proposed but unapproved durable updates live in `personal/os/memory/propagation-review/QUEUE.md`.

Do not duplicate the same rule across layers. Put the canonical rule in the narrowest stable home and link to it elsewhere.

## Quality Bar

- The workflow is grounded in at least one concrete example.
- The resulting artifact is narrower than the repeated problem, not a generic framework for its own sake.
- Deterministic checks cover exact invariants and avoid external network calls.
- Skill and manifest updates remain consistent with `os/skills/SKILL_CONTRACT.md`.
- Smoke examples are safe to run locally and do not contain private data.
- Resolver edits stay small and preserve the resolver's role as a policy spine, not a skill catalog.

## Verification

Before finishing:

1. Confirm the concrete example is named in the work summary or encoded in a smoke fixture.
2. Confirm `os/skills/MANIFEST.md` reflects any skill changes.
3. Confirm resolver or directory-resolver edits were made only for real tie-breakers.
4. Run `scripts/run-validator`.
5. If the validator changed, also run `scripts/run-validator --self-test`.
6. Run any skill-specific verification named by the changed skill.
7. Confirm no private connector data, literal private contact details, or external write happened without current-request authorization, approval, or a matching Personal Overlay GitHub allowance.
