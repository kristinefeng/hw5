"""Actions only a person can take: approving payments and resetting the database.

This is the only code that moves money. It is deliberately NOT an MCP tool:
agents (and any other MCP client) can read shop data and prepare a payment,
but nothing they can call changes cash. Only the API's approve route, which
the dashboard calls when a human clicks approve, reaches approve_payment().

Every approval is checked against the records before cash moves: the bill must
exist and still be unpaid, the amount must match it exactly, the approver must
be a person, and the account must cover it. The payment, the cash change, and
the bill's new state are written in one transaction, then audited.
"""

from __future__ import annotations

import calendar
import os
import shutil
import sqlite3
from datetime import date

from backend import audit
from backend.config import CASH_CUSHION, DB_PATH, ORIGINAL_DB_PATH
from backend.models import ROLES, AuditEntry, PaymentApproval, PaymentReceipt


class ActionRefused(Exception):
    """The records don't allow this action. `status` is the HTTP code to return."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _add_month(iso: str) -> str:
    d = date.fromisoformat(iso)
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return d.replace(year=year, month=month, day=min(d.day, calendar.monthrange(year, month)[1])).isoformat()


def _one(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> dict | None:
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def approve_payment(req: PaymentApproval) -> PaymentReceipt:
    approver = req.approved_by.strip()
    if not approver or approver.lower() in ROLES or approver.lower() in {"agent", "system"}:
        raise ActionRefused(403, "Payments must be approved by a named person, not an agent.")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")  # lock so two clicks can't both spend the same cash
        today = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()["date_today"]
        account = _one(conn, "SELECT name, balance FROM cash_accounts WHERE name = ?", (req.account,))
        if account is None:
            raise ActionRefused(404, f"No cash account named {req.account!r}.")

        if req.kind == "invoice":
            invoice = _one(conn, "SELECT id, amount, status, description FROM invoices WHERE id = ?", (req.ref_id,))
            if invoice is None:
                raise ActionRefused(404, f"No invoice {req.ref_id}.")
            if invoice["status"] != "open":
                raise ActionRefused(409, f"Invoice {req.ref_id} is already {invoice['status']}.")
            if round(req.amount, 2) != round(invoice["amount"], 2):
                raise ActionRefused(422, f"Invoice {req.ref_id} is for ${invoice['amount']:,.2f}, not ${req.amount:,.2f}.")
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (req.ref_id,))
            effect = f"Invoice {req.ref_id} ({invoice['description']}) marked paid."

        elif req.kind == "rent":
            lease = _one(conn, "SELECT id, landlord, monthly_rent, next_due FROM leases WHERE id = ?", (req.ref_id,))
            if lease is None:
                raise ActionRefused(404, f"No lease {req.ref_id}.")
            if round(req.amount, 2) != round(lease["monthly_rent"], 2):
                raise ActionRefused(422, f"Lease {req.ref_id} rent is ${lease['monthly_rent']:,.2f}, not ${req.amount:,.2f}.")
            if _one(conn, "SELECT id FROM payments WHERE kind = 'rent' AND ref_id = ? AND paid_at = ?", (req.ref_id, today)):
                raise ActionRefused(409, f"Rent on lease {req.ref_id} was already paid today ({today}).")
            next_due = _add_month(lease["next_due"])
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (next_due, req.ref_id))
            effect = f"Rent for {lease['next_due']} paid to {lease['landlord']}; next due {next_due}."

        else:  # purchase
            vendor = _one(conn, "SELECT id, name FROM vendors WHERE id = ?", (req.ref_id,))
            if vendor is None:
                raise ActionRefused(404, f"No vendor {req.ref_id}.")
            if not (req.description or "").strip():
                raise ActionRefused(422, "A purchase needs a description of what is being bought.")
            effect = f"Purchase from {vendor['name']}: {req.description.strip()}."

        before = account["balance"]
        if req.amount > before:
            raise ActionRefused(409, f"{req.account} has ${before:,.2f}; it cannot cover ${req.amount:,.2f}.")
        after = round(before - req.amount, 2)
        conn.execute("UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?", (after, today, req.account))
        payment_id = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (req.kind, req.ref_id, req.amount, req.account, today, approver),
        ).lastrowid
        if req.ticket_id is not None:
            note = f"[{today} {approver}] Approved and paid ${req.amount:,.2f} ({req.kind} {req.ref_id}). {effect}"
            conn.execute(
                "UPDATE tickets SET notes = CASE WHEN notes IS NULL OR notes = '' THEN ? "
                "ELSE notes || char(10) || ? END WHERE id = ?",
                (note, note, req.ticket_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    warnings = []
    if after < CASH_CUSHION:
        warnings.append(f"{req.account} is now ${after:,.2f}, below the ${CASH_CUSHION:,.0f} cash cushion.")
    receipt = PaymentReceipt(
        payment_id=payment_id,
        kind=req.kind,
        ref_id=req.ref_id,
        amount=req.amount,
        account=req.account,
        approved_by=approver,
        paid_at=today,
        balance_before=before,
        balance_after=after,
        effect=effect,
        warnings=warnings,
    )
    audit.append(
        AuditEntry(
            ts=audit.now(), run_id=f"human-{payment_id}", ticket_id=req.ticket_id, agent="human",
            chain=["human"], depth=0, step=0, kind="human_approval",
            text=f"{approver} approved ${req.amount:,.2f} ({req.kind} {req.ref_id}). {effect}",
            detail=receipt.model_dump(mode="json"),
        )
    )
    return receipt


def reset_database() -> None:
    """Put the working database back to the original. The original is only read."""
    tmp = DB_PATH.with_suffix(".resetting")
    shutil.copyfile(ORIGINAL_DB_PATH, tmp)
    os.replace(tmp, DB_PATH)  # atomic swap: readers see the old file or the new one, never half
    audit.append(
        AuditEntry(
            ts=audit.now(), run_id="reset", ticket_id=None, agent="system", chain=["system"],
            depth=0, step=0, kind="database_reset",
            text=f"Working database reset from {ORIGINAL_DB_PATH.name}.",
        )
    )
