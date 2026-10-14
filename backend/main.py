"""Campus Customs API for the desk dashboard.

Start it from the backend/ folder (with hw5/.venv active):

    uvicorn main:app --reload --port 8000

Routes
  GET  /tickets                   every ticket, open or resolved, with its latest team run
  POST /tickets/{ticket_id}/run   start the agent team on one ticket (runs in the background)
  GET  /runs/{run_id}             a run's state and, when done, the boss's decision
  GET  /events                    recent agent events: what each agent said and which tools it used
  POST /payments/approve          a human approves a payment or purchase; the only route that moves cash
  GET  /payments                  payments recorded so far
  GET  /cash                      current checking balance from cash_accounts
  POST /reset                     put the working database back to the original values

When a run finishes, its ticket is marked resolved; the boss's own
recommendation and the approvals it asked for stay on the run. Runs are saved
to output/runs.json so pending approvals survive a server reload.

Shop facts are read through the campus-customs MCP server, the same one the
agents use. Approving a payment and resetting go through human_actions.py,
which no agent can reach.
"""

from __future__ import annotations

import asyncio
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

# `uvicorn main:app` runs from backend/, so put hw5/ on the path to import the backend package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from backend import audit  # noqa: E402
from backend.config import CORS_ORIGIN_REGEX, CORS_ORIGINS, RUNS_PATH  # noqa: E402
from backend.human_actions import ActionRefused, approve_payment, reset_database  # noqa: E402
from backend.mcp_link import shop_mcp  # noqa: E402
from backend.models import PaymentApproval, PaymentReceipt, RunInfo, TicketDecision  # noqa: E402
from backend.team import new_run_id, run_ticket  # noqa: E402

RUNS: dict[str, RunInfo] = {}  # every run since the last reset, saved to RUNS_PATH
_tasks: set[asyncio.Task] = set()  # keep references so running tasks aren't garbage-collected


def _save_runs() -> None:
    RUNS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = RUNS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps([r.model_dump(mode="json") for r in RUNS.values()], indent=2), encoding="utf-8")
    tmp.replace(RUNS_PATH)


