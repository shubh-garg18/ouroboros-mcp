from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

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
    
class ToolRegistry:
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
