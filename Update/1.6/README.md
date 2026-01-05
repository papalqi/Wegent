# Wegent 1.6 更新验收清单（develop 近 3 天）

> 统计时间：2026-01-02 03:00:51 +0800 ～ 2026-01-05 10:25:45 +0800  
> 分支：`develop`  
> 提交范围：`44b8561..85c1351`

本目录将 `develop` 分支近 3 天内的**功能性变更**按主题拆分为可逐条验收的条目（每个条目 1 个文件）。

## 验收条目（按功能拆分）

1. `01-model-settings-models-probe.md`：模型设置 - Provider 模型发现 + Probe
2. `02-shell-public-clone-and-base-image.md`：执行环境（Shell）- 公共 Shell 展示 + 从公共复制
3. `03-task-status-phase-timeline.md`：任务状态 - status_phase/progress_text 贯通 + 阶段耗时展示
4. `04-message-debug-panel-and-sanitize.md`：消息调试 - 逐条 Debug 面板 + Debug 去敏
5. `05-codex-event-stream.md`：Codex 事件流 - 持久化 + UI 展示 + 完成后保留
6. `06-task-container-status.md`：任务容器状态 - container-status API + 顶栏/侧边栏徽标
7. `07-admin-db-management-and-transfer.md`：后台管理 - 数据库导入/导出（UI + API）& DB Transfer CLI
8. `08-pr-operator-security.md`：PR Operator - PR Action Gateway + Policy + 审计 + 执行白名单
9. `09-deploy-and-start-improvements.md`：启动/部署 - `.env.defaults` + 镜像策略 + `start.sh` 稳定性
10. `10-devx-tests-and-hooks.md`：开发体验 - Windows 测试/Mock 修复 + hooks/e2e 稳定性

## 追溯

- 原始提交列表（用于对照）：`raw-commits.md`

