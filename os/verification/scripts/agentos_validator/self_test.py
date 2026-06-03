"""Self-test orchestration for AgentOS validation."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .common import run_self_test as run_common_self_test
from .managed import run_self_test as run_managed_self_test
from .publication import run_self_test as run_publication_self_test
from .skills import run_self_test as run_skills_self_test
from .structural import run_self_test as run_structural_self_test


@dataclass
class SelfTestExpectation:
    label: str
    passed: bool


class SelfTestHarness:
    def __init__(self, validator_class: type, root: Path) -> None:
        self.validator_class = validator_class
        self.root = root
        self.expectations: list[SelfTestExpectation] = []
        self.validators: list[Any] = []

    def validator(self, root: Path | None = None) -> Any:
        return self.validator_class(root or self.root)

    def record(self, *validators: Any) -> None:
        self.validators.extend(validators)

    def expect(self, label: str, condition: bool) -> None:
        self.expectations.append(SelfTestExpectation(label, condition))

    def passed(self) -> bool:
        return all(expectation.passed for expectation in self.expectations)

    def print_report(self) -> None:
        if self.passed():
            print("SELF-TEST PASS: modular validator fixtures were caught.")
            for validator in self.validators:
                for error in validator.errors:
                    print(f"EXPECTED {error.format()}")
            return

        print("SELF-TEST FAIL: expected modular validator fixtures were not caught.")
        for expectation in self.expectations:
            if not expectation.passed:
                print(f"MISSING {expectation.label}")


SELF_TESTS: tuple[Callable[[SelfTestHarness], None], ...] = (
    run_common_self_test,
    run_managed_self_test,
    run_structural_self_test,
    run_skills_self_test,
    run_publication_self_test,
)


def run_self_test(validator_class: type) -> int:
    with tempfile.TemporaryDirectory(prefix="agentos-validator-") as tmp:
        harness = SelfTestHarness(validator_class, Path(tmp).resolve())
        for self_test in SELF_TESTS:
            self_test(harness)
        harness.print_report()
        return 0 if harness.passed() else 1
