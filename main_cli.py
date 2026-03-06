"""
AI Agent - 使用 OpenAI 兼容接口，具备 Claude Code 同等的文件/命令操作能力
"""
import argparse
from agent.config import config
from agent.core import AgentLoop, BASE_SYSTEM_PROMPT
from agent.conversation import ConversationHistory
from agent.skills import SkillRegistry
from safety.guardrails import PathSanitizer, CommandFilter
from tools.file_ops import ReadFileTool, WriteFileTool, ListDirTool
from tools.bash import BashTool
from tools.code_search import SearchFilesTool
from tools.skill_ops import ReadSkillTool


def build_agent(skills_dir: str = "skills") -> AgentLoop:
    sanitizer = PathSanitizer(config.allowed_path_list)
    cmd_filter = CommandFilter()
    skill_registry = SkillRegistry(skills_dir)
    skill_registry.load()
    local_tools = [
        ReadFileTool(sanitizer),
        WriteFileTool(sanitizer),
        ListDirTool(sanitizer),
        BashTool(cmd_filter, config.bash_timeout_secs),
        SearchFilesTool(sanitizer),
        ReadSkillTool(skill_registry),
    ]

    mcp_tools = []
    if config.mcp_enabled:
        from tools.mcp_loader import load_mcp_tools
        local_names = {t.name for t in local_tools}
        mcp_tools = load_mcp_tools(config.mcp_config_path, local_names)
        if mcp_tools:
            print(f"[MCP] Loaded {len(mcp_tools)} tool(s): {[t.name for t in mcp_tools]}")

    return AgentLoop(local_tools + mcp_tools, skill_registry=skill_registry)


def run_single(task: str, skills_dir: str = "skills") -> None:
    agent = build_agent(skills_dir)
    try:
        print(agent.run(task))
    finally:
        agent.close()


def run_interactive(skills_dir: str = "skills") -> None:
    agent = build_agent(skills_dir)
    try:
        history = ConversationHistory(system_prompt=BASE_SYSTEM_PROMPT)
        loaded = agent.skill_registry.list_skills()
        print(f"AI Agent 已启动，已加载 {len(loaded)} 个 Skills（输入 'exit' 退出，'skills' 列出技能，'reset' 重置对话）\n")
        while True:
            try:
                user_input = input("你: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n再见！")
                break
            if not user_input:
                continue
            if user_input.lower() == "exit":
                print("再见！")
                break
            if user_input.lower() == "reset":
                history = ConversationHistory(system_prompt=BASE_SYSTEM_PROMPT)
                print("对话已重置\n")
                continue
            if user_input.lower() == "skills":
                for s in agent.skill_registry.list_skills():
                    print(f"  [{s['name']}] {s['description']}")
                print()
                continue
            response = agent.run(user_input, history)
            print(f"\nAgent: {response}\n")
    finally:
        agent.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenAI 兼容接口 AI Agent")
    parser.add_argument("task", nargs="?", help="单次任务描述")
    parser.add_argument("-i", "--interactive", action="store_true", help="交互模式")
    parser.add_argument("--skills-dir", default="skills", help="Skills 目录路径，默认 skills/")
    parser.add_argument("--list-skills", action="store_true", help="列出所有已加载的 Skills")
    args = parser.parse_args()

    if args.list_skills:
        registry = SkillRegistry(args.skills_dir)
        registry.load()
        skills = registry.list_skills()
        print(f"共 {len(skills)} 个 Skills：")
        for s in skills:
            print(f"  [{s['name']}] {s['description']}")
        return

    if args.interactive or not args.task:
        run_interactive(args.skills_dir)
    else:
        run_single(args.task, args.skills_dir)


if __name__ == "__main__":
    main()
