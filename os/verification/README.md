# AgentOS Verification

Status: maintainer guidance.

Use this when changing AgentOS Core, reviewing a pull request, or preparing a public-safe release. User-facing setup should usually ask an agent to run these checks rather than asking the user to run them directly.

## Default Validator

Run the local validator:

```bash
python3 os/verification/scripts/validate_agentos.py
```

The default validator reads local files only and runs structural checks plus deterministic publication/privacy checks.

## Commit And Tree Scans

For shell-backed publication safety scans, run:

```bash
scripts/check_staged_publication_secrets.sh
scripts/check_publication_tree_secrets.sh HEAD
```

Use `scripts/check_working_tree_secrets.sh` as an advisory day-to-day scan of the mixed working tree.

## Hooks

Install the included hooks to validate and scan commits and pushes:

```bash
scripts/install_agentos_hooks.sh
```

## Publication

For public repository publication, follow `os/playbook/PUBLICATION.md`. Do not make a formerly private AgentOS repository public after private files have existed in its history.
