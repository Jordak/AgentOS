#!/usr/bin/env python3
"""Deterministic local validators for AgentOS maintenance.

The checks in this script intentionally avoid network calls and connector reads.
They inspect local Markdown files, local path existence, and portable AgentOS
metadata. Machine-local Core skill exposure is checked by the expose-skills
skill instead of this portable validator.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from agentos_validator.common import AgentOSValidatorBase, _bootstrap_lexical_absolute
from agentos_validator.managed import ManagedSymlinkValidator
from agentos_validator.publication import PublicationValidator
from agentos_validator.self_test import run_self_test
from agentos_validator.skills import SkillValidator
from agentos_validator.structural import StructuralValidator

sys.dont_write_bytecode = True


class AgentOSValidator(AgentOSValidatorBase):
    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.managed_symlinks = ManagedSymlinkValidator(self)
        self.publication_validator = PublicationValidator(self)
        self.skill_validator = SkillValidator(self)
        self.structural_validator = StructuralValidator(self)
        self._delegates = (
            self.managed_symlinks,
            self.publication_validator,
            self.skill_validator,
            self.structural_validator,
        )

    def __getattr__(self, name: str) -> Any:
        for delegate in self._delegates:
            if callable(getattr(type(delegate), name, None)):
                return getattr(delegate, name)
        raise AttributeError(name)

    def run(self) -> int:
        self.run_structural_checks()
        self.run_publication_precheck_checks()
        return self.report()

    def run_structural_only(self) -> int:
        self.run_structural_checks()
        return self.report()

    def run_structural_checks(self) -> None:
        self.structural_validator.run_structural_checks()

    def run_publication_precheck(self) -> int:
        self.run_publication_precheck_checks()
        return self.report()

    def run_publication_precheck_checks(self) -> None:
        self.publication_validator.run_publication_precheck_checks()

    def run_public_export_validation(self, export_root: Path) -> int:
        self.run_public_export_validation_checks(export_root)
        return self.report()

    def run_public_export_validation_checks(self, export_root: Path) -> None:
        self.publication_validator.run_public_export_validation_checks(export_root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic AgentOS maintenance validators.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="AgentOS repository root. Defaults to the repository containing os/.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run a safe temporary fixture that demonstrates a failing invariant.",
    )
    parser.add_argument(
        "--publication-precheck",
        action="store_true",
        help="Run publication precheck against the mixed local working tree.",
    )
    parser.add_argument(
        "--structural-only",
        action="store_true",
        help="Run only structural AgentOS checks, without publication/privacy precheck checks.",
    )
    parser.add_argument(
        "--public-export",
        type=Path,
        help="Run public-export validation against the given generated export directory.",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test(AgentOSValidator)

    if not (args.root / "os").exists():
        print(f"AgentOS validation failed: root does not contain os/: {args.root}", file=sys.stderr)
        return 2

    validator = AgentOSValidator(args.root)
    if args.public_export:
        export_root = _bootstrap_lexical_absolute(args.public_export)
        if not (export_root / "os").exists():
            print(f"AgentOS validation failed: export root does not contain os/: {export_root}", file=sys.stderr)
            return 2
        return validator.run_public_export_validation(export_root)
    if args.publication_precheck:
        return validator.run_publication_precheck()
    if args.structural_only:
        return validator.run_structural_only()

    return validator.run()


if __name__ == "__main__":
    raise SystemExit(main())
