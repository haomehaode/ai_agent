---
name: code-review
description: This skill should be used when the user asks to "review code", "code review", "check my code", "审查代码", "代码审查", "review this", or wants feedback on code quality, bugs, security issues, or best practices.
version: 1.0.0
allowed-tools: []
---

# Code Review Skill

## 审查维度

执行代码审查时，按以下维度逐一检查：

### 1. 正确性
- 逻辑是否有 bug
- 边界条件处理是否完整
- 错误处理是否充分

### 2. 安全性
- SQL 注入、XSS、命令注入等 OWASP Top 10
- 敏感信息（密钥、密码）是否硬编码
- 输入验证是否在系统边界执行

### 3. 性能
- 是否有 N+1 查询或不必要的循环
- 大数据集是否有分页或流式处理
- 是否有明显的内存泄漏风险

### 4. 可读性
- 变量/函数命名是否清晰
- 复杂逻辑是否有注释
- 函数是否单一职责

## 输出格式

```
## 代码审查报告

### 发现的问题
| 严重级别 | 位置 | 问题描述 | 建议 |
|----------|------|----------|------|
| 🔴 严重  | ...  | ...      | ...  |
| 🟡 警告  | ...  | ...      | ...  |
| 🔵 建议  | ...  | ...      | ...  |

### 整体评分：X/10
### 总结
```
