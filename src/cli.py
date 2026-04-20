"""Command-line entry point.

Usage: python -m cli "what is 17 * 23"
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from agent.loop import run_agent
from llm.gemini import GeminiProvider
from tools.local.calculator import calculator_tool
from tools.local.file_ops import read_file_tool
from tools.schema import ToolRegistry


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m cli '<goal>'", file=sys.stderr)
        return 2

    goal = " ".join(sys.argv[1:])

    registry = ToolRegistry()
    registry.register(calculator_tool)
    registry.register(read_file_tool)

    llm = GeminiProvider()
    state = run_agent(goal=goal, llm=llm, registry=registry)

    print("\n--- final answer ---")
    print(state.final_answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())