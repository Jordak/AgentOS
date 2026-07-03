# AgentOS Skills Manifest

Status: Core export map v2.

This manifest is the hand-authored export interface for AgentOS Core skills. It identifies which skill modules are intentionally exported for harness/global discovery, distribution, validation, and current-machine exposure.

Per-skill invocation and execution truth belongs with each exported skill: `SKILL.md` frontmatter is the harness-facing invocation interface, the `SKILL.md` body is the implementation entrypoint and workflow contract, and `UPSTREAM.md` is the source of truth for vendored provenance. Private skill modules introduced under exported skills use plain Markdown module files such as `INTERFACE.md` and `IMPLEMENTATION.md`; they are intentionally absent from this export map unless they become exported skills.

Machine-local exposure state and private live skill adapters belong outside portable Core metadata. Use `personal/os/skills/<skill-name>/CONFIG.md` for private live inputs to Core skills.

Contract reference: `os/skills/SKILL_CONTRACT.md`.

## Summary

- Exported Core skills: 27.

## Markdown API

This manifest stays Markdown-first. The stable machine-readable convention is intentionally narrow:

- Each exported skill entry uses an exact third-level heading shaped as ``### `skill-name` ``.
- Required metadata uses exact, case-sensitive Markdown list labels shaped as `- Field name: value`.
- `Canonical source` values are root-relative AgentOS paths to exported `SKILL.md` files, usually in a code span.
- Long-form safety, filing, verification, provenance, and maintenance facts remain with the skill contract, skill-local provenance files, generated reports, or future sidecars only when typed automation needs them.

Validators and exposure helpers may parse only this narrow convention. Do not migrate this manifest back into a duplicated per-skill registry unless multiple scripts need typed data, cross-field validation, generated machine output, or query/sort/merge behavior that cannot be derived from skill-local sources.

## Export Fields

Each exported skill entry records:

- Canonical source.
- Export group.
- Export status.
- Summary.

Allowed `Export status` values are `exported`, `transitional`, `deprecated`, and `explicit-only`.

## Exported Skills

### `audit-issues`

- Canonical source: `os/skills/audit-issues/SKILL.md`
- Export group: github-workflow.
- Export status: exported.
- Summary: Audit a project's issue tracker against merged code, local evidence, and current project state, then recommend or perform tracker updates such as status comments, closure, labels, or follow-up notes. Use when the user asks to audit issues, reconcile stale GitHub issues, post automated issue status updates, identify issues already implemented on origin main, or close verified completed issues.

### `github-issue-lifecycle`

- Canonical source: `os/skills/github-issue-lifecycle/SKILL.md`
- Export group: github-issue-lifecycle.
- Export status: exported.
- Summary: Route GitHub issue lifecycle work from issue selection through batch coordination, one-issue implementation, PR review handoff, and authorized issue landing.

### `ensure-implementation-readiness`

- Canonical source: `os/skills/ensure-implementation-readiness/SKILL.md`
- Export group: implementation-readiness.
- Export status: exported.
- Summary: Use before implementing feature-sized work: implement, build, add, redesign, substantially refactor, or start an issue/PRD/spec where the outcome changes behavior, workflow, data model, public docs policy, validation policy, or reusable AgentOS structure. Ensures durable design consensus when possible, creates required follow-up artifacts for deferred questions, and returns Ready to Implement, Needs Design Consensus, or Gate Skipped.

### `codebase-design`

- Canonical source: `os/skills/codebase-design/SKILL.md`
- Export group: design-consensus.
- Export status: exported.
- Summary: Shared vocabulary for designing deep modules. Use when the user wants to design or improve a module's interface, find deepening opportunities, decide where a seam goes, make code more testable or AI-navigable, or when another skill needs the deep-module vocabulary.

### `domain-modeling`

- Canonical source: `os/skills/domain-modeling/SKILL.md`
- Export group: design-consensus.
- Export status: exported.
- Summary: Build and sharpen a project's domain model. Use when the user wants to pin down domain terminology or a ubiquitous language, record an architectural decision, or when another skill needs to maintain the domain model.

### `grill-me`

- Canonical source: `os/skills/grill-me/SKILL.md`
- Export group: design-consensus.
- Export status: exported.
- Summary: A relentless interview to sharpen a plan or design.

### `grill-with-docs`

