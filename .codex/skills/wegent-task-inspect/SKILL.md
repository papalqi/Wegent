---
name: wegent-task-inspect
description: Inspect a Wegent task by task_id to determine whether it finished successfully and why it may be stuck (e.g., UI shows "almost done" but never "completed"). Use when asked to check "第xx号任务运行成功了吗/为什么没显示执行完成/卡在RUNNING/进度不动/执行器容器是否还在/回调是否写回数据库", or when debugging task execution status across MySQL + executor-manager + workspace.
---

# Wegent Task Inspect

## 快速开始（推荐）

- 在仓库根目录运行：`python3 .codex/skills/wegent-task-inspect/scripts/inspect_task.py --task-id 89`
- 常用参数：
  - `--executor-manager-url http://localhost:8001`
  - `--mysql-container wegent-mysql`
  - `--workspace-root /root/wecode-bot`
  - `--docker-since 7d`（扩大日志回溯范围）
  - `--subtasks-limit 30`（默认只显示最近 N 条 subtask，减少噪音）
  - `--subtasks-all`（显示全部 subtask）
  - `--probe-llm`（对 `model.base_url` 做 `/models` 探测；401/404 也能用于判断“网关是否可达”）

脚本会输出：服务健康、DB 中 task/subtask 状态、模型/网关配置（`model.base_url`）、executor 是否存在、workspace git 状态、以及关键日志命中，并给出“为何未完成”的归因提示（默认只诊断活跃 subtask 的 executor，避免历史 executor 被清理导致误报）。

## 工作流（手动排查时按顺序）

### 1) 确认基础服务是否可用

- `docker ps` 看 `wegent-mysql/wegent-redis/wegent-executor-manager` 是否在跑
- `curl http://localhost:8001/health` 看 executor-manager 是否 healthy

### 2) 查数据库里的 task/subtask 状态（是否真的完成）

- `tasks`：确认 `id=<task_id>` 是否存在、`updated_at` 是否还在变化
- `tasks.json.status.*`：关注 `status/progress/statusPhase/completedAt/errorMessage`
- `subtasks`：找到对应的 `RUNNING` subtask（通常是 Assistant 的那条）以及 `executor_name`

### 3) 查 executor 是否还存在（为什么“跑到最后但不完成”最常见原因）

- 用 executor-manager：`/executor-manager/executor/status?executor_name=<executor_name>`
- 用 Docker：`docker ps -a | rg <executor_name>`

判定规则（经验）：如果 `subtask.status=RUNNING` 但 executor `exists=false`，通常代表容器已退出/被清理，导致最终的 COMPLETED/FAILED 回调没有写回 DB，于是 UI 永远等不到“执行完成”。

### 4) 查 workspace 是否已有代码产物（“代码做完了但状态没收尾”）

- 默认在 `${HOME}/wecode-bot/<task_id>/`（可按部署配置调整）
- 看是否已创建分支/提交：`git branch --show-current`、`git log -1 --oneline`、`git status --porcelain`

### 5) 扫描关键日志（注意脱敏）

优先扫描：
- `backend/uvicorn.log`、`frontend/next.log`（若存在）
- `docker logs wegent-executor-manager --since <range>`

检索关键词：`task_id=<id>`、`subtask_id=<id>`、`executor_name`、`callback`、`COMPLETED/FAILED`、`Traceback/Exception`、`timeout/refused`。

本 skill 自带脚本会对常见 token 做基础脱敏后再打印（但仍建议你在分享日志前二次确认）。
