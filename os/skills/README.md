# Skills Resolver

Status: directory resolver v1.

Use `os/skills/` for reusable workflows: repeatable procedures that an agent can invoke or follow across projects and harnesses.

## Belongs Here

- Canonical AgentOS skill sources.
- The AgentOS skill contract and skills manifest.
- Thin adapters that intentionally route to fuller agent definitions.
- Durable workflow rules, quality bars, verification expectations, and filing rules for repeated work.

## Does Not Belong Here

- One-off instructions for a single agent run: put those in the chat, issue, or mapped project.
- Durable recurring jobs with their own role, cadence, reports, and operational memory: use `personal/os/agents/`; use `os/agents/` for public-safe templates and examples.
- Broad operating policy: use `os/playbook/`.
- Project-specific implementation procedures: use the mapped project from the appropriate source map.
- Machine-local installed harness adapters or mirrors as source of truth. Keep canonical behavior here and use `expose-skills` to check or create current-machine Core skill adapters.

## Common Tie-Breakers

- Skill vs agent: use a skill for a callable repeated workflow; use an agent for a durable role with its own job, inputs, outputs, cadence, reports, and history.
- Skill vs playbook: use a skill when the workflow is invoked as a capability; use the playbook for cross-cutting AgentOS operating policy.
- Skill vs manifest: the manifest tracks maintenance facts. It is not the invocation surface and should not duplicate harness-provided descriptions.
- Skill vs installed adapter: edit canonical files first, then use `expose-skills` to update current-machine Core skill adapters when needed. Canonical public skills live in Core; canonical private skills can live in the Personal Overlay.

## Update Rules

- Read `os/skills/SKILL_CONTRACT.md` and `os/skills/MANIFEST.md` before changing skill behavior.
- Use `os/skills/skillify-agentos/SKILL.md` when a repeated task, repeated failure, or recurring manual check should become durable AgentOS behavior.
- Keep skill files portable and harness-neutral unless the file is explicitly an adapter.
- Put private user-specific skills under `personal/os/skills/<skill-name>/SKILL.md` when the skill itself depends on private identity, tools, paths, agents, or account state. Use `personal/os/skills/<core-skill>/CONFIG.md` for private inputs to a reusable Core skill.
- Record mutability, tools/connectors, safety posture, output artifact, filing rule, and verification coverage.
- Prefer upgrading skills during real repeated work over speculative rewrites.

## Provenance

When a skill comes from a repeated user request, failed run, or external recipe, record the reason in the skill or manifest. Do not record current-machine adapter or mirror paths or state in the manifest; rerun `expose-skills` on each machine.

## Handoff Rules

- If a workflow becomes a durable live role, create or update an agent under `personal/os/agents/`; use `os/agents/` only for reusable public-safe scaffolding.
- If a skill creates external effects, ensure live account capability and permission files under `personal/os/connections/` are current, and keep public-safe approval policy under `os/connections/`.
- If a skill produces substantial domain artifacts, file them in the mapped project and keep only routing or summary state in AgentOS.
