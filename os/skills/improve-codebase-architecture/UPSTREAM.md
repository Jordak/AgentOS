# Upstream Provenance

Source: `mattpocock/skills`

Path: `skills/engineering/improve-codebase-architecture/`

Vendored ref: `321658273cb1d20b76026717d027d505790106d4`

Files vendored:

- `agents/openai.yaml`
- `SKILL.md`
- `HTML-REPORT.md`

Local AgentOS patches:

- Add this provenance file.
- Update AgentOS manifest and `review-pass` references to consume the upstream `codebase-design` split instead of the removed local `LANGUAGE.md` companion file.

Update procedure:

1. Fetch the upstream directory at the new ref.
2. Diff against this vendored copy.
3. Accept upstream changes deliberately.
4. Reapply local AgentOS patches above.
5. Run skill validation, `scripts/run-validator`, and an `expose-skills` dry run when current-machine discoverability matters.

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
