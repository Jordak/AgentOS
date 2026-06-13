# AgentOS Publishing Architecture

This domain model defines the language for separating AgentOS into reusable publishable scaffolding and private user-specific state.

## Language

**AgentOS Core**:
The publishable, reusable AgentOS framework under the Core Root: layer structure, playbooks, templates, validators, skills, and agent/job patterns that do not depend on user-specific facts.
_Avoid_: public repo, whole repository, sanitized snapshot, starter template

**Core Root**:
The tracked directory root for AgentOS Core, written as `$root/os/`.
_Avoid_: public folder, main OS folder, whole repository

**Publication Candidate**:
A sanitized filesystem tree used as an optional final dry run before creating the public AgentOS repository from fresh Git history.
_Avoid_: backup, current private repo, sanitized branch

**Publishable File Set**:
The Git-visible AgentOS files that can become the fresh public initial commit after the Publication Precheck passes, including AgentOS Core, public-safe root support files, public-safe repository support directories, and the tracked Personal Overlay skeleton.
_Avoid_: raw working directory, ignored overlay files

**Publishable Support File**:
A Git-visible public-safe file or directory outside the Core Root that supports repository discovery, adapters, documentation, governance, CI, validation, installation, or publication.
_Avoid_: Core file, Personal Overlay file, root noise

**AgentOS-Managed File Set**:
The repository paths AgentOS tools and policies treat as managed for structural checks such as symlink, publication, export, and validation rules; broader than AgentOS Core, narrower than every local filesystem entry.
_Avoid_: raw filesystem tree, ignored local artifacts, only Core

**Export Script**:
A deterministic script that builds an optional Publication Candidate from the allowlisted Publishable File Set.
_Avoid_: manual public copy

**Fresh-History Publication**:
The rule that public AgentOS is created from a new initial commit built from the prechecked Publishable File Set, not by making the current private repository public.
_Avoid_: history rewrite, publicize private repo

**Publication Gate**:
The sequencing rule that repo deletion, replacement, public creation, or visibility changes wait until migration and validation are complete.
_Avoid_: publish while migrating

**Privacy Validator**:
A deterministic verification step that checks the working tree and Publishable File Set against AgentOS Core rules, public-safe support-file rules, Personal Overlay skeleton rules, `.gitignore` coverage, and known private markers.
_Avoid_: LLM privacy vibes, private-looking file detector

**Guidance**:
A benchmark style that asks an AgentOS scenario question and grades whether the answer makes the policy decision required by the relevant AgentOS guidance source. It evaluates guidance-shaped behavior, not transcript-level file access.
_Avoid_: guidance decision verification, playbook decision verification, source lookup benchmark, transcript access check

**Judge-Assisted Grading**:
A benchmark grading mode where a grader agent receives the scenario, harness answer, expected solution, grading rubric, and references to relevant AgentOS guidance sources, then returns a structured verdict with rationale.
_Avoid_: deterministic answer parser, exact prose matcher

**Fixture Staleness**:
A benchmark failure mode where a fixture's expected solution no longer matches the current AgentOS guidance source it references.
_Avoid_: flaky answer, bad model run

**Guidance Verdict**:
The judge-produced structured outcome for a Guidance fixture: `pass`, `fail`, `fixture_stale`, or `needs_user_judgment`. Only `pass`, `fail`, and `fixture_stale` are status-counting outcomes; `needs_user_judgment` is an ineligible escalation state until the user resolves it.
_Avoid_: partial credit, numeric grade

**Needs User Judgment**:
An ineligible judge-assisted grading state where the grader cannot fairly decide a Guidance fixture and escalates the scenario, harness answer, expected solution, current guidance source, and uncertainty reason to the user.
_Avoid_: final uncertain verdict, hidden tie-break

**Source Alignment**:
A diagnostic judgment in Guidance that records whether the harness answer named or used the expected guidance source correctly, without controlling the final Guidance Verdict.
_Avoid_: citation pass/fail gate

