# Thin Trusted Scripts

AgentOS scripts should be thin, deterministic, and easy to audit before a user runs them on a personal or work computer. Executable code is a trust boundary: a cautious user or security reviewer should be able to understand what a script can read, what it can write, what subprocesses it can run, and what external effects it can have without reverse-engineering broad agent-like behavior.

Scripts may gather deterministic facts, validate deliberately structured inputs, run bounded read-only checks, print exact command recommendations, and perform explicit write modes when the command and flags clearly advertise those writes. Scripts should not absorb ambiguous policy judgment, private prose interpretation, open-ended setup diagnosis, or remediation orchestration when a Markdown skill or playbook can handle that judgment with explanation and user approval.

Markdown skills and playbooks own the richer layer: interpreting ambiguous local state, comparing conflicting evidence, deciding whether private notes are active or obsolete, synthesizing recommendations, and asking before changes. When executable checks encounter ambiguous evidence, the preferred outcome is a conservative warning such as `needs agent review`, not a hard PASS produced by clever parsing.

More complex scripts are allowed when the complexity itself provides deterministic value that must be executable, such as a validator, installer, exporter, skill exposure adapter manager, or benchmark runner. That complexity should remain narrowly scoped, testable, and explicit about mutability. Trust is earned by making behavior legible and bounded, not by moving every possible judgment into code.
