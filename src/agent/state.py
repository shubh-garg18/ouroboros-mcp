"""Agent state — the single source of truth for a run.

The loop is just a function that takes state, calls the LLM, maybe dispatches
a tool, and returns updated state. Keeping state explicit (rather than hidden
in instance variables) makes the loop easy to test, log, and replay.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum

class Role(str,Enum):
    """Who produced a message. Matches the 3 roles LLM API uses."""
    USER="user"
    ASSISTANT="assistant"
    TOOL="tool"
    
@dataclass
class Message:
    """One turn of conversation.

    For a plain text message, `content` is set and `tool_calls`/`tool_result`
    are None. For an assistant message that requested tools, `tool_calls` is
    populated. For a tool-result message, `tool_result` is populated.
    """
    role:Role
    content:str|None=None
    tool_call:list[ToolCall]=field(default_factory=list)
    tool_result:ToolResult|None=None
    
@dataclass
class ToolCall:
    """An LLM's request to invoke a tool. We don't execute; we dispatch."""
    id:str
    name:str
    arguments:dict[str,Any]
    
@dataclass
class ToolResult:
    """What we send back to the LLM after running a tool.

    `is_error` tells the LLM the call failed — the LLM then decides whether
    to retry, try a different tool, or give up. Errors are observations,
    not exceptions. This is the key insight of agent design.
    """
    tool_call_id:str
    content:str
    is_error:bool=False
    
@dataclass
class StepLog:
    """One iteration of the loop, captured for tracing/debugging.

    Written as JSON per step. This is your M3 preview — good structured logs
    now mean easy OTEL span mapping later.
    """
    step:int
    llm_text:str|None
    tool_calls:list[ToolCall]
    tool_results:list[ToolResult]
    duration_ms:int
    
@dataclass
class AgentState:
    """Everything a single agent run carries."""
    goal:str
    messages:list[Message]=field(default_factory=list)
    step:int=0
    max_steps:int=0
    completed:bool=False
    final_answer:str|None=None
    step_logs:list[StepLog]=field(default_factory=list)
    
    def append(self, message:Message)->None:
        self.messages.append(message)
        
    def is_budget_exhausted(self)->bool:
        return self.step>=self.max_steps