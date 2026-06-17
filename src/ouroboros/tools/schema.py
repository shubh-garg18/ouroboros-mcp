from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Callable, Protocol

@dataclass
class Tool:
    name:str
    description:str
    parameters_schema:dict[str, Any]
    handler:Callable[..., str] 
    
    def invoke(self, arguments:dict[str, Any])->str:
        """Run the tool. Any exception is the CALLER's problem to convert
        to a ToolResult with is_error=True — we deliberately don't swallow.
        """
        return self.handler(**arguments)
    
class ToolSource(Protocol):
    """The slice of registry behaviour the agent loop depends on.

    run_agent only ever asks a source for two things: the tools to advertise to
    the model (all_tools) and the tool to dispatch by name (get). Anything that
    answers these two is a drop-in — a full ToolRegistry, or a ScopedTools view
    of one — so the loop can stay ignorant of scoping entirely.
    """

    def all_tools(self) -> list[Tool]: ...
    def get(self, name: str) -> Tool | None: ...


class ToolRegistry(ToolSource):
    """Holds all known tools. The agent loop dispatches through this."""
    def __init__(self)->None:
        self._tools:dict[str,Tool]={}
        
    def register(self, tool:Tool)->None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name]=tool
        
    def get(self, name:str)->Tool|None:
        return self._tools.get(name)
    
    def all_tools(self)->list[Tool]:
        return list(self._tools.values())


class ScopedTools(ToolSource):
    """A read-only view over a parent source, restricted to a set of names.

    A role is handed one of these instead of the full registry: it sees and can
    call only its allowed tools, while the parent stays the single source of
    truth (no tools are copied). An out-of-scope get() returns None, which the
    loop already treats as an unknown tool → ToolResult(is_error=True), so
    enforcement reuses the existing error-as-observation path for free.
    """

    def __init__(self, parent: ToolSource, allowed: Iterable[str]) -> None:
        self._parent = parent
        self._allowed = set(allowed)  # copy: caller can't widen the scope after construction

    def all_tools(self) -> list[Tool]:
        return [t for t in self._parent.all_tools() if t.name in self._allowed]

    def get(self, name: str) -> Tool | None:
        return self._parent.get(name) if name in self._allowed else None
