# Glossary

Status: draft.

- AgentOS: a portable Markdown control plane with static HTML as the preferred format for substantial human-facing artifacts.
- AgentOS Core: the public-safe reusable AgentOS layer under `$root/os/`.
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
