---
mode: plan
cwd: /root/project/Wegent
task: Build a Codex Shell with ClaudeCode parity (1:1 inside Wegent)
complexity: complex
planning_method: builtin
created_at: 2026-01-01T14:03:09+08:00
---

# Plan: Codex Shell (ClaudeCode Parity)

🎯 任务概述

在 Wegent 现有「Shell/Agent」体系内新增一个本地执行引擎 `Codex`（目标体验对齐 `ClaudeCode`：一比一复刻 Wegent 里 ClaudeCode Shell 的能力与交互）。若现有 Docker 镜像/基础镜像缺失 Codex 运行时，需要补齐镜像构建与发布配置，并在前后端、executor、executor_manager 全链路打通。

📋 执行计划

1. **需求澄清与验收矩阵（Parity Matrix）**：梳理 Wegent 当前 `ClaudeCode` Shell 在「会话/流式输出/工具调用/仓库操作/技能/附件/MCP/取消/日志与遥测/权限模式」等能力清单，产出 `Codex` 的一比一对齐表与验收用例。
2. **Codex 运行时选型与 PoC**：确定目标是“Codex CLI（推荐）”还是“Codex SDK/Agent API”；在容器内做最小 PoC（非交互模式、流式输出捕获、工作目录读写、退出码与错误信息），明确所需环境变量/配置文件位置与版本固定策略。
3. **Docker 镜像补齐**：基于 `wegent-base-python3.12` 增加 Codex 依赖（可能包含 Node/npm 或 Python 包），新增/调整 Dockerfile 与 build 脚本，保证 `amd64/arm64` 可构建，并把镜像验证逻辑接入 `ImageValidator`。
4. **Executor 新增 CodexAgent（复用/抽象公共逻辑）**：在 `executor/agents/` 下实现 `codex/` 模块；优先抽取 `ClaudeCodeAgent` 与新 Agent 共享的能力（git 环境变量、hooks、skills 下载部署、MCP 变量替换、进度/ThinkingStep 上报、敏感信息脱敏、任务取消与资源清理），避免复制粘贴。
5. **交互与协议对齐**：实现与现有 WebSocket/回调协议一致的事件与状态更新（start/chunk/done、progress、error）；确保 `Codex` 产出的消息与 `useUnifiedMessages` 数据流兼容（尤其是流式 chunk 合并与 completed 状态）。
6. **Backend 扩展 ShellType=Codex**：更新 Pydantic schema、wizard 推荐逻辑、模型聚合/校验逻辑（如需要）；补充 `init_data` 的公共 Shell 配置（`kind: Shell`，`shellType: Codex`，`baseImage` 指向新镜像或可复用镜像）。
7. **Executor Manager 支持与镜像校验**：在 `/images/validate` 放行 `Codex`，并在 `ImageValidatorAgent` 增加 Codex 的依赖检查项（Node/Python/CLI 版本、必要二进制、配置目录权限等）；确保调度/并发/取消对 Codex 生效。
8. **Frontend 接入与 UI 限制**：更新 TypeScript `AgentType`/表单校验/文案（i18n），把 Codex 作为可选 Shell；按能力开关显示（例如：是否支持 Skills、附件上传、MCP 类型映射等），避免出现“选了 Codex 但 UI 仍按 ClaudeCode 特判”的逻辑漏洞。
9. **测试与回归**：为 executor、backend、executor_manager、frontend 分别补充最小但关键的单测/集成测试；新增一条端到端回归用例（创建 Bot/Team→创建 Task→流式输出→产物落盘→状态完成）。
10. **文档与发布/回滚**：在 `docs/en/` 与 `docs/zh/` 增加 Codex Shell 使用与运维文档（安装、配置、镜像构建、已知限制、故障排查）；提供灰度开关（环境变量或 feature flag）与回滚路径（禁用 Codex Shell、回退到 Chat/ClaudeCode）。

⚠️ 风险与注意事项

- **“一比一复刻”口径风险**：需明确对齐的是「Wegent 内 ClaudeCode Shell 的功能集合」还是「Claude Code 产品全量能力」；建议以 Parity Matrix 作为唯一验收依据。
- **Codex 运行时不确定性**：Codex CLI/SDK 的安装方式、配置文件路径、非交互模式与流式输出接口可能变化，需要版本锁定与镜像校验。
- **安全与合规**：OpenAI Key/组织信息等机密如何注入容器与落盘（避免写入镜像层/日志），需要复用现有加密与脱敏策略。
- **多端兼容**：`amd64/arm64`、不同 Docker 版本、不同企业代理环境下的 npm/pip 安装可靠性。

📎 参考

- `backend/init_data/02-public-shells.yaml:10`
- `docker/base/Dockerfile:15`
- `docker/executor/Dockerfile:10`
- `executor/agents/factory.py:31`
- `executor/agents/claude_code/claude_code_agent.py:58`
- `backend/app/schemas/wizard.py:83`
- `backend/app/api/endpoints/wizard.py:568`
- `executor_manager/routers/routers.py:446`
