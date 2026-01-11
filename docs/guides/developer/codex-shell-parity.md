# Codex Shell 对齐矩阵（对齐 ClaudeCode）

本文档是 Wegent 实现 **Codex Shell** 的「范围合同（scope contract）」，用于防止需求漂移。

## “一比一对齐” 的含义

- **对齐目标**：Wegent 现有的 **ClaudeCode Shell 行为契约**（不等价于完整 Claude Code 产品能力）。
- **范围以矩阵为准**：不在矩阵内的能力默认视为不在范围内，除非先更新本文档与 issues CSV。
- **任何范围变化**必须先更新：
  1) 本文档；2) 本次执行使用的 issues CSV（唯一状态源）。

## 能力矩阵

| 能力项 | ClaudeCode 当前行为（refs） | Codex 目标 | 验收方式 |
|---|---|---|---|
| Shell 类型注册 | init_data 中存在 `Shell.spec.shellType=ClaudeCode`。 | 增加 `Shell.spec.shellType=Codex` 并保持兼容。 | Backend 启动后可列出 Codex shell；向导可选择 Codex。 |
| Executor 选 Agent | Executor 通过 `bot[0].shell_type` 在 `AgentFactory` 选取 Agent。 | 新增 `CodexAgent` 并注册到 `AgentFactory`。 | 单测：`shell_type=Codex` 可创建 CodexAgent。 |
| 仓库拉取与工作目录 | `download_code()` clone 仓库；agent 设置稳定 `cwd`。 | 相同行为（clone + 稳定 `cwd`）。 | 手工：派发 repo 任务后，workspace 有仓库且在目录内执行。 |
| 自定义指令 | 加载 `CUSTOM_INSTRUCTION_FILES`，创建 `.claudecode/`，生成 `CLAUDE.md` 软链，更新 `.git/info/exclude`。 | 相同加载规则；Codex 必须可获得同样的指令内容（目录/软链是否被 Codex 直接消费可选）。 | 手工：pre-exec 后 `.claudecode/` 存在；有 `AGENTS.md` 时 `CLAUDE.md` 指向它。 |
| 附件 | 下载附件到 workspace，并把 prompt 中引用替换为本地路径。 | 相同行为。 | 手工：上传附件后文件落盘；prompt 包含本地路径上下文。 |
| Skills | ClaudeCode 将技能从后端下载并部署到 `~/.claude/skills`。 | Codex 需支持 Wegent skills：要么部署到 Codex 支持的位置，要么通过 Wegent 机制注入技能提示词/工具。 | 手工：配置 skill 后可被调用；不能静默失败。 |
| MCP servers | ClaudeCode 提取 MCP 配置并进行变量替换后传给运行时。 | 相同行为（含变量替换规则）。 | 手工：配置 `${{user.name}}` 等占位符，运行时接收到替换后的配置。 |
| Git CLI 鉴权与代理 | 设置 git env；`gh`/`glab` 鉴权；可选 `REPO_PROXY_CONFIG` 配置代理。 | 相同行为。 | 手工：token 存在时可鉴权；代理配置写入 git config。 |
| 流式输出 + workbench/thinking | Executor 在 RUNNING 回调中持续更新 `result.value/thinking/workbench`，后端按增量发送 `chat:chunk`。 | 相同语义：Codex 必须以增量方式更新 `result.value`，前端才能流式展示。 | E2E：发送消息→看到 chunk 流式输出→done；刷新后内容保持。 |
| 会话续聊/恢复上下文 | 默认按 `session_id` 续聊；`retry_mode=new_session` 时使用后端下发的新 `session_id` 并回传 `result.session_id`。 | 默认按 `resume_session_id` 续聊：执行 `codex exec resume <SESSION_ID>`；`retry_mode=new_session` 时执行 `codex exec` 并回传新的 `result.resume_session_id`。 | E2E：同一 Task 多轮对话默认续聊；失败后双按钮重试；新会话重试后后续默认续聊。 |
| 取消 | ClaudeCode 支持取消并清理 client/process。 | Codex 支持取消（停止子进程、标记取消、清理资源）。 | 手工：运行中取消后不再继续 chunk，最终状态符合契约。 |
| 可观测性与安全 | 敏感信息脱敏；关键阶段日志/链路追踪。 | 相同行为。 | Code review：日志/结果不泄露密钥；关键阶段可定位。 |
| 镜像校验 | Executor Manager 仅对支持的 shell 做镜像依赖检查。 | `/executor-manager/images/validate` 支持 Codex，并增加 Codex 依赖检查项。 | API：校验 Codex 镜像返回 checks + valid。 |

