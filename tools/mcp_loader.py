"""
MCP 工具加载器：读取 mcp_servers.json，连接各服务器，返回 RemoteMCPTool 列表。

支持的传输协议（与官方 MCP 规范一致）：
  - stdio：本地子进程，command + args（如 npx -y @modelcontextprotocol/server-filesystem）
  - streamable_http：远程 HTTP，url + headers（如 Google Stitch），当前推荐
  - sse：旧版 HTTP+SSE，url + headers，用于兼容老服务器

未指定 transport 时：有 url 无 command → streamable_http，否则 → stdio。

命名冲突策略：
  1. 本地工具名优先
  2. MCP 工具与本地工具同名时，重命名为 "<server_name>__<tool_name>"
  3. 跨 MCP 服务器同名时，同样加前缀
"""

import json
import logging
import os
from typing import Dict, List, Optional, Set

from .base import BaseTool
from .mcp_client import MCPClient, MCPServerConfig
from .mcp_tool import RemoteMCPTool

logger = logging.getLogger(__name__)


def _parse_config(path: str) -> List[MCPServerConfig]:
    """解析 mcp_servers.json，返回 MCPServerConfig 列表。文件不存在时返回空列表。"""
    if not os.path.exists(path):
        logger.debug(f"[MCP] Config file not found at '{path}', skipping MCP tools.")
        return []
    try:
        with open(path, encoding="utf-8") as f:
            raw: dict = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"[MCP] Failed to parse '{path}': {e}")
        return []

    configs: List[MCPServerConfig] = []
    for name, entry in raw.get("mcpServers", {}).items():
        try:
            # 有 url 无 command 时默认用 streamable_http（如 Stitch）
            transport = entry.get("transport")
            if transport is None:
                transport = "streamable_http" if entry.get("url") and not entry.get("command") else "stdio"
            configs.append(
                MCPServerConfig(
                    name=name,
                    transport=transport,
                    command=entry.get("command"),
                    args=entry.get("args", []),
                    env=entry.get("env", {}),
                    url=entry.get("url"),
                    headers=entry.get("headers", {}),
                    timeout=float(entry.get("timeout", 10.0)),
                    call_timeout=float(entry.get("call_timeout", 30.0)),
                )
            )
        except Exception as e:
            logger.error(f"[MCP] Invalid config for server '{name}': {e}")
    return configs


def load_mcp_tools(
    config_path: str,
    existing_tool_names: Optional[Set[str]] = None,
) -> List[BaseTool]:
    """
    加载所有 MCP 服务器的工具，返回 RemoteMCPTool 列表。

    Args:
        config_path: mcp_servers.json 的路径
        existing_tool_names: 已有本地工具名集合，用于冲突检测

    Returns:
        成功加载的 RemoteMCPTool 列表（连接失败的服务器会跳过，不影响整体）
    """
    existing_tool_names = existing_tool_names or set()
    server_configs = _parse_config(config_path)
    if not server_configs:
        return []

    all_tools: List[BaseTool] = []
    seen_names: Set[str] = set(existing_tool_names)

    for cfg in server_configs:
        client = MCPClient(cfg)
        try:
            client.connect()
        except ConnectionError as e:
            logger.warning(f"[MCP] Skipping server '{cfg.name}': {e}")
            continue

        try:
            tool_infos = client.list_tools()
        except Exception as e:
            logger.warning(f"[MCP] Could not list tools for '{cfg.name}': {e}")
            client.close()
            continue

        for info in tool_infos:
            name_override: Optional[str] = None
            if info.name in seen_names:
                name_override = f"{cfg.name}__{info.name}"
                logger.warning(
                    f"[MCP] Name conflict: '{info.name}' from '{cfg.name}' "
                    f"renamed to '{name_override}'"
                )

            final_name = name_override or info.name
            seen_names.add(final_name)
            all_tools.append(RemoteMCPTool(info, client, name_override=name_override))
            logger.info(f"[MCP] Loaded tool '{final_name}' from '{cfg.name}'")

    return all_tools
