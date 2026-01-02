# PR Operator 安全执行规范（Draft）

本规范定义 Wegent 平台内 “PR Operator” 智能体在仓库协作场景下允许执行的动作边界、默认拒绝项与验收口径，用于约束实现范围并支持审计与回归验证。

## 1. 名词

- PR：Pull Request（GitHub 等平台）
- MR：Merge Request（GitLab 等平台）
- 写操作：任何会改变远端仓库状态的动作（push、创建/更新 PR、评论、加标签等）
- 受保护分支：被仓库策略保护、禁止直接推送/强制推送的分支（如 `main`、`master`、`release/*`）

## 2. 默认允许/禁止动作矩阵

### 2.1 默认允许（在策略通过后）

- 创建工作分支（必须符合分支命名规则，如 `wegent-<...>`）
- 提交并推送到工作分支（禁止向受保护分支 push）
- 创建 PR（base 分支必须在 allowlist 中）
- 更新 PR 的标题/描述（描述必须经过敏感信息检测与脱敏）
- 请求 reviewer（reviewer 必须来自允许列表或组织成员）
- 添加 comment / label（可选；同样需敏感信息检查）

### 2.2 默认禁止（无条件拒绝）

- 合并 PR（merge/squash/rebase merge）与关闭保护策略
- 强制推送（force push）
- 直接向受保护分支写入（任何 `main/master/release/*` 等）
- 修改仓库配置（branch protection、webhook、actions secrets、deploy keys 等）
- 跨仓库/跨组织写入（不在 allowlist 的 repo）

## 3. 最小闭环（成功路径）

成功的最小闭环必须满足：

1. 在 allowlist 的仓库上创建工作分支
2. 在工作分支产生至少 1 个提交并推送
3. 创建 PR 并返回可追踪的信息（repo、base、head、PR URL、PR number）
4. 产生可追溯审计记录（见第 5 节）

## 4. 失败拦截点与提示语要求

失败必须在“执行前”被拦截并给出稳定、可机器解析的拒绝原因（例如 `POLICY_DENIED` + 具体 rule code）。典型失败场景：

- repo 不在 allowlist
- base 分支不允许
- 分支命名不符合规则
- diff 超过阈值/触碰禁止路径
- 检查项（本地/CI）未通过
- token 缺失或权限不足

## 5. 审计字段（必须齐全）

每个写操作至少记录以下字段（存储位置由实现决定，但必须可查询/可关联到任务与用户）：

- user_id / team_id / task_id
- provider（github/gitlab/...）与 git_domain
- repo（owner/name）与 base/head 分支
- action（create_branch/push/create_pr/update_pr/request_review/...）
- decision（allowed/denied）与 rule codes（denied 时必须有）
- request_id / idempotency_key（如有）
- pr_number / pr_url（PR 相关动作时）
- created_at（ISO8601）

## 6. 密钥与敏感信息

- 禁止将任何 token/私钥写入日志、PR 描述、comment 或提交内容
- 所有输出必须经过敏感信息检测与脱敏（例如 GitHub PAT、GitLab token、SSH private key 片段）

