# [Page Title]

Required metadata:

Status: draft | active | archived.
Last updated: YYYY-MM-DD.
Confidence: high | medium | low | mixed.
Provenance:
- Current user corrections:
- Canonical AgentOS sources:
- Mapped project sources:
- Connected account sources:
- External sources:

Raw evidence handling: linked | sidecarred | mapped-project-source | not kept.

Optional metadata:

Owner: AgentOS | mapped project | named agent | the user.
Aliases: optional alternate names or search terms.
Related pages:
- `os/path/to/page.md`

## Compiled Truth

Write the current best synthesis here. This section should be short enough for a future agent to load quickly and strong enough to answer, "What do we currently believe, and how should that change behavior?"

Prefer bullets for separate claims. Mark uncertainty directly in the claim when confidence is mixed.

## Operating Implications

List the practical consequences for future agents:

- What should they do differently because this page exists?
- Which files, projects, or issues should they inspect next?
- Which actions still require the user's review?

## Open Questions

Track unresolved questions that affect the compiled truth. Link to issues, backlog items, source pages, or mapped projects when available.

## Timeline And Evidence

Append evidence here in chronological order. Do not delete old timeline entries when the compiled truth changes. Add a correction or superseded note instead.

Template entry:

### YYYY-MM-DD - Short Event Title

- Source: user thread | AgentOS file | mapped project file | GitHub issue | connector | external source.
- Evidence: concise summary of the source material.
- Impact on compiled truth: what changed, what became more certain, or what was superseded.
- Confidence: high | medium | low | mixed.

## Raw Evidence Handling

Use the lightest source-handling option that preserves trust without duplicating private or bulky material:

- Link public or repo-local source material when a link is enough.
- Sidecar small raw extracts only when the raw material is safe to keep in AgentOS and future agents need the exact excerpt.
- Leave substantial project artifacts, research corpora, private exports, datasets, logs, and implementation evidence in the mapped project source.
- Do not copy private connector data into AgentOS unless the user explicitly asks for a durable summary and the relevant connection rules allow it.

## Update Rules

- Update `Last updated` whenever the compiled truth changes.
- Keep the compiled truth current by editing or replacing outdated synthesis.
- Preserve timeline evidence append-only; mark corrections and superseded claims in new entries instead of deleting history.
- Raise or lower `Confidence` when new evidence changes how much future agents should rely on the page.
- Keep provenance specific enough that a future agent can retrace the claim.
- If the page starts carrying workflow instructions, promote those instructions into the relevant `os/skills/` or `os/playbook/` file and link back here.
