"""技能相关工具：read_skill 用于读取技能的完整内容"""
from .base import BaseTool, ToolResult
from agent.skills import SkillRegistry


class ReadSkillTool(BaseTool):
    """加载技能内容。"""
    name = "read_skill"
    description = "加载指定技能的完整 SKILL.md 内容。当用户请求与 Skills 概览中某技能的 description 匹配时，先调用此工具获取完整指令、工作流与最佳实践，再执行。"
    parameters = {
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "技能名称，如 agent-browser、code-review、code-generator、git-helper",
            },
        },
        "required": ["skill_name"],
    }

    def __init__(self, registry: SkillRegistry):
        self._registry = registry

    def execute(self, skill_name: str) -> ToolResult:
        skill = self._registry.get_skill_by_name(skill_name.strip())
        if not skill:
            available = [s.name for s in self._registry.get_all_skills()]
            return ToolResult(
                content=f"未找到技能 '{skill_name}'。可用技能: {', '.join(available)}",
                error=True,
            )
        guide = self._registry.build_skill_guide(skill_name)
        return ToolResult(content=guide)
