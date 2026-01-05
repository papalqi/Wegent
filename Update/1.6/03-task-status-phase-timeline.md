# 03 - 任务状态：status_phase/progress_text 贯通 + 阶段耗时展示

## 变更概述

将任务执行过程中的“更细粒度阶段信号”贯通后端、WebSocket 与前端展示，重点解决：

- 用户能在消息气泡中看到当前阶段（例如拉镜像/启动 executor/执行中）而不是“笼统 running”
- 前端记录阶段变化，展示最近阶段的耗时（用于定位卡住点）
- 修复错误文案与进度文案混淆的问题（避免 `progress_text` 泄漏进 `error_message`）

## 影响范围

- Backend
  - Task schema / WS payload：新增或补齐 `status_phase`、`progress_text`、`error_message`
  - 执行器进度计算与合并逻辑（更稳定的 progress/phase 推导）
- Frontend
  - Thinking 气泡顶部展示 task-level phase strip（阶段 + 耗时 + 错误）
  - 阶段耗时 timeline 逻辑（前端侧按事件更新时间滚动）

## 验收前置

- 已启动 Backend + Frontend
- 准备一个能够跑起来的 code/chat 任务（建议 code 任务更容易出现明显阶段变化）

## 验收步骤

- [ ] 新建一个任务并触发执行（进入 running）
- [ ] 在 AI 消息的 thinking 区域，确认出现“任务阶段条”（stage strip）
  - [ ] 标题优先显示 `progress_text`（如有），否则显示 `status_phase`/fallback 文案
  - [ ] 右侧显示“已耗时（秒）”并持续更新
- [ ] 任务阶段发生变化时（例如从 booting → running），阶段列表应追加/更新最近若干条，并显示各阶段耗时
- [ ] 构造失败任务（例如故意填错配置/断网/非法参数）：
  - [ ] 阶段条中出现错误块（红色背景），内容来自 `error_message`
  - [ ] 错误内容不应夹带上一阶段的 `progress_text`

## 预期结果

- 前端能稳定展示 task phase + timeline；失败时错误展示干净、可定位。

## 相关提交（关键）

- `7e354b0` feat(backend): [CSD-030] improve progress calculation
- `540d813` feat(frontend): [CSD-040] 前端状态模型接入
- `f5997e9` feat(frontend): [CSD-050] 状态提示组件与文案实现
- `cf0b58e` feat(frontend): [CSD-060] improve task error banner
- `a32af61` feat(frontend): show real task phase timing
- `dc78634` fix: prevent progress text leaking into error_message

