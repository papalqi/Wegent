# 前端任务状态/阶段长期只显示「初始化代理 / 执行中 / 执行完成」

## 背景
前端在任务聊天页面会展示任务执行状态（Banner + Thinking 面板的阶段/时间线），理论上应该能看到更细粒度的阶段，例如：

- `queued`（等待分配）
- `booting_executor`（Docker 启动中）
- `pulling_image`（拉取镜像中）
- `loading_skills`（加载技能/模型）
- `executing`（执行中）
- `syncing`（收尾/同步中）
- `completed / failed / cancelled`

但实际 UI 经常只显示极少数文案，用户侧感知为“状态一直只有三种：初始化代理 / 执行中 / 执行完成”。

## 现象
- 状态文案长期只出现：
  - `thinking.initialize_agent` → “初始化代理”
  - `chat:messages.thinking` / `status_running` → “执行中”
  - `tasks:thinking.execution_completed` → “执行完成”
- 预期的细粒度阶段（如 Docker 启动、拉取镜像、加载技能等）在 UI 中不可见或极少出现。

## 影响范围（推测）
- 任务详情页（`/tasks/{id}`）加载的 Banner 状态与时间线阶段。
- Thinking 面板（`DetailedThinkingView`）顶部阶段时间线（若依赖任务详情字段）。
- 任务列表/任务卡片上如果有复用同一套 status/phase 展示逻辑，也可能受影响。

## 复现步骤（推测/待补充）
1. 创建一个会触发 Executor 的任务（如 code task 或使用 ClaudeCode/Codex/Agno shell 的 Team）。
2. 观察聊天页面顶部状态 Banner 与 Thinking 面板。
3. 期间可刷新页面、切换任务、或等待 WebSocket 重连。

## 期望结果
- 在任务运行过程中，UI 能显示细粒度阶段（queued/booting_executor/pulling_image/loading_skills/executing/syncing）。
- 刷新页面或重连后仍能保持正确阶段展示（不退化成只有“执行中”）。

## 实际结果
- UI 经常只显示少数文案（“初始化代理 / 执行中 / 执行完成”），细粒度阶段缺失。

## 关键观察（已确认）
前端细粒度阶段展示依赖两个字段：

- `status_phase`（细粒度阶段名，例如 `pulling_image`）
- `progress_text`（给用户看的阶段描述，例如 “拉取镜像中”）

前端在多个组件中把这两个字段作为最高优先级展示来源（例如 Banner title、Timeline stageLabel）。

## 已确认根因（Root Cause）
后端 `/tasks/{id}` 返回的 TaskDetail **缺少** `status_phase` / `progress_text` 字段，导致：

- 页面初次加载（或 refreshSelectedTaskDetail 等流程）拿不到细粒度阶段；
- 前端只能回退到粗粒度 `status`（RUNNING/PENDING/COMPLETED/FAILED…）映射出来的少数文案；
- 进一步在 UI 中表现为“只有初始化代理/执行中/执行完成”。

同时，后端 Task 字典转换函数没有把 CRD 的字段映射出去：

- CRD 内字段：`task.status.statusPhase` / `task.status.progressText`
- API 期望字段：`status_phase` / `progress_text`

## 已实现的修复（Patch）
> 该部分用于记录修复方向，便于回溯与回归验证。

- `backend/app/schemas/task.py`
  - `TaskDetail` 增加 `status_phase`、`progress_text`
- `backend/app/services/adapters/task_kinds.py`
  - `_convert_to_task_dict` 与 `_convert_to_task_dict_optimized` 返回：
    - `status_phase: task_crd.status.statusPhase`
    - `progress_text: task_crd.status.progressText`

## 猜测/待验证点（请全部视为 Hypothesis）
下面是可能导致“只显示三种状态”的其他原因或放大因素（未必同时存在）：

1. **WebSocket 的 `task:status` 事件可能在某些路径没带 `status_phase/progress_text`**
   - 虽然后端有兜底推导逻辑（基于 `progress` 推导 phase/text），但若某条更新链路绕过该逻辑，前端就只能回退显示。
2. **前端可能在刷新/重连时用 `/tasks/{id}` 的返回覆盖了 WS 事件带来的阶段信息**
   - 若 `getTaskDetail()` 返回缺字段或返回 `null/undefined`，且前端合并策略不当，可能把已有的阶段清空，造成 UI 退化。
3. **Executor/Executor Manager 的 callback 字段语义混淆**
   - Executor callback 把 `message` 映射到 `error_message` 字段（历史兼容/命名原因）。
   - 若某些 UI 错把 `error_message` 当作“进度文案”展示，可能出现“初始化代理/执行中/执行完成”这种偏 Thinking key 的文本，而不是 phase 文本。
4. **进度 `progress` 更新不够频繁或恒定**
   - 当前 Docker executor 默认上报进度可能是固定值（例如 30），后端基于 `progress` 推导 phase 时可能长期落在同一阶段，导致看起来“状态没变化”。
5. **任务模型（Task vs Subtask）字段来源不一致**
   - UI 有的地方用 `Task.status`，有的地方用 `Subtask.status`（`PROCESSING` 等子任务状态），如果混用可能导致展示路径分叉，最终只剩少数文案。
6. **i18n key 回退导致“看起来只有三种”**
   - 如果某些 phase/status 的 i18n key 缺失，`t()` 可能回退到默认 key 或 `status_running`，最终让用户只看到“执行中/执行完成”。

## 建议补充的回归用例（建议）
- 后端：为 `/tasks/{id}` 的响应增加测试，断言包含 `status_phase` / `progress_text`（当 CRD 中存在时）。
- 前端：为 `TaskExecutionStatusBanner` 或 `deriveTaskExecutionPhase` 的输入组合增加测试，覆盖：
  - 仅有 `status`（无 phase/text）时的回退策略
  - 有 `status_phase/progress_text` 时优先展示策略
  - 刷新详情（`getTaskDetail`）与 WS 更新的合并策略不回退

## 验收/验证清单
- [ ] 运行中任务在 UI 能显示 `booting_executor/pulling_image/loading_skills/executing/syncing` 等阶段
- [ ] 刷新页面后阶段仍正确（不退化为只有“执行中”）
- [ ] WS 断线重连后阶段仍正确
- [ ] `FAILED/CANCELLED` 也能正确显示并携带合适的 `completed_at` 行为

