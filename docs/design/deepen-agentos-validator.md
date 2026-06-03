# Deepen AgentOS Validator

Design readiness: ready to implement

## Problem

`os/verification/scripts/validate_agentos.py` already checks AgentOS structure, publication safety, privacy markers, benchmark manifest shape, source-routing fixtures, skill frontmatter, and basic skills-manifest consistency.

The script has grown into a roughly 3k-line monolith. That makes the validator harder to audit, harder to extend safely, and harder to keep aligned with AgentOS's thin-script habit. The main validator should coordinate smaller helper validators instead of owning every structural, publication, privacy, skill, benchmark, and self-test detail in one file.

While touching the file, the skills manifest also has a partially documented deterministic-check surface that is worth preserving: a malformed entry can still use an unsupported contract status, an unsupported mutability level, placeholder safety or filing text, or a stale summary count while satisfying minimal field-presence checks.

## Desired Behavior

Deepen the validator by splitting it into focused Python modules, each less than 1k lines. The default validator should continue to be deterministic, local-only, and fast enough for CI.

The main `os/verification/scripts/validate_agentos.py` entrypoint should:

- parse CLI arguments;
- create the shared validation context;
- call helper validators for structural, publication/privacy, skills, and self-test work;
- avoid owning large check implementations directly.

Helper validator modules should share common path, git, redaction, reporting, and loader utilities without duplicating that code.

For `os/skills/MANIFEST.md`, the validator should additionally catch:

- summary count drift from the actual number of canonical manifest entries;
- unsupported `Contract status` values outside the statuses documented by `os/skills/SKILL_CONTRACT.md`;
- unsupported `Mutability` levels outside the contract's mutability vocabulary;
- placeholder metadata such as `none`, `n/a`, `tbd`, or `safe` in required operational fields;
- mutating skills whose safety posture does not visibly name approval, explicit authorization, permission, or a default dry-run gate.

## Chosen Design

Create `os/verification/scripts/agentos_validator/` as the helper package.

Use these modules:

- `common.py` for bootstrap loading, shared constants, `Finding`, redaction, local git/path helpers, text reads, and reporting.
- `managed.py` for managed symlink policy checks.
- `publication.py` for publication precheck, public export, Personal Overlay ignore/tracking, privacy marker, generated-output, and secret-like token checks.
- `skills.py` for skills manifest, skill frontmatter, and full-skill contract checks.
- `structural.py` for Markdown portability, source map, agent, automation, resolver, PR readiness, source-routing fixture, and benchmark-manifest checks.
- `self_test.py` for the shared temporary-directory harness, expectation aggregation, and self-test orchestration.

Each helper module owns a local `run_self_test(harness)` section for the checks it implements. `self_test.py` imports those module-owned self-tests, runs them through a shared harness, and prints one consolidated pass/fail report. This keeps fixture ownership next to production validator code without duplicating temp-root setup or result formatting.

The main validator composes these helper validators and delegates individual check methods to them so existing check calls and external validator behavior stay stable. For `--self-test`, the main validator calls the self-test orchestrator rather than knowing each module's fixture list directly.

Keep every validator-family Python file under 1k lines.

For the skills-manifest deepening, extend `check_skills_manifest_consistency()` with small helper methods rather than adding a second manifest parser.

Keep checks intentionally mechanical:

- parse the existing Markdown API only;
- normalize punctuation and code spans already handled by `extract_field()`;
- treat the prefix before `:`, `;`, or `.` as the mutability level;
- fail placeholder field values exactly, not by broad natural-language interpretation;
- use a short approval-keyword heuristic only for non-read-only mutability levels.

## Scope

In scope:

- `os/verification/scripts/validate_agentos.py`;
- helper modules under `os/verification/scripts/agentos_validator/`;
- module-owned validator self-test fixtures;
- the shared self-test harness/orchestrator;
- this design note.

Out of scope:

- rewriting skills or manifest entries beyond what the new validator requires;
- adding connector reads, network calls, or current-machine exposure checks;
- validating the quality of every skill's prose;
- moving the manifest to YAML, JSON, or another structured sidecar.

## Acceptance Criteria

- Every validator-family Python file is under 1k lines.
- The main validator entrypoint calls out to focused helper validators.
- Each helper validator file has its own self-test section for its check family.
- `self_test.py` stays a small orchestrator rather than becoming the new mini-monolith.
- `scripts/run-validator` passes on the current checkout.
- `scripts/run-validator --self-test` proves the new checks catch bad fixtures.
- Existing public-safe manifest entries remain valid without broad wording churn.
- New checks remain local-only and avoid scanning Personal Overlay private content beyond existing validator behavior.

## Validation Plan

- Run `scripts/run-validator --self-test`.
- Run `scripts/run-validator`.
- Run a line-count check for `os/verification/scripts/validate_agentos.py` and `os/verification/scripts/agentos_validator/*.py`.
- Inspect `git diff` to confirm the implementation stays scoped to the validator and design note.
