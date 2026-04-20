# Agentic AI

A minimal agent loop in Python. The LLM calls tools, observes results, and repeats until it has a final answer.

---

## How it works

```text
goal → LLM → tool call → result (observation) → LLM → ... → final answer
```

Errors from tools are returned as observations (`is_error: true`), not raised as exceptions. The LLM decides whether to retry, pivot, or give up — that's what makes it an agent.

---

## Structure

```text
src/
├── cli.py                  # Entry point
├── agent/
│   ├── loop.py             # Core agent loop (run_agent)
│   ├── state.py            # AgentState, Message, ToolCall, ToolResult, StepLog
│   ├── errors.py           # LoopDetectedError, BudgetExhaustedError, ...
│   └── prompts.py          # System prompt
├── llm/
│   ├── provider.py         # Abstract LLMProvider + LLMResponse
│   └── gemini.py           # Gemini implementation
└── tools/
    ├── schema.py           # Tool, ToolRegistry
    └── local/
        ├── calculator.py   # Safe AST-based arithmetic
        └── file_ops.py     # Sandboxed file reader (workspace/ only)

scripts/
├── test_loop_detection.py  # Trust test 3: LoopDetectedError fires after 3 identical calls
└── test_path_traversal.py  # Trust test 2: sandbox blocks path traversal

docs/
└── design_choices.md       # Why the code is structured the way it is

workspace/                  # Agent's sandboxed file I/O directory
```

Layers depend only on what's below them: `state → tools → llm → loop → cli`.

---

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install google-genai python-dotenv
echo "GEMINI_API_KEY=your_key_here" > .env
```

Get a key at [aistudio.google.com](https://aistudio.google.com). The default model is `gemini-2.5-flash`.

---

## Run

```bash
# Any goal
python cli.py "what is 17 * 23"

# Multi-step: reads file then reasons over content
echo "hello world" > workspace/hello.txt
python cli.py "Read hello.txt and count its characters"
```

Each step prints a one-liner: `[step N] tools=[...] errors=N took=Nms`.

---

## Safety tests

Three trust tests that verify the loop actually works — not unit tests, but behavioral checks.

```bash
# Test 1 (multi-step chain) requires a live API call:
python cli.py "Read the file hello.txt from the workspace and tell me how many characters it contains."

# Test 2 — path traversal blocked + error returned as observation
python scripts/test_path_traversal.py

# Test 3 — LoopDetectedError raised after 3 identical tool calls
python scripts/test_loop_detection.py
```

---

## Safety nets

| Mechanism | Where | What it does |
| --- | --- | --- |
| Workspace sandbox | `tools/local/file_ops.py` | Blocks reads outside `workspace/` |
| Loop detection | `agent/loop.py:_check_loop` | Raises `LoopDetectedError` after 3 identical `(tool, args)` calls |
| Step budget | `AgentState.max_steps` | Raises `BudgetExhaustedError` at 10 steps |

See [`docs/design_choices.md`](docs/design_choices.md) for the reasoning behind each decision.
