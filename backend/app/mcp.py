"""Optional MCP client. Compile and startup must not depend on MCP servers."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import BaseTool

from app.config import Settings

logger = logging.getLogger(__name__)

FILESYSTEM_PACKAGE = "@modelcontextprotocol/server-filesystem"
FETCH_PACKAGE = "mcp-server-fetch"


def mcp_connections(workspace_dir: str) -> dict[str, dict[str, Any]]:
    """stdio configs for official filesystem + fetch MCP servers."""
    return {
        "filesystem": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", FILESYSTEM_PACKAGE, workspace_dir],
        },
        "fetch": {
            "transport": "stdio",
            "command": "uvx",
            "args": [FETCH_PACKAGE],
        },
    }


async def load_mcp_tools(settings: Settings, workspace_dir: str) -> list[BaseTool]:
    """Load MCP tools when enabled. Returns [] if disabled or servers are unavailable."""
    if not settings.mcp_enabled:
        return []
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        client = MultiServerMCPClient(
            mcp_connections(workspace_dir),
            tool_name_prefix=True,
        )
        tools = await client.get_tools()
        logger.info("loaded %s MCP tools", len(tools))
        return list(tools)
    except Exception:
        logger.exception("MCP servers unavailable; continuing without MCP tools")
        return []
