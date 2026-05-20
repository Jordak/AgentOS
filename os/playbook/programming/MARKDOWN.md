# Markdown Authoring Preferences

Status: active preference.

## Principle

Prefer soft wrapping for prose in Markdown. Let rich Markdown viewers wrap text dynamically as the window resizes instead of inserting manual line breaks at a fixed column.

## Default Shape

- Write each normal paragraph as one logical line.
- Write each bullet or numbered item as one logical line when it remains readable in source.
- Preserve semantic line breaks inside poetry, addresses, examples, code fences, tables, quoted source text, generated output, and formats where line breaks carry meaning.
- Allow intentional manual line breaks when they express structure or semantics, not merely to fit a column width.
- If a paragraph or list item becomes too long to read as one source line, prefer restructuring it into nested bullets, headings, a table, or another explicit format.
- Keep headings and naturally short list items short; do not stretch them only to satisfy this rule.
- When editing existing hard-wrapped Markdown, reflow only the paragraph or list item you are touching unless the task is explicitly a formatting cleanup.

## Tool Notes

- Do not run automatic formatters that hard-wrap Markdown prose by default.
- If a project has a stronger local Markdown style, follow that project's local docs and avoid broad formatting churn.
