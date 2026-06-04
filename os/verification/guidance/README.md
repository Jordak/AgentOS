# Guidance

Status: current benchmark surface.

Guidance checks whether a real harness applies AgentOS guidance correctly in realistic scenarios. It is not a retrieval benchmark and does not require transcript-level proof that the harness opened a specific file.

The suite asks the harness under test a direct task, captures its normal prose answer, and sends successful answers to a judge with hidden fixture context. By default, all successful answers for each harness are judged in one batch. The judge compares each answer against the expected behavior, failure modes, and current guidance sources, then returns structured verdicts.

Harness-under-test calls run from a temporary external project that contains a harness-specific local adapter. For Codex, that adapter is `AGENTS.md`. The adapter points at a sanitized temporary AgentOS copy built from tracked/index-defined file contents. The copy excludes `.git/**`, `personal/**`, and `os/verification/**` so benchmark fixtures, saved reports, answer keys, and Personal Overlay state are unavailable at runtime. Untracked local files, unstaged tracked-file edits, and symlinks are not copied into the sanitized AgentOS copy.

Real runs also create a non-private host-boundary sentinel outside the temporary external project and sanitized AgentOS copy. The sentinel is a passive contamination tripwire: if its random marker appears in captured HUT output, the run is status-ineligible. A non-observed sentinel does not prove full host filesystem isolation; it only means this tripwire did not fire.

Guidance owns the maintained source-boundary and answer-key guardrails for harness behavior. Fixture `source_paths` must point at tracked UTF-8 files that are available to the sanitized harness workspace, not at `personal/**`, `os/verification/**`, fixture files, schemas, judge prompts, reports, or other answer-key material. The judge treats reliance on benchmark fixtures, saved reports, answer keys, or private Personal Overlay files as a failure.

The suite intentionally validates the portable project-local adapter path, not the user's installed global adapter. Installed global adapter verification is tracked separately in [#83](https://github.com/Jordak/AgentOS/issues/83).

Judge calls run from the trusted benchmark checkout as measurement instrumentation. Hidden fixture data reaches the judge through the rendered judge prompt, not through readable benchmark files available to the harness under test.

The judge instructions live in `judge_prompt.md` as a benchmark-owned prompt asset. They intentionally do not live in `os/skills/`: the judge is measurement instrumentation for this suite, not reusable AgentOS workflow behavior or part of the harness-under-test skill surface.

Raw reports and run histories belong under `personal/os/verification/guidance/reports/`.
Saved reports include compact judge batch metadata so maintainers can confirm how many HUT answers were judged together without reading raw harness output.

## Compatibility

The public benchmark surface is now `guidance`. The old `guidance-eval` directory, script name, benchmark id, and default save path are not kept as command aliases. Existing local report directories under `personal/os/verification/guidance-eval/reports/` may remain as historical evidence, but new runs and status refreshes use `personal/os/verification/guidance/reports/`.

## Fixture Authoring

Fixtures live in `fixtures.json`.

Use this shape:

```json
{
  "id": "github-cli-sandbox-auth",
  "category": "github",
  "scenario": "A `gh auth status` command from the sandboxed agent terminal says the token is invalid, but `gh auth login` says the user is already logged in and other GitHub actions work.\n\nWhat do you do next?",
  "source_paths": [
    "os/playbook/GITHUB_WORKFLOW.md"
  ],
  "expected_behavior": [
    "..."
  ],
  "failure_modes": [
    "..."
  ]
}
```

Write `scenario` as a direct second-person task to the harness under test. Use "good neutral" framing: include the real operational facts the agent would have, but do not include answer-key language, source-path hints, option menus, or meta-framing that tells the HUT to use AgentOS guidance. The HUT receives the scenario text only: do not add evaluation framing, fixture ids, expected source paths, expected behavior, answer keys, or failure modes. Do not phrase it as "What should the agent do?"

Good neutral scenarios preserve trigger facts such as a sandboxed agent terminal, generated report, weekly review, durable-memory candidate, nontrivial write, private/local state, or repeated user behavior when those facts are natural to the task. They avoid priming phrases such as "You are working in an external project that uses AgentOS guidance," explicit routing choices, or policy vocabulary that the user would not naturally supply. End each scenario with `What do you do next?`.

`source_paths`, `expected_behavior`, and `failure_modes` are hidden fixture context. They are passed only to the judge.

## Judge Output

The judge prompt is loaded from `judge_prompt.md` by default and rendered with hidden fixture fields, indexed source-file contents, and harness answers. The judge treats each case's `source_files` as the current guidance source snapshot and uses `source_paths` only as labels; it does not inspect the live checkout for source files. The judge returns one JSON object matching `judge_response.schema.json`, with a `results` array containing one result per fixture in the batch.

