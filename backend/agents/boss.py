"""Boss agent: owns each ticket end to end, routes work to the specialists, records the outcome, and lists what needs a human."""

from pydantic_ai import Agent

from backend.config import load_prompt
from backend.loop import delegate
from backend.mcp_link import mcp_tools
from backend.models import TicketDecision, TeamDeps

MCP_TOOLS = {
    "get_today",
    "list_open_tickets",
    "get_ticket",
    "update_ticket",
}

agent = Agent(
    name="boss",
    instructions=load_prompt("boss"),
    deps_type=TeamDeps,
    output_type=TicketDecision,
    toolsets=[mcp_tools(MCP_TOOLS)],
    tools=[delegate],
    retries=2,
)
