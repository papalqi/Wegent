# 05 - Codex 事件流：持久化 + UI 展示 + 完成后保留

## 变更概述

为 Codex 相关任务补齐“事件流（JSON event stream）”采集与前端展示能力，用于排查工具调用/执行细节：

- Executor：持久化 Codex JSON event stream
- Frontend：在 AI 消息下方展示 “Codex event stream” 折叠面板（摘要 + 关键字段 + 原始 JSON）
- 修复：任务完成后 event stream 不丢失；大行输出更稳健

## 影响范围

- Executor：Codex agent 事件采集、stdout/stderr 处理
- Frontend：`CodexEventStreamPanel` 组件与样式/Badge 对齐

## 验收前置

- 已启动 Backend + Executor + Frontend
- 准备一个会触发 Codex 事件的任务（例如 code 任务，且执行过程中会有 tool call/command 等）

## 验收步骤

- [ ] 触发一次 Codex 相关任务，等待产生 AI 响应
- [ ] 在该 AI 消息下方，确认出现 “Codex event stream” 折叠面板
- [ ] 展开后应看到：
  - [ ] 事件列表（每条含 type/摘要/Key Fields/Full JSON）
  - [ ] 错误事件应有明显标识（例如红色 tone）
  - [ ] 支持复制（Copy）原始 JSON
- [ ] 任务完成后刷新页面/切换任务再切回：
  - [ ] event stream 仍可见（不随完成而丢失）
- [ ] 构造较大输出（长命令输出/大日志），前端不应卡死或崩溃（主要验证“长行容忍”修复）

## 预期结果

- 事件流可见、可复制、完成后仍保留；异常/大输出时系统保持稳定。

## 已知关注点（建议验收时重点看）

- `Codex event stream` 标题/分隔符是否出现异常字符（如发现乱码，记录截图便于回归修正）

## 相关提交（关键）

- `7f1f5fe` feat(executor): persist codex json event stream
- `67452ef` feat(codex): surface event stream in task UI
- `376b209` feat(frontend): polish Codex event stream panel
- `7027b6d` fix: preserve Codex event stream after completion
- `e45d23b` fix(executor): tolerate long subprocess lines in codex agent
- `cf5065c` fix(frontend): align Badge variants in Codex events

