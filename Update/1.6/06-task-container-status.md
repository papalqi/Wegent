# 06 - 任务容器状态：container-status API + 顶栏/侧边栏徽标

## 变更概述

为 code 任务增加“执行容器状态”可视化：

- Backend：提供 task 维度与 batch 维度的 container-status 查询 API
- Frontend：
  - 顶栏显示当前任务容器状态 Badge（带 tooltip，定时轮询）
  - 侧边栏任务列表对 code 任务显示容器状态 icon（batch 轮询，最多 50 个）

## 影响范围

- Backend：`/api/tasks/{task_id}/container-status`、`/api/tasks/container-status`
- Frontend：TopNavigation、TaskListSection、container-status 组件与 hooks

## 验收前置

- 已启动 Backend + Executor Manager（需要真实容器状态可查）
- 准备一个 code 任务（非 group chat）并触发执行

## 验收步骤

- [ ] 进入 code 页面，打开一个正在运行/已运行过的 code 任务
- [ ] 顶栏出现 “Container Status” Badge（10s 轮询）
  - [ ] `running`：显示 Running
  - [ ] `exited`：显示 Exited
  - [ ] `not_found`：显示 Not Found
  - [ ] `unknown`：显示 Unknown
  - [ ] tooltip 中包含 `executor_name`（如可获取）
- [ ] 回到左侧任务列表：
  - [ ] code 任务条目右侧出现容器状态 icon（20s 轮询 batch）
  - [ ] tooltip 文案包含容器状态描述
- [ ] 对无权限/不存在的 task id（可用 API 手工验证）：
  - [ ] 返回应为 404 或 `unknown + reason=task_not_found_or_no_permission`（不泄露信息）

## 预期结果

- 顶栏与侧边栏的容器状态展示一致且能随容器状态变化更新；异常场景返回稳定。

## 相关提交（关键）

- `59c4cb8` feat: show coding container status
- `bcbbd8b` fix(frontend): resolve container badge typing

