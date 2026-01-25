# AGENTS.md

Wegent 是开源的智能体团队操作系统。

---
## 重要约束（必读）
- 对话用中文；代码注释一律英文。
- 提交前必须跑对应测试；不得用 `--no-verify` 跳过钩子。
- 不提交任何密钥/令牌，配置放 `.env` 或部署环境。
- 先查是否有现成组件/工具，避免重复实现。

## 自我回归和学习
AGENTS.md 的更新是提升 AI 编程效率的重要流程：当你遇到问题、走弯路，或总结出稳定可复用的方法时，应把结论沉淀下来，避免同类问题反复发生。

你需要遵守三条原则：

### 让 bug 修复产生长期价值
每次修复 bug 时，如果不能防止同类问题再次发生，就只完成了一半。修复时不要只改代码，问自己：
1. 这类问题能否通过添加 lint 规则来预防？
2. 是否应该在 AGENTS.md 中记录这个陷阱？
3. 能否编写一个测试来防止回归？
4. 代码审查清单是否需要更新？
5. 一个真正的 bug 修复应该让同类问题再也不会发生。

### 从代码审查中提取模式
每次你在审查中指出问题或提出建议，可以考虑：

- 这个反馈是否适用于未来的类似代码？
- 是否应该成为项目的编码规范或检查清单？
- 我如何修改 AGENTS.md 或沉淀成 Skill，让 Agent 下次自动应用这个改进？

### 建立可复用的工作流程
当你找到一个有效的工作模式时，把它沉淀为文档或 Skill，让团队可以复用、让自动化可以接管。


## 项目架构
- Backend：FastAPI + SQLAlchemy + MySQL
- Frontend：Next.js 15 + TS + React 19 + shadcn/ui
- Executor / Executor Manager：任务执行与编排（Docker）
- Shared：通用工具与加密

## 关键术语
- Team / 智能体（Agent）：用户可见代理
- Bot / 机器人（Bot）：Team 的构件  
  关系：Bot = Ghost(提示词) + Shell(环境) + Model；Team = 多个 Bot + 协作模式  
- API/数据库/代码用 CRD 名称（Team, Bot）；前端 i18n 用“智能体/机器人”或 Agent/Bot。

## 必知编码规则
- 高内聚、低耦合；复杂模块优先拆分。
- 单文件 ≤ 1000 行；函数建议 ≤ 50 行。
- 先查-提取-复用，禁止复制粘贴重复逻辑。
- Python：PEP 8，Black 88 列，isort，类型标注；运行命令用 `uv run`。
- 组件复用：先查 `src/components/ui/`、`src/components/common/`、`src/features/*/components/`，能组合就不新建。



## 开发测试

- 前端改动每次提交前必须执行 `cd frontend && npm run lint`，不得跳过。
- 大型功能性改动必须做回归测试（优先自动化 E2E；若无对应用例，则做交互式回归并保留证据：截图/控制台/网络请求）。

- 修改对应的代码后需要跑对应的测试：
  - `cd backend && uv run pytest`
  - `cd executor && uv run pytest`
  - `cd executor_manager && uv run pytest`
  - `cd shared && uv run pytest`
  - `cd frontend && npm test`；E2E：`npm run test:e2e`

## Systemd 常用命令（运维/排障）

> 默认服务名通常是 `wegent.service`（混合模式：`start.sh`）。如你的服务名不同，把下方命令里的服务名替换掉即可。

- 查看状态：`systemctl status wegent.service --no-pager`
- 启动/停止/重启：`sudo systemctl start|stop|restart wegent.service`
- 开机自启：`sudo systemctl enable|disable wegent.service`
- 重新加载 unit 文件：`sudo systemctl daemon-reload`（改了 `/etc/systemd/system/*.service` 后必做）
- 查看最近日志：`journalctl -u wegent.service -n 200 --no-pager`
- 实时跟踪日志：`journalctl -u wegent.service -f`
- 清理失败状态：`sudo systemctl reset-failed wegent.service`
- 查看 unit 内容：`systemctl cat wegent.service`
- 临时覆盖 unit 配置：`sudo systemctl edit wegent.service`（保存后执行 `daemon-reload` + `restart`）
- 快速确认端口：`ss -lntp | rg ':3000|:8000|:8001|:3306|:6379'`

## 深入阅读
- 架构/CRD：`docs/concepts/architecture.md`、`core-concepts.md`
- YAML 规范：`docs/reference/yaml-specification.md`
- 技能系统：`docs/concepts/skill-system.md`
- 前端设计系统：`docs/guides/developer/frontend-design-system.md`
- 消息流 & useUnifiedMessages：`docs/guides/developer/chat-message-flow.md`
- i18n 规范：`docs/guides/developer/i18n-rules.md`
- WEB_SEARCH / MCP 配置：`docs/guides/developer/config-web-search-and-mcp.md`
- Git 分支策略：`docs/guides/developer/git-branch-strategy.md`
- Docker 镜像发布与 CI，本地镜像环境变量：`docs/guides/developer/docker-image-ci.md`
- 开发/测试/迁移：`docs/guides/developer/{setup,testing,database-migrations}.md`

---

**Last Updated**: 2026-01  
**Wegent Version**: 1.0.20
