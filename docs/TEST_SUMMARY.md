# Wegent 项目测试体系总结

## 项目概览

Wegent 是一个采用现代化 DevOps 实践的多服务架构项目，实现了完善的测试体系、Git hooks 自动化和 CI/CD 流水线。

---

## 一、测试体系

### 1.1 测试文件分布（共74个测试文件）

| 模块 | 测试目录 | 文件数 | 测试类型 |
|------|----------|--------|----------|
| **Backend** | `backend/tests/` | 37个 | API、服务层、模型、仓库层测试 |
| **Executor** | `executor/tests/` | 5个 | 代理测试 |
| **Executor Manager** | `executor_manager/tests/` | 9个 | 执行器测试 |
| **Shared** | `shared/tests/` | 4个 | 工具函数测试 |
| **Wegent CLI** | `wegent-cli/tests/` | 12个 | 单元测试 + 集成测试 |
| **Frontend** | `frontend/src/__tests__/` | 7个 | Jest单元测试 + Playwright E2E测试 |

### 1.2 测试框架栈

**Python 后端测试：**
- **主框架**: pytest >= 9.0.1
- **异步支持**: pytest-asyncio
- **覆盖率**: pytest-cov（上传到 Codecov）
- **并行执行**: pytest-xdist
- **Mock支持**: pytest-mock, pytest-httpx

**前端测试：**
- **单元测试**: Jest (jsdom环境)
- **E2E测试**: Playwright (Chrome为主)
- **测试分片**: 3个分片并行执行

### 1.3 测试配置文件

**pytest.ini 分布：**
- `backend/pytest.ini`
- `executor/pytest.ini`
- `executor_manager/pytest.ini`
- `shared/pytest.ini`
- `wegent-cli/pytest.ini`

**配置特点：**
```ini
[pytest]
testpaths = tests
pythonpath = ..
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --strict-markers --tb=short -n auto
asyncio_mode = auto
markers = unit, integration, slow, api
```

### 1.4 测试层次结构

1. **单元测试** - 各组件独立功能测试
2. **集成测试** - API端点、服务间交互
3. **E2E测试** - 前端到后端完整流程
4. **特殊测试** - 性能测试、视觉回归测试、API专项测试

---

## 二、Git Hooks 自动化

### 2.1 Hooks 管理方式

**前端使用 Husky：**
- `frontend/.husky/pre-commit` (4931字节)
- `frontend/.husky/pre-push` (372字节)
- `frontend/.husky/commit-msg`

**后端自定义脚本：**
- 位置：`scripts/hooks/`
- 包含：run-black.sh, run-isort.sh, check-merge-conflict.sh, check-alembic-heads.sh 等

### 2.2 Pre-commit 检查流程

**Python 文件处理：**
1. 检测暂存的 Python 文件
2. 使用 `uv run` 或 `python -m` 执行 black 格式化
3. 执行 isort 导入排序
4. 重新格式化并添加到暂存区

**前端文件处理：**
1. 运行 lint-staged 代码检查
2. 执行翻译文件检查（`find-missing-translations.js`）

**数据库迁移检查：**
1. 检查 Alembic 迁移文件
2. 运行 `check-alembic-heads.sh` 防止多 head 问题

### 2.3 Pre-push 检查（AI Push Gate）

**脚本：** `scripts/hooks/ai-push-gate.sh`

**检查内容：**
- 代码格式化检查
- 类型检查
- 单元测试
- 构建验证
- 文档更新检查

### 2.4 提交消息验证

**验证规则：**
```regex
^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\(.+\))?: .{1,}
```

**支持类型：** feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert

---

## 三、CI/CD 配置

### 3.1 GitHub Actions 工作流

**位置：** `.github/workflows/`

#### 3.1.1 测试工作流 (`test.yml`)

**触发条件：**
- 推送到 main, master, develop 分支
- 针对这些分支的 Pull Request

**测试矩阵：**
- Python: 3.10, 3.11
- Node.js: 18.x

**测试任务：**
1. `test-backend` - 后端 Python 服务（pytest + Codecov）
2. `test-executor` - 执行器服务（Python 3.10）
3. `test-executor-manager` - 执行器管理器（Python 3.11）
4. `test-shared` - 共享模块（Python 3.10）
5. `test-frontend` - 前端测试（Jest + 覆盖率）
6. `test-wegent-cli` - CLI 单元测试
7. `test-wegent-cli-integration` - CLI 集成测试（含 MySQL/Redis）
8. `test-summary` - 测试汇总

#### 3.1.2 E2E 测试工作流 (`e2e-tests.yml`)

**触发条件：**
- 推送到 main, develop 分支
- PR 到这些分支
- 每天凌晨 2 点（UTC）定时执行
- 支持手动触发

**特点：**
- **分片执行**: 3 个分片并行运行
- **服务依赖**: Docker Compose 提供 MySQL 和 Redis
- **完整环境**: Backend + Frontend + Mock Model Server
- **缓存策略**: Python 依赖和 Playwright 浏览器缓存
- **报告合并**: 自动合并所有分片的测试报告

**主要步骤：**
1. 检出代码并设置环境
2. 安装依赖（uv + npm）
3. 安装 Playwright 浏览器
4. 运行数据库迁移
5. 启动后端服务
6. 构建前端
7. 启动前端和 Mock 服务器
8. 运行分片 E2E 测试
9. 上传测试结果和日志

#### 3.1.3 发布工作流 (`release.yml`)

**触发条件：**
- 推送符合 `v*.*.*` 格式的标签
- 支持手动触发指定版本

