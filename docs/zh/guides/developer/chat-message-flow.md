# Chat 消息流与单一数据源

目标：所有聊天/任务消息的展示与导出，必须以 `useUnifiedMessages` 返回的 `messages` 为唯一数据源，确保包含 WebSocket 实时更新。

## 数据源对比
- ✅ `messages`（`useUnifiedMessages({ team, isGroupChat })`）：实时流式/群聊/自发消息全量数据。
- ❌ `selectedTaskDetail.subtasks`：仅后端缓存，缺少 WebSocket 更新，不用于展示/导出。

## 流程概要
1) 初次加载：`selectedTaskDetail.subtasks → syncBackendMessages() → streamState.messages`  
2) 自己发送：`sendMessage()` 先写入 pending → WebSocket `chat:start`/`chat:chunk`/`chat:done` 更新  
3) 他人发送（群聊）：WebSocket `chat:message` 直接写入 `streamState.messages`  
4) 切换任务/刷新：再次用后端数据同步，再继续接收 WebSocket

## 导出/展示示例
```ts
const { messages } = useUnifiedMessages({ team, isGroupChat });
const exportMessages = messages
  .filter((m) => m.status === 'completed')
  .map(({ role, content }) => ({ role, content }));
```

## 常见误用
- 使用 `selectedTaskDetail.subtasks` 导出：会缺最新 WebSocket 消息。
- 只监听 `chat:done` 不处理 `chat:chunk`：流式显示会断档。
- 切换任务未调用 `syncBackendMessages`：历史消息缺失。

## 调试建议
- 检查 WebSocket 连接与房间订阅；确认 `chat:start/chat:chunk/chat:done/chat:message` 均在前端被处理。
- 复现问题时记录：发送时间、任务 ID、消息 ID、事件序列。

## 执行状态与进度阶段表

前后端统一使用下表作为“细粒度执行状态”枚举。后端优先下发 `status_phase` 字段；缺省时前端可按 `TaskStatus` + `progress` 分段兜底（详见兼容策略）。

| 阶段键 | 展示文案 | 触发条件 | 来源信号 | 结束/降级条件 |
| --- | --- | --- | --- | --- |
| `queued` | 等待分配 | `TaskStatus=PENDING` 且 executor 未下发 phase | `task:status.status` 或 REST `TaskDetail.status` | 收到 RUNNING/FAILED/CANCELLED 即退出 |
| `booting_executor` | Docker 启动中 | 后端标记 phase=`booting_executor`；或 RUNNING 且 progress ∈ [0,20) 且无其他 phase | `status_phase`（优先）；兜底用 `task:status` + `progress` | phase 变化或 progress ≥20% |
| `pulling_image` | 拉取镜像中 | phase=`pulling_image`；或 RUNNING 且 progress ∈ [20,40) | 同上 | phase 变化或 progress ≥40% |
| `loading_skills` | 加载技能/模型 | phase=`loading_skills`；或 RUNNING 且 progress ∈ [40,60) | 同上 | phase 变化或 progress ≥60% |
| `executing` | 执行中 | phase=`executing`；或 RUNNING 且 progress ∈ [60,90) | 同上 | phase 变化或 progress ≥90% |
| `syncing` | 收尾/同步中 | phase=`syncing`；或 RUNNING 且 progress ∈ [90,100) | 同上 | 收到 COMPLETED/FAILED/CANCELLED 或 progress≥100 |
| `completed` | 已完成 | `TaskStatus=COMPLETED` | `task:status` 或 REST | 状态变更为其他终态 |
| `failed` | 执行失败 | `TaskStatus=FAILED`，附 `error_message` | `task:status`/REST + 错误字段 | 状态变更为其他终态 |
| `cancelled` | 已取消 | `TaskStatus=CANCELLED` 或 `CANCELLING` 完成 | `task:status`/REST | 状态变更为其他终态 |

### 兼容与兜底
- **优先字段**：当后端下发 `status_phase`（WebSocket `task:status` 或 REST），前端直接使用并忽略 progress 分段。
- **兜底规则**：缺少 `status_phase` 时，前端用 `TaskStatus + progress` 按表格分段映射，最小化回退到旧 UI 仅显示“执行中”。
- **观测**：所有 phase 变化应伴随日志/埋点，便于对齐后端实际触发点。
