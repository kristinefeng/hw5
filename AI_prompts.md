# AI Prompt Log — HW5

This file is the log of what I typed to the vibe coder while working on HW5. Prompts are reproduced verbatim, including typos. It is created at the start of the assignment and updated as each problem is worked.

Format: one section per problem, each with the problem number and title, at least one prompt I typed, and a follow-up prompt where one was needed (with a sentence on what was lacking after the first).

---

## Assignment setup

- **Prompt typed:**

  > Let's work on homework 5. create a folder for this project and write a joke in it

- **Result:** `hw5/` was already present and empty, so it was used as-is; `folder_joke.txt` was written there to confirm we're working in the same place.

---

## Problem 1 — Vibe coder prompts

- **Status:** In progress (this file).
- **Prompt typed:**

  > create "ai_prompts.md" at the start of the assignment and keep it updated as you work. this file is the log of what i've typed to you as the vibe coder.
  > put one section for each problem. each section must include:
  >
  > * the problem number and title
  > * at least one prompt i typed
  > * one follow-up prompt if we needed it

- **Follow-up prompts:** _(none yet — will be added here if the first prompt needed clarification)_

---

## Problem 2 — Study the Campus Customs database

- **Status:** Complete.
- **Prompt typed:**

  > problem 2: study the campus customs database
  > open "data/campus_customs.db" and look through every table and its fileds. copy the original file to "data/campus_customs_new.db" - later problems update that working copy. study the three open tickets so you see how they link to other tables.
  > start "output/harness.md". for each table, list the fields and one short line on why that table matters for the agents. you will keep growing this harness file in later problems

- **Follow-up prompts:** _(none needed)_

---

## Problem 3 — Build the MCP server

- **Status:** Complete.
- **Prompt typed:**

  > problem 3: build the MCP server
  > write an MCP sener in "mcp_server/" using FastMCP . it will talk to "data/campus_customs_new.db". you do NOT need to connect or run it in this problem.
  >
  > every agent in this homework uses the tools in this MCP server. you will add more tools to it later; for now write THREE tools you know you will need for the tickets in the database. keep the names clear. never invent any data, only use information in the database.
  >
  > in "output/harness.md", list each of your three MCP tools. for every tool include: which table it reas, which ticket it helps unlock (101, 102, or 103), and ONE SENTENCE on why that tool is the right one for that ticket. vague lines like "reads inventory" socre low - tie the tool to the ticket. also add a short "mcp_server/README.md" file that explains what the MCP server is for, which database file it uses, and the three tools it has

- **Follow-up prompt:**

  > can you fix whatever is broken? what do you need from me

  What was lacking after the first prompt: the server code was written, but the `fastmcp` package on my machine was broken (missing dependency), so it couldn't actually be imported or run. The fix was a dedicated `hw5/.venv` with a clean install.

---

## Problem 4 — Add the MCP server to the vibe coder and test each tool

- **Status:** Complete.
- **Prompt typed:**

  > problem 4: add the mcp server to vibe coder and test each tool
  > add your mCP server to THIS PROJECT so the vibe coder can call the tools. save the connection jSON text in ".mcp.json" at the project root.
  > then, test EACH of the three MCP tools. save the evidence in "output/mcp_smoke.json". for every tool include
  >
  > * the prompt you asked the vibe coder
  > * the tool name
  > * the tool output (must match values in data/campus_customs_new.db)

- **Follow-up prompt:**

  > can you execute steps 1-4 above on my behalf

  What was lacking after the first prompt: `.mcp.json` was written, but a running vibe coder session only loads MCP servers at startup, so the tools couldn't be called until a new session was started and the server was approved.

- **Follow-up prompt:**

  > For HW5 Problem 4, test each campus-customs MCP tool. Make these three calls one at a time, as three separate tool calls:
  >   Prompt A: "Use the campus-customs MCP tool check_stock to look up CC-TEE-WHITE in size S."
  >   Prompt B: "Use the campus-customs MCP tool get_lease to look up lease 1."
  >   Prompt C: "Use the campus-customs MCP tool get_pricing to look up CC-HOOD-NAVY."
  > Then write hw5/output/mcp_smoke.json: a list with one entry per tool containing "prompt" (the exact Prompt A/B/C text), "tool_name", and "tool_output" (the raw tool result, unedited). Verify each output against hw5/data/campus_customs_new.db with sqlite3 and add "matches_db": true/false. Finally, in hw5/ai_prompts.md, under Problem 4, mark the status Complete and add this message as a follow-up prompt.

  What was lacking after the earlier prompts: the server was connected, but the tools hadn't been called yet, so there was no evidence. This prompt spelled out the exact test prompts and the JSON format, and asked for each result to be checked against the database.

