# Codex Shell 运行时决策（PoC）

本文档记录 Wegent **Codex Shell** 的运行时选型与可复现的容器 PoC 命令。

## 决策

- **运行时**：`@openai/codex`（CLI）
- **初始版本锁定**：`0.77.0`
- **执行模式**：`codex exec --json`（JSONL 事件流）+ `--dangerously-bypass-approvals-and-sandbox`

### 选型原因

- 提供适合服务端的 **非交互** 执行模式（`exec`）。
- 支持 **JSONL 事件流输出**（`--json`），便于映射为 Wegent 的 `result.value` 流式回调。
- 在部分内核环境下 Codex 的内部沙箱（Landlock）可能不可用；在 Wegent 的容器沙箱中使用 bypass 参数更稳定可控。

## 必要配置

### 鉴权

推荐方式（容器友好、无状态）：

- `OPENAI_API_KEY`（必需）
- `OPENAI_BASE_URL`（可选）

Codex 也支持将配置持久化在 home 目录：

- `~/.codex/config.toml`
- `~/.codex/auth.json`

在 Wegent executor 容器中建议优先使用环境变量，而不是把鉴权信息落盘到镜像或容器层。

## 容器 PoC

### 1) 缺少凭证（可预期的失败）

该命令应稳定返回 **401 Unauthorized**，并输出 JSON `error` 事件：

```bash
docker run --rm \
  -v "$PWD":/workspace -w /workspace \
  ghcr.io/wecode-ai/wegent-base-python3.12:1.0.1 \
  bash -lc "npx -y @openai/codex@0.77.0 exec --json --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -C /workspace 'Say hi'"
```

### 2) 提供凭证（预期成功）

```bash
docker run --rm \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -v "$PWD":/workspace -w /workspace \
  ghcr.io/wecode-ai/wegent-base-python3.12:1.0.1 \
  bash -lc "npx -y @openai/codex@0.77.0 exec --json --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -C /workspace 'Say hi'"
```

## 参考

- `plan/2026-01-01_14-03-09-codex-shell-claude-code.md:19`
- `docker/base/Dockerfile:15`
