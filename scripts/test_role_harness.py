"""Trust test 5: role harness — run_role runs one bounded, scoped, prompted agent call.

Uses a scripted (offline) provider so no API key or network is needed. Proves:
  - the model is offered ONLY the role's scoped tools (scoping reaches the LLM)
  - the role's OWN system prompt is what the provider receives
  - an in-scope tool dispatches; an out-of-scope tool call → ToolResult(is_error=True)
"""
from ouroboros.agent.state import ToolCall
from ouroboros.llm.provider import LLMProvider, LLMResponse
from ouroboros.tools.schema import Tool, ToolRegistry
from code_fixer.roles import Role, run_role


class ScriptedProvider(LLMProvider):
    """Returns pre-baked responses in order; records what each call was handed."""

    def __init__(self, *responses):
        self._responses = list(responses)
        self.offered_tools: list[list[str]] = []
        self.seen_prompts: list[str] = []

    def complete(self, system_prompt, messages, tools):
        self.offered_tools.append(sorted(t.name for t in tools))
        self.seen_prompts.append(system_prompt)
        return self._responses.pop(0)


def make_tool(name):
    return Tool(
        name=name,
        description=name,
        parameters_schema={"type": "object", "properties": {}},
        handler=lambda: f"{name}-ran",
    )


def call(name):
    return ToolCall(id=f"{name}:1", name=name, arguments={})


registry = ToolRegistry()
for n in ("alpha", "beta", "gamma"):
    registry.register(make_tool(n))

reader = Role(name="reader", system_prompt="ROLE-READER-PROMPT", tools=("alpha", "beta"), max_steps=5)

SEP = "-" * 60

# Scenario 1 — role calls an in-scope tool, then finishes.
prov = ScriptedProvider(
    LLMResponse(text=None, tool_calls=[call("alpha")], stop_reason="tool_use"),
    LLMResponse(text="done", tool_calls=[], stop_reason="end_turn"),
)
state = run_role(reader, "do the thing", prov, registry)

print(SEP)
print("Scenario 1: run_role with an in-scope tool")
offered = prov.offered_tools[0]
print(f"  {'PASS' if offered == ['alpha', 'beta'] else 'FAIL'} — model offered only role tools: {offered} (registry has 3)")
print(f"  {'PASS' if prov.seen_prompts[0] == 'ROLE-READER-PROMPT' else 'FAIL'} — role's own system prompt reached the provider")
in_scope_ok = not state.step_logs[0].tool_results[0].is_error
print(f"  {'PASS' if in_scope_ok else 'FAIL'} — in-scope tool 'alpha' dispatched without error")
print(f"  {'PASS' if state.completed and state.final_answer == 'done' else 'FAIL'} — run reached a final answer")

# Scenario 2 — same role tries an out-of-scope tool; the harness must block it.
prov2 = ScriptedProvider(
    LLMResponse(text=None, tool_calls=[call("gamma")], stop_reason="tool_use"),
    LLMResponse(text="gave up", tool_calls=[], stop_reason="end_turn"),
)
state2 = run_role(reader, "try gamma", prov2, registry)

print(SEP)
print("Scenario 2: same role calls an out-of-scope tool")
err = state2.step_logs[0].tool_results[0]
print(f"  {'PASS' if err.is_error else 'FAIL'} — out-of-scope 'gamma' → is_error=True, content={err.content!r}")

print(SEP)
print("Done — a role is a bounded call: own prompt, own budget, only its tools.")
