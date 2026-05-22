# Automations

Status: template.

Use this file in a Personal Overlay to record live automations.

Keep live run history, delivery records, queues, and generated outputs in `personal/os/automations/` or the relevant Personal Overlay agent/memory directory. Do not move live automation state into Core `os/automations/`.

## Active Automations

### Automation Name

Automation id:

Status:

Kind:

Trigger:

Schedule rule:

Workspace:

Execution environment:

Model:

Invocation prompt:

```text
Prompt goes here.
```

Inputs:

- Input files or connectors.

Output:

- Output artifacts or destinations. Prefer `personal/os/...` for local generated artifacts.

Manual-run evidence:

- Summarize the manual runs that proved this workflow is reliable enough to automate.

Last verified:

Logs or run history:

Review mode:

- Draft-only, local artifact, self-delivery, or external delivery.

Verification:

- Required checks.

Safety:

- Approval gates and external-effect boundaries.

Disable or rollback:

- How to pause, disable, or recover if the automation behaves incorrectly.

## Candidate Automations

### Candidate Name

Purpose:

Suggested trigger:

Suggested output:

Activation standard:

Manual-run evidence needed:

Review mode:

Safety gates:
