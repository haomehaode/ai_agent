---
name: code-generator
description: This skill should be used when the user asks to "generate code", "write code", "create a function", "implement", "写代码", "生成代码", "帮我实现", "写一个函数", "写一个类", "写一个脚本", or needs new code written from scratch for any programming task.
version: 1.0.0
allowed-tools: []
---

# Code Generator Skill

## 生成原则

1. **先理解，再生成**：生成前明确需求——语言、框架、输入输出、边界条件
2. **最小可用**：只写完成任务所需的代码，不添加未要求的功能
3. **安全优先**：不生成含注入漏洞、硬编码密钥、不安全反序列化的代码
4. **可读性**：变量/函数命名清晰，复杂逻辑加注释

## 生成流程

1. 识别目标语言和运行环境
2. 确定函数签名 / 类接口
3. 实现核心逻辑
4. 添加错误处理（仅系统边界处）
5. 给出使用示例

## 输出格式

```
### 实现

\`\`\`<language>
<代码>
\`\`\`

### 使用示例

\`\`\`<language>
<调用示例>
\`\`\`

### 说明（可选）
- 关键设计决策
- 已知限制
```

## 各语言规范速查

| 语言 | 命名风格 | 类型注解 | 错误处理 |
|------|----------|----------|----------|
| Python | snake_case | 必须加 type hints | 异常 |
| TypeScript | camelCase | 严格类型，禁用 any | 异常 / Result |
| Go | camelCase | 内置 | 多返回值 error |
| Java | camelCase | 内置 | 受检异常 |

## 禁止生成的模式

- `eval()` / `exec()` 执行动态字符串
- 拼接 SQL 字符串（改用参数化查询）
- `shell=True` + 用户输入（命令注入风险）
- 硬编码 API Key / 密码（改用环境变量）
