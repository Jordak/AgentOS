# Source Routing Fixtures

Status: deterministic validator coverage.

This directory contains public-safe fixtures for checking whether AgentOS Core still exposes enough route evidence for common prompts. The fixtures are consumed by `scripts/run-validator` through `os/verification/scripts/validate_agentos.py`.

This is not a benchmark suite. It does not call a harness, grade model prose, produce a score, or save reports. Guidance Eval remains the maintained behavior benchmark for whether a harness applies AgentOS guidance correctly.

## Contents

- `fixtures.json`: route-evidence fixtures. Each fixture names a prompt category, expected route, and source evidence that must still exist in Core files.

## Updating

Add or update these fixtures when a public-safe routing behavior needs deterministic source coverage and the expected route can be checked from stable Core files. Use Guidance Eval fixtures instead when the behavior depends on how a harness applies guidance in context.
