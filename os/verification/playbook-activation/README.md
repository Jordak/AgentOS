# AgentOS Playbook Activation Verification

Status: initial playbook coverage.

This verification checks whether realistic tasks activate the AgentOS playbook files that should shape the work.

Retrieval verification asks whether a harness can find the right source when directly asked. Playbook activation verification asks whether the harness actually reads the relevant operating guidance during the task where that guidance matters.

## Purpose

AgentOS playbook entries are only useful if agents load them at the right moment. This suite makes that habit observable.

A passing fixture means the run transcript shows real access to the required guidance file. It is not enough for the final answer to claim the file was read.

## Scoring Scope

This benchmark grades only guidance activation: whether the transcript shows observed access to each fixture's `must_access` guidance files.

Observed guidance-file access remains gating because it is the activation behavior under test. Prose claims, exact quotes, task completion, and implementation correctness remain diagnostic only.

Task completion, final-answer quality, write success, read-only sandbox failures, blocked patch attempts, and implementation correctness are diagnostic context only. They do not affect activation pass/fail.

## Contents

- `fixtures.json`: task prompts and required guidance files.
- `coverage.json`: actionable playbook activation rules and fixture inventory status. Coverage entries are validated against fixture `must_access` paths before reports are produced.
- `scripts/benchmark_playbook_activation.py`: dry-run, transcript grading, report writing, and self-test.
- `personal/os/verification/playbook-activation/reports/`: saved report directories with `report.md` and `run.json`.

## Commands

Preview the whole benchmark without model calls:

```bash
python3 os/verification/playbook-activation/scripts/benchmark_playbook_activation.py
```

This should show fixture coverage for every rule currently listed in `coverage.json`.

Run the benchmark and save both report formats:

```bash
python3 os/verification/playbook-activation/scripts/benchmark_playbook_activation.py --no-dry-run --save-report
```

That runs every configured harness. Right now, that means Codex.

When producing evidence for `os/verification/BENCHMARK_STATUS.md`, run from a clean `main` checkout and add `--check-remote-main` so the saved report proves whether the reviewed commit matched live `origin/main` at run time. Default dry-run and transcript reports avoid remote network checks unless that flag is set.

Run only one harness:

```bash
python3 os/verification/playbook-activation/scripts/benchmark_playbook_activation.py --harness codex --no-dry-run --save-report
```

Run only one fixture:

```bash
python3 os/verification/playbook-activation/scripts/benchmark_playbook_activation.py --fixture-id github-pr-from-skill-report
```

Grade a saved transcript or run log:

```bash
python3 os/verification/playbook-activation/scripts/benchmark_playbook_activation.py --transcript path/to/transcript.log
```

Self-test the transcript grader:

```bash
python3 os/verification/playbook-activation/scripts/benchmark_playbook_activation.py --self-test
```