## 会话续聊/恢复上下文（实现要点）

### Codex：`resume_session_id` → `codex exec resume <SESSION_ID>`

- Executor（CodexAgent）从 Codex CLI 的 `thread.started` 事件中提取 `thread_id`，写入 `result.resume_session_id` 并持久化。
- Backend 在下一轮下发该 Task 的 subtask 时，把上一轮保存的 `resume_session_id` 带入 task payload 的 `resume_session_id` 字段。
- Executor 在 `retry_mode!=new_session` 且存在 `resume_session_id` 时，调用：`codex exec resume <SESSION_ID> --json -`。

### ClaudeCode：`session_id` 续聊与新会话切换

- 默认使用 `session_id` 续聊；若缺省则回退为 `task_id`。
- 当 `retry_mode=new_session` 时，Backend 生成新的 `session_id` 下发；Executor 回传 `result.session_id`，Backend 持久化后用于后续续聊。

## 回滚开关（feature flag）

通过环境变量 `CODE_SHELL_RESUME_ENABLED` 控制“默认续聊 + 双按钮重试入口”。默认值为 `true`。

- `CODE_SHELL_RESUME_ENABLED=true`：前端展示 Resume Badge，失败时提供 `Resume 重试/新会话重试` 两个按钮；后端按 `resume_session_id/session_id` 默认续聊。
- `CODE_SHELL_RESUME_ENABLED=false`：后端强制 Code Shell 走新会话（Codex 不下发 `resume_session_id`；ClaudeCode 下发新的 `session_id`），前端隐藏 Resume Badge 与双按钮入口，仅保留通用“重试”。

注意：该开关仅影响 Code Shell（Codex/ClaudeCode）的会话语义，不影响 `chat:resume`（断线续流）与普通 Chat。

## 推荐的端到端 Smoke 用例

使用内置公共技能 `shell_smoke`，在 **不依赖真实 LLM 输出** 的情况下验证全链路：

1) 为 ClaudeCode/Codex Bot 配置 skill `shell_smoke`
2) 从前端创建任务并发送 `@shell_smoke`
3) 验收：
   - 流式输出能够增量展示
   - 任务工作目录中生成 `shell_smoke_result.txt`

## 范围说明 / 明确非目标

- “一比一对齐”不等于复刻上游 Codex/Claude Code 产品所有能力，而是对齐 **Wegent 内 ClaudeCode Shell 的契约**。
- 若 Codex 运行时无法提供等价能力，必须先在本文档记录偏差与缓解方案，再允许合入。

## 签署（Sign-off）

当本文档与本次执行使用的 issues CSV 一起合入仓库时，视为范围已确认，可进入实现阶段。

## 参考

- `backend/init_data/02-public-shells.yaml:10`
- `executor/agents/factory.py:31`
- `executor/agents/base.py:276`
- `executor/agents/claude_code/claude_code_agent.py:633`
- `executor/agents/claude_code/claude_code_agent.py:1169`
- `executor/agents/claude_code/claude_code_agent.py:1300`
- `backend/app/services/adapters/executor_kinds.py:1054`
- `executor_manager/routers/routers.py:446`
- `plan/2026-01-01_14-03-09-codex-shell-claude-code.md:18`
