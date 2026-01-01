---
description: "End-to-end smoke test for Wegent code shells (ClaudeCode/Codex). Streams deterministic output to verify the full executor pipeline."
displayName: "Shell Smoke"
version: "0.1.0"
author: "Wegent Team"
tags: ["smoke", "e2e", "shell", "executor", "mcp"]
bindShells: ["ClaudeCode", "Codex"]
---

# Shell Smoke Skill

This skill validates the full Shell execution pipeline:

Frontend → Backend → Executor Manager → Executor → WebSocket streaming → Frontend UI.

It also includes a minimal **stdio MCP server** to simulate "click/type" interactions.

## How to use

1. Add `shell_smoke` to a `Ghost.spec.skills[]`.
2. Use a `Bot` with `ShellType=ClaudeCode` (or `Codex` when available).
3. In the frontend (Chat or Code page), send a message containing:

```
@shell_smoke
```

## Expected result

- The assistant streams multiple lines progressively.
- The executor creates `shell_smoke_result.txt` in its working directory.
- The output contains MCP simulation lines (e.g. `[mcp] clicked ...`, `[mcp] typed ...`).

