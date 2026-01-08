---
mode: plan
cwd: /root/project/Wegent
task: Code Shell 同一 Task 默认续聊（Codex `codex exec resume` 对齐 ClaudeCode）
complexity: complex
planning_method: builtin
created_at: 2026-01-06T16:11:39+08:00
---

# Plan: Code Shell 同一 Task 默认续聊（Codex `codex exec resume` 对齐 ClaudeCode）

🎯 任务概述

不新增“Bot 级别的模式开关”。改为：在**同一 Task 的对话线程**内，Code Shell 默认就是“续聊/保持上下文”。

- Codex：首轮运行创建会话，后续默认使用 `codex exec resume <SESSION_ID>` 续聊（对齐 ClaudeCode 的体验）。
- ClaudeCode：保持现有行为（同一 Task 内复用 session）。
- 前端对话界面在 Bot 名称旁展示 `Resume` Badge，用于明确这是“会话续聊”语义（非断线续流）。
- 一旦发生错误/不支持/恢复失败，前端需要展示明确的错误信息（包含可定位的错误细节）。
- 当任务失败时，UI 需要提供用户选择：继续尝试 `resume`，或“新会话重试”（跑一次 `codex exec`）。

✅ 已确认选择（决策记录）

1) `resume` 的作用范围
- ✅ A. 仅同一 Task 内多轮对话续聊（已确认）
- B. 跨 Task 续聊（需要“会话绑定/选择历史会话”，实现与产品决策更重）
- C. 先 A，B 作为后续 Phase 2

2) Codex 的 `resume` 实现策略（重点）
- ✅ A. 使用 Codex CLI：`codex exec resume <SESSION_ID> <PROMPT>`（已确认 Codex CLI 0.77.0 支持）
- B. 不依赖 Codex：由后端拼接/注入上下文（例如最近 N 轮 user+assistant）
- ❌ 不做 C：不做自动降级（已确认“只使用 codex exec resume”）

3) 前端“看到 resume 模式”的展示位置
- ✅ A. Bot 旁边（AI 消息气泡 Header / Bot 名称旁）显示 Badge（例如 `Resume`）（已确认）
- B. 聊天输入框/右侧信息面板显示当前 Bot 的模式
- C. A + B（推荐）

4) 错误展示的期望
- ✅ A. 用户友好文案 + 可展开的原始错误（已确认）
- B. 仅原始错误（偏开发态）
- C. 仅用户友好文案（不利于排障）

📐 设计取舍（已确认）
- ✅ 采用 1A：仅同一 Task 内续聊，避免引入“跨 Task 会话选择”的产品复杂度。
- ✅ 采用 2A：使用 `codex exec resume <SESSION_ID>` 恢复会话；`SESSION_ID` 取自上一轮 Codex 输出事件 `thread.started.thread_id`。
- ✅ 不启用 2C：不做“自动降级上下文注入”；`codex exec resume` 失败则 subtask 失败（已确认）。
- ✅ Codex 在同一 Task 的后续消息里**默认走 resume**（只要已拿到 `resume_session_id`），无需用户每轮手动选择；对齐 ClaudeCode 现有“同一 Task 内复用 session”的体验。
- ✅ 失败后允许用户在 UI 手动选择“Resume 重试 / 新会话重试”（不是自动降级）。
- ✅ ClaudeCode 维持现状：默认复用会话；前端展示与 Codex 对齐。
- ✅ 已确认：用户点“新会话重试”后，ClaudeCode 生成新的 `session_id`，并**持久化替换**该 Task 的“当前会话”（后续继续沿用新会话）。
- ✅ 续聊是 **按 Task 会话状态**（而非 Bot 配置）驱动：通过保存/下发 “当前会话 id” 来实现续聊与新会话切换。

📋 执行计划

1. 明确契约与命名（产品/协议）
   - 固化 UI 文案（i18n key）与字段命名，并补充接口契约说明。
   - 避免与现有“流式恢复”（`chat:resume` 断线续流）概念混淆：对外叫“续聊/恢复上下文”（Resume），不叫 `chat:resume`。
   - 明确对外字段（建议）：
     - Codex：`resume_session_id`（UUID，来自 `thread.started.thread_id`）
     - ClaudeCode：`session_id`（string）
     - Retry：`retry_mode: resume|new_session`

