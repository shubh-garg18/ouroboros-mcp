"""Test 3: loop detection — directly exercise _check_loop with 3 identical tool calls."""
from ouroboros.agent.errors import LoopDetectedError
from ouroboros.agent.loop import _check_loop
from ouroboros.agent.state import AgentState, StepLog, ToolCall

def make_call(name="broken_search", args=None):
    return ToolCall(id="x", name=name, arguments=args or {"query": "France"})

def make_log(step, calls):
    return StepLog(step=step, llm_text=None, tool_calls=calls, tool_results=[], duration_ms=0)

state = AgentState(goal="test", max_steps=10)
call = make_call()

# Simulate 2 prior identical steps in logs
state.step_logs.append(make_log(1, [call]))
state.step_logs.append(make_log(2, [call]))
state.step = 3

try:
    _check_loop(state, [call])
    print("FAIL — LoopDetectedError was not raised")
except LoopDetectedError as e:
    print("PASS — LoopDetectedError raised as expected:")
    print(" ", e)
