"""The sandbox: an isolated directory the Orchestrator clones target repos into
and runs tools within. Nothing here touches the host outside `root`.

Cloning is setup, not agent reasoning, so a failed clone raises (a run failure)
rather than returning an observation — consistent with how the runtime treats
budget/loop failures.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from code_fixer.process import run_command


class Sandbox:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    @classmethod
    def create(cls, base: Path | None = None) -> "Sandbox":
        return cls(Path(tempfile.mkdtemp(prefix="ouroboros-", dir=str(base) if base else None)))

    def clone(self, source: str, name: str = "repo", depth: int | None = 1) -> Path:
        """Clone `source` (a URL or local path) into root/name; return the repo path."""
        dest = self.root / name
        args = ["git", "clone"]
        if depth:
            args += ["--depth", str(depth)]
        args += [source, str(dest)]
        res = run_command(args, timeout=300)
        if not res.ok:
            raise RuntimeError(f"git clone failed (exit {res.exit_code}): {res.stderr.strip() or res.stdout.strip()}")
        return dest

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
