---
name: double-steelman
description: "Construct the strongest honest case for every viable side of a decision, argument, plan, or tradeoff, then expose the cruxes that matter most and recommend a path by default. Use when the user asks to double-steelman, compare options, make a life decision, evaluate a technical architecture choice, stress-test a position, or hear the best arguments for both or all sides before deciding."
---

# Double Steelman Skill

## Trigger

Use this when the user wants the best possible argument for multiple sides of a decision, dispute, plan, or tradeoff before choosing.

## Contract

Inputs:

- The decision, claim, architecture choice, plan, or dilemma.
- The candidate sides or options, if known.
- The user's values, goals, constraints, risk tolerance, timeline, and non-negotiables when supplied.
- Evidence, source material, codebase context, personal context, or current facts needed to evaluate the options.

Output artifact:

- Concise conversational decision support for simple comparisons.
- A temporary local static HTML decision brief for comparisons complex enough to warrant a substantial artifact, with a link to the HTML file in the final response.
- Each output includes a strong case for each side, key objections, cruxes, uncertainty, and a recommendation unless no choice can be made responsibly.

Mutability:

- Read-only for quick conversational comparisons.
- Local-write to a temporary file for complex HTML decision briefs.
- Durable local-write only when the user asks to save a decision brief or durable note.
- No connector-write or external-write by default.

Tools and connectors:

- User-provided context in the current thread.
- Local files, project code, or AgentOS context when the decision depends on them.
- Current official or primary sources when a decision depends on facts that may have changed, especially technical tools, APIs, vendors, laws, markets, or live product behavior.
- Codebase inspection, current docs, primary sources, and credible convention or best-practice sources when evaluating technical architecture decisions.
- `make-temp-file` when creating temporary HTML decision briefs.

Safety:

- Preserve the user's agency. Give decision support, not coercive certainty.
- Do not invent facts, preferences, constraints, or hidden motives.
- Label uncertainty and distinguish facts, values, predictions, and taste.
- For medical, legal, financial, mental health, or other high-stakes personal decisions, provide structured thinking and suggest appropriate professional help instead of presenting the answer as settled advice.
- Do not create false balance. If a side is unethical, impossible, or factually unsupported, say so and steelman the nearest legitimate concern instead.

## Workflow Phases

1. Frame the decision. State the actual choice, stakes, options, known constraints, and decision criteria. If the sides are unclear or the stakes are high, ask only the missing questions needed to avoid a distorted analysis.

2. Map the sides. Include all materially viable options, not only the two named by the user. Consider status quo, hybrid, staged experiment, reversible trial, or delayed decision when they are genuine contenders.

3. Gather evidence when useful. For technical or fact-sensitive decisions, inspect available project context and use current official or primary sources when facts may have changed. Consider popular conventions, ecosystem norms, best practices, operational maturity, and maintainability. Cite sources when sources inform the analysis, and label convention claims as convention claims rather than laws.

4. Steelman each side. For every side, explain the values it optimizes, the strongest evidence or mechanism behind it, the context where it works best, the best reply to its strongest objection, and what a thoughtful supporter would find compelling.

5. Identify cruxes. Name the assumptions, value priorities, empirical facts, or predictions that would change the decision if they moved. Prefer concrete decision tests: "choose A if X is true; choose B if Y matters more."

6. Compare without flattening. Separate fact disputes from value tradeoffs. Weigh reversibility, opportunity cost, downside asymmetry, time horizon, implementation burden, second-order effects, and regret profile.

7. Synthesize. Give a recommendation by default, with confidence level and the assumptions behind it. Omit the recommendation only when no choice can be made responsibly between the options; in that case, explain what information would break the tie and give the smallest useful next step.

## Output

Default to this structure for chat-sized comparisons:

1. Decision frame.
2. Best case for each side.
3. Strongest objection to each side.
4. Cruxes and decision tests.
5. Recommendation.
6. Sources, when sources were used.

For quick requests, compress the structure but keep at least the best cases, cruxes, and recommendation.

For complex comparisons, produce a temporary static HTML file instead of a long Markdown brief. Treat the comparison as complex when it has several viable options, many decision criteria, meaningful evidence or source citations, technical architecture tradeoffs, high personal stakes, or enough detail that a table and expandable sections would make the result easier to use. Use inline CSS, no external network dependencies, and a first viewport that shows the decision, recommendation, confidence, and navigation. Include sections for each side, cruxes, comparison table, recommendation, uncertainties, and sources when sources were used. After writing the file, return a Markdown link to the HTML file using its absolute filesystem path.

## File Conventions

- Default output stays in chat for simple comparisons.
- Complex decision briefs live in a temporary `.html` file unless the user asks to make the artifact durable.
- Use `make-temp-file` for temporary HTML artifacts. Request a safe prefix such as `double-steelman-` and extension `html`, then write the decision brief to the created path.
- Save a durable local decision brief only when the user asks.
- Durable AgentOS decisions go to the relevant memory file only when the user explicitly asks to record the decision.

## Quality Bar

- A serious supporter of each viable side would recognize their strongest case.
- Each side gets proportionate depth; asymmetry is explained rather than hidden.
- The analysis surfaces values and tradeoffs, not just pros and cons.
- Technical decisions consider project fit, ecosystem conventions, best practices, maintainability, operational cost, and migration risk when those factors are relevant.
- Source-backed claims cite their sources when citations are possible.
- Important uncertainty remains visible.
- The final synthesis helps the user decide what to do next.

## Verification

Before finishing:

1. Confirm all materially viable sides were considered or explicitly excluded.
2. Confirm no side was straw-manned or given only weak arguments.
3. Confirm facts, predictions, and values are separated.
4. Confirm current claims were checked against current sources when needed.
5. Confirm source-backed claims include citations when possible.
6. For complex comparisons, confirm the HTML file exists in a temporary location and the final response links to it.
7. Confirm no durable local file, connector, or external state was changed unless the user asked for it.

## Rules

- Prefer honest strength over rhetorical cleverness.
- Do not make both sides look equally good when the evidence is not equal.
- Ask clarifying questions only when missing context would materially distort the output.
- For technical architecture decisions, inspect the codebase or current official docs before relying on unstable tool or library claims.
- For life decisions, make emotional, identity, and relationship costs explicit without pretending they are reducible to a score.
