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