---

## Problem 5 — Build the agent team and grow the MCP tools

- **Status:** Complete.
- **Prompt typed:**

  > problem 5: build the agent team and grow the MCP tools
  > build the agentic team for campus customs using "pydanticAI: boss, inventory, accounting, facilities, and customer service". include prompts, models, and agent loops so tehy can delegate work to each other with full connectivity.
  > put the agent prompts in "backend/prompts/" -- ONE FILE PER AGENT. put data types in "backend/models.py" and the agent files under "backend/" (your layout can vary as long as the five roles are clear). use your PORTKEY_API_KEY and only "gpt-6-luna" for every agent
  >
  > write each prompt in your own words with the shop rules that agent needs. more details prompts that cover all aspects of an agent's work and scope score higher than a short generic prompt
  >
  > add any tools teh agents need to your MCP server so they can work on the open tickets. shop facts come from the MCP server over "data/campus_customs_new.db" - do not invent a second shop-tools layer that bypasses MCP.
  >
  > Wire the agents so they append to "output/audit_trail.json" as they run: for each agent-loop step, record enough to audit later. append to this file -- do not wipe it each run.
  >
  > in "output/harness.md", list each agent and each MCP tool (including ones you add in this problem) along with which table the tool uses. also add a short SAFETY section: the guardrails a real business would want when agents touch real customers and real money, plus limits that keep token use in check.
  >
  > update "mcp_server/README.md" so the tool list matches what you have now

- **Follow-up prompts:** _(none needed)_

---

## Problem 6 — Plan the three tickets

- **Status:** Complete (Expected sections filled; Actual sections left for after the agents run).
- **Prompt typed:**

  > what inputs do we need before problem 6?

  > problem 6: plan the three tickets
  > before you wire the backend, write down what you eXPECT the team to do on each open ticket. build "output/desk_tickets.html"- a page you can double-click with ONE TAB PER TICKET (101, 102, 103). also add empty "Cash" and "Reflection" tabs for later problems (leave them blank or with a short 'coming later' note for now). on each ticket tab, fill an "Expected" section only (leave room for an "Actual" section you will fill after you run the agents).
  > for each ticket's expected section, write in your own words:
  >
  > * who the boss should call first, and why
  > * all the agent delegations you expect - not 'boss calls everyone'
  > * which MCP tools you expect that run to use
  >
  > plans that send every specialist on every ticket score low. you will compare this plan to what actually happens when your agents resolve the three tickets

- **Follow-up prompts:** _(none needed)_

---

## Problem 7 — Backend routes

- **Status:** Complete.
- **Prompt typed:**

  > problem 7: backend routes
  > your react frontend dashboard (problem 8) needs a backend it can call. in "backend/main.py", use 'FastAPI' and 'add routes' that do the following:
  >
  > * return the three tickets and whether each is open or resolved
  > * take a ticket id and run your agent team on that ticket
  > * return recent agent events - what each agent said and which tools they used - so the board can refresh
  > * approve a payment or purchase after a human clicks approve (agents only prepare the pay; this route is what actually changes cash)
  > * return the current checking balance from 'cash_accounts'
  > * reset the database to the original values when you want to try a fresh run
  >
  > from the "backend/" folder, start the server with: uvicorn main:app --reload --port 8000
  >
  > this turns on the backend at "http://localhost:8000" so the frontend dashboard can call those routes. in 'output/harness.md", list each route in one line (what URL/what it does).

- **Follow-up prompts:** _(none needed)_

---

## Problem 8 — Agent dashboard

