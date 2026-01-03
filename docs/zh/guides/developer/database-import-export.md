# 数据库导入/导出（迁移到不同服务器）

本项目后端提供一个可移植的数据库导入/导出 CLI，用于在不同 MySQL 服务器之间迁移数据（不依赖修改任何 Docker 配置）。

## 快速开始（本地 uv / backend/start.sh 场景）

在 `backend/` 目录下执行（会自动读取 `backend/.env` 或环境变量 `DATABASE_URL`）：

```bash
cd backend
uv run python -m app.scripts.db_transfer export --out ./wegent-db-dump.zip
uv run python -m app.scripts.db_transfer import --in ./wegent-db-dump.zip --force
```

## 快速开始（仓库根目录 ./start.sh 场景）

仓库根目录提供了包装脚本，会按 `start.sh` 相同顺序读取 `.env.defaults` / `.env` / `.env.local`（且不覆盖已存在的环境变量），并在未设置 `DATABASE_URL` 时自动拼出默认 MySQL 连接串。

```bash
./scripts/db-export.sh --out ./wegent-db-dump.zip
./scripts/db-import.sh --in ./wegent-db-dump.zip --force
```

## Docker Compose 场景

如果你是通过 `./start.sh`（仓库根目录）以 Docker Compose 启动，后端容器默认不挂载本地代码；建议在本机直接运行 CLI，并使用可访问的 `DATABASE_URL` 指向目标 MySQL。

示例（导出 compose 内的 MySQL）：

```bash
cd backend
export DATABASE_URL='mysql+pymysql://task_user:task_password@127.0.0.1:3306/task_manager'
uv run python -m app.scripts.db_transfer export --out ./wegent-db-dump.zip
```

## 常用参数

- `--database-url`：显式指定数据库连接串（优先级最高）
- `--chunk-size`：批量写入/读取的行数（默认 500）
- `export --exclude-table <name>`：导出时排除指定表（可重复）
- `import --create-db`：数据库不存在时自动创建（需要对应权限）
- `import --no-schema`：只导入数据，不执行建表语句（适合先手动 `alembic upgrade head` 的场景）
- `import --force`：覆盖导入（若目标库已有同名表则 drop/truncate 后再导入）
