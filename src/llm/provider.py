"""Provider-agnostic LLM interface.

A provider takes messages + available tools and returns an assistant turn
— which may contain text, tool calls, or both. The agent loop does not
depend on which provider is behind this.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from agent.state import Message, ToolCall
from tools.schema import Tool

@dataclass
class LLMResponse:
    text: str | None           # free-text output, often None when tools are called
    tool_calls: list[ToolCall] # empty list = no tools requested
    stop_reason: str           # provider-reported reason ("end_turn", "tool_use", "max_tokens"...)
    
class LLMProvider(ABC):
    @abstractmethod
    def complete(
        self,
        system_prompt,
        messages: list[Message],
        tools: list[Tool],
    )->LLMResponse:
        """Send the conversation + tool definitions, get the next turn."""