**功能：**
- 自动生成 GitHub Release Notes
- 创建 GitHub Release

#### 3.1.4 Docker 镜像发布 (`publish-image.yml`)

**功能：**
- **智能构建**: 只构建发生变更的组件
- **多平台构建**: linux/amd64 + linux/arm64
- **版本管理**: 自动版本检测和补丁版本递增
- **镜像推送**: GitHub Container Registry (GHCR)
- **环境更新**: 自动更新 .env.defaults 和 docker-compose.yml

**组件镜像：**
- backend
- executor（支持 codex）
- executor_manager
- frontend

#### 3.1.5 贡献者更新 (`update-contributors.yml`)

**触发条件：**
- 每周日 00:00 UTC 定时执行
- 支持手动触发

**功能：** 自动更新 README.md 和 README_zh.md 中的贡献者列表

### 3.2 本地测试脚本

**脚本：** `scripts/run-e2e-local.sh`

**支持模式：**
- `run` - 标准运行
- `ui` - UI 模式
- `debug` - 调试模式
- `headed` - 有头模式
- `report` - 报告模式

**功能：**
- 启动所有必需的 Docker 服务
- 安装依赖
- 启动后端和前端服务
- 运行 E2E 测试

### 3.3 Docker 测试环境

**配置文件：** `docker-compose.e2e.yml`

**服务：**
- MySQL 8.0（端口 3307）
- Redis 7（端口 6380）
- 完整的 Backend 和 Frontend 服务

---

## 四、代码质量工具

### 4.1 Python 工具

**配置位置：** `backend/pyproject.toml`

**工具：**
- **Black** (>=23.7.0) - 代码格式化
  - line-length = 88
  - target-version = py310

- **isort** (>=5.12.0) - 导入排序
  - profile = "black"
  - line_length = 88

- **flake8** (>=6.0.0) - 代码检查

- **mypy** (>=1.5.0) - 类型检查

### 4.2 前端工具

**配置位置：** `frontend/package.json`

**工具：**
- **ESLint** (^9.17.0) - JavaScript/TypeScript 检查
- **Prettier** (^3.4.2) - 代码格式化
- **lint-staged** (^15.2.11) - 暂存文件检查
- **Husky** (^9.1.7) - Git hooks 管理

**lint-staged 配置：**
```json
"*.{js,jsx,ts,tsx,json,css,scss,md}": [
  "prettier --write",
  "eslint --fix"
]
```

---

## 五、关键文件路径汇总

### 5.1 Hooks 配置
- `frontend/.husky/pre-commit`
- `frontend/.husky/pre-push`
- `frontend/.husky/commit-msg`
- `scripts/hooks/ai-push-gate.sh`
- `scripts/hooks/check-alembic-heads.sh`

### 5.2 测试配置
- `backend/pytest.ini`
- `executor/pytest.ini`
- `executor_manager/pytest.ini`
- `shared/pytest.ini`
- `wegent-cli/pytest.ini`
- `frontend/jest.config.ts`
- `frontend/playwright.config.ts`

### 5.3 CI/CD 配置
- `.github/workflows/test.yml`
- `.github/workflows/e2e-tests.yml`
- `.github/workflows/release.yml`
- `.github/workflows/publish-image.yml`
- `.github/workflows/update-contributors.yml`

### 5.4 工具配置
- `backend/pyproject.toml`
- `frontend/package.json`
- `docker-compose.e2e.yml`

### 5.5 测试脚本
- `scripts/run-e2e-local.sh`
- `scripts/hooks/run-black.sh`
- `scripts/hooks/run-isort.sh`

---

## 六、体系特点总结

### 6.1 多层质量保证
1. **本地开发** - Pre-commit hooks（格式化、linting）
2. **推送前** - AI Push Gate（类型检查、单元测试、构建验证）
3. **CI/CD** - 完整的测试流水线（单元、集成、E2E）

### 6.2 自动化程度高
- 零配置体验（自动检测工具）
- 智能回退（UV 优先，fallback 到 python -m）
- 详细错误报告（彩色输出）
- 并行执行（pytest-xdist + Playwright 分片）

### 6.3 完整的测试覆盖
- **单元测试** - 所有 Python 模块 + 前端组件
- **集成测试** - API 端点 + 服务间交互
- **E2E 测试** - 完整用户流程
- **覆盖率追踪** - Codecov 集成

### 6.4 多语言支持
- Python 后端（Black + isort + flake8 + mypy）
- 前端（ESLint + Prettier + Jest + Playwright）

### 6.5 现代化 DevOps 实践
- 容器化部署（Docker + Docker Compose）
- 持续集成/持续部署（GitHub Actions）
- 多平台构建（amd64 + arm64）
- 自动化发布（语义化版本 + GitHub Release）

---

## 总结

Wegent 项目实现了一个**企业级的测试和自动化体系**，涵盖了：

1. ✅ **74个测试文件** 覆盖所有核心模块
2. ✅ **三层测试体系**（单元、集成、E2E）
3. ✅ **完整的 Git hooks**（pre-commit、pre-push、commit-msg）
4. ✅ **5个 GitHub Actions 工作流**（测试、E2E、发布、镜像、贡献者）
5. ✅ **多语言代码质量工具**（Python + JavaScript/TypeScript）
6. ✅ **容器化测试环境**（Docker Compose）
7. ✅ **智能并行执行**（pytest-xdist + Playwright 分片）
8. ✅ **自动化发布流程**（Docker 镜像 + GitHub Release）

这个体系确保了代码质量、开发效率和系统稳定性，是现代化软件工程的最佳实践典范。
