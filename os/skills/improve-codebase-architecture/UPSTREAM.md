# Upstream Provenance

Source: `mattpocock/skills`

Path: `skills/engineering/improve-codebase-architecture/`

Vendored ref: `0288510dd61ff6ef7c2003834082ab8f2387e80e`

Files vendored:

- `SKILL.md`
- `LANGUAGE.md`
- `DEEPENING.md`
- `INTERFACE-DESIGN.md`
- `HTML-REPORT.md`

Local AgentOS patches:

- Prefer `DOMAIN.md` and `DOMAIN-MAP.md` as domain-doc names.
- Treat `CONTEXT.md` and `CONTEXT-MAP.md` as legacy aliases.
- Keep full architecture-review behavior separate from `review-loop`; `review-loop` may reuse this skill's vocabulary as a reviewer lens.

Update procedure:

1. Fetch the upstream directory at the new ref.
2. Diff against this vendored copy.
3. Accept upstream changes deliberately.
4. Reapply local AgentOS patches above.
5. Run skill validation, `scripts/run-validator`, and scoped `mirror-skills` audit/sync.

## License

MIT License

Copyright (c) 2026 Matt Pocock

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
