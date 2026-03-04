# AI Agent

通用 AI 助手，支持文件操作、命令执行、代码搜索，以及基于 Skills 的渐进式披露。

## 特性

- **通用助手**：文件操作、命令执行、代码搜索
- **Skills 渐进式披露**：通过 `read_skill` 按需加载技能，内容经工具调用历史传递
- **安全防护**：路径白名单、危险命令过滤
- **OpenAI 兼容**：支持任意 OpenAI 兼容 API

## 项目结构

```
ai_agent/
├── agent/                 # 核心逻辑
│   ├── config.py          # 配置（model、max_iterations、allowed_paths 等）
│   ├── core.py            # AgentLoop、API 调用、工具分发
│   ├── conversation.py    # 对话历史、上下文截断
│   └── skills.py          # SkillRegistry、SKILL.md 解析
├── tools/                 # 工具实现
│   ├── file_ops.py        # read_file, write_file, list_dir
│   ├── bash.py            # bash_exec
│   ├── code_search.py     # search_files（regex/glob）
│   └── skill_ops.py        # read_skill
├── safety/
│   └── guardrails.py      # PathSanitizer、CommandFilter
├── skills/                # 技能目录（可用 --skills-dir skills 指定）
│   ├── agent-browser/
│   ├── code-generator/
│   ├── code-review/
│   └── git-helper/
├── logs/                  # 运行日志
├── main_cli.py            # 入口
├── run.sh                 # 快捷启动（交互模式）
└── requirements.txt
```

## 安装

```bash
cd ai_agent
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 配置

创建 `.env`：

```
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_ID=gpt-4o
```

可选：`ALLOWED_PATHS`（默认 `.`）、`MAX_ITERATIONS`（默认 20）、`BASH_TIMEOUT_SECS`（默认 30）。

## 使用

```bash
# 交互模式（推荐）
./run.sh
# 或
python main_cli.py -i

# 单次任务
python main_cli.py "打开百度搜索刘德华"

# 使用项目根目录 skills/
python main_cli.py --skills-dir skills -i

# 列出已加载技能
python main_cli.py --list-skills
```

交互模式命令：`skills` 列出技能、`reset` 重置对话、`exit` 退出。

## 技能系统

### 渐进式披露

1. **Level 1**：系统提示中仅包含技能 name 与 description
2. **Level 2**：用户请求与某技能相关时，调用 `read_skill(skill_name)` 获取完整 SKILL.md
3. **传递**：技能内容通过工具调用结果进入对话历史，不注入系统提示词

### 内置技能

| 技能 | 用途 |
|------|------|
| agent-browser | 浏览器自动化：打开网页、表单填写、截图等 |
| code-generator | 代码生成 |
| code-review | 代码审查 |
| git-helper | Git 操作 |

### 添加技能

在 `skills/<name>/` 下创建 `SKILL.md`：

```markdown
---
name: my-skill
description: 何时使用此技能（含触发词）
---

# 使用说明
...
```

## 日志

日志写入 `logs/agent_YYYYMMDD_HHMMSS.log`：

- 对话开始：用户输入、系统提示词
- 迭代 N：完成原因、token、工具调用
- 工具执行：参数与结果（长结果截断）
- 对话结束：最终回复

```bash
# 实时查看最新日志
ls -t logs/agent_*.log | head -1 | xargs tail -f
```

## 安全

- **路径**：仅允许 `ALLOWED_PATHS` 内的文件操作
- **命令**：过滤 `rm -rf /`、`dd`、`curl pipe bash` 等危险命令

## 许可证

MIT