- Canonical source: `os/skills/grill-with-docs/SKILL.md`
- Export group: design-consensus.
- Export status: exported.
- Summary: A relentless interview to sharpen a plan or design, which also creates docs (ADR's and glossary) as we go.

### `grilling`

- Canonical source: `os/skills/grilling/SKILL.md`
- Export group: design-consensus.
- Export status: exported.
- Summary: Interview the user relentlessly about a plan or design. Use when the user wants to stress-test a plan before building, or uses any 'grill' trigger phrases.

### `vendor-skill`

- Canonical source: `os/skills/vendor-skill/SKILL.md`
- Export group: skill-governance.
- Export status: exported.
- Summary: Vendor a public GitHub skill into AgentOS Core with source-first provenance, license-first safety, honest export-map membership, and validation. Use when importing, refreshing, or correcting a reusable Core skill from an upstream repository.

### `refresh-benchmark-status`

- Canonical source: `os/skills/refresh-benchmark-status/SKILL.md`
- Export group: verification.
- Export status: exported.
- Summary: Refresh AgentOS Core's public-safe benchmark status snapshot from eligible local Personal Overlay benchmark evidence. Use when the user asks to refresh, update, compare, or inspect Core benchmark status, or asks whether local benchmark runs mean `os/verification/BENCHMARK_STATUS.md` should change.

### `run-benchmarks`

- Canonical source: `os/skills/run-benchmarks/SKILL.md`
- Export group: verification.
- Export status: exported.
- Summary: Run AgentOS benchmark scripts from the benchmark manifest, save status-eligible evidence for current status targets when possible, and route the result through `refresh-benchmark-status`. Use when the user asks to run AgentOS benchmarks, run all benchmarks, produce fresh benchmark evidence, or run benchmarks and refresh Core benchmark status.

### `expose-skills`

- Canonical source: `os/skills/expose-skills/SKILL.md`
- Export group: skill-governance.
- Export status: exported.
- Summary: Expose AgentOS Core skills to the global harness skill root with symlink adapters. Use when checking, planning, or applying discoverable skill exposure for AgentOS skills, especially replacing copy-based exposure with adapter links.

### `thermo-nuclear-code-quality-review`

- Canonical source: `os/skills/thermo-nuclear-code-quality-review/SKILL.md`
- Export group: review-convergence.
- Export status: exported.
- Summary: Run an extremely strict maintainability review for abstraction quality, giant files, and spaghetti-condition growth. Use for a thermo-nuclear code quality review, thermonuclear review, deep code quality audit, or especially harsh maintainability review.

### `thermo-nuclear-review`

- Canonical source: `os/skills/thermo-nuclear-review/SKILL.md`
- Export group: review-convergence.
- Export status: exported.
- Summary: Run a rigorous correctness, security, developer-experience, and feature-gate-leak audit of a branch or PR diff. Use for thermo nuclear review, thermonuclear review, deep review, security/correctness branch audits, or harsh bug/regression review.

### `improve-codebase-architecture`

- Canonical source: `os/skills/improve-codebase-architecture/SKILL.md`
- Export group: design-consensus.
- Export status: exported.
- Summary: Scan a codebase for deepening opportunities, present them as a visual HTML report, then grill through whichever one you pick.

### `check-vendored-skill-upstreams`

- Canonical source: `os/skills/check-vendored-skill-upstreams/SKILL.md`
- Export group: skill-governance.
- Export status: exported.
- Summary: Check AgentOS Core skills with `UPSTREAM.md` provenance files against their upstream GitHub sources. Use when manually auditing vendored skill freshness, preparing Weekly AgentOS Review, or deciding whether vendored skills need a reviewed update PR.

### `review-pass`

- Canonical source: `os/skills/review-pass/SKILL.md`
- Export group: review-convergence.
- Export status: exported.
- Summary: Run one read-only review panel pass for a PR, branch/base pair, commit range, patch, or local change set and return a structured Markdown review packet. Use when the user wants a single manual review iteration, fresh-context reviewer panel, verification pass after fixes, lens-based code review, design or issue compliance review, architecture-depth/code-judo review, or when an authorized Calling Workflow needs reviewer-panel mechanics without owning them directly.

### `review-loop`

- Canonical source: `os/skills/review-loop/SKILL.md`
- Export group: review-convergence.
- Export status: exported.
- Summary: Orchestrate iterative code-review loops for a PR, branch, commit range, or patch by delegating fresh and verification panel passes to review-pass, conservatively adjudicating issue families, applying and pushing `auto-fix` and `user-approved-fix` fixes, posting consolidated Agent Review comments, producing a temporary HTML report, and marking a PR ready for human review. Use when the user asks for an automated review loop, fresh-context PR review/fix panel, repeated agent review/fix cycle, reviewer subagent loop, "Agent Review" PR comments, or to review a PR or commit until clean.

### `run-agentos-doctor`

- Canonical source: `os/skills/run-agentos-doctor/SKILL.md`
- Export group: verification.
- Export status: exported.
- Summary: Run AgentOS setup health checks using a thin deterministic fact-collector plus agent judgment for ambiguous local state. Use when the user asks to run AgentOS Doctor, audit AgentOS setup health, check whether AgentOS is wired up correctly, inspect adapters, Core skill exposure, Personal Overlay starter files, or recurring AgentOS update/drift checks.

### `double-steelman`

- Canonical source: `os/skills/double-steelman/SKILL.md`
- Export group: design-consensus.
- Export status: exported.
- Summary: Construct the strongest honest case for every viable side of a decision, argument, plan, or tradeoff, then expose the cruxes that matter most and recommend a path by default. Use when the user asks to double-steelman, compare options, make a life decision, evaluate a technical architecture choice, stress-test a position, or hear the best arguments for both or all sides before deciding.

### `make-temp-file`

- Canonical source: `os/skills/make-temp-file/SKILL.md`
- Export group: utility.
- Export status: exported.
- Summary: Create temporary files with a safe prefix and extension using a bundled Bash helper. Use when the user says "make a temp file", "create a temporary file", asks for a temp path, or requests a temporary file with a specific prefix or extension such as JSON, Markdown, CSV, or log.

### `meeting-notes`

- Canonical source: `os/skills/meeting-notes/SKILL.md`
- Export group: artifact-workflow.
- Export status: exported.
- Summary: Turn user-provided notes, transcripts, or rough bullets into faithful meeting notes with decisions, action items, open questions, and optional follow-up drafts. Use when the user asks to summarize meeting material, extract decisions, or prepare meeting follow-up without inventing owners, dates, or commitments.

### `research-brief`

- Canonical source: `os/skills/research-brief/SKILL.md`
- Export group: artifact-workflow.
- Export status: exported.
- Summary: Research and synthesize a topic using current official or primary sources when needed, separating facts from inference and returning evidence, caveats, and a concrete next step. Use when the user asks for research, current tool guidance, market context, vendor comparison, or documentation synthesis.

### `skillify-agentos`

- Canonical source: `os/skills/skillify-agentos/SKILL.md`
- Export group: skill-governance.
- Export status: exported.
- Summary: Turn repeated AgentOS tasks, repeated agent failures, or recurring manual checks into durable skills, resolver guidance, deterministic validators, and smoke examples. Use when the user asks to skillify a workflow, encode a repeated miss, make a reusable AgentOS behavior, or stop relying on memory/discipline for a recurring pattern.

### `promote-private-skill-to-core`

- Canonical source: `os/skills/promote-private-skill-to-core/SKILL.md`
- Export group: skill-governance.
- Export status: exported.
- Summary: Design, audit, or perform an approved promotion of a maintained Personal Overlay skill into an AgentOS Core-safe skill by separating reusable workflow from private identity, account, path, project, live-agent, generated-output, and local configuration details.

### `verify-privacy`

- Canonical source: `os/skills/verify-privacy/SKILL.md`
- Export group: verification.
- Export status: exported.
- Summary: Audit a repository, project directory, publishable file set, or release candidate for private, personal, secret, machine-local, or otherwise nonpublishable content. Use when preparing AgentOS or another repo for publication, reviewing Core/Personal Overlay separation, checking whether private facts leaked into publishable files, validating privacy markers, or producing a privacy findings report before commit or release.

### `weekly-update`

- Canonical source: `os/skills/weekly-update/SKILL.md`
- Export group: artifact-workflow.
- Export status: exported.
- Summary: Draft concise weekly updates, status reports, or check-ins from supplied facts and local AgentOS context without inventing progress, blockers, owners, dates, or commitments. Use when the user asks for a weekly update, weekly summary, status report, or check-in draft.
