"""The one connection from the agents to shop data: the campus-customs MCP server.

Agents never open the database themselves. They get MCP tools, and each role
gets only the tools on its allow-list (see each file in backend/agents/).
"""

from __future__ import annotations

import os
import sys

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.toolsets import FilteredToolset

from backend.config import MCP_SERVER_PATH

# Quiet server logs; pass a database override through (used for dry runs on a copy).
_env = {"FASTMCP_LOG_LEVEL": "WARNING"}
if "CAMPUS_CUSTOMS_DB" in os.environ:
    _env["CAMPUS_CUSTOMS_DB"] = os.environ["CAMPUS_CUSTOMS_DB"]

shop_mcp = MCPToolset(
    Client(StdioTransport(command=sys.executable, args=[str(MCP_SERVER_PATH)], env=_env)),
    id="campus-customs",
    max_retries=1,
)


def mcp_tools(allowed: set[str]) -> FilteredToolset:
    """The campus-customs tools one role is allowed to call, and no others."""
    return shop_mcp.filtered(lambda _ctx, tool_def: tool_def.name in allowed)
