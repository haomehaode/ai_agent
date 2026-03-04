import subprocess
from typing import Optional
from .base import BaseTool, ToolResult
from safety.guardrails import CommandFilter


class BashTool(BaseTool):
    name = "bash_exec"
    description = "在 shell 中执行命令，返回 stdout 和 stderr"
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "要执行的 shell 命令"},
            "timeout": {"type": "integer", "description": "超时秒数，默认30", "default": 30},
        },
        "required": ["command"],
    }

    def __init__(self, cmd_filter: CommandFilter, default_timeout: int = 30):
        self.cmd_filter = cmd_filter
        self.default_timeout = default_timeout

    def execute(self, command: str, timeout: Optional[int] = None) -> ToolResult:
        timeout = timeout or self.default_timeout
        blocked, reason = self.cmd_filter.check(command)
        if blocked:
            return ToolResult(content=f"命令被安全策略拒绝: {reason}", error=True)
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"
            return ToolResult(content=output or "(no output)", error=result.returncode != 0)
        except subprocess.TimeoutExpired:
            return ToolResult(content=f"命令超时（>{timeout}s）", error=True)
        except Exception as e:
            return ToolResult(content=str(e), error=True)
