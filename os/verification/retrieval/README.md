# AgentOS Retrieval Verification

Status: active verification area.

This directory owns AgentOS retrieval and discoverability checks. "Retrieval" here means the practical question an agent has to answer before doing good work: which local AgentOS file is the canonical source for this prompt?

## Purpose

AgentOS is useful only if an active harness can find the right local source of truth at the moment it needs it. This verification area turns that into a repeatable check.

The benchmark asks representative AgentOS lookup questions and checks whether the answer is grounded in the right local files. A passing answer must:

- cite the relevant AgentOS source of truth;
- include structured local evidence entries;
- avoid eval fixtures, previous reports, and other answer-key files.

Exact quote support is diagnostic only. Quote mismatches are reported so humans can see grounding quality, but they do not fail the retrieval score when the answer has valid schema, valid local paths, an expected canonical source, and no disallowed sources.

`os/verification/BENCHMARK_STATUS.md` is excluded from ordinary retrieval evidence because it summarizes benchmark outcomes. A dedicated benchmark-status lookup question may target that file directly, but unrelated retrieval questions should not use it as answer evidence.

This gives AgentOS one score to watch during maintenance: can the current harness find and support the right answer from the control plane?

The goal is not to replace Codex, Claude Code, or any other harness with a homegrown retriever. The goal is to make AgentOS discoverability observable, so changes to file layout, routing language, skills, memory, and agent definitions can be checked before they silently make future agents worse.

Use this verification when:

- reorganizing AgentOS files or source-of-truth boundaries;
- adding or changing skills, agents, memory, or context files;
- comparing harness behavior across Codex, Claude Code, or future CLIs;
- preparing Weekly Review evidence that AgentOS is still easy for agents to navigate.

## Contents

- `fixtures.json`: structural route-evidence fixtures consumed by `os/verification/scripts/validate_agentos.py`.
- `questions.json`: human-language lookup questions with expected canonical paths.
- `LOCAL_BENCHMARK.md`: notes for the local lexical retrieval benchmark.
- `harness_response.schema.json`: structured response schema for real harness retrieval evals.
- `scripts/benchmark_retrieval.py`: single public CLI for local and harness retrieval benchmark suites.
- `scripts/harness_eval.py`: implementation module for Codex/Claude-style harness answers and local evidence grading.
- `personal/os/verification/retrieval/reports/`: optional saved report directories. Each saved run contains `report.md` for human review and `run.json` for diagnosis or downstream tooling.

## Eval Layers

Structural fixtures:

- Validate that local files contain the evidence needed to route common prompts.
- Run with `scripts/run-validator`.
- Offline and deterministic.

Local lexical benchmark:

- Compares whole-file keyword search with a lightweight Markdown section index.
- Run by default, or alone with `python3 os/verification/retrieval/scripts/benchmark_retrieval.py --suite local`.
- Offline and deterministic.
- Report metadata records local Git state by default. Add `--check-remote-main` only when producing saved evidence intended to prove fresh `origin/main` eligibility for Core benchmark status.

Harness answer evals:

- Ask a real harness, such as Codex CLI or Claude Code, to answer lookup questions with structured JSON.
- Gate pass/fail on schema shape, valid local paths, cited canonical paths, and disallowed-source avoidance.
- Report exact quote support as a diagnostic check only.
- Leave full prose quality as manual review unless a later judge is added.
- Harness mode defaults to dry-run. Real model calls require `--no-dry-run`.
- Harness model and effort default to each harness's configured defaults unless `--model` or `--effort` is provided.

## Commands

Run deterministic maintenance validation:

```bash
scripts/run-validator
```

Run the full safe retrieval benchmark report:

```bash
python3 os/verification/retrieval/scripts/benchmark_retrieval.py
```

Save the full safe report. This creates a timestamped directory containing `report.md` and `run.json`:

```bash
python3 os/verification/retrieval/scripts/benchmark_retrieval.py --save-report
```

When producing evidence for `os/verification/BENCHMARK_STATUS.md`, run from a clean `main` checkout and add `--check-remote-main` so the saved report proves whether the reviewed commit matched live `origin/main` at run time.

Run only the local lexical benchmark:

```bash
python3 os/verification/retrieval/scripts/benchmark_retrieval.py --suite local
```

Run only one retrieval fixture. `--question-id` remains supported; `--fixture-id` is the generic benchmark alias:

```bash
python3 os/verification/retrieval/scripts/benchmark_retrieval.py --suite local --fixture-id run-benchmarks
```

Run only the harness dry-run plan across known harnesses:

```bash
python3 os/verification/retrieval/scripts/benchmark_retrieval.py --suite harness
```

Self-test the harness grader without external model calls:

```bash
python3 os/verification/retrieval/scripts/benchmark_retrieval.py --self-test
```

Run a real single-harness eval when the CLI is installed, authenticated, and you intend to spend a model call:

```bash
python3 os/verification/retrieval/scripts/benchmark_retrieval.py --suite harness --harness codex --no-dry-run --save-report
```

Run all known harnesses for real only when you intend to spend all of those model calls:

```bash
python3 os/verification/retrieval/scripts/benchmark_retrieval.py --suite harness --harness all --no-dry-run --save-report
```

Compare a specific model or effort level when needed:

```bash
python3 os/verification/retrieval/scripts/benchmark_retrieval.py --suite harness --harness codex --model gpt-5.5 --effort high --no-dry-run --save-report
```
