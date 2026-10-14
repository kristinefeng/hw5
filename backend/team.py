"""Run the Campus Customs agent team on tickets.

The API (backend/main.py) calls run_ticket(). It also works from the command
line, from the hw5/ folder:

    .venv/bin/python -m backend.team --ticket 101
    .venv/bin/python -m backend.team --all

Each ticket gets its own run_id and its own token budget, and starts with the
boss. Every step is appended to output/audit_trail.json. Point CAMPUS_CUSTOMS_DB
(and CAMPUS_CUSTOMS_AUDIT) at copies for a dry run that leaves the real files alone.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid

from pydantic_ai import UsageLimitExceeded

from backend.loop import run_agent
from backend.mcp_link import shop_mcp
from backend.models import TeamDeps, TicketDecision


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


async def run_ticket(ticket_id: int, run_id: str | None = None) -> TicketDecision | dict:
    """Run the team on one ticket, starting with the boss. Needs shop_mcp to be open."""
    deps = TeamDeps(run_id=run_id or new_run_id(), ticket_id=ticket_id, chain=["boss"])
    task = (
        f"Work ticket {ticket_id}. Start with get_today and get_ticket, bring in the "
        "specialists you need, record the outcome with update_ticket, and return your decision."
    )
    try:
        return await run_agent("boss", task, deps)
    except UsageLimitExceeded as exc:
        return {"ticket_id": ticket_id, "run_id": deps.run_id, "stopped": "token/request limit reached", "detail": str(exc)}


async def open_ticket_ids() -> list[int]:
    result = await shop_mcp.direct_call_tool("list_open_tickets", {})
    return [t["id"] for t in result["tickets"]]


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ticket", type=int, help="work one ticket by id")
    group.add_argument("--all", action="store_true", help="work every open ticket, oldest first")
    args = parser.parse_args()

    async with shop_mcp:  # one MCP server process shared by every agent
        ids = await open_ticket_ids() if args.all else [args.ticket]
        for ticket_id in ids:
            result = await run_ticket(ticket_id)
            body = result.model_dump(mode="json") if isinstance(result, TicketDecision) else result
            print(json.dumps(body, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
