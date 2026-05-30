# UX-API-Docs Lens

Use this lens only when the reviewer prompt assigns `ux-api-docs` as the optional lens.

## Reviewer Behavior

- Check user-facing behavior, API ergonomics, compatibility, docs accuracy, confusing names, and workflow regressions.
- Look for public or semi-public contract changes that need docs, examples, migration notes, or clearer naming.
- Prefer concrete user, caller, or reader confusion paths over aesthetic preference.
- Treat the lens as weighted attention, not an exclusive scope; still review the full target.

## Prompt Snippet

```md
Apply the `ux-api-docs` lens as extra attention: check user-facing behavior, API ergonomics, compatibility, docs accuracy, confusing names, and workflow regressions. Prefer concrete user, caller, or reader confusion paths over aesthetic preference.
```
