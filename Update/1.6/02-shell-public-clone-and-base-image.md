# 02 - 执行环境（Shell）：公共 Shell 展示 + 从公共复制

## 变更概述

对“执行环境（Shell）管理”做了一轮可用性增强：

- 公共 Shell 列表支持展示 `executionType`、`baseImage` 等关键信息
- `baseImage` 支持一键复制到剪贴板（点击标签）
- 对 `local_engine` 类型的公共 Shell，支持“从公共复制”快速创建个人/组内 Shell（带预填）

## 影响范围

- Frontend：设置页 Shell 列表与编辑弹窗
- Backend：公共 shells 初始数据/默认镜像指向调整（影响“开箱即用”体验）

## 验收前置

- 已启动 Backend + Frontend
- 系统中存在公共 Shell（初始化数据已导入）

## 验收步骤

- [ ] 进入“设置 → Shells（执行环境）”
- [ ] 在“公共 Shell”区域，检查每条公共 Shell 卡片包含：
  - [ ] `shellType` 标签
  - [ ] `executionType` 标签（如 `Local Engine`）
  - [ ] `baseImage` 标签（较长时应可 hover 查看完整）
- [ ] 点击 `baseImage` 标签，应出现“已复制”toast，且剪贴板内容为该镜像字符串
- [ ] 对 `executionType=local_engine` 的公共 Shell：
  - [ ] 点击“从公共复制”（双页 icon）
  - [ ] 弹窗打开后应自动预填：`name`（以 `-custom` 结尾）、`baseShellRef`、`baseImage`

## 预期结果

- 公共 Shell 信息清晰；复制/从公共创建流程顺畅且无报错。

## 相关提交（关键）

- `804884e` fix(frontend): improve executor image display and allow cloning public executors
- `7c4df1f` chore(backend): point public shells to papalqi executor image

