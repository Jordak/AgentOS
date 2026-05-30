# Security-Privacy Lens

Use this lens only when the reviewer prompt assigns `security-privacy` as the optional lens.

## Reviewer Behavior

- Check permissions, secrets, data exposure, auth boundaries, injection, privacy markers, external-account effects, and publication safety.
- Trace whether the changed code expands read/write access, leaks private context, or changes trust boundaries.
- Treat external writes, permission changes, credential handling, MFA, and public posting as especially sensitive.
- Treat the lens as weighted attention, not an exclusive scope; still review the full target.

## Prompt Snippet

```md
Apply the `security-privacy` lens as extra attention: check permissions, secrets, data exposure, auth boundaries, injection, privacy markers, external-account effects, and publication safety. Trace trust-boundary changes and privilege expansion carefully.
```
