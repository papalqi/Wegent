# 04 - 消息调试：逐条 Debug 面板 + Debug 去敏

## 变更概述

为每条消息增加“调试信息入口”，并对 debug payload 做去敏与健壮性增强：

- 每条消息右下角提供 Debug（🐞）按钮，弹出 compact key fields + 完整 JSON
- 提供复制按钮，便于快速收集现场信息
- debug payload 统一 sanitize（避免 token/敏感字段直出；同时避免类型不一致导致前端崩溃）

## 影响范围

- Frontend：消息气泡 `MessageDebugPanel` + `debug-sanitize` 工具

## 验收前置

- 已启动 Frontend
- 产生至少一条带 `debug` 字段的消息（通常为 AI 消息，或开启相关 debug 输出）

## 验收步骤

- [ ] 找到一条带 Debug 的消息（右侧出现 🐞 图标）
- [ ] 点击 🐞：
  - [ ] 弹窗展示 summary（如 `model=... · subtask=...`）
  - [ ] `Key Fields` 区域应有关键字段（如 model_id、subtask_id、latency_ms 等）
  - [ ] `Full JSON` 区域可滚动查看
- [ ] 点击复制按钮，应复制完整 JSON 到剪贴板
- [ ] 将 debug payload 人为构造为异常类型（例如部分字段为 number/array），页面不应报错或崩溃
- [ ] 若 debug 中包含疑似敏感字段（token/key/Authorization 等），应被去敏/裁剪（不应原样直出）

## 预期结果

- Debug 面板可用、可复制、对异常 payload 不崩溃，且具备基本去敏能力。

## 相关提交（关键）

- `9ccba84` feat(frontend): add per-message debug panel
- `faf8c5d` feat(frontend): compact debug popover for message panel
- `e5c4888` fix(frontend): type guard debug panel payload
- `945cb59` fix(frontend): harden debug payload sanitizer
- `94659ea` fix(frontend): fix debug sanitize type narrowing