**Managed Path**:
A filesystem path that a trusted AgentOS script treats as part of an AgentOS-managed tree for reading, writing, copying, syncing, or validation. Managed Paths must stay under their declared root and must not silently traverse symbolic-link components beneath that root. The declared root is the caller-chosen trust boundary and must itself be a non-symlink directory; ancestor symlinks of that root are a root-selection concern rather than a Managed Path concern.
_Avoid_: arbitrary local path, resolved target

**Path Resolution Module**:
A trusted-script module that answers a policy-shaped path question, such as whether a Managed Path is safe under a declared root, while hiding lexical path normalization, containment checks, `lstat()` facts, and component walking behind its interface.
_Avoid_: path utility bag, public primitive helpers

**Private Path Primitive**:
An implementation detail used inside Path Resolution Modules for reusable filesystem mechanics such as lexical absolute paths, relative containment, and no-follow component walking.
_Avoid_: public path helper

**Publication Precheck**:
A deterministic release gate against the mixed local working tree that catches migration mistakes before creating the fresh public initial commit.
_Avoid_: candidate-only validation

**Publication Candidate Validation**:
A deterministic final dry-run check that verifies the generated Publication Candidate contains only publishable files.
_Avoid_: primary publication gate

**Private GitHub Archive**:
A Personal Overlay archive of issue, PR, settings, or planning state preserved from the old private GitHub repository before deletion or replacement.
_Avoid_: public issue import

**Local Overlay**:
The v1 Personal Overlay posture where private overlay files live as ignored local state and AgentOS Core defines no remote versioning policy for them.
_Avoid_: private overlay repo, remote overlay

**Domain File**:
The Markdown file that defines a repository's domain language, relationships, and flagged ambiguities.
_Avoid_: context file

**Personal Overlay**:
The private user-specific layer that supplies identity, preferences, memories, connections, source pointers, reports, and other non-publishable state to an AgentOS Core checkout.
_Avoid_: private info, ignored stuff, secrets

**Overlay Mirror**:
A top-level directory tree whose paths mirror AgentOS Core paths, with marker files tracked for directory shape and ordinary files ignored as private overlay content.
_Avoid_: nested personal folders, scattered private dirs

**Tracked Overlay Skeleton**:
The public-safe empty `.gitkeep` marker set under `$root/personal/` that preserves generic Personal Overlay directories without tracking private files or private-specific directory names.
_Avoid_: full private directory tree, tracked personal paths

**Additive Overlay**:
A Personal Overlay merge mode where Core files are read first and matching personal files are read after them, with personal content taking precedence only where the two conflict.
_Avoid_: shadow replacement, private fork

**Layer Parity**:
The rule that AgentOS Core and the Personal Overlay use the same AgentOS layer names and directory shape.
_Avoid_: personal-only layers, core-only layers

**Content Residency**:
The rule that publishability is determined per file by whether the file belongs in AgentOS Core or the Personal Overlay, not by which AgentOS layer contains it.
_Avoid_: layer ownership

**Core Default**:
A publishable AgentOS Core file that is safe and useful as-is for any user.
_Avoid_: generic template, placeholder

**Personal Template**:
A publishable AgentOS Core file ending in `.template.md` that describes the shape of a personal file without pretending to contain real user state.
_Avoid_: fake default, sample personal data

**Private Generated Output**:
A report, brief, history, log, or other artifact produced from a real person's private data, project state, memory, interests, accounts, or work context.
_Avoid_: report, artifact

**Example Output**:
A sanitized artifact in AgentOS Core that demonstrates expected output shape without using real private state.
_Avoid_: sample from private data

**Live Agent Instance**:
A named agent configured around a real person's interests, routines, connected-account assumptions, private output paths, or personal project state.
_Avoid_: agent template, generic agent

**Agent Template**:
A publishable AgentOS Core agent scaffold or sanitized example that demonstrates how to define a durable role without depending on real private state.
_Avoid_: live agent

