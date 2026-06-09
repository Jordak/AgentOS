# Upstream Provenance

Source: `installed-global-skill`

Path: `grill-me/SKILL.md`

Vendored ref: `issue-122-called-workflow-20260609-002`

Files vendored:

- `SKILL.md`

Local AgentOS patches:

- Add this provenance file.
- Add AgentOS operating contract, safety, filing, quality, and verification sections.
- Preserve the upstream skill name and read-only interview behavior.
- Avoid recording current-machine adapter paths in Core metadata.

Update procedure:

1. Fetch the current upstream `grill-me` skill content from the maintained installed/global source.
2. Diff against this vendored Core copy.
3. Accept upstream behavior changes deliberately.
4. Reapply the local AgentOS contract wrapper above.
5. Confirm the skill remains read-only by default.
6. Run `scripts/run-validator` and `git diff --check`.

Freshness note:

The current upstream source is an installed/global skill source rather than a supported public GitHub repository source. `check-vendored-skill-upstreams` may report this provenance as unsupported until a public upstream repository is recorded.
