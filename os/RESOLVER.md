# AgentOS Resolver

Status: policy spine v1.

Use this file when a task is broad, ambiguous, or needs a durable AgentOS update. The resolver answers:

1. Where should the agent look first?
2. Which AgentOS layer, workflow, or mapped project should handle the task?
3. Which source wins when sources conflict?
4. When should the agent pause for approval?
5. Where should new durable state be filed?

## Brain-First Lookup

Before external lookup, search local AgentOS files unless the user explicitly asks for current external information or a current-docs rule applies.

Lookup order:

1. Current user request and explicit corrections in the current thread.
2. Active system, developer, tool, and safety instructions.
3. Root adapter instructions, then `os/INDEX.md`, then this resolver.
4. `os/playbook/PERSONAL_OVERLAY.md` when private user-specific state may affect the task.
5. The narrowest relevant AgentOS Core file under `$root/os/`, followed by the matching Personal Overlay file under `$root/personal/os/` when present.
6. `os/context/SOURCE_MAP.md` and the matching Personal Overlay source-map file when present, then the mapped project source when the request is project-specific.
7. Connected account data only when the request requires it and the relevant connection rules allow the read.
8. External web or API sources only when local and mapped sources are insufficient, when the fact may have changed, or when a current-docs rule requires a current primary or official source.

Use local search before manual wandering. Prefer `rg` for text and `rg --files` for paths, except when proving whether Personal Overlay files exist. For Personal Overlay absence checks, follow `os/playbook/PERSONAL_OVERLAY.md`: use direct filesystem discovery of the canonical Personal Overlay root and do not treat ignore-aware or git-aware indexes as absence evidence.

## Source Authority

When sources conflict, use this order unless a higher-priority instruction says otherwise:

1. Current explicit user instructions and corrections.
2. System, developer, tool, and safety instructions.
3. Personal Overlay files for user-specific facts.
4. AgentOS Core policy and templates.
5. Mapped project sources for that project's implementation state.
6. Connected-account data for the account-specific facts it directly contains.
7. Current official or primary external sources for fast-moving public facts.
8. Historical reports, generated artifacts, drafts, and chat summaries.

Generated reports and agent histories are evidence. They are not canonical state unless promoted into context, memory, source map, playbook, agent, skill, verification, or automation files.

## Routing Tie-Breakers

Use the narrowest route that can answer the task.

- Personal identity, preferences, communication, or boundaries: `personal/os/identity/`.
- Work context, career direction, interests, projects, tools, glossary, or source routing: `personal/os/context/`, using Core templates under `os/context/`.
- Current short state, durable personal decisions, lessons, or review history: `personal/os/memory/`.
- A repeated reusable workflow: `os/skills/`.
- Private live skill configuration: Personal Overlay skill config files.
- A durable live agent role: `personal/os/agents/`.
- Generic agent scaffolding: `os/agents/`.
- Live agent histories, queues, reports, briefs, run logs, and generated outputs: `personal/os/agents/` or another narrow Personal Overlay directory.
- Tool access, connector boundaries, or account safety: `personal/os/connections/`, using Core safety policy under `os/connections/`.
- Quality check code, schemas, and sanitized fixtures: `os/verification/`.
- Private run reports and benchmark results: `personal/os/verification/`.
- Cross-cutting operating policy, artifact policy, portability, publication, or programming preferences: `os/playbook/`.
- Feature-sized implementation requests: check `os/playbook/IMPLEMENT_FEATURES.md` and use `os/skills/check-implementation-readiness/SKILL.md` before coding unless the work is clearly gate-exempt. If only chat consensus exists, create or update a durable design source before implementation code. For tracked-file changes meant to land through a pull request, also use the Branch and Integration Discipline section of `os/playbook/GITHUB_WORKFLOW.md` before the first edit.
- GitHub issue drafting, pull request drafting/creation, branch handoffs, merge/landing notes, issue closure comments, or GitHub CLI authentication during those operations: `os/playbook/GITHUB_WORKFLOW.md`, even when the request is a follow-up to another skill's report or recommendation.
- Live schedules, recurring jobs, or automation prompts: `personal/os/automations/`, using Core templates under `os/automations/`.
- Live automation histories, queues, delivery records, and generated outputs: `personal/os/automations/` or the relevant Personal Overlay agent/memory directory.
- Public repository publication, fresh-history export, privacy validation, or deletion/replacement of an old private GitHub repository: `os/playbook/PUBLICATION.md`.

If two routes both seem plausible, choose the route where the resulting file will be most stable over time. Prefer linking to neighboring layers over copying the same fact into multiple places.

## Safety And Approval Pauses

Pause and ask the user before:

- sending email, chat, social, GitHub comments, or any message to another person;
- posting publicly;
- changing sharing permissions or granting write access;
- entering credentials or handling MFA;
- deleting nontrivial data;
- changing account settings;
- making purchases or other external commitments;
- connecting new external services;
- creating automations that will act without a manual review step;
- deleting, replacing, archiving, or changing visibility of a GitHub repository.

## Filing Destinations

File durable updates in the narrowest stable home:

- Personal preference, communication style, boundary: `personal/os/identity/`.
- Work/project knowledge, interests, tools, source pointer: `personal/os/context/`.
- Current operating state: `personal/os/memory/WORKING_MEMORY.md`.
- Durable personal decision or lesson: `personal/os/memory/DECISIONS_LOG.md` or `personal/os/memory/LONG_TERM_MEMORY.md`.
- Core architecture decision: `docs/adr/` or `os/memory/DECISIONS_LOG.md`.
- Reusable workflow: `os/skills/`.
- Private skill config: a matching Personal Overlay skill config file.
- Live agent job definition or report: `personal/os/agents/`.
- Generic agent template: `os/agents/`.
- Connection capability, permission, or account safety rule: `personal/os/connections/`.
- Quality checklist, validator, or verification schema: `os/verification/`.
- Private verification run evidence: `personal/os/verification/`.
- Cross-cutting operating policy: `os/playbook/`.
- Local implementation readiness or design follow-up artifacts: the mapped project's design-doc convention, or an issue-specific implementation-readiness Markdown file under a project design-doc directory when no narrower convention exists.
- Live schedule or automation prompt: `personal/os/automations/`.

Core `os/agents/` and `os/automations/` are templates/examples/policy only. Do not file live personal jobs, run histories, queues, reports, briefs, or generated outputs there.

## Completion Check

Before finishing AgentOS work:

1. Did the answer or edit use the narrowest relevant files?
2. Did project-specific claims inspect the mapped source?
3. Did fast-moving public/tool facts use current official or primary sources?
4. Did external actions or private-data handling receive approval?
5. Did generated durable-state recommendations go to the right inbox: GitHub or mapped tracker for public-safe actionable project work, propagation review queue for private/tentative/pre-issue proposals, or direct edit only for exact approved changes?
6. Did durable new state land in one canonical home?
7. Did publication work preserve the fresh-history gate in `os/playbook/PUBLICATION.md`?
8. For feature-sized implementation, did the work pass or intentionally skip the implementation-readiness gate in `os/playbook/IMPLEMENT_FEATURES.md`, and is that verdict visible in the PR body when there is a PR?
