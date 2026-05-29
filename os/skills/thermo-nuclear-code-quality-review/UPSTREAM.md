# Upstream Provenance

Source: `cursor/plugins`

Path: `thermos/skills/thermo-nuclear-code-quality-review/SKILL.md`

Vendored ref: `5102244dabd626b101cff40accbe7f7d1eeefa15`

Alternate upstream path: `cursor-team-kit/skills/thermo-nuclear-code-quality-review/SKILL.md`

Original import: `cursor-team-kit/skills/thermo-nuclear-code-quality-review/SKILL.md` at `26878d6606afd611197c900bf2dc451ee2e80a74`.

Notes:

- Cursor's Thermos plugin is the semantic upstream for this review family.
- Cursor restored the same `thermo-nuclear-code-quality-review` skill into `cursor-team-kit` after moving it into Thermos, so both upstream paths currently publish the same skill content.
- AgentOS preserves the original import history above, but tracks the Thermos path as the primary upstream for future freshness checks.

Files vendored:

- `SKILL.md`

Local AgentOS patches:

- Add this provenance file.
- Reference use as source material for `review-pass`'s structural-depth lens.
- Remove upstream `disable-model-invocation` frontmatter because Codex skill validation only allows supported metadata keys.

Update procedure:

1. Fetch the upstream skill file from the primary Thermos path at the new ref.
2. Diff against this vendored copy.
3. Accept upstream changes deliberately.
4. Reapply local AgentOS patches above.
5. Check whether the alternate `cursor-team-kit` path still mirrors the same content, and record any divergence if it matters.
6. Run skill validation, `scripts/run-validator`, and scoped `mirror-skills` audit/sync.

## License

MIT License

Copyright (c) 2026 Cursor

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
