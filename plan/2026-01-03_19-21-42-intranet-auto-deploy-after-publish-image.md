# 内网机器在 GitHub 镜像发布后自动重部署（基于 publish-image.yml）

## 目标
当仓库的 `.github/workflows/publish-image.yml` 触发并完成镜像发布（push 到 GHCR）后，让一台**位于内网**的部署机器能够“被通知”并自动执行重部署（拉取新镜像并重启服务）。

约束：内网机器不可被公网直接访问（GitHub 不能主动回调到内网 Webhook）。

## 总体方案选择
### 方案 A（推荐）：内网机作为 GitHub Actions self-hosted runner（内网主动出站）
GitHub 不需要访问内网机器；runner 会主动连接 GitHub 拉取作业。`publish-image.yml` 在发布完成后新增一个 `deploy` job，跑在该 runner 上执行部署命令。

优点：近实时、可审计（Actions 日志）、实现清晰、无需引入中继服务。  
缺点：需要维护 runner，必须做好最小权限与隔离。

### 方案 B（简单但非实时）：内网机定时轮询 GHCR 镜像 digest/tag
用 systemd timer/cron 每 N 分钟检查镜像是否更新，更新则重启服务。

优点：不改 GitHub 工作流也可做；缺点：延迟由轮询间隔决定、可观测性需要额外建设。

### 方案 C（较复杂）：公网中继 + 内网长连接
Webhook 发到公网中继（VPS/云函数），内网机器与中继保持长连接，由中继推送事件触发部署。

适用于已有统一消息/中控系统时，不作为首选落地路径。

## 前置条件（方案 A 必备）
1. **网络出站**：内网机器可访问：
   - `github.com`（runner 拉取作业）
   - `ghcr.io`（拉取容器镜像）
2. **镜像可拉取**：部署机器具备拉取目标镜像的权限：
   - 如果镜像/包是私有：需要 `docker login ghcr.io`（推荐使用一个最小权限 PAT：`read:packages`）
3. **部署方式确定**：内网机器上实际重部署命令与目录固定，例如：
   - `docker compose pull && docker compose up -d`
   - 或执行仓库内 `./start.sh --no-rag`（需注意环境变量覆盖与 `.env.defaults` 逻辑）
4. **安全隔离**：
   - runner 尽量使用专用用户、专用目录
   - runner 机器只做部署用途（避免作为共享开发机）

## 方案 A 落地步骤（建议顺序）
### 1) 配置 self-hosted runner（在内网机）
1. GitHub 仓库 → `Settings` → `Actions` → `Runners` → `New self-hosted runner`
2. 按页面给的命令在内网机安装并注册 runner
3. 给 runner 设置 label（示例：`wegent-intranet`），后续 workflow 通过 label 精确调度
4. 让 runner 以 systemd service 方式运行（保证机器重启后自动上线）

检查点：
- Actions 页面能看到 runner online
- runner 用户具备执行 Docker 的权限（通常需要加入 `docker` 组）

### 2) 准备部署脚本（在内网机）
目标：将“重部署”收敛成一个可重复执行的脚本（便于 workflow 调用与本地手动回滚/重试）。

建议脚本职责：
- 拉取镜像
- 重启服务（compose 或 start.sh）
- 输出必要的版本信息（镜像 tag / digest / 当前容器信息）

建议额外能力（可选）：
- 健康检查（例如 `docker compose ps` + HTTP 健康探测）
- 失败时保留日志与退出码，方便 Actions 直接判定失败

### 3) 修改 `publish-image.yml`：新增 deploy job（在仓库）
在镜像发布完成后新增 `deploy_intranet` job：
- `needs:` 依赖镜像发布成功的 job（避免发布失败还触发部署）
- `runs-on:` 使用 `self-hosted` + `wegent-intranet`（避免跑到其他 runner）
- `if:` 限制触发范围，建议至少满足之一：
  - 仅 `push` 到 `main`
  - 或仅 `push` tag：`vMAJOR.MINOR.PATCH`
  - 明确不在 `pull_request` 触发部署
- `permissions:` 最小化：
  - 不需要写仓库时就不给 `contents: write`
  - 如需使用 `GITHUB_TOKEN` 拉取私有包，需确认 `packages: read` 是否足够；不稳定时使用 PAT（`read:packages`）作为 secret
- `steps:` 执行部署脚本：
  - `docker login ghcr.io`（如需要）
  - `cd` 到部署目录
  - 运行脚本：`./deploy.sh` 或 `docker compose pull && docker compose up -d`

### 4) 加固与可观测性（建议）
- 为部署 job 增加环境锁（避免并发部署）：使用 `concurrency`（以环境名作为 key）
- 在部署脚本中打印：
  - 当前部署版本（镜像 tag/digest）
  - 关键容器状态（`docker ps` 过滤）
- 失败告警（可选）：
  - 如果企业有内网告警系统（邮件/IM/Webhook to 内部网关），在部署失败时通知

## 回滚策略（最少要具备）
1. **保留上一个可用 tag**：发布时保持稳定 tag（例如 `v1.2.3`）+ 可选 `latest`
2. **一键回滚命令**：明确如何切回旧 tag 并重启（或直接 `docker compose` 指定旧 tag）
3. **部署日志可追踪**：Actions 日志 + 机器本地日志（systemd/journal 或文件）

## 方案 B（轮询）最小落地（备选）
如果无法或不想引入 self-hosted runner：
- 使用 systemd timer/cron 定时执行：
  - `docker pull ghcr.io/<owner>/<image>:<tag>`
  - 比较 digest 是否变化，变化则 `docker compose up -d`
- 或使用 watchtower 监听特定容器并自动更新（注意私有仓库登录与更新策略）

## 需要确认的信息（用于最终定稿与实现）
1. 部署触发点：只在 tag `v*.*.*` 后部署，还是 `main` 每次发布都部署？
2. 内网机器部署命令：`docker compose` 还是 `./start.sh --no-rag`？
3. GHCR 镜像是否私有？如果私有，是否允许在内网机上配置一个只读 PAT（`read:packages`）？

