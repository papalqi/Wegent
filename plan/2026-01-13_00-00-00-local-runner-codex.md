# 本地 Local Runner（弱交互）跑 Codex：设计与落地计划

## 背景与目的

当前 Wegent 的 Codex Shell 执行链路以容器化 Executor 为主：由服务器端（Backend/Executor Manager）调度任务，并在容器内运行 `@openai/codex` CLI。  
本计划要新增一种“执行面在用户本地桌面机”的模式，使 **服务器与执行环境不在同一台机器**：

- **服务器（Control Plane）**：仍然负责数据（任务/对话/审计/产物索引）与控制（创建任务、调度、展示）。
- **本地桌面机（Worker Plane）**：运行一个常驻 `local-runner`，在 **本地已有的 repo 工作目录**中执行 Codex，并回传日志/事件/patch/artifact。

该模式选择 **弱交互**：
- 以“任务（TaskRun）”为中心：创建 → 执行 → 日志/产物 → 完成。
- 不做 tmux/PTY 终端接管、抢占控制权、逐字符输入等强交互能力。

## 目标（必须实现）

### 端到端体验
1. Web UI 可以选择一个在线 Runner + 选择一个 workspace（仅 `workspace_id`，不暴露本机路径）发起 Codex 任务。
2. Runner 在本地 workspace 的 repo 目录中运行 Codex（非交互 `exec --json`），并回传：
   - `result.value`（流式文本）
   - `codex_events`（JSON event stream，用于排障，UI 折叠展示）
   - 最终状态与错误信息
   - git pre/post 信息（HEAD、branch、dirty、changed_files）
   - patch（`git diff` + `git diff --binary`）
   - artifact（可选 zip，受大小上限约束）
3. 支持同一 Task 的 **续聊/重试**：沿用 Wegent 现有 `retry_mode` + `resume_session_id` 契约。

### 安全与审计
1. Runner 与服务器之间有可撤销的认证机制（token 或证书）。
2. Runner 本地必须执行“策略闸门”（不只信任服务器下发）：
   - dirty workspace 策略（默认拒绝；允许需显式设置）
   - 写入范围限制（仅 workspace 内）
   - env 注入 allowlist（不上传任何密钥）
   - 超时、产物大小上限
3. 服务器落库审计：谁触发、对哪个 runner/workspace、执行耗时、结果、patch 摘要/哈希。

## 非目标（第一阶段不做）
- 不做终端接管/实时输入（强交互）。
- 不做源码全量同步到服务器（仅回传 patch/artifact）。
- 不做自动 push/开 PR（可作为后续增强）。

## 现状对齐：复用 Wegent 已有 Codex 实现

Wegent 已存在 Codex 非交互执行与事件流契约，可直接复用：

- Executor 侧 `CodexAgent` 使用命令：`codex exec --json --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -C <cwd> -`
- 从 JSONL 事件流中：
  - 将事件批量写入 `result.codex_event`，由 Backend 合并为持久 `result.codex_events`
  - 将 `item.completed/agent_message` 的文本按 chunk 追加到 `result.value`，驱动 UI 流式展示
- 通过 `thread.started` 事件解析并回写 `resume_session_id`，用于后续 `codex exec resume <id>`
- Backend 在 dispatch payload 时携带 `retry_mode/resume_session_id`，并保证只有 `result.value` 可注入 prompt

本计划要求 local-runner 复用同一套“事件/状态回写”契约，避免前后端再造轮子。

## 目标架构与组件边界

### Server（Backend + Frontend）
- Runner 管理：注册/禁用/心跳/在线判定/能力与 workspace 列表（仅 id/name，不含 path）。
- 调度：将某些 Codex 类任务分配到指定 Runner（显式选择或标签匹配）。
- 状态与产物：保存日志/事件/patch/artifact 元数据，驱动 UI。

### Local Runner（新增）
- 常驻进程（建议支持 systemd 或手动运行）。
- 本地配置：
  - runner_id、server_url、token
  - workspaces：`workspace_id -> { name, path, policies }`
- 工作流：
  1) 心跳上报在线与 workspace 列表（不含 path）
  2) claim 任务（pull 模式）
  3) 在 workspace path 执行 Codex（复用 Wegent Codex CLI/事件解析）
  4) pre/post git 信息、patch、artifact 回传
  5) complete 任务（成功/失败/取消）

## 关键问题与解决策略（必须纳入实现）

1) **workspace_id 与本机路径隔离**
- 服务器不存本机路径；UI 只看到 workspace 名称与 id。
- 路径映射只存在 Runner 本地配置中。

2) **resume_session_id 的稳定性**
- `codex exec resume` 依赖同一份 Codex HOME/会话存储。
- Runner 必须为同一 Task 固定 Codex HOME（或按 workspace 固定，但需隔离污染）。

3) **事件流吞吐与存储膨胀**
- 事件上报必须批处理（节流），后端合并持久化。
- 需要最大条数/最大字节的截断策略（默认保留最近 N 条或最近 X MB）。

4) **git 状态与 patch 的可复现性**
- 既输出 `git diff`（易读）也输出 `git diff --binary`（可复现）。
- 记录 pre/post：HEAD、branch、dirty、changed_files。

5) **安全边界**
- Runner 本地二次校验策略（dirty/写入范围/env allowlist/超时/产物大小）。
- 敏感信息脱敏（日志、事件、错误信息）。

6) **与现有 docker executor 共存**
- 保持现有链路不变；local-runner 作为新增执行目标，仅对选定任务生效。

## 里程碑与验收标准（按顺序实现）

### M0：规格冻结
- 输出：Runner/Task payload schema、API 列表、数据表/字段、状态机、策略默认值。
- 验收：评审通过；明确“不泄露本机路径”；明确 resume HOME 策略。

### M1：Runner 可见性
- Backend：Runner 注册/禁用/心跳/列表 API。
- Frontend：Runner 列表与在线状态展示（含 workspaces）。
- 验收：Web 可看到在线 Runner 与 workspace（仅 id/name）。

### M2：任务下发与 Codex 执行闭环
- Backend：任务分配与 claim/complete；日志/事件回写接口（或复用现有 subtask update 通道）。
- Runner：领取任务并在 workspace 执行 `codex exec --json`，回传 `value` 与 `codex_events`，完成状态回传。
- 验收：Web 可触发任务并看到流式输出、事件面板、最终状态。

### M3：git pre/post + patch + artifact
- Runner：preflight dirty 检查；postflight 生成 diff/diff--binary/changed_files；artifact 打包上传。
- Frontend：diff/patch/产物链接展示。
- 验收：至少覆盖三类用例：无改动、文本改动、二进制改动；patch 可复现应用。

### M4：续聊/重试稳定性
- Runner：固定 Codex HOME；支持 resume/new_session 的 retry_mode。
- 验收：同一 Task 多轮：首次→resume→new_session→resume 连续通过。

### M5：安全与运维加固
- 策略闸门完善、速率限制、离线任务回收、诊断命令、日志保留策略。
- 验收：可撤销 runner；可审计；故障可定位（日志/事件/错误码齐备）。

## 使用文档（最终交付需补齐）
- 如何安装/启动 local-runner（含 systemd 示例）
- 如何配置 workspace（workspace_id/name/path/policy）
- 如何在 UI 中选择 Runner + workspace 发起 Codex 任务
- 如何查看日志/事件/patch/artifact
- 常见问题：resume 失败、路径无权限、dirty workspace、事件太大、Codex CLI 不可用

