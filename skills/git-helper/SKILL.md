---
name: git-helper
description: This skill should be used when the user asks about "git", "commit", "branch", "merge", "rebase", "pull request", "git操作", "提交", "分支", "合并", or needs help with version control workflows.
version: 1.0.0
allowed-tools: [Bash(git:*)]
---

# Git Helper Skill

## 常用工作流

### 功能开发流程
```bash
git checkout -b feature/your-feature  # 新建功能分支
# ... 开发 ...
git add -p                             # 交互式暂存（推荐，避免误提交）
git commit -m "feat: 描述变更"
git push -u origin feature/your-feature
```

### Commit Message 规范（Conventional Commits）
```
<type>(<scope>): <description>

type: feat | fix | docs | style | refactor | test | chore
```

### 常用紧急操作
- 撤销最后一次提交（保留修改）：`git reset --soft HEAD~1`
- 丢弃工作区修改：`git checkout -- <file>`
- 查看某文件历史：`git log -p -- <file>`
- 找回误删的提交：`git reflog`

## 执行 Git 操作的原则

1. **破坏性操作前先确认**：`reset --hard`、`force push` 等需用户二次确认
2. **优先非破坏性方案**：用 `revert` 代替 `reset`，用 `--force-with-lease` 代替 `--force`
3. **不跳过钩子**：不使用 `--no-verify`
