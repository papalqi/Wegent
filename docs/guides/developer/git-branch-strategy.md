# Git 分支策略（强制执行）

本文件用于承载原本在 `AGENTS.md` 里的 Git 分支策略说明，避免让通用协作约束过长。

## 核心规则

1. **main 分支**
   - ✅ 通常只接受来自 `develop` 分支的 PR（允许修复类变更）
   - ✅ 所有发布标签从 `main` 创建
   - ✅ 由维护者管理

2. **develop 分支**
  - ❌ 不直接推送新功能（修复内容允许直接提交，不需要新开分支）
  - ✅ 接受所有功能分支的 PR
  - ✅ 集成测试在此进行
  - ✅ 始终保持可工作状态

3. **功能分支（feature/fix/hotfix）**
   - ✅ 从 `develop` 创建：`git checkout -b feature/xxx develop`
   - ✅ 完成后 PR 到 `develop`
   - ✅ 合并后删除分支

注意：如果当前在 `develop` 分支，且只是修 bug，可以直接提交到 `develop`。

## 正确工作流程

```bash
# 1. 更新 develop
git checkout develop && git pull origin develop

# 2. 创建功能分支
git checkout -b feature/new-feature develop

# 3. 开发并提交
git add . && git commit -m "feat: add feature"

# 4. 推送并创建 PR：feature/new-feature → develop
git push origin feature/new-feature

# 5. 合并后删除分支
git branch -d feature/new-feature
```
