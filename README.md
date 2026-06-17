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
├── ouroboros/              # reusable runtime (core) — knows nothing about code-fixing
│   ├── cli.py              # single-agent demo entry point
│   ├── agent/
│   │   ├── loop.py         # Core agent loop (run_agent)
│   │   ├── state.py        # AgentState, Message, ToolCall, ToolResult, StepLog
│   │   ├── errors.py       # LoopDetectedError, BudgetExhaustedError, ...
│   │   └── prompts.py      # System prompt
│   ├── llm/
│   │   ├── provider.py     # Abstract LLMProvider + LLMResponse
│   │   └── gemini.py       # Gemini implementation
│   └── tools/
│       ├── schema.py       # Tool, ToolRegistry, ToolSource (Protocol), ScopedTools
│       └── local/
│           ├── calculator.py   # Safe AST-based arithmetic
│           └── file_ops.py     # Sandboxed file reader (workspace/ only)
└── code_fixer/             # Ouroboros application (composes core into roles)
    ├── roles.py            # Role + run_role: one bounded, scoped, prompted agent call
    ├── process.py          # run_command + CommandResult (fail-closed subprocess helper)
    ├── sandbox.py          # Sandbox: clone a target repo into an isolated dir
    └── toolchain/
        ├── base.py         # Toolchain ABC + Issue / Severity / CheckResult
        └── python.py       # PythonToolchain: ruff/mypy/bandit + pytest

scripts/
├── test_loop_detection.py  # LoopDetectedError fires after 3 identical calls
├── test_path_traversal.py  # sandbox blocks path traversal
├── test_tool_scoping.py    # ScopedTools hides out-of-scope tools
├── test_role_harness.py    # a role is offered only its own tools
└── test_toolchain.py       # parsers, clone, pytest pass/fail, fail-closed check

docs/
└── design_choices.md       # Why the code is structured the way it is

workspace/                  # Agent's sandboxed file I/O directory
```

Layers depend only on what's below them: `state → tools → llm → loop → cli`. The application (`code_fixer`) depends on the core one-way; the core never imports from it.

---

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install google-genai python-dotenv
pip install -e .                          # installs ouroboros + code_fixer from src/
echo "GEMINI_API_KEY=your_key_here" > .env
```

Get a key at [aistudio.google.com](https://aistudio.google.com). The default model is `gemini-2.5-flash`.

---

## Run

```bash
# Run from the repo root. Any goal:
python -m ouroboros.cli "what is 17 * 23"

# Multi-step: reads file then reasons over content
echo "hello world" > workspace/hello.txt
python -m ouroboros.cli "Read hello.txt and count its characters"
```

Each step prints a one-liner: `[step N] tools=[...] errors=N took=Nms`.

---

## Safety tests

Behavioral checks that verify the loop and its guardrails actually work — not unit tests.

```bash
# Multi-step chain (requires a live API call):
python -m ouroboros.cli "Read the file hello.txt from the workspace and tell me how many characters it contains."

# Sandbox — path traversal blocked, error returned as observation
python scripts/test_path_traversal.py

# Loop detection — LoopDetectedError after 3 identical tool calls
python scripts/test_loop_detection.py

# Scoping — a role sees only its own tools; out-of-scope calls return is_error
python scripts/test_tool_scoping.py
python scripts/test_role_harness.py

# Toolchain — parsers, clone, pytest pass/fail, fail-closed check
python scripts/test_toolchain.py
```

---

## Safety nets

| Mechanism | Where | What it does |
| --- | --- | --- |
| Workspace sandbox | `ouroboros/tools/local/file_ops.py` | Blocks reads outside `workspace/` |
| Loop detection | `ouroboros/agent/loop.py:_check_loop` | Raises `LoopDetectedError` after 3 identical `(tool, args)` calls |
| Step budget | `AgentState.max_steps` | Raises `BudgetExhaustedError` at 10 steps |

See [`docs/design_choices.md`](docs/design_choices.md) for the reasoning behind each decision.
