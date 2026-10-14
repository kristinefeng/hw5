"""Campus Customs MCP server.

The single source of shop facts for every agent in this homework. Tools read
data/campus_customs_new.db and return only what is stored there; when a record
is missing they say so instead of guessing. Dates are judged against
desk.date_today (the shop's "today"), never the computer's clock.

Only one tool writes: update_ticket, which records an agent's work on a ticket.
No tool moves money or changes stock.
"""

import os
import sqlite3
from datetime import date
from pathlib import Path

from fastmcp import FastMCP

DB_PATH = Path(
    os.getenv(
        "CAMPUS_CUSTOMS_DB",
        Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db",
    )
)

TICKET_STATUSES = (
    "open",
    "in_progress",
    "waiting_on_vendor",
    "waiting_on_customer",
    "needs_approval",
    "resolved",
)
MAX_NOTE_CHARS = 1000

mcp = FastMCP("campus-customs")


def _query(sql: str, params: tuple = ()) -> list[dict]:
    """Run a SELECT against the working database and return rows as dicts."""
    # Read-only connection: lookup tools can never change data.
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _today() -> str:
    return _query("SELECT date_today FROM desk LIMIT 1")[0]["date_today"]


def _days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


# --- Desk and tickets --------------------------------------------------------


@mcp.tool
def get_today() -> dict:
    """Return the shop's current business date and desk notes.

    Always use this date, not the real-world date, when judging what is due,
    overdue, or how long a restock will take.
    """
    rows = _query("SELECT date_today, notes FROM desk LIMIT 1")
    if not rows:
        return {"found": False, "message": "The desk table has no date."}
    return {"found": True, **rows[0]}


@mcp.tool
def list_open_tickets() -> dict:
    """List every ticket that is not resolved, oldest first (id, type, requester, subject, status)."""
    rows = _query(
        "SELECT id, type, requester, subject, status, created_at FROM tickets "
        "WHERE status != 'resolved' ORDER BY created_at"
    )
    return {"count": len(rows), "tickets": rows}


