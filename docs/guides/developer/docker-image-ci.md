# Docker 镜像发布与 CI（publish-image.yml）

本文用于承载原本在 `AGENTS.md` 里的镜像发布相关说明，避免让通用协作约束过长。

## PR（镜像发布）触发条件

- 如需触发 `.github/workflows/publish-image.yml`（合并到 `main` 的 PR），PR 标题必须包含 `Changeset version bump`，否则该工作流会被条件跳过（显示 Skipped）。该流程也会走镜像版本/tag 更新相关逻辑。

## 本地 start.sh 环境注意

- start.sh 读取顺序：`.env.defaults` < `.env` < `.env.local` < 现有环境变量；已有环境变量不会被文件覆盖。
- 若环境提前设置了 `WEGENT_EXECUTOR_IMAGE` / `WEGENT_EXECUTOR_VERSION` / `WEGENT_IMAGE_PREFIX`，可能指向不存在的 `ghcr.io/wecode-ai/wegent-executor:latest-codex`，导致 Executor Manager 健康检查超时。
- 处理方式：启动前执行：
  - `unset WEGENT_EXECUTOR_IMAGE WEGENT_EXECUTOR_VERSION WEGENT_IMAGE_PREFIX`
  - 或显式设置：`export WEGENT_EXECUTOR_IMAGE=ghcr.io/papalqi/wegent-executor:1.0.33-codex`，再运行 `./start.sh --no-rag`

## Docker 镜像 CI（publish-image.yml）

- 触发：合并到 `main` 的 PR（标题必须含 `Changeset version bump`）、推送标签 **`vMAJOR.MINOR.PATCH`**（如 `v1.35.0`）、或手动 `workflow_dispatch`（可传 `version`、`base_ref`、`force_modules`）。
- 注意：`pull_request: closed` 会触发 workflow，但 PR 标题不含 `Changeset version bump` 时 Job 会被条件跳过（显示 Skipped）。
- 标签要求：只有 `vMAJOR.MINOR.PATCH` 形如 `v1.35.0` 才会被识别；`v1.35` 这类两段式不会触发构建。
- 逻辑：`dorny/paths-filter` 检测 `backend/`、`executor/`、`executor_manager/`、`frontend/` 目录变化；按需多架构 buildx 构建并推送到 GHCR `ghcr.io/<owner>/`，同时维护 `latest` 与 `${version}`（`executor` 还带 `${version}-codex` 和 `latest-codex`）。
- 无代码变更但打 tag：直接 `imagetools` retag 复用上一个版本；末尾自动更新 `.env.defaults` 中的镜像版本并推 PR（或在 tag 情况下尝试直接推送）。
