---
mode: plan
cwd: /root/project/Wegentdev
task: 重构模型设置：自动检索 /models 选择模型、地址拼接展示、支持更多接口、用完整 prompt 做端口/模型检测并展示结果
complexity: complex
planning_method: builtin
created_at: 2026-01-02T18:13:24+08:00
---

# Plan: Model 设置重构（/models 自动检索 + Prompt 探测）

🎯 任务概述
- 当前 Model 设置里 `model_id` 主要依赖预置列表/手输，不利于对接 OpenAI-compatible 等自建服务。
- 目标是在不牺牲密钥安全的前提下：自动从上游的 `/models` 拉取可选模型；`base_url` 支持不填 `/v1` 且 UI 展示最终拼接后的请求地址；探测不再只是连通性，而是对关键接口做最小可重复的 prompt/请求校验，并在前端明确显示 OK/Fail。

📋 执行计划
1. Git 准备与范围确认
   - 操作：`git checkout main && git pull`，创建分支 `feature/model-settings-models-probe`（命名可按实际需求调整）。
   - 明确兼容策略：已存量的 `Model.spec.modelConfig.env.base_url`/`model_id` 不做破坏性迁移；新增能力尽量“向后兼容 + 可渐进启用”。

2. 现状梳理与复用点定位（避免重复实现）
   - 前端：确认 Model 设置入口与编辑弹窗（`frontend/src/features/settings/components/ModelEditDialog.tsx`）的现状：
     - `base_url` 目前默认要求 OpenAI 填到 `/v1`。
     - `model_id` 基于预置常量（如 `OPENAI_MODEL_OPTIONS`）+ `Custom...`。
     - “测试连接”调用 `POST /models/test-connection` 但 UI 仅 Toast，无持久状态展示。
   - 后端：确认已有聚合模型列表与测试接口（`backend/app/api/endpoints/adapter/models.py`）：
     - `GET /models/unified`（列 Wegent 内部模型资源/公共模型，不等于上游 provider 的 `/models`）。
     - `POST /models/test-connection` 当前对 LLM/Embedding 有真实请求；对 `tts/stt/rerank` 仍是“配置成功”占位。

3. 设计：上游 Provider 能力探测 API（后端新增，前端统一调用）
   - 新增后端接口（建议新增，不直接扩展旧接口返回结构以降低破坏面）：
     - `POST /models/provider-models`：输入 `{ provider_type, base_url, api_key, custom_headers }`，返回上游可选 `model_ids[]`（核心满足“自动检索 /models”）。
     - `POST /models/provider-probe`：输入 `{ provider_type, base_url, api_key, model_id?, custom_headers, probe_targets[] }`，返回结构化结果：
       - `base_url_resolved`（最终拼接后的地址）
       - `checks: { list_models, prompt_llm, embed, rerank, ... }` 每项含 `ok:boolean`, `latency_ms`, `error?`
   - 约束：所有上游请求由后端发起，避免前端直连导致 CORS/泄露 `api_key`。

4. 设计：`base_url` 归一化与“最终拼接地址展示”规则
   - 前端展示：用户输入 `base_url_input` 后，实时展示只读的 `base_url_resolved`（例如：
     - 输入 `https://api.openai.com` => 展示 `https://api.openai.com/v1`
     - 输入 `http://localhost:8000` => 展示 `http://localhost:8000/v1`
     - 输入 `http://localhost:8000/v1/` => 展示 `http://localhost:8000/v1`
   - 后端兜底：对 OpenAI-compatible `provider_type`（`openai` / `openai-responses` / embedding 走 openai 协议）统一做 `rstrip('/')` + “必要时补 `/v1`” 归一化，避免仅靠前端。
   - 协议差异：Anthropic/Gemini 等不强行补 `/v1`，仅 `rstrip('/')` 并在 UI 清晰提示“不同协议的默认路径不同”。

5. 前端重构：`model_id` 改为可检索选择（带回退）
   - 在 `ModelEditDialog` 中将 `model_id` 输入拆为：
     - “获取模型列表”按钮/自动拉取（触发 `POST /models/provider-models`），并支持搜索过滤；
     - 下拉选择 `model_id`（从上游列表选）；
     - 保留 `Custom...` 手输作为兜底（上游禁用 `/models` 或权限不足时仍可配置）。
   - i18n：新增/复用文案（如“已解析地址”“拉取模型列表失败”“使用自定义模型 ID”等）。

6. 前端增强：端口/模型检测改为“完整请求”并展示 OK 状态
   - 将“测试连接”升级为结构化探测：
     - 针对 LLM：发送一个可判定的 prompt（例如 system 指令“只输出 OK”+ `temperature=0`），校验响应包含 `OK`（容错：去空白/大小写）。
     - 针对 Embedding：固定输入 `"test"`，校验返回向量维度>0。
     - 针对 Rerank（如走 Cohere/Jina/自定义）：若暂不支持真实请求，UI 明确标注“未实现探测/需要手动验证”，不要返回 `success=true` 误导。
   - UI 呈现：在弹窗内展示每项 check 的状态（✅/❌ + 耗时 + 错误摘要），而不是只靠 Toast。

7. 后端实现：补齐 provider_type/接口覆盖（满足“更多接口，不一定是 chat”）
   - 扩展 `provider_type` 支持：前端类型与后端保持一致（至少包含 `openai-responses`）。
   - 探测覆盖面建议：
     - OpenAI-compatible：`GET /models`、`POST /chat/completions`（或 `POST /responses`）以及（可选）`POST /embeddings`。
     - 其他 provider：根据现有 LangChain 适配能力，优先保证“最小可验证请求”。
   - 可观测性：为探测请求增加超时（例如 10s）、错误分类（鉴权失败/模型不存在/不支持的端点/网络错误）。

8. 测试与回归
   - 后端：为新接口补单测（模拟请求/用 stub），并跑 `cd backend && uv run pytest`。
   - 前端：补 `ModelEditDialog` 的关键交互测试（至少：地址解析展示、拉取列表失败回退、探测结果渲染），并跑 `cd frontend && npm test`。
   - 回归：创建/编辑模型、保存后列表展示正常；`ModelList` 的“Test Connection”仍可用（或同步升级到新探测接口）。

9. 文档与发布注意
   - 更新开发文档/提示：说明 `base_url` 可不带 `/v1`、探测会实际发请求（可能计费）。
   - 若探测会触发计费：在 UI/文档中提示并允许用户手动触发（不要在输入时自动频繁请求）。

⚠️ 风险与注意事项
- 计费/速率限制：探测是“真实请求”，必须默认手动触发，并控制频率/超时。
- 兼容性：不同 OpenAI-compatible 服务对 `/models`、`/responses`、`/chat/completions` 支持不一致，需要“多策略探测 + 结果解释”。
- 安全：`api_key` 仅在后端使用；日志中严禁输出明文密钥（包括异常堆栈/请求体）。
- i18n：新增文案需同步中英文（或至少保证默认语言不出现 key）。

📎 参考
- `frontend/src/features/settings/components/ModelEditDialog.tsx:1`
- `frontend/src/apis/models.ts:1`
- `backend/app/api/endpoints/adapter/models.py:1`
- `frontend/src/features/settings/components/ModelList.tsx:1`
