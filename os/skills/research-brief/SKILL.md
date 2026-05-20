---
name: research-brief
description: "Research and synthesize a topic using current official or primary sources when needed, separating facts from inference and returning evidence, caveats, and a concrete next step. Use when the user asks for research, current tool guidance, market context, vendor comparison, or documentation synthesis."
---

# Research Brief Skill

## Trigger

Use this when the user asks for research, current tool guidance, market context, vendor comparison, or documentation synthesis.

## Contract

Inputs:

- the user's research question, comparison target, tool/product, market, vendor, or documentation topic.
- Any supplied source material, constraints, date range, audience, or output format.
- Current official or primary sources when the topic is fast-moving or accuracy depends on recent facts.

Output artifact:

- Conversational or Markdown research brief with answer, evidence, caveats, and recommended next step.

Mutability:

- Read-only by default.
- No local-write, connector-write, or external-write unless the user explicitly asks for a durable file or external action.

Tools and connectors:

- Web/current-source lookup when required by the current-docs rule or by time-sensitive facts.
- User-provided documents or direct source material.
- Connector reads only when explicitly relevant and allowed by connection safety rules.

Safety:

- Use current official or primary sources for fast-moving tool, product, API, legal, financial, medical, or security claims.
- Separate facts from inference.
- Cite web or connector sources when used.
- Ask before writing to external systems, changing account state, or creating durable files.
- Do not rely on AgentOS memory for product features that may have changed.

## Workflow Phases

1. Classify the research need: stable explanation, current tool guidance, vendor/market comparison, documentation synthesis, or decision support.
2. Decide whether current sources are required. If yes, use official or primary sources first.
3. Gather only the sources needed to answer the question.
4. Separate evidence, inference, caveats, and recommended action.
5. Produce the brief with citations when external or connector sources were used.

## Process

1. Check whether current sources are required.
2. Prefer official docs, primary sources, or direct source material.
3. Separate facts from inference.
4. Cite sources when web or connector sources are used.

## Output

Use this structure:

- Answer.
- Evidence.
- Caveats.
- Recommended next step.

## File Conventions

- Default output stays in chat.
- If the user asks for a durable artifact, file it in the mapped project or the narrow AgentOS layer that owns the research topic.
- Do not promote research claims into memory, context, source map, skills, or playbook files unless the user asks or a specific workflow requires it.

## Quality Bar

- The answer directly addresses the question.
- Current claims use current official or primary sources where needed.
- Citations point to the source actually used.
- Caveats are specific, not generic.
- The recommended next step is concrete and proportionate to the evidence.

## Verification

Before finishing:

1. Confirm whether the topic required current sources.
2. Confirm current claims are backed by official, primary, or clearly labeled secondary sources.
3. Confirm facts and inference are separated.
4. Confirm source links or citations are included when browsing or connector reads were used.
5. Confirm no external write or durable filing happened without the user's request.

## Rules

- For OpenAI, Codex, ChatGPT, MCP, and fast-moving tools, verify current documentation first.
- Do not rely on memory for product features that may have changed.
