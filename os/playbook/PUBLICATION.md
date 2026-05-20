# Publication

Status: publication safety rule v2.

Use this when preparing AgentOS for a public GitHub repository.

## Rule

Do not make the current private AgentOS GitHub repository public.

Publish AgentOS by creating a fresh-history public repository from the prechecked publishable AgentOS file set.

Do not delete, archive, replace, or make public the current private GitHub repository until the local migration, publication precheck, staged snapshot privacy scan, and manual review are complete.

The publication candidate is not a backup. It is an optional temporary dry-run artifact for final inspection. It is incomplete by design because it excludes private Personal Overlay files and old Git history.

The publication candidate contains:

- AgentOS Core under `$root/os/`.
- Publishable root files such as `README.md`, `AGENTS.md`, `CLAUDE.md`, `DOMAIN.md`, `.gitignore`, and docs.
- Public-safe GitHub Actions workflows under `$root/.github/workflows/`.
- The tracked Personal Overlay skeleton under `$root/personal/`, using empty `.gitkeep` files only.
- Only public-safe Personal Overlay directory names; private-specific directory names must remain ignored local state.

The publication candidate must not contain:

- private Personal Overlay files;
- GitHub metadata outside public-safe workflow YAML files;
- private generated outputs;
- non-empty `.gitkeep` files;
- old Git history from the current private repository;
- private local paths, account identifiers, connector output, personal reports, or user-specific live state.

## Why

Moving or deleting a private file does not remove it from Git history. A formerly private repository can expose private information if it is made public after private files have existed in prior commits.

GitHub's own guidance treats sensitive-data removal as history-rewrite work, not ordinary deletion. See:

- <https://docs.github.com/articles/deleting-files>
- <https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository>

## Publication Plan

1. Finish the Core and Personal Overlay migration locally.
2. Before deleting or replacing the current private GitHub repository, export or copy any GitHub issue, ADR, PR, settings, automation, or planning text worth preserving into the private GitHub archive under the Personal Overlay.
3. Run the publication precheck against the migrated working tree.
4. Run the working-tree Gitleaks scan as an advisory mixed-tree sweep.
5. Stage the migration and run the staged snapshot privacy scan so Git's publishable file set and blob contents match the intended public initial commit.
6. Optionally build and inspect a clean staged publication candidate as a final dry run.
7. Optionally run TruffleHog or an LLM privacy review as an advisory second pass.
8. If publishing from the same local directory, follow the same-directory fresh-history flow before any GitHub replacement or visibility change.
9. Create the replacement GitHub repository private-first, push only the fresh initial history, and verify an independent clone.
10. Recreate only sanitized public-safe roadmap issues after the fresh repository is verified.
11. Delete, archive, replace, or make visible any GitHub repository only after the user explicitly approves that external or destructive action.

Do not initialize fresh publication history, start the replacement GitHub repository, push, change visibility, or delete/replace the current private repository before steps 1-5 are complete. Use step 6 when doing the final release operation or after changing export behavior.

When pushing AgentOS public repository changes from this workspace, use `scripts/agent-push` instead of raw `git push` when that helper is available. This keeps publication checks and push behavior in one reviewed entrypoint. If the helper is missing or unsuitable, pause and ask before pushing.

The public repository also runs `.github/workflows/agentos-validation.yml` on pushes to `main` and on pull requests. CI is a backstop, not a replacement for the local hooks and `scripts/agent-push`.

## Same-Directory Fresh-History Flow

Use this flow when the current AgentOS directory should remain the local working home and ignored Personal Overlay files should stay in place.

Keep local Personal Overlay files in place. The publication operation changes Git metadata and remote state; it does not recopy, delete, or move ignored private files under `$root/personal/os/`.

Before moving `$root/.git`, inspect linked worktrees:

```bash
git worktree list --porcelain
```

Prune stale worktree metadata with `git worktree prune` before replacing Git metadata. Remove real linked worktrees only with explicit human approval, and do not move `$root/.git` while live linked worktrees still depend on it.

Neutralize old remotes before GitHub name reuse. Remove or rename old remotes in the old metadata before any replacement repository is connected, so no later command can accidentally push old history to the replacement repository or fresh history to the old remote.

Back up the old `$root/.git` metadata instead of deleting it. Store that backup in a local ignored location outside the Publishable File Set. Treat the backup as private state because it can contain old history, reflogs, remote URLs, branch names, and other repository metadata. Do not include it in AgentOS Core, the Publication Candidate, or the replacement repository.

