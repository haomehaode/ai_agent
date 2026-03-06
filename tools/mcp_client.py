"""
MCP 客户端：封装与 MCP 服务器的连接、工具发现和工具调用。

支持三种传输协议：
  - stdio：启动子进程，通过 stdin/stdout 通信
  - sse：连接 HTTP SSE 端点（GET 建立连接，需服务器先发 endpoint 事件）
  - streamable_http：Streamable HTTP（POST 请求），适用于 Google Stitch 等云端 MCP

使用专用后台线程运行 asyncio 事件循环，以提供同步 API，
避免与调用方可能存在的 asyncio 环境产生冲突。
"""

import asyncio
import logging
import threading
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx
import mcp.types as mcp_types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """单个 MCP 服务器的配置，对应 mcp_servers.json 中的一个条目。"""

    name: str
    transport: str = "stdio"
    # stdio 专用
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    # SSE 专用
    url: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    # 通用
    timeout: float = 10.0
    call_timeout: float = 30.0


@dataclass
class MCPToolInfo:
    """list_tools() 返回的工具描述。"""

    name: str
    description: str
    input_schema: Dict[str, Any]


class _AsyncRunner:
    """
    在专用守护线程中运行独立的 asyncio 事件循环，
    使同步代码可以安全地提交 coroutine 并等待结果。
    """

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, daemon=True, name="mcp-async")
        self._thread.start()

    def _run(self) -> None:
        self._loop.run_forever()

    def run(self, coro, timeout: float = 30.0):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)


# 模块级单例：进程内所有 MCPClient 共用一个事件循环线程
_runner = _AsyncRunner()


class MCPClient:
    """
    同步 MCP 客户端。

    用法::

        client = MCPClient(config)
        client.connect()
        tools = client.list_tools()
        text = client.call_tool("tool_name", {"arg": "value"})
        client.close()
    """

    def __init__(self, config: MCPServerConfig) -> None:
        self._config = config
        self._session: Optional[ClientSession] = None
        self._stack: Optional[AsyncExitStack] = None

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """连接服务器并完成 MCP 初始化握手。"""
        try:
            _runner.run(self._async_connect(), timeout=self._config.timeout + 5)
            logger.info(
                f"[MCP] Connected to '{self._config.name}' ({self._config.transport})"
            )
        except Exception as e:
            raise ConnectionError(
                f"[MCP] Failed to connect to server '{self._config.name}': {e}"
            ) from e

    def list_tools(self) -> List[MCPToolInfo]:
        """获取服务器提供的工具列表。"""
        if not self._session:
            raise RuntimeError(
                f"[MCP] Not connected to '{self._config.name}'. Call connect() first."
            )
        result = _runner.run(self._session.list_tools(), timeout=self._config.timeout)
        tools = []
        for t in result.tools:
            schema = (
                t.inputSchema.model_dump()
                if hasattr(t.inputSchema, "model_dump")
                else dict(t.inputSchema)
            )
            tools.append(
                MCPToolInfo(
                    name=t.name,
                    description=t.description or "",
                    input_schema=schema,
                )
            )
        return tools

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        调用指定工具，返回文本结果。
        多个 content 块以换行拼接；若服务器报告错误则结果前缀 "[MCP ERROR]"。
        """
        if not self._session:
            raise RuntimeError(f"[MCP] Not connected to '{self._config.name}'.")
        result = _runner.run(
            self._session.call_tool(tool_name, arguments=arguments),
            timeout=self._config.call_timeout,
        )
        parts: List[str] = []
        for block in result.content:
            if isinstance(block, mcp_types.TextContent):
                parts.append(block.text)
            elif isinstance(block, mcp_types.ImageContent):
                parts.append(f"[image: {block.mimeType}]")
            elif isinstance(block, mcp_types.EmbeddedResource):
                uri = getattr(block.resource, "uri", "unknown")
                parts.append(f"[resource: {uri}]")
            else:
                parts.append(str(block))
        text = "\n".join(parts) if parts else "(no content)"
        return f"[MCP ERROR] {text}" if result.isError else text

    def close(self) -> None:
        """关闭连接，释放资源。"""
        if self._stack:
            try:
                _runner.run(self._async_close(), timeout=5.0)
            except Exception as e:
                logger.warning(
                    f"[MCP] Error closing connection to '{self._config.name}': {e}"
                )
            finally:
                self._session = None
                self._stack = None

    # ------------------------------------------------------------------
    # 内部异步实现
    # ------------------------------------------------------------------

    async def _async_connect(self) -> None:
        stack = AsyncExitStack()
        try:
            if self._config.transport == "stdio":
                params = StdioServerParameters(
                    command=self._config.command,
                    args=self._config.args,
                    env=self._config.env or None,
                )
                read, write = await stack.enter_async_context(stdio_client(params))
            elif self._config.transport == "sse":
                read, write = await stack.enter_async_context(
                    sse_client(
                        url=self._config.url,
                        headers=self._config.headers or None,
                        timeout=self._config.timeout,
                    )
                )
            elif self._config.transport == "streamable_http":
                if not self._config.url:
                    raise ValueError("streamable_http transport requires 'url'")
                http_client = create_mcp_http_client(
                    headers=self._config.headers or None,
                    timeout=httpx.Timeout(
                        self._config.timeout,
                        read=300.0,
                    ),
                )
                await stack.enter_async_context(http_client)
                streams = await stack.enter_async_context(
                    streamable_http_client(
                        url=self._config.url,
                        http_client=http_client,
                    )
                )
                read, write = streams[0], streams[1]
            else:
                raise ValueError(f"Unknown transport: '{self._config.transport}'")

            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self._session = session
            self._stack = stack
        except Exception:
            await stack.aclose()
            raise

    async def _async_close(self) -> None:
        if self._stack:
            await self._stack.aclose()
