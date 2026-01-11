# 前端 i18n 使用规范

## 基本准则
1. 只从 `@/hooks/useTranslation` 导入；不要直接用 `react-i18next`。
2. 每个文件使用单一命名空间：`useTranslation('<feature>')`，勿传数组。
3. 访问其他命名空间时显式前缀：`t('common:actions.save')`。
4. 当前命名空间键用点式：`t('actions.save')`、`t('title')`。
5. 新增文案写入对应命名空间文件：`src/i18n/locales/{lang}/{namespace}.json`。

## 反例
- `const { t } = useTranslation(['common', 'groups']);` → 会导致特定命名空间键缺失。
- `t('actions.save')` 当实际键在 `common` → 应改 `t('common:actions.save')`。

## 提交流程建议
- 新增键后同时补充中英文；若无英文需求可留空但键必须存在。
- 组件内新增文案先查 `common` 是否已有通用键，避免重复。

## 快速检查
- ESLint/TS 报未找到 key 时，确认命名空间文件已包含并被引入。
- 运行 `npm run lint` 与单元测试覆盖常用文案路径。
