# Architecture-Depth Lens

Use this lens only when the reviewer prompt assigns `architecture-depth` as the optional lens.

## Reviewer Behavior

- Check module boundaries, interface depth, locality, abstraction leverage, wrong-layer logic, and whether new structure earns its keep.
- Ask whether callers gain a simpler interface or inherit nearly the same complexity through a shallow module.
- Prefer findings that identify a concrete module/interface/locality problem.
- Treat the lens as weighted attention, not an exclusive scope; still review the full target.

## Prompt Snippet

```md
Apply the `architecture-depth` lens as extra attention: check module boundaries, interface depth, locality, abstraction leverage, wrong-layer logic, and whether new structure earns its keep. Prefer concrete module/interface/locality findings over broad redesign advice.
```
