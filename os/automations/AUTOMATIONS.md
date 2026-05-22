# Automations

Status: Core default.

This file describes the publishable automation registry shape. Live automation schedules, prompts, destinations, accounts, and activation state belong in `personal/os/automations/AUTOMATIONS.md`.

Core `os/automations/` is templates/examples/policy only. It must not contain live personal jobs, run histories, delivery queues, report archives, connector destinations, account-specific prompts, or generated outputs.

## Principle

Automate only work that has been run manually and verified.

Default to reviewable local artifacts. Be conservative with email, messages, public posts, account changes, and anything with external consequences.

## Activation Evidence

Before a live automation is activated, record:

- manual-run evidence;
- last verification date;
- expected logs, run history, or output paths;
- review mode, such as draft-only, local artifact, self-delivery, or external delivery;
- safety gates and approval requirements;
- disable, pause, or rollback notes.

Automations that act without manual review need explicit user approval for that behavior. When in doubt, keep the automation in draft or local-artifact mode.

## Active Automations

No active Core automations.

## Retired / Completed One-Offs

No retired Core automations.

## Candidate Automations

No Core candidate automations.

## Automation Creation Checklist

- output location
- verification checklist
- external sends
- workspace path
- source map
- manual-run evidence
- last verified date
- log or run-history path
- review mode
- disable or rollback notes

## Automation Spec Template

### Automation Name

Purpose:

Suggested trigger:

Suggested output:

Activation standard:

Safety notes:

Manual-run evidence:

Last verified:

Logs or run history:

Review mode:

Disable or rollback:
