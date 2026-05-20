---
name: make-temp-file
description: Create temporary files with a safe prefix and extension using a bundled Bash helper. Use when the user says "make a temp file", "create a temporary file", asks for a temp path, or requests a temporary file with a specific prefix or extension such as JSON, Markdown, CSV, or log.
---

# Make Temp File

## Contract

Inputs:

- Optional prefix or name-like hint for the temporary filename.
- Optional extension or common file type such as JSON, Markdown, CSV, text, or log.
- Optional count and intended use when the user needs multiple temporary files.

Output artifact:

- One or more real temporary files created by the bundled helper.
- The created file path printed by the helper and relayed to the user when useful.

Mutability:

- Local-write only, limited to creating temporary files under `${TMPDIR:-/tmp}`.
- No durable AgentOS files, connector state, or external account state are changed during normal use.

Tools and connectors:

- Local Bash.
- `mktemp` or `gmktemp` when available.
- No network calls or external connectors.

Safety:

- Use the bundled helper rather than hand-assembling random temp paths.
- Do not accept prefixes containing `/`; the helper rejects them.
- Do not write outside the system temporary directory unless the helper is intentionally changed and reviewed.
- Ask before creating many files or creating files for sensitive data handling that needs a stricter location or permissions.

## Quick Start

Run the bundled helper whenever the user wants a real temporary file path:

```bash
bash scripts/make_temp_file.sh
```

Resolve `scripts/make_temp_file.sh` relative to this skill directory.

The script prints the created file path on stdout. Relay that path to the user when useful.

## Arguments

Prefer explicit flags when the user specifies a prefix or extension:

```bash
bash scripts/make_temp_file.sh --prefix api-cache- --extension json
bash scripts/make_temp_file.sh --prefix readme- --extension .md
```

Positional arguments are also accepted for compatibility with the original function:

```bash
bash scripts/make_temp_file.sh api-cache- json
```

Defaults:

- Prefix: `tmp-`
- Extension: `.tmp`
- Directory: `${TMPDIR:-/tmp}`

## Argument Selection

Map common file-type requests to extensions:

- JSON -> `--extension json`
- Markdown or md -> `--extension md`
- CSV -> `--extension csv`
- text or txt -> `--extension txt`
- log -> `--extension log`

If the user only says "make a temp file", run the script with no arguments.

If the user gives only an extension or file type, keep the default prefix and pass only `--extension`.

If the user gives a name-like hint, use it as a prefix and make sure it ends with `-` unless the user gave an exact prefix.

## Multiple Files

If the user asks for multiple temp files, run the script once per file. Keep each call independent and report the resulting paths with their intended use.

## Workflow Phases

1. Interpret the request. Identify the requested prefix, extension, file type, count, and intended use.
2. Choose arguments. Map common file types to extensions and keep the default prefix unless the user supplied a name-like hint.
3. Create files. Run `bash scripts/make_temp_file.sh` once per requested file, resolving the script path relative to this skill directory.
4. Report paths. Return the created path or paths, with intended uses when there are multiple files.

## File Conventions

- Temporary files use `${TMPDIR:-/tmp}` through the helper.
- Prefix defaults to `tmp-`.
- Extension defaults to `.tmp`.
- Prefixes are filename prefixes only, not directories.

## Quality Bar

- The file actually exists before the path is reported.
- The extension matches the user-requested type when one was supplied.
- Name-like hints are used only as safe prefixes.
- Multiple requested files are created independently, not by reusing one path.

## Verification

Before finishing:

1. Confirm the helper exited successfully.
2. Confirm each reported path exists.
3. Confirm requested prefixes and extensions appear in the resulting filename.
4. For multiple files, confirm paths are unique.
