# 01 - 模型设置：Provider 模型发现 + Probe

## 变更概述

为模型配置页补齐“上游模型列表发现”和“结构化探测（probe）”能力，主要面向 `openai` / `openai-responses` 两类 provider：

- 支持基于 `api_key + base_url(+custom_headers)` 调用上游 `/models` 拉取 `model_id` 列表
- 支持结构化 probe：按目标集合（`list_models` / `prompt_llm` / `embedding`）分别给出 `ok/latency/error`
- 前端展示 `base_url_resolved`（例如自动补齐 `/v1`），并对 `custom_headers` 做 JSON/类型校验

## 影响范围

- Backend
  - `POST /api/models/provider-models`
  - `POST /api/models/provider-probe`
- Frontend
  - 模型编辑弹窗：Provider 模型列表、probe 结果、resolved base_url 展示
  - `custom_headers` 校验（必须是 JSON object 且 value 为 string）

## 验收前置

- 已启动 Backend + Frontend（任意方式均可）。
- 准备：
  - 正向：一个可用的 OpenAI Key（或可访问的兼容 OpenAI `/v1/models` 的网关）。
  - 反向：任意无效 key（用于验证错误提示稳定性）。

## 验收步骤（建议逐条勾选）

- [ ] 进入“模型设置”，新建/编辑一个 LLM 模型，provider 选择 `openai` 或 `openai-responses`
- [ ] `base_url` 填写不带 `/v1` 的地址（例如 `https://api.openai.com`），确认页面展示“resolved base_url”为 `.../v1`
- [ ] 不填写 `api_key` 点击“获取模型列表/发现模型”，应提示 `api_key required`（前端直接拦截）
- [ ] 填写 `api_key` 后点击“获取模型列表/发现模型”，应获得模型下拉项（或提示为空但不报错）
- [ ] 将 `custom_headers` 填成非法 JSON（例如 `{"Authorization": 1}` 或缺括号），应提示 headers 非法并阻止请求
- [ ] 选择一个模型 `model_id`，点击“测试连接/Probe”
  - LLM：应至少看到 `list_models` 与 `prompt_llm` 检查结果
  - Embedding：应至少看到 `list_models` 与 `embedding` 检查结果
- [ ] 将 `api_key` 改为无效值再次 Probe，应提示失败且给出稳定错误信息（不崩溃、不空白）

## 预期结果

- Provider 模型发现/Probe 可用，错误提示稳定；`base_url` 规范化与 `custom_headers` 校验生效。

## 相关提交（关键）

- `a243a9c` feat(backend): [MSP-030] add provider models proxy
- `50088ee` feat(backend): [MSP-070] add provider probe endpoint
- `e939c02` feat(frontend): [MSP-040] show resolved base_url
- `7e419d5` feat(frontend): [MSP-050] fetch provider model IDs
- `3b3a0f2` feat(frontend): [MSP-060] show provider probe results

