# Codex Shell Runtime Decision (PoC)

This document records the runtime choice for Wegent’s **Codex Shell** and a reproducible container PoC command.

## Decision

- **Runtime**: `@openai/codex` (CLI)
- **Pinned version (initial)**: `0.77.0`
- **Execution mode**: `codex exec --json` (JSONL events) + `--dangerously-bypass-approvals-and-sandbox`

### Rationale

- Provides a stable **non-interactive** mode (`exec`) suitable for server-side execution.
- Supports **event streaming as JSONL** (`--json`) which can be mapped into Wegent `result.value` streaming.
- Internal sandboxing may fail on some kernels (Landlock); bypass flag ensures predictable execution inside Wegent’s container sandbox.

## Required configuration

### Authentication

Preferred (stateless, container-friendly):

- `OPENAI_API_KEY` (required)
- `OPENAI_BASE_URL` (optional)

Codex can also use persisted config under the home directory:

- `~/.codex/config.toml`
- `~/.codex/auth.json`

For Wegent executor containers, prefer environment variables instead of persisting auth on disk.

## Container PoC

### 1) Missing credentials (deterministic failure)

This should reliably return **401 Unauthorized** and emit JSON `error` events:

```bash
docker run --rm \
  -v "$PWD":/workspace -w /workspace \
  ghcr.io/wecode-ai/wegent-base-python3.12:1.0.1 \
  bash -lc "npx -y @openai/codex@0.77.0 exec --json --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -C /workspace 'Say hi'"
```

### 2) With credentials (expected success)

```bash
docker run --rm \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -v "$PWD":/workspace -w /workspace \
  ghcr.io/wecode-ai/wegent-base-python3.12:1.0.1 \
  bash -lc "npx -y @openai/codex@0.77.0 exec --json --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -C /workspace 'Say hi'"
```

## References

- `plan/2026-01-01_14-03-09-codex-shell-claude-code.md:19`
- `docker/base/Dockerfile:15`
