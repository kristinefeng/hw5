"""Customer service agent: what the customer is told. Drafts replies and order options from real stock and list prices."""

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
    "get_pricing",
}

agent = Agent(
    name="customer_service",
    instructions=load_prompt("customer_service"),
    deps_type=TeamDeps,
    output_type=SpecialistReport,
    toolsets=[mcp_tools(MCP_TOOLS)],
    tools=[delegate],
    retries=2,
)
