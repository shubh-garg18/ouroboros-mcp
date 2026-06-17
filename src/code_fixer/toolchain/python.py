"""Python adapter: ruff + mypy + bandit for discovery/checks, pytest for tests.

Each tool is split into 'run it' (subprocess) and 'parse its output' (pure
string -> Issues). The parsers carry no side effects, so they're unit-testable
against captured sample output without the tool installed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from code_fixer.process import CommandResult, run_command
from code_fixer.toolchain.base import CheckResult, Issue, Severity, Toolchain


class PythonToolchain(Toolchain):
    # Never read a stale .pyc when verifying a fix: a one-character edit can collide
    # with cached bytecode of the same size written in the same second, so the cache
    # looks valid and the old code runs. Not writing bytecode forces a recompile from
    # current source on every run — a real correctness need for the verify boundary.
    _ENV = {"PYTHONDONTWRITEBYTECODE": "1"}

    def __init__(self, repo_path: Path | str, target: str = ".", timeout: int = 120) -> None:
        self.repo = Path(repo_path)
        self.target = target
        self.timeout = timeout

    def _run(self, args: list[str]) -> CommandResult:
        return run_command(args, cwd=self.repo, timeout=self.timeout, env=self._ENV)

    def discover(self) -> list[Issue]:
        issues: list[Issue] = []

        ruff = self._run(["ruff", "check", "--output-format", "json", self.target])
        if ruff.found:
            issues += parse_ruff(ruff.stdout, self.repo)

        mypy = self._run(["mypy", "--no-error-summary", "--show-column-numbers", "--show-error-codes", self.target])
        if mypy.found:
            issues += parse_mypy(mypy.stdout, self.repo)

        bandit = self._run(["bandit", "-r", self.target, "-f", "json", "-q"])
        if bandit.found:
            issues += parse_bandit(bandit.stdout, self.repo)

        # Ranked: highest severity first, then a stable file/line order.
        return sorted(issues, key=lambda i: (-int(i.severity), i.path, i.line))

    def check(self) -> CheckResult:
        runs = (
            self._run(["ruff", "check", self.target]),
            self._run(["mypy", self.target]),
            self._run(["bandit", "-r", self.target, "-q"]),
        )
        return CheckResult(runs=runs)

    def test(self) -> CommandResult:
        return self._run(["pytest", "-q"])


# --- parsers (pure: captured output -> normalized Issues) ---

def parse_ruff(stdout: str, repo: Path | None = None) -> list[Issue]:
    text = stdout.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    out: list[Issue] = []
    for it in data:
        code = it.get("code") or "?"
        loc = it.get("location") or {}
        out.append(Issue(
            tool="ruff",
            code=code,
            message=it.get("message", ""),
            path=_rel(it.get("filename", ""), repo),
            line=int(loc.get("row", 0)),
            column=loc.get("column"),
            severity=_ruff_severity(code),
        ))
    return out


_MYPY_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):(?P<col>\d+):\s+"
    r"(?P<sev>error|warning|note):\s+(?P<msg>.*?)(?:\s+\[(?P<code>[\w-]+)\])?$"
)


def parse_mypy(stdout: str, repo: Path | None = None) -> list[Issue]:
    out: list[Issue] = []
    for line in stdout.splitlines():
        m = _MYPY_RE.match(line.strip())
        if not m or m.group("sev") == "note":
            continue
        out.append(Issue(
            tool="mypy",
            code=m.group("code") or "?",
            message=m.group("msg"),
            path=_rel(m.group("path"), repo),
            line=int(m.group("line")),
            column=int(m.group("col")),
            severity=_mypy_severity(m.group("sev")),
        ))
    return out


def parse_bandit(stdout: str, repo: Path | None = None) -> list[Issue]:
    text = stdout.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    out: list[Issue] = []
    for it in data.get("results", []):
        out.append(Issue(
            tool="bandit",
            code=it.get("test_id", "?"),
            message=it.get("issue_text", ""),
            path=_rel(it.get("filename", ""), repo),
            line=int(it.get("line_number", 0)),
            column=it.get("col_offset"),
            severity=_bandit_severity(it.get("issue_severity", "LOW")),
        ))
    return out


def _rel(path: str, repo: Path | None) -> str:
    if not path or repo is None:
        return path
    try:
        return str(Path(path).relative_to(Path(repo)))
    except ValueError:
        return path


# Severity assignment is a starting heuristic — tune as real runs inform it.
def _ruff_severity(code: str) -> Severity:
    if code.startswith(("E9", "F82", "F7")):   # syntax errors, undefined names, logic bugs
        return Severity.HIGH
    if code.startswith("F"):                    # pyflakes (unused imports/vars, ...)
        return Severity.MEDIUM
    return Severity.LOW


def _mypy_severity(sev: str) -> Severity:
    return {"error": Severity.HIGH, "warning": Severity.MEDIUM}.get(sev, Severity.LOW)


def _bandit_severity(sev: str) -> Severity:
    return {"HIGH": Severity.HIGH, "MEDIUM": Severity.MEDIUM}.get(str(sev).upper(), Severity.LOW)
