# AgentOS Artifact Policy

Status: production.

Use this file to decide the output format for AgentOS artifacts.

## Core Rule

Keep the AgentOS control plane in Markdown. Use static HTML as the canonical preferred output for substantial human-facing artifacts.

Generated artifacts default to the Personal Overlay. Reports, briefs, histories, queues, run logs, and substantial generated outputs derived from a real user, private project, connector, account, or live agent belong under `personal/os/` unless the user explicitly asks for a sanitized Core example.

When the user asks for a substantial human-facing report about a repository's live state, make both decisions together: prefer a local static HTML report, and route the generated live output to the Personal Overlay by default rather than Core.

The control plane includes:

- instructions and tool adapters;
- `INDEX.md`, source maps, playbooks, skills, agent contracts, and automation specs;
- working memory, long-term memory, decisions logs, and compact operational logs;
- small pointers, indexes, and compatibility notes.

Human-facing artifacts include:

- weekly and monthly review reports;
- research briefs;
- implementation plans;
- code review explainers;
- design explorations;
- portfolio or capability reports;
- one-off editors for structured decisions or prioritization.

## HTML Artifact Rules

- Write final substantial reports as local static HTML by default.
- Inline CSS. Avoid external network dependencies.
- Use browser-native interactions such as links, tables, and `<details>` / `<summary>` before adding JavaScript.
- Add JavaScript only when interaction materially improves the artifact.
- Make the first viewport useful: clear status, conclusion, and navigation.
- Use visual hierarchy, cards or panels, tables, and expandable detail to make the report easier to scan than the Markdown equivalent.
- Include a clear source/provenance note when the HTML is derived from a Markdown draft or another artifact.
- Keep filenames plain and stable, such as `YYYY-MM-DD.html`.

## Markdown Companion Rules

Markdown remains useful as glue around HTML artifacts:

- Follow `os/playbook/programming/MARKDOWN.md` for Markdown source style; prefer soft wrapping for prose so rich viewers wrap dynamically.
- Keep a short Markdown index when a directory contains multiple HTML reports.
- Keep Markdown drafts only when they help the review workflow.
- Keep Markdown compatibility records for legacy reports.
- Do not duplicate the full HTML content in Markdown unless the user explicitly asks for a plain-text fallback.

## Current Defaults

- Current-awareness briefs: static HTML.
- Weekly review final reports: static HTML under the appropriate Personal Overlay output directory.
- Portfolio or project reports: prefer static HTML for substantial durable reports; Markdown is acceptable for quick notes or legacy reports.
- Core artifact examples: sanitized templates or fixtures only, never live personal reports or run histories.

## Portability Note

HTML is now the preferred readable artifact format, but Markdown remains the portable AgentOS instruction and memory format. If another tool cannot ingest HTML well, give it the relevant Markdown control-plane files plus a concise summary of the HTML artifact.
