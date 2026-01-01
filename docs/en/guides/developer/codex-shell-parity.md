# Codex Shell Parity Matrix (vs ClaudeCode)

This document is the scope contract for implementing the **Codex Shell** in Wegent.

## What “1:1 parity” means

- **Parity target**: the existing **Wegent ClaudeCode Shell behavior** (not the full Claude Code product).
- **In-scope = in this matrix**: if it is not listed here, it is out of scope until this doc and the issues CSV are updated.
- **Any scope change** must update:
  1) this document, and 2) the current issues CSV snapshot used as the single source of truth.

## Capability matrix

| Capability | ClaudeCode behavior (refs) | Codex target | Verification |
|---|---|---|---|
| Shell type registration | `Shell.spec.shellType=ClaudeCode` exists in init data. | Add `Shell.spec.shellType=Codex` and keep backward compatibility. | Backend starts and lists Codex shell; wizard can select Codex. |
| Executor agent selection | Executor selects agent by `bot[0].shell_type` via `AgentFactory`. | Add `CodexAgent` and register in `AgentFactory`. | Unit test: factory returns CodexAgent for `shell_type=Codex`. |
| Repo checkout & workspace root | `download_code()` clones repo; agent sets `cwd` for execution. | Same behavior (clone + stable `cwd`). | Manual: dispatch a repo task; workspace contains cloned repo and agent runs inside it. |
| Custom instructions | Load `CUSTOM_INSTRUCTION_FILES`, create `.claudecode/`, symlink `CLAUDE.md`, update `.git/info/exclude`. | Same load rules; Codex must see the same instruction content (directory/symlink is optional if Codex doesn’t consume it directly). | Manual: after pre-exec, `.claudecode/` exists and `CLAUDE.md` points to `AGENTS.md` (if present). |
| Attachments | Attachments are downloaded into workspace and prompt references are rewritten to local paths. | Same behavior. | Manual: upload attachment and confirm file exists in workspace; prompt includes local path context. |
| Skills | ClaudeCode deploys skills under `~/.claude/skills` from Backend API. | Codex must support Wegent skills either by: (a) deploying to a Codex-supported location, or (b) injecting skill prompts/tools via Wegent integration. | Manual: a task with configured skills can invoke them; no silent failures. |
| MCP servers | ClaudeCode extracts MCP config, performs variable replacement, and passes to runtime. | Same behavior (including variable substitution rules). | Manual: configure an MCP server with `${{user.name}}` and verify runtime receives substituted config. |
| Git CLI auth & proxy | Set git env vars; authenticate `gh`/`glab`; optional proxy config via `REPO_PROXY_CONFIG`. | Same behavior. | Manual: authenticated operations succeed when token is present; proxy config applied to git config. |
| Streaming + workbench/thinking | Executor sends `RUNNING` callbacks with `result.value` + `thinking` + `workbench`, and backend emits `chat:chunk` incrementally. | Same event semantics: Codex must update `result.value` incrementally to enable streaming. | E2E: send message → see streaming chunks → done; refresh keeps final content. |
| Cancellation | ClaudeCode supports cancellation and cleans up client/process. | Codex supports cancellation (stop subprocess, mark cancelled, cleanup resources). | Manual: cancel while running, ensure no further chunks and final status is CANCELLED/COMPLETED per contract. |
| Observability & safety | Sensitive data masking; logs and spans for major phases. | Same behavior. | Code review: no secrets in logs/results; key phases logged/spanned. |
| Image validation | Executor Manager validates images for supported shells. | Codex is accepted by `/executor-manager/images/validate` and has dependency checks. | API: validate Codex image returns checks + final valid flag. |

## Scope notes / explicit non-goals

- “1:1 parity” does **not** mean reproducing every feature of the upstream Codex/Claude Code products; it means matching **Wegent’s ClaudeCode Shell contract**.
- If Codex runtime cannot provide a ClaudeCode-equivalent feature, the deviation must be documented here before merging (with a clear mitigation).

## Sign-off

This document is considered **approved for implementation** when merged together with the issues CSV snapshot used for execution.

## References

- `backend/init_data/02-public-shells.yaml:10`
- `executor/agents/factory.py:31`
- `executor/agents/base.py:276`
- `executor/agents/claude_code/claude_code_agent.py:633`
- `executor/agents/claude_code/claude_code_agent.py:1169`
- `executor/agents/claude_code/claude_code_agent.py:1300`
- `backend/app/services/adapters/executor_kinds.py:1054`
- `executor_manager/routers/routers.py:446`
- `plan/2026-01-01_14-03-09-codex-shell-claude-code.md:18`

