"""Language adapters. One Toolchain per language, three deterministic jobs:
discover issues, run checks, run tests. The agents never change; only the
adapter swaps (Python today; JS/TS and Go later)."""

from code_fixer.toolchain.base import CheckResult, Issue, Severity, Toolchain
from code_fixer.toolchain.python import PythonToolchain

__all__ = ["Toolchain", "Issue", "Severity", "CheckResult", "PythonToolchain"]