Initialize fresh history in the same working directory only after the migration and privacy gates pass and the old Git metadata is backed up. Use the current working tree as the source, run `git init`, stage only the Publishable File Set, create a fresh initial commit, and confirm `git log` shows no older commits.

Create the replacement GitHub repository private-first. Add its remote explicitly after fresh initialization, then push only the fresh initial branch. Do not reuse old remote configuration.

Before public visibility, clone the replacement repository into an independent temporary directory and run the publication validation and a semantic spot-check there. The clone should contain Core, publishable root files, and the tracked Personal Overlay skeleton only; it should not contain ignored Personal Overlay files, old history, old remotes, or local backup metadata.

After the replacement repository is verified, recreate only sanitized public-safe roadmap issues. Do not import old private issues, comments, pull requests, labels, milestones, settings, or transcripts wholesale. Promote an issue only when its title, body, labels, and links contain no private history, local paths, account details, private repository names, or user-specific live state.

Ask for explicit human approval before moving or deleting `$root/.git`, removing real linked worktrees, deleting or replacing a GitHub repository, creating a replacement GitHub repository, pushing to a remote, changing repository visibility, recreating public issues, or changing repository permissions/settings.

## Old GitHub State

Before deleting or replacing the current private GitHub repository, preserve useful GitHub-side state in a Private GitHub Archive under the Personal Overlay.

Suggested paths:

- `$root/personal/os/playbook/github-archive/issues/YYYY-MM-DD.json`
- `$root/personal/os/playbook/github-archive/issues/<issue-number>-<short-title>.md`
- `$root/personal/os/playbook/github-archive/prs/YYYY-MM-DD.json`
- `$root/personal/os/playbook/github-archive/settings/README.md`

Do not import old private issues wholesale into AgentOS Core or the new public repository.

After the fresh public repository exists, selectively recreate only public-safe issues, discussions, or docs from the archive.

## Privacy Validator Shape

The validator should prove a narrow structural claim: the current AgentOS working tree has a publishable Git file set, private overlay files are ignored, and Core has no obvious private markers.

Prefer deterministic checks over semantic guessing:

- fail when tracked or unignored files under `personal/` are anything other than `.gitkeep`;
- fail when `.gitkeep` files under `personal/` are outside the explicit public-safe skeleton allowlist;
- fail when any exported `.gitkeep` file is anything other than an empty regular file;
- fail when private files under `personal/` are not covered by `.gitignore`;
- fail when tracked Personal Overlay skeleton paths contain private markers, because directory names can disclose private state;
- fail when generated output directories are tracked in Core, except sanitized examples;
- fail when live personal files appear in Core where only `.template.md` is allowed;
- fail when live personal filenames or nested paths appear anywhere under high-risk Core layers even if the file contents contain no known private marker;
- fail when Git-visible symlinks are present, because public export must not follow links into ignored or private content;
- fail when any Git-visible `.gitkeep` marker is non-empty before export;
- fail on known private markers such as local absolute paths, private repository URLs, account identifiers, email addresses, calendar IDs, Drive URLs, personal names chosen for exclusion, and workplace-specific strings chosen for exclusion;
- scan every publishable regular file as UTF-8 content, regardless of suffix, so unknown text formats cannot bypass private-marker checks;
- fail on secret-like patterns using a dedicated secret scanner where possible;
- skip ignored local artifacts outside the explicit private overlay ignore-coverage check;
- fail when tracked files are deleted in the working tree and need their deletions staged before a publication commit.

LLM review may supplement this process, but it is not the release gate.

Run publication validation in the working tree by default:

```bash
python3 os/verification/scripts/validate_agentos.py --publication-precheck
scripts/check_working_tree_secrets.sh
scripts/audit_agentos_leak_paths.sh
```

The working-tree precheck catches migration mistakes early and tolerates ignored private files under `$root/personal/`.

When performing the final release operation, optionally build and validate a publication candidate for manual inspection:

```bash
python3 scripts/export_public_agentos.py --staged --output <export-dir> --force
python3 os/verification/scripts/validate_agentos.py --public-export <export-dir>
```

The staged export validates the exact Git index contents that can become the fresh public initial commit. The candidate is a dry run, not the default day-to-day gate.

## Secret Scanning

Use Gitleaks as the required local scanner.

