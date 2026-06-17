"""Subprocess helper shared by the sandbox and the toolchains.

Every external command (git, ruff, pytest, ...) goes through run_command so that
'tool not installed', timeouts, and exit codes are reported uniformly. A result
is deterministic data — no exceptions for a non-zero exit; the caller decides
what a failure means (fail-closed for checks, best-effort for discovery).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    found: bool = True       # False when the executable wasn't on PATH
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        # A command only "passed" if it actually ran to completion with exit 0.
        # Missing tool or timeout => not ok, so checks/tests fail closed.
        return self.found and not self.timed_out and self.exit_code == 0


def run_command(
    args: list[str],
    cwd: Path | None = None,
    timeout: int = 120,
    env: dict[str, str] | None = None,
) -> CommandResult:
    pretty = " ".join(args)
    exe = shutil.which(args[0])
    if exe is None:
        return CommandResult(pretty, 127, "", f"executable not found: {args[0]}", 0, found=False)

    full_env = {**os.environ, **env} if env else None
    start = time.monotonic()
    try:
        proc = subprocess.run(
            [exe, *args[1:]],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=full_env,
        )
    except subprocess.TimeoutExpired as e:
        dur = int((time.monotonic() - start) * 1000)
        out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        return CommandResult(pretty, -1, out, f"{err}\n[timed out after {timeout}s]", dur, timed_out=True)

    dur = int((time.monotonic() - start) * 1000)
    return CommandResult(pretty, proc.returncode, proc.stdout, proc.stderr, dur)
