# src/agentic_mcp/tools/local/file_ops.py
"""Sandboxed file reader.

Reads files under a workspace directory only. Path traversal is blocked
by resolving and checking containment.
"""
from pathlib import Path

from tools.schema import Tool

WORKSPACE = Path("./workspace").resolve()
WORKSPACE.mkdir(exist_ok=True)


def read_file(path: str) -> str:
    target = (WORKSPACE / path).resolve()
    if not target.is_relative_to(WORKSPACE):
        raise ValueError(f"Path escapes workspace: {path}")
    if not target.exists():
        raise FileNotFoundError(f"No such file: {path}")
    if target.stat().st_size > 100_000:
        raise ValueError(f"File too large (>100KB): {path}")
    return target.read_text(encoding="utf-8")


read_file_tool = Tool(
    name="read_file",
    description=(
        "Read a UTF-8 text file from the local workspace. "
        "Paths are relative to the workspace root. Max 100KB."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path within workspace."},
        },
        "required": ["path"],
    },
    handler=read_file,
)