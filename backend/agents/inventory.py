"""Inventory agent: stock by SKU and size, shelf locations, and realistic restock timing from vendor lead times."""

from pydantic_ai import Agent

from backend.config import load_prompt
from backend.loop import delegate
from backend.mcp_link import mcp_tools
from backend.models import SpecialistReport, TeamDeps

MCP_TOOLS = {
    "get_today",
    "get_ticket",
    "check_stock",
    "check_all_sizes",
    "list_vendors",
    "get_invoice",
}

agent = Agent(
    name="inventory",
    instructions=load_prompt("inventory"),
    deps_type=TeamDeps,
    output_type=SpecialistReport,
    toolsets=[mcp_tools(MCP_TOOLS)],
    tools=[delegate],
    retries=2,
)