Required result fields:

- `fixture_id`: the fixture being graded.
- `verdict`: `pass`, `fail`, `fixture_stale`, or `needs_user_judgment`.
- `rationale`: concise explanation of the verdict.
- `source_alignment`: `aligned`, `partial`, `missing`, `wrong`, or `not_applicable`.
- `staleness`: `current`, `stale`, or `uncertain`.
- `confidence`: `high`, `medium`, or `low`.

Nullable fields:

- `source_alignment_rationale`.
- `staleness_rationale`.

Codex structured-output schemas require every property to be listed in `required`, so these fields are present in the schema and may be `null` when not needed. Soft convention: include `staleness_rationale` text when `staleness` is `stale` or `uncertain`, but the validator does not hard-fail only because that optional explanation is absent or null.

## Verdict Semantics

- `pass`: the harness answer makes the guidance-shaped decision required by the current source guidance.
- `fail`: the harness answer misses or contradicts the required guidance-shaped decision.
- `fixture_stale`: the fixture's expected behavior no longer matches the referenced current guidance source.
- `needs_user_judgment`: the judge cannot fairly decide. This is diagnostic only and blocks status eligibility until a later workflow resolves it.

`source_alignment` is diagnostic. An answer can pass without naming the expected source file when it still makes the correct guidance-shaped decision.

## CLI

Preview without model calls:

```bash
python3 os/verification/guidance/scripts/benchmark_guidance.py --dry-run
```

Run deterministic self-tests:

```bash
python3 os/verification/guidance/scripts/benchmark_guidance.py --self-test
```

Run Codex as the harness under test and save a diagnostic report:

```bash
python3 os/verification/guidance/scripts/benchmark_guidance.py --no-dry-run --harness codex --save-report
```

Use `--quiet` for log-sensitive runs such as public GitHub Actions trials. Quiet mode still writes requested `--save-report` or `--output` artifacts, and still prints errors, but suppresses the rendered benchmark report, progress lines, and generated local report paths from stdout/stderr.

Use `--judge-prompt <path>` or `--judge-schema <path>` to test alternate judge assets. The prompt must contain the documented placeholder tokens from `judge_prompt.md`. Alternate judge assets are diagnostic and make the run status-ineligible.

Use `--judge-batch-size 1` to debug one judge call per successful HUT answer. The default `--judge-batch-size 0` batches all successful HUT answers for each harness into one judge call. Non-default judge batch sizes are diagnostic and make the run status-ineligible.

Harness and judge prompts are passed to Codex through stdin. Dry-run command shapes display `<prompt>` placeholders and do not include hidden fixture fields, answer keys, or source snapshots in argv.

Status-eligible runs require a clean, remote-fresh `main` checkout and:

```bash
python3 os/verification/guidance/scripts/benchmark_guidance.py --no-dry-run --harness codex --save-report --check-remote-main
```

For a log-sensitive status-eligible trial, add `--quiet` and route status interpretation through `os/skills/refresh-benchmark-status/SKILL.md` rather than copying report contents into workflow logs.

## Status Summary

Saved reports expose a manifest-resolvable `summary` object and raw fixture provenance metadata. `behavioral_total` counts only `pass` and `fail`. Freshness checks derive the status-counting total from `behavioral_total + fixture_stale`; reports do not store a separate derived total. `fixture_stale` is reported separately and does not make the run ineligible. `needs_user_judgment` makes the run ineligible.

`summary.status_eligible` includes fixture-scope, judge-protocol, and host-boundary tripwire checks: status-eligible Guidance reports must use the default canonical fixture file, the full default fixture set, no `--fixture-id` subset, default judge prompt, default judge schema, default judge batch size, and no observed host-boundary sentinel marker. Alternate fixture files, selected fixture subsets, alternate judge assets, non-default judge batch sizes, and observed host-boundary sentinel markers are diagnostic runs.

Example:

```json
{
  "total": 12,
  "behavioral_total": 10,
  "behavioral_pass": 8,
  "behavioral_fail": 2,
  "fixture_stale": 2,
  "needs_user_judgment": 0,
  "harness_unavailable": 0,
  "status_eligible": true,
  "status_ineligible_reasons": []
}
```

Saved reports also include Git metadata and host-boundary tripwire metadata so refresh workflows can reject dry-run, dirty-worktree, non-main, non-remote-fresh, host-contaminated, or unresolved diagnostic evidence.
