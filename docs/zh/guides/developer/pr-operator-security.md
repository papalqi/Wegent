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

## 5.1 后端 PR Action Gateway（参考实现）

平台侧建议提供统一写操作入口并强制执行策略与审计（提示词不作为安全控制）。当前后端参考路由：

- `POST /api/pr/actions/create-pr`
  - Header：`Idempotency-Key: <string>`
  - Body：`{ repo_full_name, base_branch, head_branch, title, body, ... }`
  - 失败返回：HTTP 403 且 `detail` 为结构化对象（`code/message/audit_id`），便于前端与审计查询。

默认工具链建议：

- **读**：GitHub MCP `READ_ONLY` 模式（显式枚举 `GITHUB_TOOLSETS`）
- **写**：后端 PR Action Gateway（策略门禁 + 审计 + 幂等）

## 6. 密钥与敏感信息

- 禁止将任何 token/私钥写入日志、PR 描述、comment 或提交内容
- 所有输出必须经过敏感信息检测与脱敏（例如 GitHub PAT、GitLab token、SSH private key 片段）

## 7. 威胁模型（Threat Model）

### 7.1 主要威胁

- 令牌泄漏：token 被写入日志、错误栈、PR 描述/评论或被模型回显
- 越权写入：访问不在 allowlist 的 repo / 向受保护分支写入 / 以错误身份执行写操作
- 提示词注入：PR 描述/issue 内容诱导执行高危命令（例如上传密钥、修改安全策略）
- 供应链/执行面扩大：在执行环境中引入不受控依赖/脚本，导致任意代码执行
- 敏感信息进入 PR：将 `.env`、密钥、内部 URL、用户数据写入提交或 PR 文本

### 7.2 缓解措施（必须由平台/实现强制）

- 平台侧策略门禁：所有写操作必须通过 policy gate；提示词仅用于“如何做”，不作为“是否能做”的依据
- 最小权限：token 仅授予必要 repo 与必要 scope；优先使用短期 token（如 GitHub App installation token）替代长期 PAT
- 审计可追溯：所有写操作记录 user/team/task/repo/action/decision/rule codes；拒绝也要记录
- 统一脱敏：日志与模型输出对敏感模式进行掩码；错误输出禁止包含请求头/Authorization
- 执行隔离：在容器/临时目录中执行；限制可执行命令与网络出口（至少默认不允许访问非 git provider 域）

## 8. 安全基线（Security Baseline）

实现 PR Operator 必须满足以下基线条款：

1. **默认只读**：未显式开启写能力时，任何写操作必须被拒绝（create PR / push / comment 等）
2. **Repo Allowlist**：仅允许对配置的仓库执行写操作；跨 repo 写入必须拒绝并审计
3. **保护分支对齐**：禁止向受保护分支 push/force push；base 分支必须在允许列表
4. **结构化拒绝原因**：拒绝必须返回稳定的错误码与 rule code，便于前端与审计查询
5. **密钥零落盘**：token 不得持久化；任务结束后执行环境清理；日志与输出必须脱敏
6. **幂等与重试边界**：同一 intent 重试不能产生重复 PR；对外请求必须设置超时与上限重试
7. **可回滚/降级**：存在一键降级到只读的开关；降级后写操作立即不可用

## 9. 策略引擎（Policy Engine）配置与拒绝码

后端策略评估建议在“执行前”完成，且不依赖外部网络调用（性能与稳定性更可控）。当前实现以环境变量/配置为输入，支持组合以下规则：

- 开关与 allowlist：`PR_ACTION_WRITE_ENABLED`、`PR_ACTION_REPO_ALLOWLIST`、`PR_ACTION_BASE_BRANCH_ALLOWLIST`
- 分支命名：`PR_POLICY_HEAD_BRANCH_REGEX`
- Diff 阈值：`PR_POLICY_MAX_CHANGED_FILES`、`PR_POLICY_MAX_DIFF_LINES`
- 禁止路径：`PR_POLICY_FORBIDDEN_PATH_PATTERNS`
- 必须通过检查项：`PR_POLICY_REQUIRED_CHECKS`

常见拒绝码（`detail.code`）：

- `PR_WRITE_DISABLED` / `REPO_NOT_ALLOWED` / `BASE_NOT_ALLOWED`
- `HEAD_BRANCH_INVALID` / `DIFF_TOO_LARGE` / `FORBIDDEN_PATH_TOUCHED` / `REQUIRED_CHECKS_FAILED`

## 10. Executor 执行面收敛（参考实现）

为降低注入风险，Executor 侧建议对 PR 相关流程启用受限命令白名单（例如仅允许 `git/gh/glab`），并避免 `shell=True` 拼接；同时对 stdout/stderr 进行统一脱敏后再记录日志。
