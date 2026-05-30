# Deep-Review Lens

Use this lens only when the reviewer prompt assigns `deep-review` as the optional lens.

This is the correctness/security/devex branch-audit lens sourced from `os/skills/thermo-nuclear-review/SKILL.md`. It is a lens inside `review-pass`, not a request to run the full Thermos orchestration workflow or spawn Thermos subagents.

## Reviewer Behavior

- Scope findings to code added or modified by the target change. Do not report untouched pre-existing vulnerabilities unless the changed code newly exposes or worsens them.
- Trace cross-package and cross-module side effects before reporting. Do not leave client/server, caller/callee, or flag boundary questions unresolved when the code is available.
- Check breaking functionality, breaking developer experience, security vulnerabilities, and feature-gate leaks.
- Treat required new environment variables, secret lookup changes, port/network remaps, and required manual setup scripts as developer-experience risks when they change existing workflows.
- Calibrate severity honestly. Do not report a high-priority finding unless the impact and path are concrete.
- If the branch intentionally introduces a risky breakage and the scope is clearly constrained, do not report it as accidental. Escalate only when implications look under-weighted, unclear, or unsafe.
- If medium-or-higher findings exist and PR/MR discussion is available through read-only metadata already provided to the panel, incorporate valid external findings after the independent audit and attribute them. Do not post comments or perform external writes.
- If the target's risk profile deserves a standalone branch audit rather than another local patch, report a `Design escape hatch` concern recommending a separate `thermo-nuclear-review` pass instead of trying to run that workflow inside `review-pass`.
- Treat the lens as weighted attention, not an exclusive scope; still review the full target.

## Prompt Snippet

```md
Apply the `deep-review` lens as extra attention. This lens is sourced from `os/skills/thermo-nuclear-review/SKILL.md`, but it is only a review-pass lens; do not run the full Thermos orchestration workflow or spawn Thermos subagents. Scope findings to changed code, trace cross-package/module side effects, check breaking functionality, breaking developer experience, security vulnerabilities, and feature-gate leaks, and calibrate severity honestly. If the target deserves a standalone branch audit, report a `Design escape hatch` recommending a separate `thermo-nuclear-review` pass.
```
