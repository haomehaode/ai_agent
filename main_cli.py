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
    tools = [
        ReadFileTool(sanitizer),
        WriteFileTool(sanitizer),
        ListDirTool(sanitizer),
        BashTool(cmd_filter, config.bash_timeout_secs),
        SearchFilesTool(sanitizer),
        ReadSkillTool(skills_dir),
    ]
    return AgentLoop(tools, skills_dir=skills_dir)


def run_single(task: str, skills_dir: str = "skills") -> None:
    agent = build_agent(skills_dir)
    print(agent.run(task))


def run_interactive(skills_dir: str = "skills") -> None:
    agent = build_agent(skills_dir)
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
