"""The agent loop.

Input state → LLM → (tool call → execute → update state → LLM again) → repeat → final answer

That's it. Everything else in the file is error handling, logging, and
termination checks.
"""

from __future__ import annotations

import json
import time

from agent.errors import (
    BudgetExhaustedError,
    LoopDetectedError,
    ToolNotFoundError,
)
from agent.prompts import SYSTEM_PROMPT
from agent.state import (
    AgentState,
    Message,
    Role,
    StepLog,
    ToolCall,
    ToolResult,
)
from llm.provider import LLMProvider
from tools.schema import ToolRegistry

def run_agent(
    goal:str,
    llm:LLMProvider,
    registry:ToolRegistry,
    max_steps:int=10,
)->AgentState:
    """Drive the agent loop until a final answer is produced or the step budget is exhausted."""
    state=AgentState(
        goal=goal,
        max_steps=max_steps,
    )
    state.append(Message(
        role=Role.USER,
        content=goal
    ))
    
    while not state.completed:
        if state.is_budget_exhausted():
            raise BudgetExhaustedError(
                f"Agent hit {max_steps} steps without a final answer."
            )
            
        state.step+=1
        step_start=time.monotonic()
        
        # 1. Ask LLM what to do next
        response=llm.complete(
            system_prompt=SYSTEM_PROMPT,
            messages=state.messages,
            tools=registry.all_tools(),
        )
        
        # 2. Record Assistant's turn in state
        assistant_msg=Message(
            role=Role.ASSISTANT,
            content=response.text,
            tool_call=response.tool_calls,
        )
        state.append(assistant_msg) # conversation history must stay consistent
        
        # 3. No tool calls? This is the final answer. Exit.
        if not response.tool_calls:
            state.completed=True
            state.final_answer=response.text or ""
            _log_step(
                state,
                step_start,
                response.text,
                [],
                [],
            )
            break
        
        # 4. Loop detection — same tool+args repeated means we're stuck in a loop
        _check_loop(state, response.tool_calls)
        
        # 5. Dispatch each tool call and append results
        results:list[ToolResult]=[]
        for call in response.tool_calls:
            result=_dispatch_tool(call, registry)
            results.append(result)
            state.append(Message(
                role=Role.TOOL,
                tool_result=result,
            ))
        _log_step(
            state,
            step_start,
            response.text,
            response.tool_calls,
            results,
        )
        
    return state

def _dispatch_tool(
    call:ToolCall,
    registry:ToolRegistry,
)->ToolResult:
    """Look up the requested tool in the registry and invoke it, returning a structured result even on failure."""
    tool=registry.get(call.name)
    if tool is None:
        return ToolResult(
            tool_call_id=call.id,
            content=f"Tool '{call.name}' is not registered. Available: {[t.name for t in registry.all_tools()]}",
            is_error=True,
        )
    try:
        output=tool.invoke(call.arguments)
        return ToolResult(
            tool_call_id=call.id,
            content=output,
            is_error=False,
        )
    except Exception as e:
        return ToolResult(
            tool_call_id=call.id,
            content=f"{type(e).__name__}: {e}",
            is_error=True,
        )
        
def _check_loop(
    state: AgentState, 
    new_calls: list[ToolCall]
) -> None:
    """If the last 3 steps all made the same (name, args) call, we're looping."""
    if state.step < 3:
        return
    recent = [log for log in state.step_logs[-2:]] + [None]  # placeholder for current
    signatures = []
    for log in state.step_logs[-2:]:
        signatures.append([(c.name, json.dumps(c.arguments, sort_keys=True)) for c in log.tool_calls])
    signatures.append([(c.name, json.dumps(c.arguments, sort_keys=True)) for c in new_calls])
    if len(signatures) == 3 and signatures[0] == signatures[1] == signatures[2] and signatures[0]:
        raise LoopDetectedError(
            f"Same tool call issued 3 steps in a row: {signatures[0]}"
        )


def _log_step(
    state: AgentState,
    step_start: float,
    llm_text: str | None,
    tool_calls: list[ToolCall],
    results: list[ToolResult],
) -> None:
    """Record a completed step's timing and tool activity, then print a one-line summary."""
    log = StepLog(
        step=state.step,
        llm_text=llm_text,
        tool_calls=tool_calls,
        tool_results=results,
        duration_ms=int((time.monotonic() - step_start) * 1000),
    )
    state.step_logs.append(log)
    print(
        f"[step {log.step}] tools={[c.name for c in tool_calls]} "
        f"errors={sum(1 for r in results if r.is_error)} "
        f"took={log.duration_ms}ms",
        flush=True,
    )
        
