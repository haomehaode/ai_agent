"""
RemoteMCPTool：将 MCP 服务器提供的工具包装为本地 BaseTool。

AgentLoop 会像对待本地工具一样对待 RemoteMCPTool：
  - to_openai_schema() 使用 MCP 工具的 inputSchema 生成工具描述
  - execute(**kwargs) 将调用转发给 MCPClient，同步返回 ToolResult
"""

import logging
from typing import Any, Dict, Optional

from .base import BaseTool, ToolResult
from .mcp_client import MCPClient, MCPToolInfo

logger = logging.getLogger(__name__)


class RemoteMCPTool(BaseTool):
    """将单个 MCP 工具包装为 BaseTool。"""

    def __init__(
        self,
        tool_info: MCPToolInfo,
        client: MCPClient,
        name_override: Optional[str] = None,
    ) -> None:
        """
        Args:
            tool_info: 从 MCP 服务器获取的工具描述
            client: 已连接的 MCPClient 实例
            name_override: 命名冲突时使用的替代名称，如 "server__toolname"
        """
        self.name = name_override or tool_info.name
        self.description = tool_info.description
        self.parameters: Dict[str, Any] = tool_info.input_schema
        self._original_name = tool_info.name  # 调用 MCP 时使用的真实名称
        self._client = client

    def execute(self, **kwargs) -> ToolResult:
        server_name = self._client._config.name
        try:
            content = self._client.call_tool(self._original_name, kwargs)
            is_error = content.startswith("[MCP ERROR]")
            return ToolResult(
                content=content,
                error=is_error,
                metadata={"source": "mcp", "server": server_name},
            )
        except TimeoutError as e:
            msg = str(e)
            logger.error(msg)
            return ToolResult(
                content=msg,
                error=True,
                metadata={"source": "mcp", "server": server_name},
            )
        except Exception as e:
            msg = f"[MCP] Tool '{self._original_name}' on '{server_name}' failed: {e}"
            logger.error(msg)
            return ToolResult(
                content=msg,
                error=True,
                metadata={"source": "mcp", "server": server_name},
            )

    def close(self) -> None:
        """关闭 MCP 连接，释放资源。"""
        self._client.close()
