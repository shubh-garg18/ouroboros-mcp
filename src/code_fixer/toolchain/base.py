"""The Toolchain contract and its shared, language-neutral result types.

This is the one boundary everything language-specific hides behind. The
Orchestrator and the role agents speak only in Issue / CheckResult / CommandResult
— never in 'ruff' or 'pytest'. Swapping languages swaps the adapter, nothing else.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum

from code_fixer.process import CommandResult


class Severity(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass(frozen=True)
class Issue:
    """One discovered problem, normalized across analyzers."""

    tool: str            # which analyzer found it (ruff / mypy / bandit)
    code: str            # rule id, e.g. "F401", "B101", "operator"
    message: str
    path: str            # file path, relative to the repo root
    line: int
    column: int | None
    severity: Severity


@dataclass(frozen=True)
class CheckResult:
    """Aggregate of every checker run. Empty or any failed/missing run => not ok."""

    runs: tuple[CommandResult, ...]

    @property
    def ok(self) -> bool:
        return bool(self.runs) and all(r.ok for r in self.runs)


class Toolchain(ABC):
    @abstractmethod
    def discover(self) -> list[Issue]:
        """Best-effort: run the analyzers and return a ranked list of issues.
        A missing analyzer contributes nothing; it never aborts discovery."""

    @abstractmethod
    def check(self) -> CheckResult:
        """Fail-closed gate: run the analyzers; a missing or failing one => not ok."""

    @abstractmethod
    def test(self) -> CommandResult:
        """Fail-closed: run the test suite. This is the trust boundary."""
