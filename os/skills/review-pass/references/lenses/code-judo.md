# Code-Judo Lens

Use this lens only when the reviewer prompt assigns `code-judo` as the optional lens.

## Reviewer Behavior

- Look for smaller moves that preserve behavior while deleting concepts, branches, wrappers, flags, conditionals, or layers.
- Prefer simplification that removes moving parts over refactors that merely rearrange them.
- Call out missed simplifications only when the simpler shape is concrete enough to act on.
- Treat the lens as weighted attention, not an exclusive scope; still review the full target.

## Prompt Snippet

```md
Apply the `code-judo` lens as extra attention: look for smaller moves that preserve behavior while deleting concepts, branches, wrappers, flags, conditionals, or layers. Report only simplifications concrete enough for the caller to evaluate.
```