def _load_runs() -> None:
    try:
        saved = json.loads(RUNS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return
    for raw in saved:
        run = RunInfo.model_validate(raw)
        if run.state == "running":  # the server stopped mid-run; that run can't finish now
            run.state, run.error, run.finished_at = "error", "Server restarted during the run.", audit.now()
        RUNS[run.run_id] = run


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _load_runs()
    async with shop_mcp:  # one MCP server process for the API and every agent run
        yield


app = FastAPI(title="Campus Customs desk API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _mcp(tool: str, **args: Any) -> dict:
    return await shop_mcp.direct_call_tool(tool, args)


def _running(ticket_id: int | None = None) -> list[RunInfo]:
    return [r for r in RUNS.values() if r.state == "running" and ticket_id in (None, r.ticket_id)]


def _latest_run(ticket_id: int) -> RunInfo | None:
    runs = [r for r in RUNS.values() if r.ticket_id == ticket_id]
    return max(runs, key=lambda r: r.started_at) if runs else None


# --- Tickets and runs ---------------------------------------------------------


@app.get("/tickets")
async def list_tickets() -> list[dict]:
    """Every ticket with its full status, an open/resolved flag, and its latest team run."""
    tickets = (await _mcp("list_tickets"))["tickets"]
    out = []
    for t in tickets:
        latest = _latest_run(t["id"])
        out.append(
            {
                **t,
                "state": "resolved" if t["status"] == "resolved" else "open",
                "running_run_id": next((r.run_id for r in _running(t["id"])), None),
                "latest_run": latest.model_dump(mode="json") if latest else None,
            }
        )
    return out


async def _mark_resolved(run: RunInfo) -> None:
    """The team finished, so the ticket is resolved; what the owner still has to sign stays on the run."""
    decision = run.decision or {}
    waiting = len(decision.get("approvals_needed", []))
    note = (
        f"Team run {run.run_id} finished. Boss recommended '{decision.get('status')}'"
        + (f"; {waiting} item(s) waiting for owner sign-off on the desk." if waiting else ".")
    )
    await _mcp("update_ticket", ticket_id=run.ticket_id, status="resolved", note=note, author="desk")


async def _work(run: RunInfo) -> None:
    try:
        result = await run_ticket(run.ticket_id, run.run_id)
        if isinstance(result, TicketDecision):
            run.state, run.decision = "done", result.model_dump(mode="json")
            await _mark_resolved(run)
        else:  # the team hit its token/request limit; the ticket stays open
            run.state, run.decision = "stopped", result
    except Exception as exc:
        run.state, run.error = "error", f"{type(exc).__name__}: {exc}"
    finally:
        run.finished_at = audit.now()
        _save_runs()


@app.post("/tickets/{ticket_id}/run", status_code=202)
async def run_team(ticket_id: int) -> RunInfo:
    """Start the agent team on one ticket. Poll GET /runs/{run_id} and GET /events to follow it."""
    if not (await _mcp("get_ticket", ticket_id=ticket_id)).get("found"):
        raise HTTPException(404, f"No ticket {ticket_id}.")
    if busy := _running(ticket_id):
        raise HTTPException(409, f"Ticket {ticket_id} is already being worked (run {busy[0].run_id}).")
    run = RunInfo(run_id=new_run_id(), ticket_id=ticket_id, state="running", started_at=audit.now())
    RUNS[run.run_id] = run
    _save_runs()
    task = asyncio.create_task(_work(run))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return run


@app.get("/runs/{run_id}")
async def get_run(run_id: str) -> RunInfo:
    if run_id not in RUNS:
        raise HTTPException(404, f"No run {run_id} since the server started.")
    return RUNS[run_id]


# --- Agent events -------------------------------------------------------------


def _said(entry: dict) -> str | None:
    detail = entry.get("detail", {})
    match entry["kind"]:
        case "delegation_sent":
            return f"Asked {detail.get('to')}: {detail.get('request')}"
        case "delegation_returned":
            return f"{detail.get('from')} reported back" + ("" if detail.get("ok") else f" with an error: {detail.get('error')}")
        case "delegation_refused":
            return f"Could not ask {detail.get('to')}: {detail.get('reason')}"
        case _:
            return entry.get("text")


@app.get("/events")
async def list_events(
    limit: int = Query(100, ge=1, le=1000),
    ticket_id: int | None = None,
    run_id: str | None = None,
    after: int | None = Query(None, description="Only events with seq greater than this (for refreshing)."),
) -> list[dict]:
    """Recent audit-trail events, oldest first: who acted, what they said, and which tools they called."""
    events = []
    for seq, e in enumerate(audit.read_all()):
        if after is not None and seq <= after:
            continue
        if ticket_id is not None and e.get("ticket_id") != ticket_id:
            continue
        if run_id is not None and e.get("run_id") != run_id:
            continue
        detail = e.get("detail", {})
        events.append(
            {
                "seq": seq,
                "ts": e["ts"],
                "run_id": e["run_id"],
                "ticket_id": e.get("ticket_id"),
                "agent": e["agent"],
                "chain": e.get("chain", []),
                "kind": e["kind"],
                "said": _said(e),
                # final_result is PydanticAI handing back the typed answer, not a shop tool.
                "tools": [c for c in e.get("tool_calls", []) if c["tool"] != "final_result"],
                "tool_results": [r for r in e.get("tool_results", []) if r["tool"] != "final_result"],
                "usage": e.get("usage"),
                # delegation events: who handed off to whom, and the specialist's one-line report
                "to": detail.get("to"),
                "from": detail.get("from"),
                "summary": detail.get("summary"),
                "call_id": detail.get("tool_call_id"),
            }
        )
    return events[-limit:]


# --- Money --------------------------------------------------------------------


def _approval_card(req: PaymentApproval) -> dict | None:
    """The approvals_needed entry this payment settles, if the dashboard sent one."""
    if req.run_id is None:
        return None
    run = RUNS.get(req.run_id)
    cards = ((run.decision or {}).get("approvals_needed") or []) if run else []
    if req.approval_index is None or not 0 <= req.approval_index < len(cards):
        raise HTTPException(404, "That approval card doesn't exist.")
    card = cards[req.approval_index]
    if card.get("approval", {}).get("status") == "approved":
        raise HTTPException(409, "That approval card was already signed.")
    return card


@app.post("/payments/approve")
def approve(req: PaymentApproval) -> PaymentReceipt:
    """A human approved a payment or purchase. Checks it against the records, then moves the cash."""
    card = _approval_card(req)
    try:
        receipt = approve_payment(req)
    except ActionRefused as refused:
        raise HTTPException(refused.status, refused.message) from None
    if card is not None:
        card["approval"] = {"status": "approved", **receipt.model_dump(mode="json")}
        _save_runs()
    return receipt


@app.get("/payments")
async def list_payments() -> list[dict]:
    return (await _mcp("list_payments"))["payments"]


@app.get("/cash")
async def checking_balance() -> dict:
    accounts = (await _mcp("get_cash_balance")).get("accounts", [])
    checking = next((a for a in accounts if a["name"] == "checking"), None)
    if checking is None:
        raise HTTPException(404, "No checking account on file.")
    today = (await _mcp("get_today")).get("date_today")
    return {"account": "checking", "balance": checking["balance"], "as_of": checking["date"], "shop_date": today}


# --- Reset --------------------------------------------------------------------


@app.post("/reset")
def reset() -> dict:
    """Copy the original database over the working copy. The audit trail is kept."""
    if busy := _running():
        raise HTTPException(409, f"Wait for run {busy[0].run_id} on ticket {busy[0].ticket_id} to finish.")
    reset_database()
    RUNS.clear()  # old runs' approvals point at bills that are unpaid again; start the desk fresh
    _save_runs()
    return {"ok": True, "message": "Working database reset to the original values. Audit trail kept."}
