# 本地 Local Runner（弱交互 Codex）使用文档

本指南介绍如何在“服务器端只负责数据与控制、本地桌面机负责执行”的模式下，让 Wegent 通过 Web UI 触发你本地已有 repo 工作目录中的 Codex 执行，并回传日志/事件流/patch/artifact。

## 适用场景
- 你希望 **容器/服务器不在同一台机器**。
- 你希望在 **本地桌面机的真实开发环境**（IDE/依赖/工具链/证书）中运行 Codex。
- 你选择 **弱交互**：以“任务”为中心，不做终端接管（tmux/PTY）。

## 总体架构（你会部署哪些东西）
- **Server**：Wegent Backend + Frontend + DB（保持现有部署方式）
- **本地桌面机**：运行 `wegent-local-runner` 常驻进程（本仓库 `local_runner/`）

## 前置条件
1. 本地桌面机已安装并可运行 `codex` CLI（`codex` 在 PATH 中可用）。
2. 本地桌面机能够访问 Wegent 服务器的 HTTP API（默认 `.../api`）。
3. 你在 Wegent 中已有一个 **Codex** Team/Bot（参见 `docs/guides/user/codex-shell.md`）。

## Step 1：准备一个专用 API Key（推荐）
Local Runner 通过 API Key 鉴权访问服务端接口。建议为 Runner 单独创建一个 personal API key（以 `wg-` 开头），并只在本机保存。

## Step 2：编写 Runner 配置文件

默认配置路径：`~/.wegent/local-runner.toml`

示例（请按需修改 `server_url/api_key/runner_id/workspaces.path`）：

```toml
server_url = "http://127.0.0.1:8000"
api_key = "wg-xxxxxxxxxxxxxxxx"
runner_id = "desktop-dev-1"
name = "开发机-桌面"
poll_interval_sec = 2.0
codex_cmd = "codex"

[[workspaces]]
id = "wegent"
name = "Wegent"
path = "/Users/you/work/Wegent"

[workspaces.policy]
dirty_mode = "reject"
max_artifact_mb = 50
```

约束：
- `workspaces.path` **只存在于本机配置**，不会上报到服务器，也不会写入数据库。
- `workspaces.id` 是你在 UI 中选择的 `local_workspace_id`，必须唯一且稳定。

## Step 3：启动 Local Runner

在本仓库目录下（或将 `local_runner/` 拷贝到你的桌面机）：

```bash
cd local_runner
uv run wegent-local-runner --config ~/.wegent/local-runner.toml
```

Runner 启动后会：
- 定期向服务器发送心跳（上报 runner 在线状态 + workspace 列表，**不包含路径**）
- 轮询领取分配给自己的 `type=local` 任务
- 在本机 workspace 目录中运行 `codex exec --json ...`
- 回传 `result.value` 流式输出与 `codex_events` 事件流
- 执行结束后生成并上传：
  - `patch.diff`（文本 diff）
  - `patch.diffbin`（二进制 diff）
  - 以及其它可选 artifact（后续可扩展）

## Step 4：在 Web UI 中选择 Runner + Workspace 并发起任务
1. 选择一个 **Codex** Team
2. 在输入框旁边选择：
   - 本地 Runner（在线优先）
   - 本地工作区（workspace）
3. 发送消息

服务端会将该任务标记为 `type=local` 并绑定 `localRunnerId/localWorkspaceId`，之后只会被对应 Runner 领取执行。

## 结果查看
- **流式输出**：正常显示在聊天消息中（`result.value`）
- **Codex 事件流**：消息下方的 `Codex 事件流` 面板可折叠查看（用于排查 tool call/执行细节）
- **本地 Runner 产物**：消息下方会展示 patch/artifact 下载链接，并可在线预览 `patch.diff`

## 常见问题

### 1) Web 看不到 Runner
- 确认 Runner 进程已运行且能访问 `server_url`
- 确认 `api_key` 有效且以 `wg-` 开头
- 确认服务器端数据库迁移已执行（包含 `local_runners` 表）

### 2) 任务一直 PENDING
- 确认你选择了 Runner + workspace
- 确认任务被创建为 `type=local`（本功能不会被 docker executor_manager 领取）
- 确认 Runner 的 `runner_id` 与任务绑定一致

### 3) Codex resume 失败
- Runner 会为同一 task 固定 `HOME=~/.wegent/runs/<task_id>/.home`，确保 `codex exec resume` 可找到会话存储
- 如果你手工清理了该目录，resume 可能失败；可以用“新会话重试”兜底

### 4) Workspace dirty 被拒绝
- 默认 `dirty_mode=reject`（避免在脏工作区上改代码）
- 如确实需要，调整 workspace policy 为 `dirty_mode=allow`

