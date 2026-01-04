---
mode: plan
cwd: H:/project/Wegent
task: Codex Executor 多轮对话上下文连续性（避免每轮断上下文）
complexity: medium
planning_method: builtin
created_at: 2026-01-04T20:32:03+08:00
---

# Plan: Codex Executor 多轮对话上下文连续性（避免每轮断上下文）

## 0. 背景与问题复现

当前选择 `shell_type=Codex`（以及其它 executor-based shells）时，每次用户在同一个 `task_id` 里发送 follow-up，后端下发给 executor 的 `prompt` 主要是「本轮 user prompt」；不会携带之前轮次的 user/assistant 内容，因此模型在多轮对话中表现为“上下文不连贯 / 断档”。  

补充：Codex CLI 虽然有 `codex exec resume`，但该子命令不支持 `--json` 事件流输出，无法复用当前 Wegent executor 对 JSONL event stream 的解析与进度回传机制；短期内不作为主方案。

## 1. 目标与成功标准

### 目标
1. 对 `shell_type=Codex` 的 follow-up 消息，在每次下发 executor 任务时，自动拼接最近若干轮对话历史到 `prompt` 中，使模型能理解上下文。
2. 方案尽量通用：同时覆盖其它 executor-based shells（如 ClaudeCode/Agno），避免只为 Codex 写特例。
3. 兼容现有 pipeline 协作模式：不破坏“上一步执行结果（Previous execution result）”的链式传递语义。

### 成功标准（可验证）
1. 对同一 `task_id` 连续发 3+ 轮追问，模型能正确引用前文（至少能引用上一轮 assistant 的结论/约束）。
2. 刷新页面/多端同步后，历史消息展示顺序与内容保持一致（不引入重复/错序）。
3. 不显著增加失败率：prompt 拼接后仍能稳定执行（不出现明显的 token 爆炸导致的频繁失败）。

## 2. 方案选型

### 方案 A（推荐）：后端下发 executor prompt 时注入历史对话
在 `backend/app/services/adapters/executor_kinds.py` 构造 `prompt` 时，把该 task 的历史 subtasks（USER/ASSISTANT）按顺序转换为“对话 transcript”，并做截断策略：
- 优先保留最近 N 轮（或最近 M 条 message），必要时按字符长度裁剪；
- ASSISTANT 内容优先读取 `result.value`（不存在时降级为序列化后的 `result`）；
- 可选：group chat 时为 USER 补 `User[username]:` 前缀；
- pipeline 模式：保留现有“Previous execution result”逻辑，同时把历史对话作为“Conversation History”段落插到 `prompt` 顶部。

优点：实现成本低、与现有 JSONL 流式回传完全兼容、对 executor shells 通用。  
缺点：prompt 增大，需要谨慎的截断/压缩策略。

### 方案 B（备选/探索）：Codex CLI session resume
基于 executor 内的隔离 HOME（`WORKSPACE_ROOT/<task_id>/.wegent_home`），尝试 `codex exec resume --last` 续会话。  
当前阻塞点：`codex exec resume` 不支持 `--json`，需要新增“非 JSON 模式的 stdout 流解析/回传”实现，范围较大，暂不优先。

## 3. 设计细节（方案 A）

### 3.1 Prompt 结构建议
建议的最终 prompt 结构（示意）：
1. `Conversation History`（截断后的历史 user/assistant transcript）
2. `Current User Message`（本轮 user prompt）
3. `Previous execution result`（仅 pipeline / 多 bot 链式步骤需要时保留）

### 3.2 截断策略
1. 先按“message 条数”截断（例如最近 12 条消息：6 轮 user+assistant）。
2. 再按“字符长度”硬上限截断（例如 20k–40k chars，具体需结合模型上下文窗口与平均 token/char 比例）。
3. 对单条消息内容设置上限（例如每条 4k chars），避免某条超长输出吞噬预算。

### 3.3 可配置项
在 backend settings 中新增（或沿用已有类似配置）：
- `EXECUTOR_HISTORY_MAX_MESSAGES`
- `EXECUTOR_HISTORY_MAX_CHARS`
- `EXECUTOR_HISTORY_PER_MESSAGE_MAX_CHARS`

并允许按 `taskType` 做差异化：`code` 可更大，`chat` 可更小。

## 4. 实施步骤

1. 需求澄清与验收用例
   - 明确只改 executor-based shells（Codex/ClaudeCode/Agno），Chat Shell 不改。
   - 明确“历史注入”的轮数/大小默认值与可配置入口。
2. Backend：抽取 prompt builder
   - 在 `executor_kinds.py` 增加纯函数/工具函数：`build_executor_prompt_with_history(...)`。
   - 复用现有 `related_subtasks` 查询结果，避免额外 DB 查询。
3. Backend：接入到 `_format_subtasks_response`
   - 替换当前的 `aggregated_prompt` 拼接逻辑：由 prompt builder 产出最终 prompt。
   - 保留 pipeline 的“Previous execution result”语义（必要时将其作为单独段落）。
4. 单测
   - 增加后端单测：覆盖多轮 USER/ASSISTANT、pipeline、多种 `result` 结构、截断逻辑、group chat USER 前缀。
5. 可观测性
   - 在后端日志中输出“注入历史条数/截断是否发生/最终 prompt 长度（chars）”，但不打印完整 prompt 内容（避免泄露）。
6. 回归验证
   - 手动回归：创建 Codex task，连续追问 3–5 轮，验证能引用前文。
   - 关键路径：刷新页面后继续追问，验证仍连贯。

## 5. 风险与回滚

### 风险
1. token 增长导致执行变慢/失败：需要分层截断策略与默认值谨慎设定。
2. 历史注入可能引入“旧指令污染”：需要在 transcript 中明确角色边界（User/Assistant）。
3. group chat 多用户场景：若不带 sender 信息，模型可能混淆“谁说的”；可逐步增强。

### 回滚
1. 配置开关：允许关闭历史注入（恢复当前仅本轮 prompt）。
2. 出问题时可快速降级到仅注入“上一轮 assistant”或仅注入最近 1 轮。

