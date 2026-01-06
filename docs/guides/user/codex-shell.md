# 🧩 Codex Shell 使用指南

本指南介绍 Wegent 的 **Codex Shell**（基于 OpenAI 的编码运行时）：如何配置、基础镜像要求、排错，以及如何安全灰度/回滚。

---

## ✅ 什么时候使用 Codex

当你希望使用 **OpenAI 模型**进行代码类工作流（体验接近 Wegent 中的 ClaudeCode 编码模式）时，选择 Codex。

关键能力：

- 支持流式输出（`chat:chunk`）
- 附件会下载到工作区（与 ClaudeCode 一致）
- 支持 Skills，并部署到 `~/.codex/skills`
- 支持 MCP Servers（与 ClaudeCode 使用相同的 MCP 配置 schema）

---

## 🐳 基础镜像要求

如果你直接使用系统内置的公共 `Codex` Shell，Wegent 会提供默认镜像。

如果你要基于 Codex 构建 **自定义 Shell 镜像**，基础镜像建议包含：

- Node.js **>= 20**
- `codex` CLI（Wegent 的基础镜像固定版本：`@openai/codex@0.77.0`）
- Python **>= 3.12**

你可以在 UI 中验证自定义镜像：

设置 → Shell 管理 → 创建/编辑 Shell → **Validate**

---

## 🤖 为 Codex 配置 Bot

### 方式 A：使用预设 Model（推荐）

1) 在设置 → Models 中创建一个 `Model`（OpenAI 协议）
2) 创建一个 `Bot`，Shell 选择 `Codex`
3) 通过 Model 选择绑定该 Model

### 方式 B：使用自定义 Model 配置

Codex 会从 `agent_config.env` 读取 OpenAI 配置：

- `api_key` → `OPENAI_API_KEY`
- `base_url` → `OPENAI_BASE_URL`（可选）
- `model_id` / `model` → `codex --model`（可选）

示例：

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

## 🧪 Smoke 测试（推荐）

Wegent 内置了一个公共 skill `shell_smoke`，可用于确定性端到端验证，**无需依赖真实 LLM 输出**。

1) 在你的 Ghost 中添加 skill `shell_smoke`
2) 使用一个 Codex Bot
3) 发送：

```
@shell_smoke
```

期望结果：

- 流式输出会逐步出现
- 任务工作目录下会生成 `shell_smoke_result.txt`

---

## ⚠️ 已知限制

- `shell_smoke` 主要用于验证端到端执行与流式链路，但不会验证真实 LLM 的输出质量。
- 详细能力范围（支持/不支持）以对齐矩阵为准。

---

## 🛠 故障排查

### `codex: command not found`

- 你的 Shell 基础镜像缺少 Codex CLI
- 解决方式：基于 Wegent 的基础镜像构建，或安装 `@openai/codex`
- 在 Shell 管理中重新执行镜像验证

### Skills 不可用

- 确认 executor 容器能访问 backend（`TASK_API_DOMAIN`）
- 确认任务 payload 中包含 `auth_token`（Wegent 会自动生成）

---

## 🚦 灰度 / 回滚

Backend 支持一个 feature flag：

- `CODEX_SHELL_ENABLED=true`（默认）：Codex 可用
- `CODEX_SHELL_ENABLED=false`：Codex 会从统一 Shell 列表中隐藏，并阻止 Codex 任务下发

### 回滚步骤

1) 在 backend 环境变量中设置 `CODEX_SHELL_ENABLED=false`
2) 重启 backend
3) （可选）重启 frontend 以刷新 Shell 列表

不会影响其它 Shell（Chat / ClaudeCode / Agno / Dify）。

---

## 🔗 参考

- [Codex Shell 对齐矩阵](../developer/codex-shell-parity.md)
- [Codex Shell 运行时决策](../developer/codex-shell-runtime.md)
