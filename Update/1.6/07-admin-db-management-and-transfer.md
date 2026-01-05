# 07 - 后台管理：数据库导入/导出（UI + API）& DB Transfer CLI

## 变更概述

新增数据库运维能力，覆盖“管理员 UI 直出 SQL dump / 导入 SQL dump”和“可移植 DB Transfer CLI（zip）”两条路径：

1) Admin UI（Web）
- `GET /api/admin/database/export`：导出 SQL 文件（下载）
- `POST /api/admin/database/import`：上传 `.sql` 并导入（带安全确认弹窗、大小/内容校验）

2) DB Transfer CLI（开发/运维脚本）
- 后端提供 `app.scripts.db_transfer`，支持导出/导入 zip（用于跨服务器迁移）
- 仓库根目录提供 wrapper：`scripts/db-export.sh`、`scripts/db-import.sh`

## 影响范围

- Backend：admin endpoints、数据库导入导出服务、db_transfer 脚本
- Frontend：Admin 页面新增 `database` tab（仅 admin 可见）
- Docs：新增数据库迁移说明

## 验收前置

- 已启动 Backend + Frontend
- 使用管理员账号登录（`role=admin`）
- 准备一个小体积 `.sql` 文件用于导入（建议先用导出得到）

## 验收步骤（Admin UI）

- [ ] 访问 Admin 页面并切换到 `Database` 标签
- [ ] 点击“导出”：
  - [ ] 浏览器下载 `.sql` 文件
  - [ ] toast 提示成功
- [ ] 点击“导入”并选择文件：
  - [ ] 选择非 `.sql` 文件应被拒绝并提示
  - [ ] 选择 `.sql` 文件后应弹出“危险操作”确认弹窗
  - [ ] 确认导入后应提示成功（包含文件名与大小 MB）

## 验收步骤（DB Transfer CLI）

- [ ] 在仓库根目录运行帮助（不要求真正导入生产库）：
  - [ ] `./scripts/db-export.sh --help`
  - [ ] `./scripts/db-import.sh --help`
- [ ] 在可控测试库中，执行一次导出与导入（按需）：
  - [ ] `./scripts/db-export.sh --out ./wegent-db-dump.zip`
  - [ ] `./scripts/db-import.sh --in ./wegent-db-dump.zip --force`

## 预期结果

- Admin UI 可完成导出/导入并有明确风险提示；CLI 可用于跨环境迁移，参数与文档一致。

## 相关提交（关键）

- `3ebb634` feat(admin): add database management functionality
- `ef29d29` feat(backend): add db import/export tooling