**Core Skill**:
A publishable reusable skill procedure, safety contract, and verification workflow that does not require private user-specific inputs to understand.
_Avoid_: private skill

**Orchestration Loop**:
A workflow that coordinates repeated steps, delegated workflows, tools, agents, or human decisions toward a convergence condition.
_Avoid_: generic loop, one-off checklist, child workflow

**Calling Workflow**:
The workflow that delegates work in a specific invocation relationship. A workflow can be a Calling Workflow in one relationship and a Called Workflow in another.
_Avoid_: parent loop as a permanent classification

**Called Workflow**:
The workflow being delegated to in a specific invocation relationship. A Called Workflow may itself be an Orchestration Loop.
_Avoid_: child workflow as a permanent classification

**Authorization Boundary**:
The effective mutation permission for a workflow invocation. If a Calling Workflow provides no explicit Authorization Boundary, the Called Workflow's own contract is the default boundary.
_Avoid_: blanket permission, silent permission expansion

**Recovery Record**:
The minimum durable or reconstructable state a Calling Workflow needs to resume safely after a pause, compaction, handoff, or Called Workflow completion. A Recovery Record is an obligation to preserve recoverability, not necessarily a separate file format.
_Avoid_: mandatory ledger file, chat memory

**Recovery Checkpoint**:
A durable write or update that preserves the current Recovery Record, or enough of it to resume safely from the checkpointed phase.
_Avoid_: compaction summary, model memory

**Blocking Human Decision**:
A human decision that must be resolved before an Orchestration Loop can safely continue along its current path.
_Avoid_: human decision blocker, vague HITL need

**Workflow Result**:
The return shape a Called Workflow provides to its Calling Workflow, containing enough status, evidence, mutation, validation, risk, decision, and next-action information for the Calling Workflow to continue safely. A Workflow Result may be represented by a domain-specific artifact such as a Review Packet.
_Avoid_: raw output, unstructured transcript dump

**Workflow Invocation Reference**:
The callback or coordination reference a Calling Workflow gives to a Called Workflow for one invocation, such as a callback thread id, child-thread URL, ledger location, issue or PR comment surface, or local report path.
_Avoid_: hidden worker handle, informal callback note

**Callback-First Invocation**:
The orchestration rule that durable Called Workflows receive a Workflow Invocation Reference and report completed, blocked, failed, cancelled, or needs-human states back through that reference instead of relying on continuous polling by the Calling Workflow.
_Avoid_: live worker monitoring, supervisor polling

**Minimal Assignment Packet**:
A pointer-first launch message that gives a Called Workflow only the invocation-specific target, callback reference, boundaries, required durable sources, validation expectations, expected result, release instruction, and prohibited actions.
_Avoid_: universal worker prompt, copied skill contract

**Effort Recommendation**:
The model-effort level a workflow would prefer for an invocation when the active harness supports such control. It is an invocation-level intention, not a guarantee that a live thread can switch effort repeatedly inside one turn.
_Avoid_: guaranteed runtime effort, mandatory thread setting

**Prescribed Effort**:
The model effort requested by a workflow default, Calling Workflow override, user instruction, custom-agent configuration, or platform default.
_Avoid_: actual effort

**Effective Effort**:
The model effort actually used for a workflow invocation when it is observable, including inherited same-thread effort, platform-selected effort, custom-agent override, user override, unsupported/degraded effort, unknown, or not reported.
_Avoid_: prescribed effort

**Isolation Boundary**:
The scope that lets a Calling Workflow run Called Workflows concurrently without uncoordinated mutation of the same surface. An Isolation Boundary may be an issue, task, branch and worktree, PR, artifact, domain or module area, read-only lane, or explicit non-overlap assumption with conflict-resolution.
_Avoid_: mandatory file ownership, shared mutable checkout

