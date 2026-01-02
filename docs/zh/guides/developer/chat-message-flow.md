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
