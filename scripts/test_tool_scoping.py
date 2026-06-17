"""Trust test 4: tool scoping — a ScopedTools view restricts what a role can see and call.

  - all_tools() advertises only in-scope tools to the model
  - get() returns the tool when in scope, None when not
  - an out-of-scope call dispatched through the loop becomes ToolResult(is_error=True),
    reusing the same error-as-observation path as an unknown tool
"""
from ouroboros.agent.loop import _dispatch_tool
from ouroboros.agent.state import ToolCall
from ouroboros.tools.schema import ScopedTools, Tool, ToolRegistry


def make_tool(name):
    return Tool(
        name=name,
        description=name,
        parameters_schema={"type": "object", "properties": {}},
        handler=lambda: name,
    )


registry = ToolRegistry()
for n in ("alpha", "beta", "gamma"):
    registry.register(make_tool(n))

scoped = ScopedTools(registry, {"alpha", "beta"})

SEP = "-" * 60

print(SEP)
print("Part A: all_tools() advertises only in-scope tools")
names = sorted(t.name for t in scoped.all_tools())
print(f"  {'PASS' if names == ['alpha', 'beta'] else 'FAIL'} — scoped.all_tools() = {names} (parent has 3)")

print(SEP)
print("Part B: get() respects scope")
print(f"  {'PASS' if scoped.get('alpha') is not None else 'FAIL'} — get('alpha') in scope → tool")
print(f"  {'PASS' if scoped.get('gamma') is None else 'FAIL'} — get('gamma') out of scope → None")

print(SEP)
print("Part C: out-of-scope dispatch → ToolResult(is_error=True)")
call = ToolCall(id="gamma:test", name="gamma", arguments={})
result = _dispatch_tool(call, scoped)
print(f"  {'PASS' if result.is_error else 'FAIL'} — dispatch('gamma') → is_error={result.is_error}, content={result.content!r}")

print(SEP)
print("Done — scope restricts visibility and dispatch; enforcement reuses the error path.")
