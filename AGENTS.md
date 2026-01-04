# AGENTS.md

Wegent 是开源的智能体团队操作系统。本文件是贡献者的中文速查卡，只列“必须先知道的规则与入口”，细节请查 docs。

---

## 重要约束（必读）
- 对话用中文；代码注释一律英文。
- 提交前必须跑对应测试；不得用 `--no-verify` 跳过钩子。
- 前端改动每次提交前必须执行 `cd frontend && npm run lint`，不得跳过。
- 大型功能性改动必须做回归测试（优先自动化 E2E；若无对应用例，则做交互式回归并保留证据：截图/控制台/网络请求）。
- 不提交任何密钥/令牌，配置放 `.env` 或部署环境。
- PR 只创建到 fork 仓库（如 `papalqi/Wegent`）；不要往 upstream（`wecode-ai/Wegent`）创建 PR（upstream 仅用于同步）。
- 先查是否有现成组件/工具，避免重复实现。

## 项目速览
- Backend：FastAPI + SQLAlchemy + MySQL
- Frontend：Next.js 15 + TS + React 19 + shadcn/ui
- Executor / Executor Manager：任务执行与编排（Docker）
- Shared：通用工具与加密

## 关键术语
- Team / 智能体（Agent）：用户可见代理
- Bot / 机器人（Bot）：Team 的构件  
  关系：Bot = Ghost(提示词) + Shell(环境) + Model；Team = 多个 Bot + 协作模式  
- API/数据库/代码用 CRD 名称（Team, Bot）；前端 i18n 用“智能体/机器人”或 Agent/Bot。

## ⚠️ Git 分支策略（强制执行）

**严格禁止直接推送到 main 分支！**

```
┌─────────────────────────────────────────────────────────┐
│              MAIN 分支（main）                          │
│  ✅ 仅接受来自 develop 的 PR                           │
│  ❌ 禁止直接推送                                        │
│  ✅ 代表生产环境代码                                    │
│  ✅ 受分支保护规则保护                                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ 仅接受 develop 的 PR
                     │
┌────────────────────┴────────────────────────────────────┐
│            DEVELOP 分支（develop）                      │
│  ✅ 开发集成分支                                        │
│  ✅ 接受 feature/fix/hotfix 分支的 PR                   │
│  ✅ 持续集成在此进行                                    │
│  ❌ 禁止推送未完成的功能                                │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ 接受功能分支的 PR
                     │
       ┌─────────────┼─────────────┐
       │             │             │
┌──────┴──────┐ ┌────┴─────┐ ┌─────┴──────┐
│ feature/*   │ │ fix/*    │ │ hotfix/*  │
│ 新功能      │ │ Bug修复  │ │ 紧急修复   │
└─────────────┘ └──────────┘ └────────────┘
```

**核心规则：**

1. **main 分支**
   - ❌ **严禁直接推送**任何内容
   - ✅ **只接受来自 develop 分支的 PR**
   - ✅ 所有发布标签从 main 创建
   - ✅ 由维护者管理

2. **develop 分支**
   - ❌ 不直接推送新功能
   - ✅ 接受所有功能分支的 PR
   - ✅ 集成测试在此进行
   - ✅ 始终保持可工作状态

3. **功能分支（feature/fix/hotfix）**
   - ✅ 从 develop 创建：`git checkout -b feature/xxx develop`
   - ✅ 完成后 PR 到 develop
   - ✅ 合并后删除分支

**正确工作流程：**
```bash
# 1. 更新 develop
git checkout develop && git pull origin develop

# 2. 创建功能分支
git checkout -b feature/new-feature develop

# 3. 开发并提交
git add . && git commit -m "feat: add feature"

# 4. 推送并创建 PR：feature/new-feature → develop
git push origin feature/new-feature

# 5. 合并后删除分支
git branch -d feature/new-feature
```

## 基础工作流
- 分支：`<type>/<description>`，如 `feature/ghost-import`（从 develop 创建，PR 回 develop）
- Commit：Conventional Commits，例 `feat(backend): add ghost import api`
- PR（镜像发布）：如需触发 `publish-image.yml`，合并到 `main` 的 PR 标题必须包含 `Changeset version bump`（否则会显示为 Skipped）。
- 必跑测试：
  - `cd backend && uv run pytest`
  - `cd executor && uv run pytest`
  - `cd executor_manager && uv run pytest`
  - `cd shared && uv run pytest`
  - `cd frontend && npm test`；E2E：`npm run test:e2e`
- 常用命令：
  - 启动：`docker-compose up -d`
  - Backend 格式：`black . && isort .`
  - Frontend 格式：`npm run format && npm run lint`
  - 迁移：`uv run alembic revision --autogenerate -m "<msg>" && uv run alembic upgrade head`

