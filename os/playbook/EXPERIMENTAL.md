# AgentOS Experiments

Status: no active experiments.

Use this file for reversible AgentOS behavior experiments that are not yet core operating rules. Experiments here should be narrow, observable, and easy to remove.

## Graduated Experiments

### HTML-First Human Artifacts

Status: graduated to production on 2026-05-09.

The HTML-first human artifacts experiment is now production AgentOS behavior. See `os/playbook/ARTIFACTS.md` for the canonical policy.

## Completed Pilots

### Local Markdown Retrieval

Status: graduated to verification benchmark on 2026-05-16.

The local retrieval pilot compared broad keyword lookup with a lightweight Markdown section index over AgentOS files. The section index improved fixture hit rate. AgentOS still keeps full GBrain-style retrieval out of scope, but the fixture set and local benchmark are now part of retrieval verification.

See `os/verification/retrieval/LOCAL_BENCHMARK.md` for the Core benchmark description. Live saved retrieval runs belong in `personal/os/verification/retrieval/reports/`.
