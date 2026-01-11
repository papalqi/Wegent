---
name: wegent-add-model-agent
description: Add a new LLM Model and a new Agent (Team/Bot/Ghost) in Wegent without starting the frontend UI. Use when asked to "不启动前端新增/添加模型/智能体/机器人/Team/Bot" or when bootstrapping Model+Team resources via `wegent-cli` (Kind API under `/api/v1/namespaces/...`).
---

# Wegent Add Model & Agent（无需启动前端）

目标：在**不启动 Next.js 前端**的情况下，通过 Wegent 后端 API 写入资源（Model/Ghost/Bot/Team），让“模型”和“智能体（Team）”可用。

## 快速开始（推荐）

1) 安装/使用 CLI（`wegent-cli`）并登录：
- `cd wegent-cli && pip install -e .`
- `wegent config set server http://localhost:8000`
- `wegent login`

2) 生成资源包（本 skill 自带脚本，输出 JSON 数组；`wegent apply` 用 YAML 解析器可直接读取 JSON）：
- `python3 .codex/skills/wegent-add-model-agent/scripts/generate_resources.py --team-name my-team --model-name my-model --model-id gpt-4o-mini --api-key-env OPENAI_API_KEY --out /tmp/wegent-resources.json`

3) 应用资源包到指定 namespace：
- `wegent apply -f /tmp/wegent-resources.json -n default`

4) 验证：
- `wegent get models`
- `wegent get bots`
- `wegent get teams`

## 工作流（按顺序）

### 1) 明确你要新增的“模型”和“智能体”分别是什么

- “模型”对应 `Model` 资源（CRD：`kind: Model`）
- “智能体”通常对应 `Team` 资源（CRD：`kind: Team`），并且至少需要一个 `Bot` + `Ghost`
- `Shell` 一般可复用内置的公共 Shell：`Chat` / `Codex` / `ClaudeCode` / `Agno` / `Dify`

### 2) 生成 Model/Ghost/Bot/Team 资源包

优先用脚本生成，避免手写字段出错（尤其是 `modelConfig.env`）：

- 必填：`--team-name --model-name --model-id`
- 推荐：用 `--api-key-env OPENAI_API_KEY` 存占位符 `${OPENAI_API_KEY}`，避免把明文 key 写进 DB/文件
- 可选：`--provider openai|claude|gemini|...`（默认 `openai`）
- 可选：`--shell-name Chat|Codex|ClaudeCode|Agno|Dify`（默认 `Chat`）

### 3) 通过 CLI 写入（无需启动前端）

`wegent apply` 会调用后端 Kind API（`/api/v1/namespaces/...`）创建或更新资源：

- `wegent apply -f /tmp/wegent-resources.json -n default`

### 4) 验证资源是否生效

建议至少验证：

- 资源存在：`wegent get models/bots/teams`
- Shell 是否存在：`wegent get shells`

### 5) 安全与常见坑

- 不要把包含 `api_key` 的资源文件提交到 Git；建议放在临时目录（如 `/tmp`）并及时清理。
- Model 里真正会被解析的结构是 `spec.modelConfig.env`（例如 `env.api_key/env.model_id/env.base_url/env.model`）。
- 如果用 `${ENV_VAR}` 占位符：确保**后端进程（以及需要时 executor 容器）**真的有该环境变量。

