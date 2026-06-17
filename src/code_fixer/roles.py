"""The role harness: a Role is one bounded, scoped, prompted agent call.

This is the "compose core into roles" seam. The Orchestrator (plain code)
dispatches one `run_agent` per role — each with its own system prompt, its own
step budget, and a ScopedTools view exposing only that role's tools. `run_agent`
is therefore a subroutine the Orchestrator calls per role, not the top-level
driver.

This module is generic: it knows nothing about Analyzer/Fixer/Critic. The actual
role definitions (their prompts and tool sets) live where the Orchestrator is
built, not here.
"""
from __future__ import annotations

from dataclasses import dataclass

from ouroboros.agent.loop import run_agent
from ouroboros.agent.state import AgentState
from ouroboros.llm.provider import LLMProvider
from ouroboros.tools.schema import ScopedTools, ToolSource


@dataclass(frozen=True)
class Role:
    """A bounded agent persona: a prompt, the tool names it may use, a step budget.

    Frozen so a role definition is an immutable value the Orchestrator can reuse
    across issues without fear of mutation; `tools` is a tuple for the same reason.
    """

    name: str
    system_prompt: str
    tools: tuple[str, ...]
    max_steps: int = 10


def run_role(
    role: Role,
    goal: str,
    llm: LLMProvider,
    registry: ToolSource,
) -> AgentState:
    """Run one role as a single bounded agent call over a scoped slice of `registry`.

    The role only ever sees and can dispatch the tools named in `role.tools`;
    everything else in the registry is invisible to it (and an attempted call
    returns an is_error observation, via ScopedTools + the loop's unknown-tool path).
    """
    scoped = ScopedTools(registry, role.tools)
    return run_agent(
        goal=goal,
        llm=llm,
        registry=scoped,
        system_prompt=role.system_prompt,
        max_steps=role.max_steps,
    )
