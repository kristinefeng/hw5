# Campus Customs Desk: design notes

The dashboard (`frontend/`, React + Vite + TypeScript) is designed as **a back-office desk, not an admin panel**. Campus Customs is a small shop on Chapel Street, and the person using this board is its owner. They should feel like they're sitting at a tidy desk with their staff around them, not reading a log file. Every visual choice follows one idea: **familiar paper objects for the things a shop owner already understands, and a live floor plan for the part that's new, the agents.**

## Layout: three columns, read left to right like a workday

| Inbox (left) | Desk (center) | Transcript (right) |
|---|---|---|
| The three tickets as paper stubs | The selected ticket, the agent floor, then the outcome | Everything the agents said and did, live |

- **Left, the inbox.** Each ticket is a stub with a punched, perforated edge and a coloured top border by type: plum for customer orders, brick for rent, gold for price requests. The owner can see the whole queue at a glance and click to put one on the desk.
- **Center, the desk.** The flow goes from the top down:
  - the ticket card (who asked, for what, the linked records, the original note),
  - **the floor**, where the agents work,
  - the **Boss's memo**,
  - **cheques and slips waiting for a signature**, and the draft customer letter,
  - **"Who did what"**.
- **Right, the transcript.** A live feed for anyone who wants the detail. Every tool call is a chip you can click to see the exact record that came back from the database, so a number on the board can always be traced to its source.
- **Top bar.** A Yale-navy band with a brass rule holds the brand, a paper "Shop date" tag (agents use the shop's date, not today's, so it's shown prominently), and **the cash till**.

The columns stack on narrower screens: the transcript drops below at about 1280px, and everything goes to one column on a phone.

## How the agents read differently

Each agent has **its own ink, icon, and seat**, and those stay the same everywhere they appear: the floor, the transcript, the summary cards.

| Agent | Ink | Icon | Desk |
|---|---|---|---|
| Boss | Navy | Briefcase | Runs the desk, has a brass ring around its seat |
| Inventory | Green | Box | The stockroom |
| Accounting | Gold | Ledger and coin | The ledger |
| Facilities | Brick | Key | Lease & landlord |
| Customer Service | Plum | Speech bubble | Front counter |

- **The floor is a floor plan.** On a faint blueprint grid, the Boss sits at the top and the four specialists sit in a row below, joined by dotted wires. Seat positions match the reporting lines, so the org chart *is* the picture.
- **Hand-offs light up.** When one agent delegates to another, the wire between them turns the recipient's colour and the dashes flow toward them. When the work comes back, the wire goes solid and fades. Specialist-to-specialist hand-offs, like Accounting asking Inventory, draw as an arc over the row, so full connectivity is visible rather than just claimed.
- **Every seat shows a state:**
  - *idle*: greyed out,
  - *working*: a pulsing ring,
  - *waiting* on someone else: a slowly turning dashed ring,
  - *done*: a green badge.
- **Speech bubbles turn tool calls into plain English.** "Checking the shelf · CC-TEE-WHITE, S", "Pulling the invoice · 501", "Asked Accounting for help". When a specialist reports back, its bubble becomes its one-line finding.
- **"Sat this one out."** After a run, any agent that wasn't needed stays dimmed with that label. It makes the routing visible: the owner can see that the rent ticket never bothered Inventory. It also gives the Problem 6 plan-vs-actual comparison something concrete to look at.

## How resolved tickets show up

- **Rubber stamps.** Each stub carries an inked stamp, tilted like a real one: **OPEN** (blue), **WORKING** (brass, pulsing while the team runs), **RESOLVED** (green), or **STOPPED** (red, if a run hit its token cap). When a run finishes, the RESOLVED stamp "thunks" on with a quick scale-down. It's a small moment of closure that a status label doesn't give you.
- **Resolved still shows what's left to do.** The backend marks a ticket resolved when the team finishes, but the Boss may still want the owner's signature. Those tickets keep a small amber **"✍ 1 to sign"** tag, so "the agents are done" and "you're done" are never confused.
- **The Boss's memo** sits under the floor, on a navy letterhead with a pill showing the recommendation (e.g. "Needs your approval"), the summary in readable serif type, and next steps.
- **"Who did what"** has one card per agent who worked, in that agent's colour. Each card shows who asked them, their one-line report, the shop tools they used with counts (`get_invoice ×2`), and who they handed off to. It's the shortest honest account of the run.

## How cash shows up

- **The till** sits top right, always visible: a large serif balance for checking. When a payment clears, the number **counts down** to the new balance and a red "−$840.00" drifts away under it. The owner *feels* the money leave, which is the point.
- **A gauge** under the balance shows the cash level, with a red tick at the **$500 cushion**. Payments that are waiting for a signature appear as a striped band ("$3,240.00 waiting for your signature → leaves $160.00"), so the owner sees the combined effect *before* signing anything. That's the same cash rule the Accounting agent follows.
- **Click the till** to open a ledger page (ruled paper) listing every payment, its date, and who signed it.

## Approving a payment: a cheque you sign

Payments aren't "Approve" buttons. Each payment the Boss recommends arrives as a **cheque**:
- a security-paper background,
- *Pay to the order of* the payee from the records,
- the amount in a boxed field,
- a memo line with the reason,
- "Checking after this: $X", in amber if it would go below the cushion,
- an **authorized signature** line.

The owner types their name on the signature line, where it shows in handwriting, and clicks **Sign & pay**. The server re-checks everything (amount matches the bill, bill still unpaid, enough cash, a person and not an agent). Then the cheque gets a red **PAID** stamp and a receipt, and the till counts down. If the server refuses, the cheque shows why in plain words ("Refused: Invoice 501 is already paid").

Why a cheque? Because signing something is a deliberate act. A one-click "approve" button makes approving money feel trivial; a signature line makes the human-in-the-loop rule tangible. Agents only *prepare* the cheque, and only a human signs it. The signer's name is remembered between visits.

Approvals that aren't payments (sending a customer reply, a discount) show as **sign-off slips**. The customer reply appears as a **draft letter** on ruled paper with a Copy button and the footer "Not sent. Agents draft, you decide."

## The small things that make it pleasant

- **Warm paper, not grey chrome.** A cream desk background, paper cards with soft shadows, a serif for anything a person would *read* (subjects, memos, letters, money) and a sans-serif for labels. Tool names use monospace, so it's clear they are the machine's words.
- **Nothing important is hidden.** Every number traces to a clickable tool result, and every hand-off is drawn.
- **Cost is shown, quietly.** "Last run · 0:49 · 41.8k tokens · ≈ $0.0057 on gpt-6-luna", plus a live clock and token count while the team works. Owners should know what a ticket costs.
- **Live but calm.** While a run is going, the board fetches only *new* events about every 1.2 seconds, and it stops polling as soon as the run ends. The transcript auto-scrolls only while live. Animations respect "reduce motion" settings.
- **A safe reset.** "Reset desk" (top right) asks for confirmation, restores the original database for a fresh run, and keeps the audit trail.
- **Friendly failure.** If the backend isn't running, a banner says so and shows the exact command to start it.
- **No setup surprises.** System fonts only, and no external assets or CDNs, so the desk looks the same offline.