- **Status:** Complete.
- **Prompt typed:**

  > problem 8: agent dashboard
  > build the frontend dashboard in "frontend/" with React + Vite + TypeScript. the page should call the routes you built in problem 7. at minimum the board should:
  >
  > * list all three tickets
  > * let you pick one ticket and start the agent team on it
  > * show each agent and what they are saying / doing while the ticket runs
  > * mark a ticket resolved when the run finishes
  > * show a short summary of what each agent did on that ticket
  > * let a human approve a pay or purchase when asked
  > * show the checking balance (it should drop after an approved pay)
  >
  > make the dashboard look good. be creative with the layout and feel - this is a real desk people would want to sit at, so put thought into how it looks
  >
  > tell the front end to talk to your backend at "http://localhost:8000". on the backend, allow the vite page origin (usually "http://localhost:5173") so the browser is allowed to call those routes. start the board with "npm run dev"
  >
  > this opens the react desk in your browser so you can pick tickets and watch agents
  >
  > write output/design.md with what you chose for the dashboard look (layout, how agents read differently, how resolved tickets and cash show up) and why - including the creative choices that make it feel special and something humans would actually enjoy using

- **Follow-up prompts:** _(none needed)_

---

## Problem 9 — Resolve the tickets

- **Status:** Complete.
- **Prompt typed:**

  > Problem 9: Resolve the tickets
  > before testing the agents on a full run over the three tickets, reset the working database "data/campus_customs_new.db" again so you start clean. Note the starting checking balance. Then run all three tickets on the board (101, 102, 103) until each is resolved. Open "output/desk_tickets.html" from Problem 6. On each ticket tab, fill the Actual section from this run: which agents worked, what they delegated, and which tools they used. Keep your Expected section so you can compare the two.
  > On the Cash tab of the same "output/desk_tickets.html", itemize the money:
  >
  > * starting checking balance (after the reset)
  > * for each ticket: how cash changed when that ticket resolved, and why (which pay/purchase, dollar amount)
  > * ending checking balance - it must match "cash_accounts" in the working database
  >
  > wrong cash math loses points even if the board shows every ticket resolved. also save:
  >
  > * output/resolved_tickets.json - for each ticket: id, final status, short outcome, what each agent contributed, and any human approvals
  > * output/resolved_board.html - a page you can double-click with a screenshot of your React board for EACH resolved ticket (101, 102, and 103)
  >
  > append real runs to "output/audit_trail.json". finish "output/harness.md" so it covers tables, MCP tools, the five agents, API routes, the dashboard and safety rules

- **Follow-up prompts:** _(none needed. Before signing any cheques, I answered the vibe coder's question about payments: "Sign each one", signed as "Kristine Feng".)_

---

## Problem 10 — Reflection

- **Status:** Complete. The Reflection tab of `output/desk_tickets.html` is filled in.
- **Prompt typed:**

  > open output/desk_tickets.html and fill the Reflection tab. Answer in your own vibe, and be detailed and thorough:
  >
  > * how would you evaluate the performance of the agents on each ticket and why?
  > * for each ticket, how did Actual compare to the Expected plan you wrote earlier?
  > * what would have been simpler as one agent with tools - and why?
  > * describe three NEW problems campus customs might face that this agent team could solve with the tools you built
  > * describe three NEW problems campus customs might face that this agent team could NOT solve with the tools you built, and explain the tools and agents you would need to solve them
  >
  > tie every answer to THIS app and the three tickets you ran - use the ticket tabs and Cash tab on the same page as your evidence. generic AI essays without Campus Customs details will score low.

- **Follow-up prompts:** _(none needed)_

---

## Problem 11 — Submit to GitHub

- **Status:** Complete. Pushed to https://github.com/kristinefeng/hw5
- **Prompt typed:**

  > okay, problem 11: submit to GitHub
  >
  > push your code to a public GitHub repository so graders can clone it.  put the repo URL in output/github_url.txt
  >
  > do NOT push the real ".env" to the github repo. DO include both database files under "data/" (the original and your working copy) so graders can run our app easily
  >
  > expected file layout attached in a screenshot above.
  >
  > The README shoudl explain: copy original DB to the working copy wen you need a clean run, start MCP server, start FastAPI backend, start the React board, reset the DB before a full three-ticket run

- **Follow-up prompt:**

  > heres the repo link https://github.com/kristinefeng/hw5
  >
  > i think i turned the readme on by accident. can you fix the settings to be exactly what we need/as required by the assignment

  What was lacking after the first prompt: the vibe coder can't create GitHub repos from this machine, so I had to create it myself. I gave it the URL, and because the repo started with GitHub's auto-generated README, the vibe coder had to merge that starter commit (keeping the project README) before pushing.

---

_Sections will be appended for each remaining problem as we work through the assignment._
