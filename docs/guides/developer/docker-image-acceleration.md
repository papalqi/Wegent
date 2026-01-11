# Docker 镜像加速配置指南

当从 GitHub Container Registry (ghcr.io) 拉取镜像速度较慢时，可以通过配置 Docker 镜像加速器来提升下载速度。

## 方案 1: 配置 Docker 镜像加速器（推荐）

### macOS / Linux

编辑或创建 `~/.docker/daemon.json` 文件：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ],
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false
}
```

**注意**: `ghcr.io` 是 GitHub Container Registry，国内镜像加速器可能无法加速。如果仍然很慢，请参考方案 2。

### 重启 Docker

配置完成后，重启 Docker Desktop（macOS）或 Docker 服务：

```bash
# macOS: 通过 Docker Desktop 界面重启
# Linux:
sudo systemctl restart docker
```

## 方案 2: 使用代理（适用于 ghcr.io）

如果镜像加速器无法加速 `ghcr.io`，可以配置 Docker 使用代理：

### macOS / Linux

编辑 `~/.docker/config.json`：

```json
{
  "proxies": {
    "default": {
      "httpProxy": "http://127.0.0.1:7890",
      "httpsProxy": "http://127.0.0.1:7890",
      "noProxy": "localhost,127.0.0.1"
    }
  }
}
```

将 `7890` 替换为你的代理端口。

### 重启 Docker

配置完成后重启 Docker。

## 方案 3: 手动预拉取镜像

在启动前手动拉取镜像，可以避免启动脚本中的等待：

```bash
# 拉取 executor-manager 镜像
docker pull ghcr.io/papalqi/wegent-executor-manager:1.35.0

# 拉取 executor 镜像（如果需要）
docker pull ghcr.io/papalqi/wegent-executor:1.0.33-codex
```

## 方案 4: 使用本地构建的镜像

如果镜像拉取很慢，可以考虑本地构建镜像：

```bash
# 构建 executor-manager 镜像
cd /path/to/Wegent
docker build -f docker/executor_manager/Dockerfile -t ghcr.io/papalqi/wegent-executor-manager:1.35.0 .
```

## 验证配置

检查 Docker 配置是否生效：

```bash
# 查看 Docker 信息
docker info | grep -A 10 "Registry Mirrors"

# 测试拉取速度
time docker pull ghcr.io/papalqi/wegent-executor-manager:1.35.0
```

## 常见问题

### Q: 为什么镜像加速器对 ghcr.io 无效？

A: 国内镜像加速器主要加速 Docker Hub，对 GitHub Container Registry (ghcr.io) 的支持有限。建议使用代理或手动预拉取。

### Q: 如何检查镜像是否已存在本地？

A: 使用以下命令：

```bash
docker images | grep wegent-executor-manager
# 或
docker image inspect ghcr.io/papalqi/wegent-executor-manager:1.35.0
```

### Q: 如何清理未使用的镜像以节省空间？

A:

```bash
# 清理未使用的镜像
docker image prune -a

# 查看镜像占用空间
docker system df
```

