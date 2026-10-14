# Campus Customs: Agent Desk (HW5)

A five-agent back office for Campus Customs, a small Yale merch shop on Chapel Street. A **boss** agent routes each ticket to **inventory**, **accounting**, **facilities**, and **customer service** agents (PydanticAI, `gpt-6-luna` via Portkey). They read shop data only through an **MCP server** over SQLite. A **FastAPI** backend and a **React** desk board let a person watch the agents work and sign the payments they recommend. Agents can recommend payments, but only a person signing on the board can move money.

```
data/            campus_customs.db (original, never modified) + campus_customs_new.db (working copy)
mcp_server/      FastMCP server: the only way agents read or update shop data
backend/         FastAPI app (main.py), agent team (agents/, loop.py, team.py), data types (models.py), prompts/
frontend/        React + Vite + TypeScript desk board
output/          harness, plan vs. actual (desk_tickets.html), run results, audit trail, screenshots
AI_prompts.md    log of every prompt typed to the vibe coder
```

## 1. One-time setup

You need Python 3.11+, Node 20+, and a Portkey API key.

```bash
# from the repo root
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                 # then paste your PORTKEY_API_KEY into .env

cd frontend && npm install && cd ..
```

`.env` is git-ignored. Never commit a real key.

## 2. Copy the original database to the working copy (clean run)

The agents and the API read and write **`data/campus_customs_new.db`**. `data/campus_customs.db` is the original and is never modified. Whenever you want a clean slate, with tickets 101–103 open and checking at $3,400.00, copy the original over the working copy:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

The working copy in this repo is the state after our full three-ticket run: all tickets resolved, invoice 501 paid, checking at $2,560.00.

## 3. Start the MCP server

The MCP server (`mcp_server/server.py`) exposes 15 shop tools over stdio.

- **With the app:** you don't need a separate terminal. The FastAPI backend starts the MCP server itself when it boots (see `backend/mcp_link.py`), and every agent shares that one process.
- **On its own,** to check that it starts:
  ```bash
  python mcp_server/server.py        # stdio server; waits for an MCP client. Ctrl+C to stop.
  ```
- **In Claude Code (the vibe coder):** open Claude Code in this folder. `.mcp.json` registers the `campus-customs` server using `.venv/bin/python mcp_server/server.py`. Approve it when prompted, and the tools (`check_stock`, `get_lease`, `get_pricing`, …) become callable.

See `mcp_server/README.md` for every tool and the table it uses.

## 4. Start the FastAPI backend

```bash
cd backend
uvicorn main:app --reload --port 8000        # with .venv active
```

This serves the API at <http://localhost:8000>. Interactive docs are at <http://localhost:8000/docs>.

| Route | What it does |
|---|---|
| `GET /tickets` | All tickets, open/resolved, with each one's latest team run |
| `POST /tickets/{id}/run` | Start the agent team on a ticket (runs in the background) |
| `GET /runs/{run_id}` | A run's state and the boss's decision |
| `GET /events` | What each agent said and which tools it called (`?run_id=&after=` for refreshing) |
| `POST /payments/approve` | A human approves a payment. **The only route that moves cash** |
| `GET /payments` | Payments recorded so far |
| `GET /cash` | Checking balance from `cash_accounts` |
| `POST /reset` | Copy the original DB over the working copy and clear saved runs |

## 5. Start the React board

In a second terminal:

```bash
cd frontend
npm run dev
```

Vite opens the desk in your browser at <http://localhost:5173>, or the next free port. The board calls the backend at `http://localhost:8000`, and the backend allows the Vite origin through CORS.

On the board:
1. Pick a ticket in the **Inbox** and press **Start the team**.
2. Watch the agents on **the floor**: each agent's status, what it's saying, and hand-offs as they happen. The **Transcript** on the right shows every tool call.
3. When the run finishes, the ticket is stamped **RESOLVED**. Read the boss's memo and "Who did what".
4. To pay a recommended bill, sign the **cheque** and press **Sign & pay**. The checking balance in the top-right drops.

## 6. Reset the database before a full three-ticket run

Always start a full run from the original data:

1. On the board, click **Reset desk** (top right) and confirm. That calls `POST /reset`, which copies `campus_customs.db` over `campus_customs_new.db`. Or, with the backend stopped, run `cp data/campus_customs.db data/campus_customs_new.db`.
2. Check the board shows tickets **101, 102, 103 = OPEN** and checking **$3,400.00**.
3. Run **101**, then **102**, then **103**, signing any payments you approve as each one resolves. Cash is shared, so the order matters.

Every agent step is **appended** to `output/audit_trail.json`. Resets and approvals are logged too, and nothing is ever wiped.

You can also run the team without the board, from the repo root:

```bash
python -m backend.team --ticket 101
python -m backend.team --all
```

## Safety, in short

- Agents get read-only shop tools. Only the boss can write, and only ticket status and notes. **No MCP tool can pay, change stock, or change a price.**
- `POST /payments/approve` re-checks every payment before cash moves: a named human approver, an exact match to the invoice or rent amount, a bill that's still unpaid, and enough cash.
- Each ticket run is capped at 30 model requests, 60 tool calls, and 150k tokens, with delegation depth 2 and at most 8 hand-offs.
- Full details are in `output/harness.md` (tables, tools, agents, routes, dashboard, safety).

## Results of our run

See `output/desk_tickets.html` for the plan vs. actual on each ticket, the itemized cash, and the reflection. Also see `output/resolved_tickets.json` and `output/resolved_board.html` (board screenshots). Checking went **$3,400.00 → $2,560.00**: invoice 501, $840, was signed by the owner. Rent ($2,400, due 2026-09-02) is held for landlord confirmation.
