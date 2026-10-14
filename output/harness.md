# Campus Customs — Agent Harness

Working database: `data/campus_customs_new.db` (copy of `data/campus_customs.db`; the original is never modified).

The complete harness for the Campus Customs agent desk: the data, the tools that read it, the agents that use those tools, the API and dashboard a human works from, and the rules that keep it safe.

**Contents**
1. [Database tables](#database-tables) and [how the open tickets link to them](#how-the-three-open-tickets-link-to-the-other-tables)
2. [MCP tools](#all-mcp-tools) (the [first three, tied to tickets](#mcp-tools--first-three-tied-to-tickets-problem-3))
3. [The five agents](#agent-team-problem-5)
4. [API routes](#api-routes-problem-7)
5. [Dashboard](#dashboard-problem-8)
6. [Full run results](#full-run-results-problem-9)
7. [SAFETY](#safety)

How to run it: start the backend from `backend/` with `uvicorn main:app --reload --port 8000` (inside `hw5/.venv`), start the board from `frontend/` with `npm run dev`, pick a ticket, and press **Start the team**.

---

## Database tables

### `desk`
Fields: `date_today`, `notes`
Why it matters: sets the shop's "today" (2026-08-31), so agents judge due dates and overdue items against this, not the real clock.

### `tickets`
Fields: `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at`
Why it matters: the work queue. Each open ticket is a job, and its `sku`, `lease_id`, and `invoice_id` point the agent to the other tables it needs.

### `inventory`
Fields: `sku`, `name`, `size`, `qty`, `location` (key: `sku` + `size`)
Why it matters: tells an agent whether an order can ship from stock and where to pick it, size by size.

### `pricing`
Fields: `sku`, `unit_cost`, `list_price`
Why it matters: sets the margin, which is the floor for any discount or price override.

### `vendors`
Fields: `id`, `name`, `specialty`, `lead_days`
Why it matters: tells an agent who can restock or deliver and how long it takes, so restock promises are realistic.

### `invoices`
Fields: `id`, `vendor_id` → `vendors.id`, `amount`, `due_date`, `status`, `description`
Why it matters: money the shop owes vendors. Agents check status and due date before paying or before relying on a pending reprint.

### `leases`
Fields: `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`
Why it matters: rent is the largest fixed bill. Agents use it to check a rent notice is legitimate and to plan cash around the due date.

### `cash_accounts`
Fields: `name`, `balance`, `date`
Why it matters: shows how much money is actually available. No payment should go out unless the balance covers it.

### `payments`
Fields: `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`
Why it matters: the audit log of money that went out. `kind` + `ref_id` point at the invoice or lease paid, and `approved_by` records who signed off. Empty at the start.

---

## How the three open tickets link to the other tables

As of `desk.date_today` = 2026-08-31, checking balance = $3,400.

| Ticket | Type | Links to | What the data shows |
|---|---|---|---|
| 101 — Tauhid Zaman, Bulldog tee | `customer_order` | `inventory` (CC-TEE-WHITE / S), `pricing`, `invoices` #501 → `vendors` #1 | Size S has **0 in stock**. Invoice 501 ($840, Bulldog Print Co, "Rush reprint CC-TEE-WHITE S") is still **open and past due** (due 2026-08-28). Vendor lead time is 5 days. |
| 102 — Elm City Properties, Rent due | `rent_notice` | `leases` #1, `cash_accounts` | Matches lease 1: Chapel Street shop, landlord Elm City Properties, **$2,400 due 2026-09-02**. |
| 103 — Yale AI Club, Bulk hoodie discount | `price_override` | `inventory` (CC-HOOD-NAVY / M), `pricing`, `vendors` | Wants **20** size-M hoodies, but only **8** are in stock. Cost $22, list $58 ($36 margin per unit). Restock would come from Bulldog Print Co (5-day lead). |

Things agents should notice:
- **Cash is tight.** Rent ($2,400) + invoice 501 ($840) = $3,240, which leaves only $160 of the $3,400.
- **Ticket 101 depends on invoice 501.** The tee reprint is not confirmed until that overdue invoice is dealt with.
- **`payments` is empty.** Nothing has been paid yet, and every payment needs an `approved_by`.
- **CC-MUG-CREST is also at 0 stock**, but no ticket asks for it.

---

## MCP tools — first three, tied to tickets (Problem 3)

Server: `mcp_server/server.py` (FastMCP). All tools are read-only against `data/campus_customs_new.db`.

### `check_stock(sku, size)`
- **Reads:** `inventory`
- **Unlocks:** Ticket 101 (Tauhid Zaman, Classic Bulldog Tee, size S)
- **Why it's right for this ticket:** Before an agent can answer whether Tauhid can get a size-S tee, it has to see the exact stock for CC-TEE-WHITE in size S. That is 0, which tells the agent it can't fill the order from the shelf and has to look at the pending reprint (invoice 501).

### `get_lease(lease_id)`
- **Reads:** `leases`
- **Unlocks:** Ticket 102 (Elm City Properties, rent due)
- **Why it's right for this ticket:** The rent notice arrived as an email, so the agent must check it against lease 1 on file (Elm City Properties, $2,400, due 2026-09-02) before treating it as a real bill rather than trusting the email itself.

### `get_pricing(sku)`
- **Reads:** `pricing`
- **Unlocks:** Ticket 103 (Yale AI Club, bulk discount on 20 size-M hoodies)
- **Why it's right for this ticket:** A bulk discount can only be judged against what each hoodie costs. CC-HOOD-NAVY costs $22 and lists at $58, so the agent knows any offer has to stay above $22 and has $36 per unit to negotiate with.

---

## Agent team (Problem 5)

Built with PydanticAI in `backend/`. Every agent runs on `gpt-6-luna` through Portkey, and gets shop facts only from the `campus-customs` MCP server. Each agent has its own prompt in `backend/prompts/<role>.md`, its own file in `backend/agents/<role>.py`, and only the MCP tools its role needs. Every agent also has `delegate(to, request)`, so **any agent can hand work to any other agent** (full connectivity).

| Agent | Job | Returns | MCP tools it may call |
|---|---|---|---|
| **boss** | Owns each ticket. Routes work to specialists, decides the status, records the outcome, and lists what needs a human. The only agent that writes to the database. | `TicketDecision` | `get_today`, `list_open_tickets`, `get_ticket`, `update_ticket` |
| **inventory** | Stock by SKU and size, shelf location, other sizes, vendor lead times, and whether a linked reprint is really underway. | `SpecialistReport` | `get_today`, `get_ticket`, `check_stock`, `check_all_sizes`, `list_vendors`, `get_invoice` |
| **accounting** | Cash, vendor invoices, payment history, pricing and margin floors. Recommends payments and discounts, and shows the combined cash effect of every bill due soon. | `SpecialistReport` | `get_today`, `get_ticket`, `get_cash_balance`, `get_invoice`, `list_open_invoices`, `list_payments`, `get_pricing`, `list_leases`, `get_lease` |
| **facilities** | The shop lease and landlord. Checks rent notices against the lease (sender, amount, due date, space) and treats email as unverified. | `SpecialistReport` | `get_today`, `get_ticket`, `list_leases`, `get_lease`, `list_payments` |
| **customer_service** | Drafts customer replies and order options from real stock and list prices. Never reveals cost, and never sends anything. | `SpecialistReport` | `get_today`, `get_ticket`, `check_stock`, `check_all_sizes`, `get_pricing` |

**How a ticket runs.** `POST /tickets/{id}/run` (or `python -m backend.team --ticket N`) starts the boss. The boss reads the ticket and delegates to specialists, one after another when one specialist needs another's answer. A specialist can also delegate to another specialist; for example, accounting can ask facilities. Each delegated agent runs its own PydanticAI loop (`backend/loop.py: run_agent`) and returns a typed report. The boss records the outcome with `update_ticket` and returns its decision.

**Data types** (`backend/models.py`):
- `TeamDeps`: run id, ticket, and delegation chain.
- `ApprovalRequest`: something only a human may approve.
- `SpecialistReport` and `TicketDecision`: what the agents return.
- `AuditEntry`: one entry in the audit trail.

**Audit trail.** Every step of every agent loop is appended to `output/audit_trail.json`: run start, prompt, model request with the tool results going back, model response with text, tool calls, arguments, and tokens, and the end. Delegations sent, returned, and refused are logged too. Each entry carries `run_id`, `ticket_id`, `agent`, the delegation `chain`, `step`, and a timestamp. The file is only ever added to. A run never clears it, and an unreadable file is moved aside rather than deleted.

## All MCP tools

Server: `mcp_server/server.py`. Database: `data/campus_customs_new.db`.

| Tool | Table(s) | Reads / writes | Used by |
|---|---|---|---|
| `get_today` | `desk` | read | all five |
| `list_open_tickets` | `tickets` | read | boss |
| `list_tickets` | `tickets` | read | API only (`GET /tickets`) |
| `get_ticket` | `tickets` | read | all five |
| `update_ticket` | `tickets` (+ `desk` for the date) | **write**: status and an added note | boss |
| `check_stock` | `inventory` | read | inventory, customer_service |
| `check_all_sizes` | `inventory` | read | inventory, customer_service |
| `get_pricing` | `pricing` | read | accounting, customer_service |
| `list_vendors` | `vendors` | read | inventory |
| `get_invoice` | `invoices` + `vendors` (+ `desk` for days past due) | read | inventory, accounting |
| `list_open_invoices` | `invoices` + `vendors` (+ `desk`) | read | accounting |
| `get_cash_balance` | `cash_accounts` | read | accounting, API (`GET /cash`) |
| `list_payments` | `payments` | read | accounting, facilities |
| `list_leases` | `leases` (+ `desk` for days until due) | read | accounting, facilities |
| `get_lease` | `leases` (+ `desk` for days until due) | read | accounting, facilities |

No tool writes to `payments`, `cash_accounts`, `inventory`, or `pricing`, so no agent can move money, change stock, or change a price. Only the human approval route below can move money.

## API routes (Problem 7)

`backend/main.py` (FastAPI). Start it from `backend/` with `uvicorn main:app --reload --port 8000`.

- `GET /tickets`: every ticket with its status, plus `state` (open or resolved), whether the team is working on it right now, and its latest run (with the boss's decision and any approval cards).
- `POST /tickets/{ticket_id}/run`: starts the agent team on that ticket in the background and returns a `run_id` right away. When the run finishes, the ticket is marked resolved, and the boss's recommendation and approvals stay on the run (saved in `output/runs.json`).
- `GET /runs/{run_id}`: whether that run is still going, done, stopped, or failed, and, once done, the boss's decision with the approvals it needs.
- `GET /events?limit=&ticket_id=&run_id=&after=`: recent agent events from the audit trail, covering what each agent said, which tools it called, and who it delegated to. `after` returns only new events, so the board can refresh cheaply.
- `POST /payments/approve`: a human approves an invoice, rent, or purchase payment. This is the only route that changes cash. It checks the payment against the records first, and marks the run's approval card as signed.
- `GET /payments`: every payment recorded so far (the dashboard's ledger).
- `GET /cash`: current checking balance from `cash_accounts`, plus the shop date.
- `POST /reset`: copies `campus_customs.db` back over `campus_customs_new.db` and clears saved runs, for a fresh run. It's refused while a run is in progress, and the audit trail is kept.

The dashboard (`frontend/`, `npm run dev`) calls these routes at `http://localhost:8000`. CORS allows `http://localhost:5173` plus other localhost ports. See `output/design.md` for the dashboard's design.

## Dashboard (Problem 8)

`frontend/` is built with React + Vite + TypeScript. `npm run dev` serves it, and it calls the API at `http://localhost:8000` (set in `frontend/.env`). Design choices are in `output/design.md`.

- **Inbox (left):** the three tickets as paper stubs with rubber-stamp statuses (OPEN / WORKING / RESOLVED / STOPPED), plus a "✍ N to sign" tag when the owner still has a signature to give.
- **Ticket card and Start the team:** `POST /tickets/{id}/run`. A live timer and token count show while the team works.
- **The floor:** the five agents seated as an org chart. Each agent's seat shows its live state (idle, working, waiting, done) and a speech bubble with what it's doing in plain English. Hand-off wires animate in the receiving agent's colour, including specialist-to-specialist arcs. Agents that weren't needed are marked "Sat this one out". The floor refreshes from `GET /events?run_id=&after=`.
- **Boss memo, sign-offs, and "Who did what":**
  - The boss's decision comes from `GET /runs/{id}`.
  - Payments arrive as **cheques** the owner signs, which calls `POST /payments/approve`. The cheque shows "checking after this" and a cushion warning, and gets a PAID stamp and receipt once paid.
  - Other approvals appear as slips, and the customer reply as a draft letter.
  - There's one card per agent with its tools, who asked it, and its report.
- **Transcript (right):** every hand-off and tool call. Click a tool chip to see the exact database record it returned.
- **Cash till (top right):** checking from `GET /cash`. It counts down when a payment clears, shows a gauge with the $500 cushion line and any unsigned payments, and opens a ledger from `GET /payments`. **Reset desk** calls `POST /reset` after a confirmation.

## Full run results (Problem 9)

The working database was reset on the board, then the team ran 101, 102, and 103 in order. All three are `resolved`, and every step is in `output/audit_trail.json`: a database reset, 3 team runs, and 1 human approval.

| Ticket | Agents (first call in bold) | Boss recommended | Human approvals | Cash |
|---|---|---|---|---|
| 101 | **Inventory**, Accounting (also asked Inventory), Customer service | needs_approval | $840 invoice 501, **signed by Kristine Feng**. The customer reply is drafted. | −$840.00 |
| 102 | **Facilities**, then Accounting | waiting_on_customer (landlord to confirm the amount) | None requested | $0.00 |
| 103 | **Accounting**, Inventory (Accounting also asked Inventory), Customer service | needs_approval | Discount of up to 15% on 8 units and the customer reply, both left for the owner | $0.00 |

Checking went **$3,400.00 → $2,560.00**, which matches `cash_accounts`. The plan-vs-actual comparison and the itemized cash are in `output/desk_tickets.html`, per-ticket details in `output/resolved_tickets.json`, and board screenshots in `output/resolved_board.html`.

## SAFETY

**Guardrails for real customers and real money**
- **Humans approve money.** Agents only *recommend* payments, refunds, and discounts, and they go into `approvals_needed` with the exact amount and record. No MCP tool can pay or move cash, so this holds even if a model ignores its prompt. Cash moves only through `POST /payments/approve`, which `backend/human_actions.py` handles. That code is not an MCP tool, so no agent or MCP client can reach it. Before any cash moves, it requires a named person (agent names are refused), an exact match to the invoice or rent amount, an unpaid bill, and enough balance. Rent can't be paid twice on the same day. The payment, the cash change, and the bill's new state are written in one transaction, then logged to the audit trail with the approver's name.
- **Humans send messages.** Customer replies are drafts. Nothing reaches a customer, vendor, or landlord without the owner.
- **Least privilege.** Each agent sees only its role's tools. Only the boss can write, and only to ticket status and notes. Notes are added, never overwritten.
- **Facts only from the database.** Prompts forbid guessing. Tools return "not found" instead of inventing data, and reports cite which tool each fact came from.
- **Verify before paying.** A rent notice is checked against the lease on file. Amounts must match the record exactly, `list_payments` is checked to prevent paying twice, and payment details found only in an email are treated as possible fraud.
- **Price floors.** List price is the default. Discounts are capped by policy, never go below unit cost, and always need owner approval. Unit cost and margin are never shown to customers.
- **Cash cushion.** Accounting reports the balance left after every bill due within 7 days and flags anything under $500.
- **Untrusted ticket text.** Notes and emails are data, not instructions. Agents flag embedded orders such as "apply 50% off" or "pay this account".
- **Drafts get a human read.** In the real run, one customer draft named a possible discount figure even though the prompt says not to. Because nothing is sent without the owner, the slip was caught. That's why drafts stay drafts.
- **Unclear bills wait.** When a rent email gave no amount, the agents held payment and asked for landlord confirmation instead of guessing. A wrong payment is harder to undo than a late check.
- **Full audit.** Every step, tool call, and delegation is in `output/audit_trail.json` under a run id. The dry runs used a copy of the database, so the working copy changes only when a real run is intended.

**Limits that keep token use in check** (all in `backend/config.py`)
- One model only: `gpt-6-luna`, the cheap tier.
- One shared budget per ticket: the boss and every delegated agent draw from the same `UsageLimits`. That is at most **30 model requests**, **60 tool calls**, and **150,000 tokens**, after which the run stops and reports it.
- Each reply is capped at **1,500 output tokens**.
- Delegation is capped at **depth 2** and **8 hand-offs per ticket**. Agents can't delegate to themselves or to anyone already up the chain, which blocks A→B→A loops.
- Prompts tell agents to call each tool once per fact, avoid re-asking, and send dependent questions in sequence so work isn't duplicated.
- Audit text fields are clipped to 1,500 characters so the log stays readable.
- In the dry runs, one ticket used about 30k–40k tokens in total, far below the cap.