2. 后端：会话状态下发 + Retry 意图传递
   - `backend/app/services/adapters/executor_kinds.py`：为 Codex/ClaudeCode 子任务下发“当前会话信息”：
     - Codex：`resume_session_id`（来自上一次 Codex `thread.started.thread_id`，持久化后再下发）。
     - ClaudeCode：`session_id`（默认=task_id；若用户点“新会话重试”则为新 uuid，并替换为该 Task 的当前会话）。
   - `backend/app/api/ws/events.py`：扩展 `ChatRetryPayload` 增加 `retry_mode: Literal['resume','new_session']`。
   - `backend/app/api/ws/chat_namespace.py`：`on_chat_retry` 接收 `retry_mode`，并把该选择持久化到 executor 可读取的位置（推荐：写入将被重跑的 assistant subtask 的 `result.retry_mode`，并在 dispatch 时透传）。
   - `backend/app/services/chat/operations/retry.py`：调整 reset 逻辑：
     - `retry_mode=resume`：清空 `value/error` 等展示字段，但保留 `resume_session_id/session_id`（否则无法 resume）。
     - `retry_mode=new_session`：Codex 清空 `resume_session_id`；ClaudeCode 生成新 `session_id` 并写入“当前会话”（供本次与后续续聊使用）。
   - 关键安全点：`Subtask.result` 是 JSON dict；拼 prompt 时只能取 `result.value`，避免把 `resume_session_id/session_id/retry_mode` 等内部字段注入 prompt。

3. Executor：Codex 默认续聊（`codex exec resume`）
   - 在 `executor/agents/codex/codex_agent.py`：
     - ✅ 默认规则：若存在 `resume_session_id` 且 `retry_mode != new_session`，使用：`codex exec --json resume <resume_session_id> -`；否则使用 `codex exec --json -` 创建新会话。
     - 需要补齐：首次会话与 session_id 产生/存储/传递链路：
       - 第一次运行 `codex exec --json` 时，解析事件 `thread.started.thread_id`，写入 `result.resume_session_id` 并回传到后端；
       - 后端在下一轮下发该 Task 的子任务时，把上一轮保存的 `resume_session_id` 带入 task payload。
     - 失败时将错误写入 `result.error`（必要时增加 `result.error_code`），确保前端立刻可见。
     - 新会话重试：当用户选择“新会话重试”时，强制忽略 `resume_session_id`，改为跑 `codex exec --json -` 并生成新的 `resume_session_id`。
     - 将 `resume_session_id` 回传到 result（与 `shell_type` 同级），保证后端可持久化并继续下发。

4. Executor：ClaudeCode 新会话切换（保持默认续聊）
   - 在 `executor/agents/claude_code/claude_code_agent.py`：
     - 默认继续复用会话（保持现状）。
     - 读取 `session_id`（若无则回退为 `task_id`），用作 Claude SDK 的 `session_id`（并把 client cache key 从 `task_id` 平滑迁移到 `session_id`，以支持同一 Task 内切换会话）。
     - `retry_mode=new_session`：使用后端下发的新 `session_id` 执行，并回传 `result.session_id`（后端据此持久化替换为该 Task 当前会话）。

5. 前端：Resume Badge + 双按钮重试（Codex/ClaudeCode）
   - `frontend/src/features/tasks/components/message/MessageBubble.tsx`：
     - 默认在 Code Shell（Codex/ClaudeCode）消息的 Bot 名称旁显示 `Resume` Badge。
   - 如需在输入区展示：在 ChatInput 区域展示“当前 bot: resume”。
   - 错误：沿用现有错误展示（message bubble 的红色块），补充 error_code/更友好文案（按第 4 题确认）。
   - 失败交互（新增）：当 Code Shell 的 AI 消息失败时，Retry 入口改为二选一：
     - “Resume 重试”：继续使用 `codex exec resume <SESSION_ID>`；若缺少 `resume_session_id`，提示“没有可恢复会话，请用新会话重试”。
     - “新会话重试”：跑 `codex exec`（不带 resume），并在成功后写回新的 `resume_session_id`。
   - ✅（已确认）失败交互以**两个按钮**呈现（B2），并且对 **Codex + ClaudeCode** 都提供该选择（C2）：
     - Codex：Resume 重试 = `codex exec resume`；新会话重试 = `codex exec`。
     - ClaudeCode：Resume 重试 = 复用现有 `session_id`；新会话重试 = 使用新的 `session_id` 执行一次，并持久化替换该 Task 的当前会话（不修改 Bot 配置）。
   - ✅ 新会话重试为**一次性选择**（D1）：不修改 Bot 配置；但会更新该 Task 的“当前会话”（后续消息默认沿用新会话）。

