# Campus Customs MCP Server

An MCP server, built with FastMCP, that gives the Campus Customs agents one shared, consistent way to look up shop data. Every agent in this homework calls these tools instead of querying the database directly.

**Database:** `data/campus_customs_new.db` is the working copy. The original `data/campus_customs.db` is never touched. Lookup tools open the database read-only and return only what is stored there. If a record doesn't exist, they say so rather than guessing. The one write tool, `update_ticket`, only changes ticket status and notes.

## Tools

| Tool | Table(s) | Returns |
|---|---|---|
| `get_today()` | `desk` | The shop's business date and desk notes. All due-date math uses this date. |
| `list_open_tickets()` | `tickets` | Every ticket not yet resolved: id, type, requester, subject, status |
| `list_tickets()` | `tickets` | Every ticket, resolved or not, with all fields (used by the dashboard API) |
| `get_ticket(ticket_id)` | `tickets` | One full ticket, including its linked SKU/size/qty, lease, or invoice |
| `update_ticket(ticket_id, status, note, author)` | `tickets` | **Writes.** Sets the status and adds a dated note (existing notes are kept). Status must be open, in_progress, waiting_on_vendor, waiting_on_customer, needs_approval, or resolved. |
| `check_stock(sku, size)` | `inventory` | Item name, qty on hand, shelf location, `in_stock` for one size |
| `check_all_sizes(sku)` | `inventory` | Every size of a SKU and the total on hand |
| `get_pricing(sku)` | `pricing` | Unit cost, list price, margin per unit |
| `list_vendors()` | `vendors` | Each vendor's specialty and lead time in days |
| `get_invoice(invoice_id)` | `invoices`, `vendors` | One invoice with vendor details and days past due |
| `list_open_invoices()` | `invoices`, `vendors` | Every open invoice, days past due, and the total owed |
| `get_cash_balance()` | `cash_accounts` | Each account's balance, as-of date, and the total |
| `list_payments(kind, ref_id)` | `payments` | Recorded payments, optionally filtered, for double-payment checks |
| `list_leases()` | `leases` | Every lease with rent, next due date, and days until due |
| `get_lease(lease_id)` | `leases` | One lease: space, landlord, rent, next due date, days until due |

No tool pays bills, changes cash, adjusts stock, or edits prices. Money moves only through the API's human approval route (`POST /payments/approve`), which is deliberately not an MCP tool.

Set `CAMPUS_CUSTOMS_DB` to point the server at a copy of the database for dry runs.

## Running

`hw5/.venv` has `fastmcp` installed (from `hw5/requirements.txt`). Run these from the `hw5/` folder:

```bash
.venv/bin/python mcp_server/server.py
```
