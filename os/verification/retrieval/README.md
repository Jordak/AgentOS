# AgentOS Retrieval Verification

Status: active verification area.

This directory owns AgentOS retrieval and discoverability checks. "Retrieval" here means the practical question an agent has to answer before doing good work: which local AgentOS file is the canonical source for this prompt?

## Purpose

AgentOS is useful only if an active harness can find the right local source of truth at the moment it needs it. This verification area turns that into a repeatable check.

The benchmark asks representative AgentOS lookup questions and checks whether the answer is grounded in the right local files. A passing answer must:

- cite the relevant AgentOS source of truth;
- support the answer with evidence from local files;
- avoid eval fixtures, previous reports, and other answer-key files.

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
- `os/verification/BENCHMARK_HISTORY.md`: curated Core history for public-safe retrieval benchmark outcomes. The local index and harness grader exclude this file so previous summaries cannot contaminate answer-key discovery.

## Eval Layers

Structural fixtures:

- Validate that local files contain the evidence needed to route common prompts.
- Run with `python3 os/verification/scripts/validate_agentos.py`.
- Offline and deterministic.

Local lexical benchmark:

- Compares whole-file keyword search with a lightweight Markdown section index.
- Run by default, or alone with `python3 os/verification/retrieval/scripts/benchmark_retrieval.py --suite local`.
- Offline and deterministic.

Harness answer evals:

- Ask a real harness, such as Codex CLI or Claude Code, to answer lookup questions with structured JSON.
- Grade only deterministic evidence: schema shape, cited canonical paths, local evidence support, and disallowed-source avoidance.
- Leave full prose quality as manual review unless a later judge is added.
- Harness mode defaults to dry-run. Real model calls require `--no-dry-run`.
- Harness model and effort default to each harness's configured defaults unless `--model` or `--effort` is provided.

## Commands

Run deterministic maintenance validation:

```bash
python3 os/verification/scripts/validate_agentos.py
```

Run the full safe retrieval benchmark report:

```bash
python3 os/verification/retrieval/scripts/benchmark_retrieval.py
```

Save the full safe report. This creates a timestamped directory containing `report.md` and `run.json`:

```bash
python3 os/verification/retrieval/scripts/benchmark_retrieval.py --save-report
```

Run only the local lexical benchmark:

```bash
python3 os/verification/retrieval/scripts/benchmark_retrieval.py --suite local
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
