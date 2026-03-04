import json
import logging
import os
import datetime
from typing import Any, Optional, List
from openai import OpenAI
from .conversation import ConversationHistory
from .config import config
from .skills import SkillRegistry
from tools.base import BaseTool, ToolResult

# 设置日志
def setup_logging():
    """设置日志配置，只写入带时间戳的日志文件，不显示在控制台"""
    # 创建日志目录
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)

    # 创建 logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # 清除已有处理器
    logger.handlers.clear()

    # 创建带时间戳的日志文件处理器
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f'agent_{timestamp}.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 不添加控制台处理器，确保日志只写入文件

    return logger

logger = setup_logging()


BASE_SYSTEM_PROMPT = """

你是一个通用 AI 助手，具备文件操作、命令执行、代码搜索等能力。

始终用中文回答。

"""

class AgentLoop:
    def __init__(self, tools: list[BaseTool], skills_dir: str = ".claude/skills"):
        self.client = OpenAI(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
        )
        self.tools = {t.name: t for t in tools}
        self.tool_schemas = [t.to_openai_schema() for t in tools]
        self.skill_registry = SkillRegistry(skills_dir)
        self.skill_registry.load()

    def run(self, user_input: str, history: Optional[ConversationHistory] = None) -> str:
        # 始终注入 Skills 概览，让 Agent 知道有哪些 Skills（回答「你有哪些技能」时能正确列出）
        skills_overview = self.skill_registry.build_skills_overview()
        base_system_prompt = BASE_SYSTEM_PROMPT + skills_overview

        if history is None:
            history = ConversationHistory(system_prompt=base_system_prompt)
        else:
            history.system_prompt = base_system_prompt

        history.add_user(user_input)

        # 一轮对话开始：只记录一次
        logger.info("=" * 60)
        logger.info("=== 对话开始 ===")
        logger.info("=" * 60)
        logger.info(f"用户输入: {user_input}")
        logger.info(f"系统提示词 ({len(base_system_prompt)} 字符):")
        logger.info(base_system_prompt)
        logger.info("-" * 40)

        for iteration in range(config.max_iterations):
            history.truncate_if_needed(config.max_context_tokens)

            messages = history.get_messages()

            response = self.client.chat.completions.create(
                model=config.model_id,
                messages=messages,
                tools=self.tool_schemas,
                tool_choice="auto",
            )

            # 迭代 N：API 响应
            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            tool_calls = message.tool_calls or []

            logger.info(f"--- 迭代 {iteration + 1} ---")
            logger.info(f"完成原因: {finish_reason} | token: {response.usage.total_tokens if response.usage else '-'}")

            if tool_calls:
                for tc in tool_calls:
                    logger.info(f"  工具调用: {tc.function.name}({tc.function.arguments})")
            elif message.content:
                logger.info(f"最终回复: {message.content[:500]}{'...' if len(message.content) > 500 else ''}")


            history.add_assistant(message)

            if finish_reason == "stop" or not message.tool_calls:
                logger.info("=" * 60)
                logger.info("=== 对话结束 ===")
                return message.content or ""

            # Dispatch tool calls sequentially
            for tool_call in message.tool_calls:
                result = self._dispatch(tool_call.function.name, tool_call.function.arguments)
                history.add_tool_result(tool_call.id, tool_call.function.name, result.content)

        logger.info("=" * 60)
        logger.info("=== 对话结束（达到最大迭代次数）===")
        return "已达到最大迭代次数，任务可能未完成。"

    def _dispatch(self, name: str, arguments_json: str) -> ToolResult:
        tool = self.tools.get(name)
        if not tool:
            logger.error(f"未知工具: {name}")
            return ToolResult(content=f"未知工具: {name}", error=True)
        try:
            kwargs: dict[str, Any] = json.loads(arguments_json)
            result = tool.execute(**kwargs)
            # 工具执行结果：超过 400 字符截断，避免 read_skill 等大结果刷屏
            content = result.content
            if len(content) > 400:
                logger.info(f"工具执行: {name}({kwargs}) → 共 {len(content)} 字符")
                logger.info(f"  结果预览: {content[:400]}...")
            else:
                logger.info(f"工具执行: {name}({kwargs})")
                logger.info(f"  结果: {content}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"参数解析失败: {e}")
            return ToolResult(content=f"参数解析失败: {e}", error=True)
        except Exception as e:
            logger.error(f"工具执行错误: {e}")
            return ToolResult(content=f"工具执行错误: {e}", error=True)
