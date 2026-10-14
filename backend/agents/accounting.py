"""Accounting agent: cash, vendor invoices, payment history, pricing and margins. Recommends payments; never makes them."""

from pydantic_ai import Agent

from backend.config import load_prompt
from backend.loop import delegate
from backend.mcp_link import mcp_tools
from backend.models import SpecialistReport, TeamDeps

MCP_TOOLS = {
    "get_today",
    "get_ticket",
    "get_cash_balance",
    "get_invoice",
    "list_open_invoices",
    "list_payments",
    "get_pricing",
    "list_leases",
    "get_lease",
}

agent = Agent(
    name="accounting",
    instructions=load_prompt("accounting"),
    deps_type=TeamDeps,
    output_type=SpecialistReport,
    toolsets=[mcp_tools(MCP_TOOLS)],
    tools=[delegate],
    retries=2,
)
