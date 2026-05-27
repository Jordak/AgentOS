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

**Managed Path**:
A filesystem path that a trusted AgentOS script treats as part of an AgentOS-managed tree for reading, writing, copying, syncing, or validation. Managed Paths must stay under their declared root and must not silently traverse symbolic-link components.
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