**Integration Ownership**:
The contract-defined responsibility to bring a workflow target to its completed, landed, closed, ready, or otherwise integrated state.
_Avoid_: role-based closure, opportunistic integration, outermost-loop ownership

**Review Pass**:
One read-only review execution over a target, run in `fresh` or `verification` mode, that assembles a Review Panel and returns a Review Packet. A Review Pass does not edit files, post PR comments, push commits, or decide final disposition.
_Avoid_: review loop, PR review comment, whole review workflow

**Review Panel**:
The cohort of reviewers assembled for one Review Pass. Reviewer aliases use `P<panel-number>-R<reviewer-number>`, where `P` means Review Panel.
_Avoid_: pass, priority, individual reviewer

**Review Packet**:
The structured Markdown output from a Review Pass. It is advisory evidence for a human or caller such as `review-loop`; it is not raw reviewer output, a durable loop ledger, or a PR comment.
_Avoid_: raw findings dump, Agent Review comment, final report

**Reviewer Finding**:
A concrete issue reported by one reviewer during a Review Pass. Reviewer Finding IDs append `F<finding-number>` to the reviewer alias, such as `P1-R2-F3`; `F` means finding.
_Avoid_: issue family, accepted fix, reviewer alias

**Issue Family**:
A normalized group of Reviewer Findings that share a failure mode, invariant, missing validation, API contract risk, privacy risk, UX regression, or structural smell. Review Packet issue-family IDs use `IF<family-number>`, such as `IF1`; `IF` means Issue Family.
_Avoid_: individual finding, reviewer finding ID, fix commit

**Reviewer Continuity**:
Verification-mode evidence about whether a Review Pass resumed the same source reviewer context or used packet/finding-source fallback. Reviewer Continuity records source quality and handle availability without exposing opaque reviewer handles.
_Avoid_: issue-family continuity, per-reviewer table column, handle value

**Personal Skill Config**:
A Personal Overlay file that supplies a Core Skill with private live inputs such as local paths, account IDs, artifact roots, user-specific defaults, or private examples.
_Avoid_: hardcoded path in skill, private example in core

**Structured Config Sidecar**:
A machine-readable Personal Overlay config file used only when scripts need deterministic parsing.
_Avoid_: default config format

**Firewall Template**:
A Core template for documenting employer, client, account, or other sensitive-boundary rules without naming a real private boundary.
_Avoid_: live firewall, private policy

**Migration Atom**:
The smallest safe migration unit: move one private live file to the matching Personal Overlay path, add or preserve its Core Default or Personal Template, and update loader documentation if needed.
_Avoid_: duplicate-and-clean-later

**Move-First Migration**:
The rule that private live files are moved mostly as-is into the Personal Overlay before Core replacements are sanitized or rewritten.
_Avoid_: sanitize-while-moving

**Overlay Root**:
The fixed Personal Overlay directory that agents read after AgentOS Core.
_Avoid_: configurable overlay path, hidden overlay root

**Starter Template**:
A generated or copied starting point derived from AgentOS Core for a new user or project.
_Avoid_: AgentOS Core

## Relationships