@mcp.tool
def list_tickets() -> dict:
    """List every ticket, resolved or not, oldest first, with all its fields."""
    rows = _query("SELECT * FROM tickets ORDER BY created_at")
    return {"count": len(rows), "tickets": rows}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Return one ticket in full, including the sku, size, qty, lease_id, or invoice_id it points to."""
    rows = _query("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    if not rows:
        return {"found": False, "message": f"No ticket with id {ticket_id}."}
    return {"found": True, **rows[0]}


@mcp.tool
def update_ticket(ticket_id: int, status: str, note: str, author: str) -> dict:
    """Record work on a ticket: set its status and append a dated note.

    status must be one of: open, in_progress, waiting_on_vendor,
    waiting_on_customer, needs_approval, resolved. The note is appended to the
    ticket's existing notes (never replaces them) with today's shop date and
    the author's name. This does not send anything to the customer.
    """
    if status not in TICKET_STATUSES:
        return {"ok": False, "message": f"status must be one of {', '.join(TICKET_STATUSES)}."}
    note, author = note.strip(), author.strip()
    if not note or not author:
        return {"ok": False, "message": "Both note and author are required."}
    if len(note) > MAX_NOTE_CHARS:
        return {"ok": False, "message": f"Note is too long; keep it under {MAX_NOTE_CHARS} characters."}
    if not _query("SELECT id FROM tickets WHERE id = ?", (ticket_id,)):
        return {"ok": False, "message": f"No ticket with id {ticket_id}."}

    entry = f"[{_today()} {author}] {note}"
    conn = sqlite3.connect(DB_PATH)
    try:
        with conn:
            conn.execute(
                "UPDATE tickets SET status = ?, "
                "notes = CASE WHEN notes IS NULL OR notes = '' THEN ? ELSE notes || char(10) || ? END "
                "WHERE id = ?",
                (status, entry, entry, ticket_id),
            )
    finally:
        conn.close()
    return {"ok": True, **get_ticket(ticket_id)}


# --- Inventory and pricing ----------------------------------------------------


@mcp.tool
def check_stock(sku: str, size: str) -> dict:
    """Look up on-hand quantity and shelf location for one SKU in one size.

    Use this before promising a customer an item. Sizes are S, M, L, XL for
    apparel and OS (one size) for hats and mugs.
    """
    rows = _query(
        "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
        (sku, size),
    )
    if not rows:
        return {"found": False, "message": f"No inventory record for {sku} size {size}."}
    item = rows[0]
    return {"found": True, **item, "in_stock": item["qty"] > 0}


@mcp.tool
def check_all_sizes(sku: str) -> dict:
    """Return stock for every size of one SKU, plus the total on hand.

    Use this when the requested size is short and you need to see what other
    sizes could cover part of an order.
    """
    rows = _query(
        "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? "
        "ORDER BY CASE size WHEN 'S' THEN 1 WHEN 'M' THEN 2 WHEN 'L' THEN 3 WHEN 'XL' THEN 4 ELSE 5 END",
        (sku,),
    )
    if not rows:
        return {"found": False, "message": f"No inventory records for {sku}."}
    return {"found": True, "sku": sku, "total_qty": sum(r["qty"] for r in rows), "sizes": rows}


@mcp.tool
def get_pricing(sku: str) -> dict:
    """Return unit cost, list price, and per-unit margin for a SKU.

    Use this before quoting any discount: a price below unit_cost loses money
    on every unit.
    """
    rows = _query("SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,))
    if not rows:
        return {"found": False, "message": f"No pricing record for {sku}."}
    price = rows[0]
    return {
        "found": True,
        **price,
        "margin_per_unit": round(price["list_price"] - price["unit_cost"], 2),
    }


@mcp.tool
def list_vendors() -> dict:
    """List every vendor with its specialty and lead time in days."""
    rows = _query("SELECT id, name, specialty, lead_days FROM vendors ORDER BY id")
    return {"count": len(rows), "vendors": rows}


# --- Money: invoices, cash, payments ------------------------------------------


@mcp.tool
def get_invoice(invoice_id: int) -> dict:
    """Return one vendor invoice with its vendor's name, specialty, and lead time.

    Also reports days_past_due against the shop's date (positive means overdue).
    """
    rows = _query(
        "SELECT i.id, i.vendor_id, v.name AS vendor_name, v.specialty AS vendor_specialty, "
        "v.lead_days AS vendor_lead_days, i.amount, i.due_date, i.status, i.description "
        "FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
        (invoice_id,),
    )
    if not rows:
        return {"found": False, "message": f"No invoice with id {invoice_id}."}
    invoice = rows[0]
    return {"found": True, **invoice, "days_past_due": _days_between(invoice["due_date"], _today())}


@mcp.tool
def list_open_invoices() -> dict:
    """List every invoice whose status is open, with vendor name and days past due, plus the total owed."""
    today = _today()
    rows = _query(
        "SELECT i.id, v.name AS vendor_name, i.amount, i.due_date, i.status, i.description "
        "FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.status = 'open' ORDER BY i.due_date"
    )
    for row in rows:
        row["days_past_due"] = _days_between(row["due_date"], today)
    return {"count": len(rows), "total_owed": round(sum(r["amount"] for r in rows), 2), "invoices": rows}


@mcp.tool
def get_cash_balance() -> dict:
    """Return every cash account with its balance and the date that balance was taken."""
    rows = _query("SELECT name, balance, date FROM cash_accounts ORDER BY name")
    if not rows:
        return {"found": False, "message": "No cash accounts on file."}
    return {"found": True, "accounts": rows, "total_balance": round(sum(r["balance"] for r in rows), 2)}


@mcp.tool
def list_payments(kind: str | None = None, ref_id: int | None = None) -> dict:
    """List recorded payments, optionally filtered by kind (e.g. invoice, rent) and ref_id.

    Check this before recommending a payment so the same bill is never paid twice.
    """
    sql, params = "SELECT * FROM payments WHERE 1 = 1", []
    if kind is not None:
        sql, params = sql + " AND kind = ?", [*params, kind]
    if ref_id is not None:
        sql, params = sql + " AND ref_id = ?", [*params, ref_id]
    rows = _query(sql + " ORDER BY paid_at", tuple(params))
    return {"count": len(rows), "payments": rows}


# --- Facilities ---------------------------------------------------------------


@mcp.tool
def list_leases() -> dict:
    """List every lease the shop holds, with landlord, monthly rent, next due date, and days until due."""
    today = _today()
    rows = _query("SELECT id, space_name, landlord, monthly_rent, next_due FROM leases ORDER BY next_due")
    for row in rows:
        row["days_until_due"] = _days_between(today, row["next_due"])
    return {"count": len(rows), "leases": rows}


@mcp.tool
def get_lease(lease_id: int) -> dict:
    """Return the lease on file: space, landlord, monthly rent, next due date, and days until due.

    Use this to check a rent notice against the actual lease before any
    payment is considered.
    """
    rows = _query(
        "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
        (lease_id,),
    )
    if not rows:
        return {"found": False, "message": f"No lease with id {lease_id}."}
    lease = rows[0]
    return {"found": True, **lease, "days_until_due": _days_between(_today(), lease["next_due"])}


if __name__ == "__main__":
    mcp.run(show_banner=False)
