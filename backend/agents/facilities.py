"""Facilities agent: the Chapel Street shop lease, the landlord, and rent notices."""

from pydantic_ai import Agent

from backend.config import load_prompt
from backend.loop import delegate
from backend.mcp_link import mcp_tools
from backend.models import SpecialistReport, TeamDeps

MCP_TOOLS = {
    "get_today",
    "get_ticket",
    "list_leases",
    "get_lease",
    "list_payments",
}

agent = Agent(
    name="facilities",
    instructions=load_prompt("facilities"),
    deps_type=TeamDeps,
    output_type=SpecialistReport,
    toolsets=[mcp_tools(MCP_TOOLS)],
    tools=[delegate],
    retries=2,
)