- An **AgentOS Core** may be used without a **Personal Overlay**, but with generic placeholders and examples only.
- The **Core Root** is `$root/os/`.
- A **Publishable File Set** is the source for the public GitHub repository and is broader than **AgentOS Core**.
- A **Publishable Support File** may live outside the **Core Root** without broadening **AgentOS Core** to mean the whole repository.
- An **AgentOS-Managed File Set** may include **Publishable Support Files** and any Personal Overlay paths explicitly managed by a bounded script operation.
- A **Publication Candidate** may be generated from the **Publishable File Set** for final inspection.
- An **Export Script** builds the optional **Publication Candidate**; manual assembly is not the dry-run mechanism.
- **Fresh-History Publication** prevents old private Git commits from becoming public.
- The **Publication Gate** prevents repository deletion, replacement, public creation, or visibility changes before the migrated **Publishable File Set** is validated.
- A **Privacy Validator** gates the **Publishable File Set** with deterministic checks; LLM review can supplement it but does not replace it.
- **Guidance** may use AgentOS Core playbooks, skills, resolver rules, or ADR-backed guidance as sources for scenario decisions.
- **Guidance** may use **Judge-Assisted Grading** when answer correctness depends on applying prose guidance rather than matching deterministic strings.
- **Judge-Assisted Grading** can detect **Fixture Staleness** by comparing the expected solution with the referenced current guidance source.
- A **Guidance Verdict** distinguishes harness behavior failure from stale fixtures.
- **Source Alignment** is diagnostic because **Guidance** gates on the guidance-shaped decision rather than citation behavior.
- A trusted script may check a **Managed Path** through a **Path Resolution Module**.
- A **Path Resolution Module** may share **Private Path Primitives** with other path-resolution modules, but callers outside that module family should depend on the policy-shaped path-resolution interface.
- A **Publication Precheck** is the primary local release gate.
- **Publication Candidate Validation** is optional final dry-run evidence.
- A **Private GitHub Archive** preserves old repository planning state before selective public-safe promotion.
- A **Local Overlay** is the v1 posture for Personal Overlay files.
- The root **Domain File** is `DOMAIN.md`.
- A **Personal Overlay** customizes exactly one user's AgentOS experience by layering private state onto **AgentOS Core**.
- An **Overlay Mirror** gives a **Personal Overlay** the same directory shape as **AgentOS Core** while keeping private content files out of git.
- A **Tracked Overlay Skeleton** keeps generic Personal Overlay directories visible while private-specific paths remain ignored.
- An **Additive Overlay** preserves useful standalone **AgentOS Core** defaults while allowing a **Personal Overlay** to extend or override user-specific details.
- **Layer Parity** keeps all AgentOS layers available in both **AgentOS Core** and the **Personal Overlay**.
- **Content Residency** decides whether an individual file is publishable scaffolding or private user-specific state.
- A **Core Default** is loaded directly from **AgentOS Core**.
- A **Personal Template** is copied or used as guidance for a corresponding **Personal Overlay** file.
- A **Private Generated Output** belongs in the **Personal Overlay** by default.
- An **Example Output** may live in **AgentOS Core** when it contains no real private state.
- A **Live Agent Instance** belongs in the **Personal Overlay** by default.
- An **Agent Template** may live in **AgentOS Core**.
- A **Core Skill** may read an optional **Personal Skill Config** from the **Personal Overlay**.
- An **Orchestration Loop** may be a **Calling Workflow** when it delegates work, a **Called Workflow** when another workflow delegates to it, or both across nested invocations.
- An **Authorization Boundary** may narrow a Called Workflow's default contract permissions; it may widen them only when the wider scope is explicitly authorized and supported.
- A **Recovery Record** may be reconstructed from existing durable artifacts such as issues, PR comments, commits, reports, design docs, and chat pause messages; it does not imply a dedicated file.
- A **Recovery Checkpoint** is the act or artifact that makes a Recovery Record durable at a recovery boundary.
- A **Blocking Human Decision** should be captured in a **Recovery Record** before the Orchestration Loop pauses for the human.
- A **Workflow Result** may use a domain-specific artifact name and schema when the Calling Workflow can still extract the generic result fields it needs.
- A **Workflow Invocation Reference** is the callback surface for a **Callback-First Invocation**.
- A **Minimal Assignment Packet** should point to durable task and contract sources rather than copying those sources into the launch message.
- An **Effort Recommendation** may become a **Prescribed Effort** when a workflow or caller requests it for a specific invocation.
- An **Effective Effort** may differ from the **Prescribed Effort** when the active harness inherits, overrides, degrades, or does not report effort.
- An **Isolation Boundary** is required before running parallel Called Workflows that may mutate state.
- **Integration Ownership** belongs to the workflow contract and Authorization Boundary, not inherently to the Calling Workflow or Called Workflow role.
- A **Review Pass** assembles one **Review Panel** and returns one **Review Packet**.
- A **Review Packet** is the **Workflow Result** returned by a **Review Pass**.
- A **Review Packet** groups **Reviewer Findings** into **Issue Families**.
- A **Reviewer Finding** keeps its reviewer-scoped `F` ID even when it is grouped into an **Issue Family**.
- An **Issue Family** may preserve its `IF` ID across verification packets when a prior packet is supplied and the family is clearly the same. New issue families receive new `IF` IDs.
- `P` means panel in **Review Panel** reviewer aliases such as `P1-R2`; `P0` / `P1` / `P2` / `P3` mean severity only when explicitly labeled as severity.
- A **Reviewer Continuity** record belongs in packet-level metadata, not in the Review Panel table.
- A **Personal Skill Config** keeps private live inputs out of reusable skill logic.
- Personal Overlay config is Markdown-first; use a **Structured Config Sidecar** only when automation needs deterministic parsing.
- Live `context` files belong in the **Personal Overlay** by default; AgentOS Core may keep context templates, generic glossary terms, and **Firewall Templates**.
- Live `identity` files belong in the **Personal Overlay** by default; AgentOS Core may keep identity templates and public-safe collaboration guidance.
- Live `memory` files belong in the **Personal Overlay** by default; AgentOS Core may keep memory mechanics, templates, and Core architecture ADRs.
- Live `connections` files belong in the **Personal Overlay** by default; AgentOS Core may keep connection schemas, safety categories, and approval patterns.
- Live `automations` files belong in the **Personal Overlay** by default; AgentOS Core may keep automation schemas, safety policy, and examples.
- Live `verification` reports belong in the **Personal Overlay** by default; AgentOS Core may keep reusable validators, schemas, sanitized fixtures, and sanitized example reports.
- Root adapter files are **Publishable Support Files** when they are generic launchers into **AgentOS Core** and the optional **Personal Overlay**; local adapter install state belongs in the **Personal Overlay**.
- A **Migration Atom** keeps AgentOS publishability from depending on stale duplicate private files.
- **Move-First Migration** preserves private live state while Core replacements are made publishable.
- The **Overlay Root** is `$root/personal/os/` for v1.
- A **Starter Template** can be generated from **AgentOS Core**, but it is not the canonical publishable source.

