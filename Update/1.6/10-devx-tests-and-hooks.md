# 10 - 开发体验：Windows 测试/Mock 修复 + hooks/e2e 稳定性

## 变更概述

这一组变更主要面向“开发与回归效率”，不直接改变业务功能，但会显著影响日常验收/CI 稳定性：

- 修复 Windows 下 tests/mocks 不工作的兼容性问题
- hooks：后端相关检查改为通过 `uv` 运行，避免环境差异
- 前端 e2e：稳定 settings 相关用例与 mock 捕获

## 建议验收方式

- [ ] Windows 环境下跑基础测试（按需选择模块）：
  - [ ] `cd backend && uv run pytest`
  - [ ] `cd executor && uv run pytest`
  - [ ] `cd executor_manager && uv run pytest`
  - [ ] `cd shared && uv run pytest`
- [ ] 前端：
  - [ ] `cd frontend && npm test`
  - [ ] `cd frontend && npm run lint`
  - [ ] 如有 UI 回归需求：`cd frontend && npm run test:e2e`

## 预期结果

- Windows 下单测/Mock 不再失败；hooks 与 e2e 结果更稳定，便于后续 1.6 大版本回归。

## 相关提交（关键）

- `1c16acd` fix: make tests and mocks work on windows
- `4297235` fix(hooks): run backend checks via uv
- `8228337` fix(frontend-e2e): stabilize settings and mock capture