For day-to-day development, scan the AgentOS working tree with `.gitleaks.toml`. This is faster than generating the publication candidate each time and avoids scanning ignored private overlay files under `personal/`.

```bash
scripts/check_working_tree_secrets.sh
```

Gitleaks `dir` mode does not use `.gitignore` as the source of truth for what to scan. Use `.gitleaks.toml` path allowlists for directories that must be excluded from working-tree scans, such as `personal/`.

For pre-commit and release, validate and scan the staged snapshot so the gate reads the exact blob contents that can be committed:

```bash
scripts/check_staged_publication_secrets.sh
```

For release, the staged scan is the main gate. Optionally scan the publication candidate as a final dry run to prove the generated publishable tree is clean, with no old Git history and no private overlay files.

Use TruffleHog as a second-pass scanner before creating the fresh public repository. It has useful verification and decoding behavior, but it can be slower and noisier, so it is not the default pre-commit gate.

Optional candidate dry-run command:

```bash
scripts/check_public_export_secrets.sh
```

That script runs the publication precheck, regenerates a staged publication candidate in a unique temporary export directory unless an explicit export path is provided, validates the publication candidate, and runs:

```bash
gitleaks dir --redact --verbose <export-dir>
```

Optional second-pass command:

```bash
AGENTOS_TRUFFLEHOG_SCAN=1 scripts/check_public_export_secrets.sh
```

That additionally runs:

```bash
trufflehog filesystem --results=verified,unknown --fail --no-update <export-dir>
```

Run the working-tree Gitleaks scan during ordinary development. Run the staged publication scan before ordinary commits and before any publication commit. Run the publication-candidate Gitleaks scan before creating the fresh public GitHub repository if you want a final artifact to inspect. Run the TruffleHog second pass before creating the fresh public GitHub repository or after large structural changes to export behavior.

Do not use a secret scanner against the old private repository history as evidence that the current repository can be made public. A history scan is useful for awareness and key rotation, but publication still uses a fresh-history publication candidate.

## Pre-Commit

AgentOS includes a local pre-commit configuration:

```bash
pre-commit install
```

This requires the `pre-commit` CLI in addition to `gitleaks`.

The pre-commit hooks run:

- staged public-export validation against the Git index;
- Gitleaks against the same staged snapshot through `scripts/check_staged_publication_secrets.sh`.

To run the same checks manually:

```bash
pre-commit run --all-files
```

To include the optional TruffleHog second pass in a manual run:

```bash
AGENTOS_TRUFFLEHOG_SCAN=1 scripts/check_public_export_secrets.sh
```

Keep TruffleHog out of the default pre-commit path unless the team accepts the extra latency and possible verification noise.

## Export Script

If a publication candidate is generated, it should be generated by script.

Suggested path:

`scripts/export_public_agentos.py`

The script should:

- derive the copy set from Git-visible files (`git ls-files --cached --others --exclude-standard`) rather than a raw filesystem walk;
- run the publication precheck before copying, even when post-copy validation is skipped;
- fail instead of silently omitting any Git-visible file outside the publishable allowlist;
- fail on Git-visible symlinks instead of following them;
- fail when Git-visible tracked paths are missing from the working tree;
- fail on high-risk live personal Core filenames and nested paths before copying;
- fail on non-empty `.gitkeep` markers before copying;
- copy allowlisted Core files;
- copy only public-safe empty skeleton `.gitkeep` files from the explicit Personal Overlay allowlist;
- exclude ignored private files;
- exclude `.git/`;
- fail on forbidden paths and private markers;
- write to a clean temporary candidate directory;
- run validation against the candidate or print the exact validation command.
- leave release-candidate secret scanning to `scripts/check_public_export_secrets.sh`.

Manual assembly is not a reliable dry-run mechanism because it is easy to get wrong and hard to repeat.

## Current Plan

The current publication plan is:

1. Keep one local AgentOS working tree with tracked Core under `$root/os/` and ignored Personal Overlay files under `$root/personal/os/`.
2. Do the full migration in one focused effort rather than publishing layer-by-layer.
3. Preserve useful GitHub-side planning state from the current private repository.
4. Create the replacement GitHub repository private-first with fresh history from the prechecked publishable file set; optionally use the script-generated sanitized publication candidate as the final inspected source tree.
5. Use `.gitignore` and `.gitkeep` so the public repository keeps the Personal Overlay directory shape but not private files.

Deletion, replacement, or public-repo creation waits until migration and validation are complete.