## Example Dialogue

> **Dev:** "Are we publishing the user's current AgentOS after deleting private files?"
> **Domain expert:** "No. The public repository is built from the **Publishable File Set**, centered on **AgentOS Core**, while user-specific state stays in a **Personal Overlay**."

## Flagged Ambiguities

- "Public repo" was too vague; resolved: the public initial commit is built from the **Publishable File Set**, not from a one-time sanitized snapshot of a private workspace.
- "Context" conflicted with `os/context/`; resolved: domain vocabulary lives in `DOMAIN.md`.
- "Core layer" versus "personal layer" implied layer ownership; resolved: AgentOS uses **Layer Parity** plus **Content Residency**.
- "Core" versus "publishable repository root" was ambiguous; resolved: **AgentOS Core** means the **Core Root** at `$root/os/`, while root-level and sibling compatibility files are **Publishable Support Files** in the broader **Publishable File Set** or **AgentOS-Managed File Set**.
- "P" in review artifacts was ambiguous between priority, pass, and panel; resolved: `P` in reviewer aliases means **Review Panel**, while `P0` / `P1` / `P2` / `P3` are severity values only when labeled as severity.
- "F" in review artifacts was ambiguous between finding and family; resolved: `F` means **Reviewer Finding** and `IF` means **Issue Family**.
- "Playbook Decision Verification" was too narrow; resolved: **Guidance** covers scenario decisions from playbooks and other AgentOS guidance sources without claiming transcript-level file access.
- "Flaky benchmark" was too broad for stale expectations; resolved: **Fixture Staleness** means the expected solution no longer matches current guidance.
