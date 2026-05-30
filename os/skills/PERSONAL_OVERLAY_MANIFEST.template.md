# Personal Overlay Skills Manifest

Status: template.

Use this public-safe template to create the ignored local file at `personal/os/skills/MANIFEST.md` when maintaining private canonical skills or important private config overlays for Core skills.

Personal Overlay skills implement the Core skill contract in `os/skills/SKILL_CONTRACT.md`. This manifest records private governance facts; it is not a routing catalog, invocation surface, exposure registry, source map, or connection inventory.

Do not commit the live `personal/os/skills/MANIFEST.md` file. It may contain private skill names, project references, local paths, account references, and maintenance notes.

## Rules

- A Personal Overlay skill counts as a maintained canonical private skill only when it has a manifest entry with `Lifecycle status: maintained`.
- Directory-only private skills without manifest entries are drafts or ad hoc local files.
- Use the existing Core contract; do not create a separate private skill contract unless a future design explicitly introduces one.
- Put stable source routes in `personal/os/context/SOURCE_MAP.md` and real connector/account permissions in `personal/os/connections/CONNECTIONS.md`; reference them here instead of duplicating their contents.
- Use `Private config: none` when private settings live in the private `SKILL.md` or no config is needed.
- Use `personal/os/skills/<skill-name>/CONFIG.md` only for volatile, machine-specific, generated, profile-like, separately audited, or Core-skill-private settings.
- Do not record global harness adapter paths, exposure state, or machine-local installed-skill mirrors.
- Do not add a Core-promotion field by default. Add promotion notes only when a user or workflow is actively evaluating a private skill for Core promotion.
- `expose-skills` is Core-only in v1 and must not scan or expose Personal Overlay skills.

## Canonical Private Skills

### `<skill-name>`

- Lifecycle status: maintained.
- Canonical source: `personal/os/skills/<skill-name>/SKILL.md`
- Private config: none.
- Contract status: full, partial, needs-upgrade, or thin-adapter.
- Mutability:
- Source refs: see `personal/os/context/SOURCE_MAP.md#...`, or none.
- Connection/tool refs: see `personal/os/connections/CONNECTIONS.md#...`, or none.
- Output artifact:
- Filing rule:
- Safety posture:
- Verification coverage:
- Provenance:
- Last reviewed:
- Review trigger:
- Maintenance notes:
- Private follow-ups:

## Core Skill Private Config

Use this section only when a reusable Core skill has important private config, dependencies, safety rules, or filing details that future agents need before using that private overlay.

### `<core-skill-name>`

- Lifecycle status: maintained.
- Core source: `os/skills/<core-skill-name>/SKILL.md`
- Private config: `personal/os/skills/<core-skill-name>/CONFIG.md`
- Contract status: inherited from Core skill.
- Mutability:
- Source refs: see `personal/os/context/SOURCE_MAP.md#...`, or none.
- Connection/tool refs: see `personal/os/connections/CONNECTIONS.md#...`, or none.
- Output artifact:
- Filing rule:
- Safety posture:
- Verification coverage:
- Provenance:
- Last reviewed:
- Review trigger:
- Maintenance notes:
- Private follow-ups:
