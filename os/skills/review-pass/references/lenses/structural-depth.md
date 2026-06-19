# Structural-Depth Lens

Use this lens only when the reviewer prompt assigns `structural-depth` as the optional lens.

This is the composite architecture-depth/code-judo lens. It blends `os/skills/thermo-nuclear-code-quality-review/SKILL.md` and `os/skills/codebase-design/SKILL.md` into a PR-review posture. It is a lens inside `review-pass`, not a request to run the full `thermo-nuclear-code-quality-review` workflow or the full `improve-codebase-architecture` HTML-report workflow.

## Reviewer Behavior

- Be ambitious about structural simplification. Look for a code-judo move that preserves behavior while deleting concepts, branches, wrappers, conditionals, or layers.
- Treat spaghetti growth as a design risk: new ad-hoc conditionals, scattered special cases, one-off flags, cast-heavy contracts, wrong-layer logic, and bespoke helpers should be flagged when they make the code harder to reason about.
- Watch file-size and decomposition pressure, especially a PR pushing a file from below 1000 lines to above 1000 lines.
- Use the architecture vocabulary exactly where relevant: **module**, **interface**, **implementation**, **depth**, **deep**, **shallow**, **seam**, **adapter**, **leverage**, **locality**.
- Apply the deletion test to suspicious modules: if deleting the module makes complexity vanish, it is probably pass-through; if complexity would reappear across callers, it may be earning its keep.
- Prefer deeper modules with smaller interfaces, better locality, and tests that cross the same interface callers use.
- Do not approve merely because behavior works if the PR clearly makes the codebase structurally messier.
- If the best answer is a separate architecture or code-quality pass rather than another local patch, report a `Design escape hatch` concern recommending a standalone `improve-codebase-architecture` or `thermo-nuclear-code-quality-review` pass instead of trying to run those workflows inside `review-pass`.
- Treat the lens as weighted attention, not an exclusive scope; still review the full target.

## Prompt Snippet

```md
Apply the `structural-depth` lens as extra attention. This lens blends `os/skills/thermo-nuclear-code-quality-review/SKILL.md` and `os/skills/codebase-design/SKILL.md` into a PR-review posture, but it is only a review-pass lens; do not run the full code-quality workflow or the full architecture HTML-report workflow. Be ambitious about structural simplification, watch for spaghetti growth and file-size pressure, use the architecture vocabulary where relevant, apply the deletion test, and prefer deeper modules with smaller interfaces and better locality. If the target deserves a standalone architecture or code-quality pass, report a `Design escape hatch` recommending `improve-codebase-architecture` or `thermo-nuclear-code-quality-review`.
```
