# AgentOS Experiments

Status: no active experiments.

Use this file for reversible AgentOS behavior experiments that are not yet core operating rules. Experiments here should be narrow, observable, and easy to remove.

## Graduated Experiments

### HTML-First Human Artifacts

Status: graduated to production on 2026-05-09.

The HTML-first human artifacts experiment is now production AgentOS behavior. See `os/playbook/ARTIFACTS.md` for the canonical policy.

## Completed Pilots

### Local Markdown Retrieval

Status: retired on 2026-06-02.

The local retrieval pilot compared broad keyword lookup with a lightweight Markdown section index over AgentOS files. The section index improved fixture hit rate, but AgentOS keeps full GBrain-style retrieval and local lexical scoring out of scope.

AgentOS no longer keeps retrieval as a runnable benchmark suite. The useful route-evidence fixtures from this pilot now live as deterministic validator coverage under `os/verification/source-routing/fixtures.json`; Guidance Eval owns harness behavior, hidden fixture, and source-boundary checks.
