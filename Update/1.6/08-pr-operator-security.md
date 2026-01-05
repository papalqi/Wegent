# 08 - PR Operator：PR Action Gateway + Policy + 审计 + 执行白名单

## 变更概述

为“PR Operator”类写操作提供平台侧安全收敛：

- Backend 增加 PR Action Gateway：
  - 统一写入口：`POST /api/pr/actions/create-pr`、`POST /api/pr/actions/update-pr`
  - 强制执行策略（Policy）+ 审计（Audit）+ 幂等（Idempotency-Key）
  - 写能力默认关闭（只读）
- Policy Engine 支持多类规则（allowlist、分支正则、diff 阈值、禁止路径、必跑 checks 等）
- Executor 侧收敛 PR 相关命令白名单并做脱敏（降低注入风险）

## 影响范围

- Backend：`pr_actions` endpoints、`pr_action_gateway`、`pr_policy`、审计表 `pr_action_audits`
- Executor：PR 相关命令白名单/脱敏
- Docs：PR Operator 安全执行规范与 runbook（验收口径）

## 验收前置

- 已启动 Backend（并完成数据库迁移，确保 `pr_action_audits` 表存在）
- 准备一个可用的 GitHub token（如要做“写开启”的正向链路验收）

## 验收步骤（默认只读）

- [ ] 确保未显式设置 `PR_ACTION_WRITE_ENABLED=true`（默认应为 false）
- [ ] 请求 `POST /api/pr/actions/create-pr`（Header 带 `Idempotency-Key`，Body 填必要字段）
  - [ ] 应返回 HTTP 403
  - [ ] `detail` 为结构化对象：包含 `code/message/audit_id`
  - [ ] `detail.code` 应为 `PR_WRITE_DISABLED`

## 验收步骤（开启写入的灰度/正向链路）

- [ ] 设置并重启 backend 以加载配置：
  - [ ] `PR_ACTION_WRITE_ENABLED=true`
  - [ ] `PR_ACTION_REPO_ALLOWLIST=<owner/repo,...>`
  - [ ] `PR_ACTION_BASE_BRANCH_ALLOWLIST=<main,release/*,...>`
- [ ] 对 allowlist 内 repo/base 发起 create-pr：
  - [ ] 返回 200，响应体包含 `audit_id/idempotency_key/pr_number/pr_url`
- [ ] 使用相同 `Idempotency-Key` 重试：
  - [ ] 不应创建重复 PR（返回同一结果或等价结果）
- [ ] 对非 allowlist repo/base：
  - [ ] 返回 403，`detail.code` 为 `REPO_NOT_ALLOWED` / `BASE_NOT_ALLOWED` 等稳定码

## 预期结果

- 默认只读时写请求稳定拒绝且产生审计；开启写入后在 allowlist 范围内闭环成功且具备幂等。

## 相关提交（关键）

- `9924575` feat(backend): [PRSAFE-050] PR Action Gateway（鉴权/策略/审计/幂等）
- `d1b8bb5` feat(backend): [PRSAFE-060] 可配置策略引擎（6类规则）
- `dc72ffe` feat(backend): [PRSAFE-030] pr-operator 模板与结构化契约
- `727d836` feat(executor): [PRSAFE-070] PR 相关命令白名单与脱敏
- `85c1351` fix(backend): avoid duplicate index in pr_action_audits
- `faa55a7` fix(backend): remove invalid MySQL TEXT default

