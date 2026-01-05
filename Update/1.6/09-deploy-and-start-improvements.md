# 09 - 启动/部署：`.env.defaults` + 镜像策略 + `start.sh` 稳定性

## 变更概述

对本地/部署启动链路做了系统性增强，目标是“开箱即用 + 易诊断 + 更少因环境差异导致的失败”：

- 引入 `.env.defaults`：用于固定镜像版本/前缀的默认值，并支持多 `.env` 文件合并
- `start.sh` 支持按顺序读取：`.env.defaults` < `.env` < `.env.local` < 现有环境变量（不覆盖已设置环境变量）
- 支持 `WEGENT_PUBLIC_HOST=auto`：自动探测非 loopback IPv4
- Redis auth：支持 `REDIS_PASSWORD`，缺省时自动生成并写入 `.env.local`
- 新增 `./start.sh --dev`：前端开发模式（更适合本地调试）
- 端口占用处理更稳健：释放/kill 逻辑优化，`--help` 不再误触发清理退出

## 影响范围

- 根目录：`start.sh`、`.env.defaults`、`.env.example`、`docker-compose.yml`
- CI：镜像发布与 retag 逻辑（影响发布流程，不影响线上运行时功能）

## 验收前置

- 本地具备 Docker + Docker Compose
- 允许脚本写入 `.env.local`（用于自动生成 `REDIS_PASSWORD`）

## 验收步骤

- [ ] 直接执行 `./start.sh --help`：
  - [ ] 不应触发停服务/清理逻辑
- [ ] 删除/清空本地 `.env.local`，执行 `./start.sh --no-rag`：
  - [ ] 首次启动应自动生成 `REDIS_PASSWORD` 并写入 `.env.local`
  - [ ] docker-compose redis 容器应启用鉴权且服务正常
- [ ] 使用 `WEGENT_PUBLIC_HOST=auto` 启动：
  - [ ] 脚本输出中显示的 Public Host 不为 `localhost/127.0.0.1`
- [ ] 在端口被占用时启动（可手动占用一个端口模拟）：
  - [ ] 脚本应能给出明确提示并按策略释放/退出
- [ ] 执行 `./start.sh --dev`：
  - [ ] 前端应进入 dev 模式（热更新可用）

## 预期结果

- 启动链路对 `.env`、端口、Redis 密码、公网访问配置更健壮；在常见错误场景下提示清晰可定位。

## 相关提交（关键）

- `a275eec` feat(deploy): default to latest images and auto-detect GHCR prefix
- `a1244e4` feat(deploy): load .env files and pin images via .env.defaults
- `e1f0479` feat(start): allow overriding GHCR images
- `225ff9a` feat: support WEGENT_PUBLIC_HOST=auto and Redis auth
- `9f1a0a1` feat(start): add --dev option for frontend development mode
- `d8ea36a` fix(start): fallback to python3/uv when python is missing
- `3844ae3` fix(start): avoid shutdown on --help and free ports reliably
- `118584b` fix(start): fix port kill fallback logic

