# AGENTS.md

Wegent 是开源的智能体团队操作系统。本文件是贡献者的中文速查卡，只列“必须先知道的规则与入口”，细节请查 docs。

---

## 重要约束（必读）
- 对话用中文；代码注释一律英文。
- 提交前必须跑对应测试；不得用 `--no-verify` 跳过钩子。
- 不提交任何密钥/令牌，配置放 `.env` 或部署环境。
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

## 基础工作流
- 分支：`<type>/<description>`，如 `feature/ghost-import`
- Commit：Conventional Commits，例 `feat(backend): add ghost import api`
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

**Last Updated**: 2025-12  
**Wegent Version**: 1.0.20
