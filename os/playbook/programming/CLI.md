# CLI Design Preferences

Status: active preference.

## Principle

Prefer established Unix/GNU-style CLI conventions where they make commands more predictable, scriptable, and easy to remember. Use project-local style when it is already coherent, but avoid inventing new option patterns without a clear reason.

This is a preference for familiar command shapes, not a blanket rule to follow all GNU Coding Standards. Check the relevant ecosystem and existing project style before changing a public CLI.

## Boolean Options

Use one conceptual option with positive and negative forms.

Preferred:

- `--dry-run` / `--no-dry-run`
- `--color` / `--no-color`
- `--cache` / `--no-cache`

Avoid pairing a preview flag with a separate action verb for the same boolean choice, such as `--dry-run` / `--apply`.

For Python `argparse`, prefer `argparse.BooleanOptionalAction` for this shape when the supported Python version includes it.

## Dry-Run Defaults

For commands that mutate files, external accounts, permissions, public state, or other nontrivial durable state:

- prefer dry-run-first behavior when practical;
- make the write mode explicit;
- make preview output specific enough that the user can trust what will change;
- name the write mode as the negation of the preview option when the operation is controlled by a boolean flag.

## Option Naming

Prefer conventional long option names before inventing project-specific names. Use names users can transfer between tools, such as:

- `--help`
- `--version`
- `--verbose`
- `--quiet`
- `--output`
- `--dry-run`

## Exceptions

Follow the surrounding project's existing CLI style when consistency matters more than this global preference. Record intentional deviations in the project's local docs or `AGENTS.md`.

## References

- GNU Coding Standards, command-line interfaces: https://www.gnu.org/prep/standards/html_node/Command_002dLine-Interfaces
- GNU Coding Standards, long option table: https://www.gnu.org/prep/standards/html_node/Option-Table.html
- Python `argparse.BooleanOptionalAction`: https://docs.python.org/3/library/argparse.html#argparse.BooleanOptionalAction
