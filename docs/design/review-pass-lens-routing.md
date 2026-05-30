# Review Pass Lens Routing

Design readiness: ready to implement

## Problem

`review-pass` currently embeds substantial lens behavior in `references/reviewer-prompts.md`. That makes every prompt-reference load heavier than necessary, and it blurs the distinction between choosing a lens and expanding the full lens instructions. The `deep-review` and `structural-depth` lenses also say they use vendored skills as source material, but the escalation path from an in-panel lens to a standalone audit workflow could be clearer.

## Current Behavior

- `SKILL.md` defines default reviewer counts and lens spread.
- `references/reviewer-prompts.md` contains the lens catalog, full behavior for `deep-review` and `structural-depth`, prompt templates, packet schema, caller notes, and recovery prompt.
- `deep-review` and `structural-depth` are lenses inside `review-pass`, not automatic invocations of their source skills.
- Larger structural concerns are supposed to become `Design Escape Hatch` findings, but the standalone follow-up workflows are not named as explicit escalation options.

## Desired Behavior

- `SKILL.md` keeps the orchestration contract, default lens spread, activation criteria for heavier lenses, and explicit escalation guidance for standalone review-quality workflows.
- Base prompt templates remain in `references/reviewer-prompts.md`.
- Lens behavior is progressively disclosed from per-lens reference files and loaded only when the lens is assigned.
- The prompt checklist, prompt templates, recovery prompt, and verification checklist all refer to loading assigned lens reference files.
- `structural-depth` explicitly escalates larger architecture/code-quality work to a standalone `improve-codebase-architecture` or `thermo-nuclear-code-quality-review` pass through `Design Escape Hatch`, not by invoking them automatically.
- `deep-review` explicitly escalates larger correctness/security/devex/feature-gate risk to a standalone `thermo-nuclear-review` pass through `Design Escape Hatch`, not by invoking it automatically.

## Chosen Design

Create `references/lenses/` with one Markdown file for each built-in reviewer lens, plus the conditional Contract Surface Matrix lens. Lightweight lenses may stay short, but they still get a file so prompt assembly has a uniform progressive-disclosure rule.

Keep lightweight one-line lens summaries in `reviewer-prompts.md` and put the full additional priorities in the per-lens files. Update `SKILL.md` so lens selection remains possible without loading all lens files, while prompt assembly loads only the files for assigned lenses.

## Alternatives Considered

- Keep all lens instructions in `reviewer-prompts.md`: simpler file structure, but worse context locality as lenses grow.
- Move all lens criteria and behavior out of `SKILL.md`: more modular, but makes lens choice require extra reads and risks inconsistent panel selection.
- Automatically run source skills when a lens is assigned: deeper review, but too much nested workflow, output-shape drift, and surprise scope expansion for `review-pass`.

## Non-Goals

- Do not standardize the Review Packet rendering template in this change.
- Do not create or post a GitHub issue for packet-template standardization in this change.
- Do not change default reviewer counts or the default lens spread.
- Do not alter `review-pass` mutability; it remains read-only except optional temporary packet files.
- Do not run standalone source skills from inside `review-pass`.

## Acceptance Criteria

- Assigned named-lens reviewer prompts load their per-lens reference files.
- Targets that change reusable contract surfaces load the Contract Surface Matrix reference file.
- `reviewer-prompts.md` remains the base prompt/reference entrypoint but no longer contains full long-form lens behavior.
- `SKILL.md` explains when heavier standalone source skills should be recommended instead of automatically invoked.
- `SKILL.md` keeps enough activation criteria to choose lenses without loading every lens file.
- Verification instructions confirm assigned lens files were read and no full source-skill workflow was run.

## Validation Plan

- Inspect the updated files for broken references.
- Run repository validators if available.
- Use `rg` to confirm no stale wording still implies full source-skill orchestration.

## Open Questions

- Packet rendering standardization is out of scope and should get its own design pass, likely a GitHub issue plus a grill session before implementation.

## Deferred Follow-Ups

- Standardize the Review Packet template, severity vocabulary, issue-family ID format, table layout, bolding rules, and empty-section behavior in a dedicated follow-up issue or design doc.
