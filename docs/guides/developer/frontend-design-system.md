# 前端设计系统速查

定位：Calm UI（低饱和、低对比、留白充足、少阴影），主色 Teal `#14B8A6`。用于保证新组件与现有风格一致。

## 基础变量
```css
--color-bg-base: 255 255 255;
--color-bg-surface: 247 247 248;
--color-text-primary: 26 26 26;
--color-text-secondary: 102 102 102;
--color-primary: 20 184 166;
--color-border: 224 224 224;
--radius: 0.5rem;
```

常用 Tailwind 类：
- 背景：`bg-base`，卡片 `bg-surface border-border`
- 主按钮：`bg-primary text-white`
- 字色：`text-text-primary` / `text-text-secondary`

## 字体与层级
- H1: `text-xl font-semibold`
- H2: `text-lg font-semibold`
- Body: `text-sm`
- Small: `text-xs text-text-muted`

## 响应式断点
- Mobile: `max-width: 767px`
- Tablet: `768–1023px`
- Desktop: `min-width: 1024px`
辅助钩子：`useIsMobile()` / `useIsDesktop()`。

## 组件复用与目录
- 先查 `src/components/ui/`（shadcn/ui）和 `src/components/common/`。
- 功能组件放对应 `src/features/*/components/`，能组合勿复制。

## 设计小贴士
- 少用阴影，多用分隔线和留白。
- 控件圆角统一 `var(--radius)`。
- 交互动画少量、有目的（加载、分步进入），避免花哨微动效。

## Chat / Workbench 组件实践
- **任务状态与进度**：优先用 `status_phase/progress/progress_text` 驱动展示；组件参考 `frontend/src/features/tasks/components/chat/TaskExecutionStatusBanner.tsx`。
- **系统提示词展示**：默认折叠 + 可滚动 + 复制按钮，避免混入消息流；组件参考 `frontend/src/features/tasks/components/chat/SystemPromptPanel.tsx`。
- **文件变更 Diff**：避免硬编码 Tailwind 色值（如 `text-green-600/bg-red-50`），优先用 tokens（`text-success/bg-success/10` 等）与 UI 组件（`Card/Input/Tag/Button`）；实现参考 `frontend/src/features/tasks/components/message/DiffViewer.tsx`。
