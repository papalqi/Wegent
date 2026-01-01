---
description: "Automate website functional checks by simulating user actions via an embedded MCP HTTP driver (open URL, click links, submit forms, assert status/text). Use for smoke/regression checks after deploys or before releases."
displayName: "Web UI Validator (HTTP/MCP)"
version: "0.1.0"
author: "Wegent Team"
tags: ["web", "qa", "smoke", "regression", "mcp", "http"]
bindShells: ["ClaudeCode", "Codex"]
---

# Web UI Validator (HTTP/MCP)

This skill provides a **deterministic** way to validate website flows using an embedded **stdio MCP server**.

It simulates "click" by **following links** and "type" by **submitting forms** (HTTP-level). It does **not** execute JavaScript, so it is best for:
- server-rendered pages
- auth pages that post forms
- link navigation
- basic availability / regression checks

If you need full JS SPA validation, use a real browser-based MCP server (Playwright) and keep the same step spec.

## Quick start

Run with a JSON spec file:

```bash
python3 ~/.claude/skills/web_ui_validator/web_ui_validator.py --spec ./example_spec.json
```

For Codex shell deployments, the skills folder is `~/.codex/skills/`:

```bash
python3 ~/.codex/skills/web_ui_validator/web_ui_validator.py --spec ./example_spec.json
```

Or run with a single URL + expected text:

```bash
python3 ~/.claude/skills/web_ui_validator/web_ui_validator.py \
  --url "https://example.com" \
  --assert-contains "Example Domain"
```

## Run from Wegent UI

1. Add `web_ui_validator` to `Ghost.spec.skills[]`.
2. Use a `Bot` with `ShellType=ClaudeCode` (or `Codex` when enabled).
3. Send a message that starts with:

```
@web_ui_validator --url "https://example.com" --assert-contains "Example Domain"
```

## Spec format (JSON)

```json
{
  "base_url": "https://example.com",
  "steps": [
    {"action": "open", "url": "/"},
    {"action": "assert_status", "status": 200},
    {"action": "assert_contains", "text": "Example Domain"}
  ]
}
```

Supported actions:
- `open`: `{ "url": "https://..." | "/path" }`
- `click_link`: `{ "text_contains": "Login" }` or `{ "href_contains": "/login" }`
- `submit_form`: `{ "action_contains": "/login", "method": "post", "fields": {"username":"u","password":"p"} }`
- `assert_status`: `{ "status": 200 }`
- `assert_contains`: `{ "text": "..." }` or `{ "regex": "..." }`
- `save_body`: `{ "path": "last_response.html" }`

## Output

The validator prints step-by-step logs and exits non-zero on failure.

