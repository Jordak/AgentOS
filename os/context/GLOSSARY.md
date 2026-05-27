# Glossary

Status: draft.

- AgentOS: a portable Markdown control plane with static HTML as the preferred format for substantial human-facing artifacts.
- AgentOS Core: the public-safe reusable AgentOS layer under `$root/os/`.
- Core Root: `$root/os/`, the tracked directory root for AgentOS Core.
- Publishable File Set: Git-visible AgentOS files eligible for a fresh public initial commit after publication precheck, including AgentOS Core, public-safe support files, and the tracked Personal Overlay skeleton.
- Publishable support file: a public-safe root-level or sibling repository file outside the Core Root that supports discovery, adapters, documentation, governance, CI, validation, installation, or publication.
- AgentOS-managed file set: repository paths AgentOS tools and policies treat as managed for checks such as symlink, publication, export, and validation rules; broader than Core, narrower than the raw local filesystem.
- Personal Overlay: the local private AgentOS layer under `$root/personal/os/`, used for real identity, projects, tools, memories, live agents, automations, and generated outputs.
- `$root`: the location where AgentOS is installed.
- Harness: the agentic tool running the work, such as Codex, Claude Code, Google Antigravity, OpenClaw, Hermes, or another agent interface.
- Adapter: a small harness-specific instruction file or bridge that points an agent tool back to the portable AgentOS control plane.
- Drift: a mismatch between the current intended AgentOS state and installed local mirrors, adapters, automations, or other current-machine setup.
- Thought Partner: the persistent companion that translates AgentOS projects into the current tool.
- Resolver: the small AgentOS policy spine for brain-first lookup, routing tie-breakers, source authority, safety pauses, and filing destinations. It is not a skill catalog or file inventory.
- Compiled truth: a durable memory page that keeps the current best synthesis above an append-only timeline of the evidence and decisions that produced it.
- Propagation review queue: a manual queue where agent outputs can propose durable AgentOS state changes before those changes become canonical.
- Identity: who the user is, how they communicate, preferences, and boundaries.
- Context: work knowledge that helps agents avoid generic answers.
- Skill: reusable instructions for a repeated workflow.
- Skill mirror: a current-machine copy of a canonical AgentOS skill that lets a harness discover or invoke the skill directly.
- Memory: working notes, durable decisions, lessons, and history.
- Connection: access to an external tool or real-world system.
- Agent: a specific job running on top of the OS.
- Verification: checks that make outputs trustworthy.
- Automation: scheduled or event-driven agent work.
