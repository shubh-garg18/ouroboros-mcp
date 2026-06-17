# Design Decisions

## Agent Implementation

### 1. Layering (Bottom-Up)

Build in this order:
`state → tools → llm/provider → loop → cli`

Each layer depends only on previous ones.

---

### 2. ToolCall vs ToolResult

Keep them separate.

- `ToolCall`: from LLM  
- `ToolResult`: from system  

Do not merge into a single type.  
Fields like `is_error` belong only to results.

---

### 3. No Exceptions in Tools

Return errors, don’t raise them.

- Use: `is_error: true`
- Include failure as text for the LLM

Exceptions break the loop.  
Returning errors enables recovery → this is what makes it an agent.

---

### 4. Step Logging (Required)

Add `StepLog` from the start.

- Debugging = reading logs
- Retrofitting logs later is painful

---

### 5. Limit Steps

Default: `max_steps = 10`

- Most tasks: 3–5 steps
- Frequent limit hits = bad prompts or tools

Treat it as a signal, not a bug.

---

### 6. Invoke() in Tools Schema

This function does NOT handle errors.
Because:

- Tool shouldn’t decide error semantics
- Agent loop controls error handling

---

### 7. Role Mapping to Gemini (`user` / `model`)

Gemini supports only two roles. We map:

- `USER → user`
- `ASSISTANT → model`
- `TOOL → user` (via `function_response`)

Tool results are injected as **user messages** so the model treats them as new input, not prior reasoning.

---

### 8. Synthetic Tool Call IDs

Gemini does not return tool call IDs. We generate:
    `{tool_name}:{uuid}`
    and recover the tool name via:
    `tool_call_id.split(":", 1)[0]`

This avoids maintaining a separate mapping.

---

### 9. Single Candidate Only

Only `response.candidates[0]` is used.

Avoids complexity of ranking or multi-path execution in the agent loop.

---

## Application (Ouroboros)

### 10. Core / App Split (One-Way Dependency)

`ouroboros` (runtime) and `code_fixer` (application) are separate packages.

- `code_fixer` imports from `ouroboros`. Never the reverse.
- The runtime stays reusable: it knows nothing about code-fixing.

A boundary is only load-bearing if it's enforced — so the rule is stated, not assumed.

---

### 11. Registry Scoping (a View, Not a Copy)

Each role is handed `ScopedTools(parent, allowed)`, not the full registry.

- The loop depends on a narrow `ToolSource` Protocol (`all_tools` + `get`).
- `ScopedTools` filters a parent source; no tools are copied — parent stays the single source of truth.
- Out-of-scope `get()` returns `None` → reuses the loop's unknown-tool path → `is_error` observation. No new enforcement code.
- `allowed` is copied on construction so a caller can't widen scope afterward.

---

### 12. Toolchain Adapter (the Language Boundary)

Everything language-specific hides behind one `Toolchain` ABC: `discover` / `check` / `test`.

- Orchestrator and agents speak only `Issue` / `CheckResult` / `CommandResult` — never "ruff" or "pytest".
- Swap language = swap adapter. The agents don't change.
- `Severity` is an `IntEnum` so ranking is just sorting.

---

### 13. Fail-Closed Execution

`CommandResult.ok = found and not timed_out and exit_code == 0`.

- Missing tool and timeout both read as not-ok. No exceptions for a non-zero exit — the result is data; the caller decides meaning.
- `discover()` is best-effort (a missing analyzer contributes nothing).
- `check()` / `test()` are the gate: `CheckResult` with no runs, or any failed run, is not ok. "Ran nothing" must never read as "passed".

---

### 14. No Stale Bytecode at the Verify Boundary

`PythonToolchain` runs every tool with `PYTHONDONTWRITEBYTECODE=1`.

A one-character, same-size edit in the same wall-clock second can collide with CPython's
timestamp+size `.pyc` cache, so old compiled code runs and a broken test "passes" — the
wrong-PR failure mode. Not writing bytecode forces a recompile from current source every run.