6. 测试与回归（必须）
   - Backend：`cd backend && uv run pytest`（新增：executor_kinds + chat retry reset 相关单测；覆盖 session_id/resume_session_id 不被 prompt 注入）。
   - Executor：`cd executor && uv run pytest`（新增：CodexAgent 命令选择/解析 thread_id；ClaudeCodeAgent session_id 切换/缓存）。
   - Frontend：`cd frontend && npm run lint` + `npm test`。
   - 回归：优先补 Playwright 用例（同一 Task 多轮续聊；失败后双按钮重试；新会话替换后继续续聊）。若无法稳定自动化，则做交互式回归并保留证据（截图/控制台/网络请求）。

7. 文档与发布/回滚
   - 更新 `docs/guides/developer/codex-shell-parity.md`：新增“会话续聊/恢复上下文”能力项与实现要点（Codex 使用 `codex exec resume <SESSION_ID>`）。
   - 回滚策略：提供 feature flag 关闭“默认续聊”行为（强制所有 code shell 走新会话），并隐藏/禁用前端两个重试按钮。

✅ 验收标准（建议）
- 同一 Task 内多轮对话：Codex 首轮生成 `resume_session_id`，后续默认走 `codex exec resume <SESSION_ID>` 续聊；ClaudeCode 行为保持一致（按当前会话 `session_id` 续聊）。
- 任务执行时，executor 回传 `resume_session_id/session_id`；前端消息气泡可显示 Resume Badge（Bot 名称旁）。
- `resume` 不可用/失败时：前端能看到明确错误（含可定位细节），且不影响其它非 code shell 对话。
- 失败时 UI 提供两个按钮：`Resume 重试` / `新会话重试`（Codex + ClaudeCode）；新会话重试会替换该 Task 的当前会话。
- 全套模块测试 + 前端 lint 通过；完成回归并留存证据。

⚠️ 风险与注意事项
- 已验证 `codex-cli 0.77.0` 支持 `codex exec resume <SESSION_ID>`；但必须确保同一 Task 内多轮调用使用同一份 Codex HOME/会话存储（否则 resume 可能找不到会话数据）。
- 已确认不做自动降级：因此 `codex exec resume` 失败会直接表现为任务失败（需确保错误足够可定位），但 UI 提供“新会话重试”作为人工兜底。
- 新会话重试需要一条明确的“意图传递链路”（`chat:retry` payload 增加 `retry_mode: resume|new_session`），否则后端无法区分两种重试方式。
- 多 Bot Team 的语义：当前多个 agent 读取 `bot[0]`，需明确 resume 在多 bot 下的实际效果。
- 与现有 `chat:resume`（流式断线恢复）概念易混淆：命名/文案需明确区分。

📎 参考
- `backend/app/services/adapters/executor_kinds.py:840`（aggregated prompt）
- `backend/app/api/ws/events.py:1`（ChatRetryPayload 扩展 retry_mode）
- `backend/app/api/ws/chat_namespace.py:960`（on_chat_retry）
- `backend/app/services/chat/operations/retry.py:119`（reset_subtask_for_retry）
- `executor/agents/codex/codex_agent.py:248`（Codex CLI 调用与 prompt 构建）
- `executor/agents/claude_code/claude_code_agent.py:110`（Claude session_id 复用逻辑）
- `frontend/src/features/tasks/contexts/chatStreamContext.tsx:700`（chat:error / retry 相关）
- `frontend/src/features/tasks/components/message/MessageBubble.tsx:1249`（错误展示块）
