# 🧩 Codex Shell Guide

This guide explains how to use Wegent's **Codex Shell** (OpenAI-based coding runtime), including configuration, base image requirements, troubleshooting, and safe rollout/rollback.

---

## ✅ When to use Codex

Use Codex when you want a **code-oriented workflow with OpenAI models**, similar to the ClaudeCode coding experience in Wegent.

Key capabilities:

- Streaming output (`chat:chunk`) is supported
- Attachments are downloaded into the workspace (same as ClaudeCode)
- Skills are supported and deployed to `~/.codex/skills`
- MCP servers are supported (same MCP config schema as ClaudeCode)

---

## 🐳 Base image requirements

If you use the built-in public `Codex` Shell, Wegent provides a default image.

If you create a **custom shell image** based on Codex, your base image should include:

- Node.js **>= 20**
- `codex` CLI (Wegent base images pin `@openai/codex@0.77.0`)
- Python **>= 3.12**

You can validate a custom image in the UI:

Settings → Shell Management → Create/Edit Shell → **Validate**

---

## 🤖 Configure a Bot for Codex

### Option A: Use a predefined Model (recommended)

1) Create a `Model` (OpenAI protocol) in Settings → Models
2) Create a `Bot` and select Shell = `Codex`
3) Bind the model via Model selection

### Option B: Use a custom Model config

Codex reads OpenAI settings from `agent_config.env`:

- `api_key` → `OPENAI_API_KEY`
- `base_url` → `OPENAI_BASE_URL` (optional)
- `model_id` / `model` → `codex --model` (optional)

Example:

```yaml
apiVersion: agent.wecode.io/v1
kind: Bot
metadata:
  name: my-codex-bot
  namespace: default
spec:
  ghostRef:
    name: my-ghost
    namespace: default
  shellRef:
    name: Codex
    namespace: default
  modelRef:
    name: my-openai-model
    namespace: default
```

---

## 🧪 Smoke test (recommended)

Wegent includes a public skill `shell_smoke` for deterministic end-to-end verification **without requiring real LLM output**.

1) Add skill `shell_smoke` to your Ghost
2) Use a Codex Bot
3) Send:

```
@shell_smoke
```

Expected:

- Streaming output appears incrementally
- `shell_smoke_result.txt` is created in the task working directory

---

## ⚠️ Known limitations

- The `shell_smoke` skill validates the end-to-end execution and streaming path, but it does not validate real LLM quality/output.
- For the detailed capability scope (what is supported / out of scope), refer to the parity matrix.

---

## 🛠 Troubleshooting

### `codex: command not found`

- Your shell base image is missing the Codex CLI
- Fix by building from Wegent base images or installing `@openai/codex`
- Re-run image validation in Shell Management

### Skills are not available

- Ensure the backend is reachable from executor containers (`TASK_API_DOMAIN`)
- Ensure the task payload includes `auth_token` (Wegent generates this automatically)

---

## 🚦 Rollout / rollback

Backend supports a feature flag:

- `CODEX_SHELL_ENABLED=true` (default): Codex is available
- `CODEX_SHELL_ENABLED=false`: Codex is hidden from unified shell listing and Codex task dispatch is blocked

### Rollback steps

1) Set `CODEX_SHELL_ENABLED=false` in backend environment
2) Restart backend
3) (Optional) Restart frontend to refresh shell lists

No other shells (Chat / ClaudeCode / Agno / Dify) are affected.

---

## 🔗 References

- [Codex Shell Parity Matrix](../developer/codex-shell-parity.md)
- [Codex Shell Runtime Decision](../developer/codex-shell-runtime.md)
