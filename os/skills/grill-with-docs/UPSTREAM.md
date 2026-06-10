# Upstream Provenance

Source: `mattpocock/skills`

Path: `skills/engineering/grill-with-docs/`

Vendored ref: `e3b90b5238f38cdea5996e16861dcae28ef52eda`

Files vendored:

- `SKILL.md`
- `CONTEXT-FORMAT.md`
- `ADR-FORMAT.md`

Local AgentOS patches:

- Add this provenance file.

Update procedure:

1. Fetch the upstream directory at the new ref.
2. Diff against this vendored copy.
3. Accept upstream changes deliberately.
4. Reapply local AgentOS patches above.
5. Run skill validation, `scripts/run-validator`, and an `expose-skills` dry run when current-machine discoverability matters.