### 本地 start.sh 环境注意
- start.sh 读取顺序：`.env.defaults` < `.env` < `.env.local` < 现有环境变量；已有环境变量不会被文件覆盖。
- 若环境提前设置了 `WEGENT_EXECUTOR_IMAGE/WEGENT_EXECUTOR_VERSION/WEGENT_IMAGE_PREFIX`，可能指向不存在的 `ghcr.io/wecode-ai/wegent-executor:latest-codex`，导致 Executor Manager 健康检查超时。
- 处理方式：启动前 `unset WEGENT_EXECUTOR_IMAGE WEGENT_EXECUTOR_VERSION WEGENT_IMAGE_PREFIX`，或显式设为 `export WEGENT_EXECUTOR_IMAGE=ghcr.io/papalqi/wegent-executor:1.0.33-codex`，再运行 `./start.sh --no-rag`。

### 远程运维：systemd 持久化启动（SSH 断开不退出）
当你在远程 SSH 上运行 `./start.sh` 时，断开连接会导致脚本退出，进而触发脚本的 `cleanup`（会停止它启动的前后端进程与相关容器）。推荐用 systemd 托管启动。

- Unit 文件位置：`/etc/systemd/system/wegent.service`
- 行为等价于在仓库根目录执行：`./start.sh --no-rag`（如需 `--rag`/`--dev` 请修改 unit 的 `ExecStart`）
- 停止语义：`systemctl stop wegent.service` ≈ 前台运行时按 `Ctrl+C`（会触发脚本清理并停止全部组件）

常用命令：
```bash
systemctl status wegent.service
systemctl start wegent.service
systemctl restart wegent.service
systemctl stop wegent.service

# 开机自启/取消自启
systemctl enable wegent.service
systemctl disable wegent.service

# 查看实时日志（start.sh 的 stdout/stderr 都在这里）
journalctl -u wegent.service -f

# 修改 unit 后需要 reload
systemctl daemon-reload
```

### Docker 镜像 CI（publish-image.yml）
- 触发：合并到 main 的 PR（标题必须含 “Changeset version bump”）、推送标签 **`v*.*.*`（三段式版本）**、或手动 `workflow_dispatch`（可传 `version`、`base_ref`、`force_modules`）。
- 注意：`pull_request: closed` 会触发 workflow，但 PR 标题不含 “Changeset version bump” 时 Job 会被条件跳过（显示 Skipped）。
- 标签要求：只有 `vMAJOR.MINOR.PATCH` 形如 `v1.35.0` 才会被识别；`v1.35` 这类两段式不会触发构建。
- 逻辑：dorny/paths-filter 检测 backend/executor/executor_manager/frontend 目录变化；按需多架构 buildx 构建并推送到 GHCR `ghcr.io/<owner>/`，同时维护 `latest` 与 `${version}`（executor 还带 `${version}-codex` 和 `latest-codex`）。
- 无代码变更但打 tag：直接 imagetools retag 复用上一个版本；末尾自动更新 `.env.defaults` 中的镜像版本并推 PR（或在 tag 情况下尝试直接推送）。

## 必知编码规则
- 高内聚、低耦合；复杂模块优先拆分。
- 单文件 ≤ 1000 行；函数建议 ≤ 50 行。
- 先查-提取-复用，禁止复制粘贴重复逻辑。
- Python：PEP 8，Black 88 列，isort，类型标注；运行命令用 `uv run`。
- TypeScript：strict 模式，函数式组件，单引号、无分号；文件 kebab-case，类型放 `src/types/`。
- 组件复用：先查 `src/components/ui/`、`src/components/common/`、`src/features/*/components/`，能组合就不新建。

## 深入阅读（中文）
- 架构/CRD：`docs/zh/concepts/architecture.md`、`core-concepts.md`
- YAML 规范：`docs/zh/reference/yaml-specification.md`
- 技能系统：`docs/zh/concepts/skill-system.md`
- 前端设计系统：`docs/zh/guides/developer/frontend-design-system.md`
- 消息流 & useUnifiedMessages：`docs/zh/guides/developer/chat-message-flow.md`
- i18n 规范：`docs/zh/guides/developer/i18n-rules.md`
- WEB_SEARCH / MCP 配置：`docs/zh/guides/developer/config-web-search-and-mcp.md`
- 开发/测试/迁移：`docs/zh/guides/developer/{setup,testing,database-migrations}.md`

---

**Last Updated**: 2026-01  
**Wegent Version**: 1.0.20
