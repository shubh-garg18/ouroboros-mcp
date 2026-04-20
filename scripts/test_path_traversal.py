"""Test 2: path traversal blocked — directly exercise the sandbox and error-as-observation pattern.

The LLM is too smart to call read_file("/etc/passwd") after reading the tool description
("Paths are relative to the workspace root"), so this test drives the mechanism directly:

  step 1 — call read_file with a traversal path → ValueError raised
  step 2 — _dispatch_tool wraps it as ToolResult(is_error=True)   ← the observation
  (the LLM would then see the error and report "can't read that file")
"""
import sys
sys.path.insert(0, "src")

from agent.loop import _dispatch_tool
from agent.state import ToolCall
from tools.local.file_ops import read_file, read_file_tool
from tools.schema import ToolRegistry

SEPARATOR = "-" * 60

# ── Part A: raw handler raises ValueError ─────────────────────────
print(SEPARATOR)
print("Part A: read_file() handler blocks path traversal")
for bad_path in ("/etc/passwd", "../../../etc/passwd"):
    try:
        read_file(bad_path)
        print(f"  FAIL  path={bad_path!r} — no exception raised")
    except ValueError as e:
        print(f"  PASS  path={bad_path!r} → ValueError: {e}")
    except Exception as e:
        print(f"  FAIL  path={bad_path!r} — unexpected {type(e).__name__}: {e}")

# ── Part B: _dispatch_tool wraps the exception as is_error=True ───
print(SEPARATOR)
print("Part B: _dispatch_tool converts exception → ToolResult(is_error=True)")

registry = ToolRegistry()
registry.register(read_file_tool)

for bad_path in ("/etc/passwd", "../../../etc/passwd"):
    call = ToolCall(id=f"read_file:test", name="read_file", arguments={"path": bad_path})
    result = _dispatch_tool(call, registry)
    if result.is_error:
        print(f"  PASS  path={bad_path!r} → is_error=True, content={result.content!r}")
    else:
        print(f"  FAIL  path={bad_path!r} — expected is_error=True, got content={result.content!r}")

print(SEPARATOR)
print("Done — sandbox blocks traversal; errors are observations, not crashes.")
