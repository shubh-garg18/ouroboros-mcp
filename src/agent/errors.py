"""Typed errors for the agent runtime.

Rule of thumb: if the LLM should see and react to it, it becomes a
ToolResult with is_error=True. If the run itself can't continue, raise.
"""


class AgentError(Exception):
    """Base class. Catch this to catch anything from the agent module."""


class BudgetExhaustedError(AgentError):
    """Agent hit max_steps without producing a final answer."""


class LoopDetectedError(AgentError):
    """Same tool+args called 3+ times in a row. Likely infinite loop."""


class MalformedResponseError(AgentError):
    """LLM returned something we couldn't parse. Retry-able."""


class ToolNotFoundError(AgentError):
    """LLM asked for a tool that isn't registered. Becomes a ToolResult error."""