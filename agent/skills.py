"""
Skills 系统：参考 Claude Code / Agent Skills 标准，实现渐进式披露。

- 始终加载：YAML frontmatter 的 name + description，~100 tokens/skill
- 触发时加载：SKILL.md 完整内容，通过 read_skill 工具或工具调用触发注入
- 格式：.claude/skills/<name>/SKILL.md，遵循 agentskills.io 规范
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict  # Python 3.9 兼容


@dataclass
class Skill:
    name: str
    description: str
    content: str          # SKILL.md body (去掉 frontmatter 之后的正文)
    path: str
    version: str = "1.0.0"
    allowed_tools: List[str] = None  # 该技能允许使用的工具列表


class SkillRegistry:
    """扫描 .claude/skills/ 目录，加载所有 SKILL.md 文件，被动提供技能信息。"""

    def __init__(self, skills_dir: str = ".claude/skills"):
        self.skills_dir = os.path.abspath(skills_dir)
        # Ensure the directory exists
        os.makedirs(self.skills_dir, exist_ok=True)
        self._skills: List[Skill] = []
        self._loaded = False

    def load(self) -> None:
        self._skills = []
        if not os.path.isdir(self.skills_dir):
            return
        for skill_md in Path(self.skills_dir).rglob("SKILL.md"):
            skill = self._parse(str(skill_md))
            if skill:
                self._skills.append(skill)
        self._loaded = True

    def _parse(self, path: str) -> Optional[Skill]:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError:
            return None

        # 解析 YAML frontmatter（简易解析，不引入额外依赖）
        fm: Dict[str, str] = {}
        body = text
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                fm_block = text[3:end].strip()
                body = text[end + 4:].strip()
                for line in fm_block.splitlines():
                    if ":" in line:
                        k, _, v = line.partition(":")
                        fm[k.strip()] = v.strip()

        name = fm.get("name", "")
        description = fm.get("description", "")
        if not name or not description:
            return None

        # 解析 allowed-tools 字段
        allowed_tools_str = fm.get("allowed-tools", "")
        allowed_tools = []
        if allowed_tools_str:
            # 解析格式：Bash(npx agent-browser:*), Bash(agent-browser:*)
            import re
            matches = re.findall(r'(\w+)\(([^)]*)\)', allowed_tools_str)
            allowed_tools = [f"{m[0]}({m[1]})" for m in matches]

        return Skill(
            name=name,
            description=description,
            content=body,
            path=path,
            version=fm.get("version", "1.0.0"),
            allowed_tools=allowed_tools,
        )

    def get_all_skills(self) -> List[Skill]:
        """获取所有已加载的技能（被动模式：不进行匹配）。"""
        if not self._loaded:
            self.load()
        return self._skills

    def get_skill_by_name(self, name: str) -> Optional[Skill]:
        """根据名称获取特定技能。"""
        if not self._loaded:
            self.load()
        for skill in self._skills:
            if skill.name == name:
                return skill
        return None

    def build_skills_overview(self) -> str:
        """构建 Skills 概览，始终注入 system prompt。"""
        if not self._loaded:
            self.load()
        if not self._skills:
            return ""

        lines = [
            "Skills",
            "",
            "当用户请求与某技能相关时：先调用 read_skill(skill_name) 获取完整指南，再按指南执行。",
            "",
        ]
        for s in self._skills:
            lines.append(f"- **{s.name}**：{s.description}")

        return "\n".join(lines)

    def build_skill_guide(self, skill_name: str) -> str:
        """构建特定技能的使用指南（按需调用，非自动注入）。"""
        skill = self.get_skill_by_name(skill_name)
        if not skill:
            return ""
        return f"\n## {skill.name} 使用指南\n\n{skill.content}"

    def list_skills(self) -> List[Dict]:
        if not self._loaded:
            self.load()
        return [{"name": s.name, "description": s.description[:80], "path": s.path,
                 "allowed_tools": s.allowed_tools} for s in self._skills]
