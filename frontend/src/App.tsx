import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { API_BASE, api } from "./api";
import { AgentFloor } from "./components/AgentFloor";
import { CashTill } from "./components/CashTill";
import { BossCall, SignOffs, WhoDidWhat } from "./components/Outcome";
import { TicketRail } from "./components/TicketRail";
import { Transcript } from "./components/Transcript";
import { buildTimeline, clock, estimateCost, prettyDate } from "./timeline";
import type { AgentEvent, Cash, Payment, Run, Ticket } from "./types";

const POLL_MS = 1200;

function duration(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function kTokens(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

function TicketCard({ ticket, run, onStart, starting, liveFor, tokens }: {
  ticket: Ticket;
  run: Run | null;
  onStart: () => void;
  starting: boolean;
  liveFor: number | null;
  tokens: { input: number; output: number };
}) {
  const running = !!ticket.running_run_id;
  const [original, ...log] = (ticket.notes ?? "").split("\n");
  const total = tokens.input + tokens.output;
  const ran = run && run.finished_at ? Date.parse(run.finished_at) - Date.parse(run.started_at) : null;

  return (
    <section className="ticket">
      <div className="ticket__head">
        <div>
          <div className="ticket__no">
            No. {ticket.id} · {ticket.type.replace(/_/g, " ")} · {ticket.requester} · {clock(ticket.created_at)}
          </div>
          <h1>{ticket.subject}</h1>
        </div>
        <div className="ticket__action">
          {running ? (
            <div className="working">
              <span className="working__dots" aria-hidden="true">
                <i />
                <i />
                <i />
              </span>
              Team at work · {duration(liveFor ?? 0)} · {kTokens(total)} tokens
            </div>
          ) : (
            <button className={`btn ${ticket.state === "resolved" ? "btn--ghost" : "btn--brass"}`} onClick={onStart} disabled={starting}>
              {starting ? "Calling the team…" : ticket.state === "resolved" ? "Run the team again" : "Start the team"}
            </button>
          )}
        </div>
      </div>

      <div className="ticket__facts">
        {ticket.sku && (
          <span>
            {ticket.qty} × {ticket.sku} · size {ticket.size}
          </span>
        )}
        {ticket.invoice_id && <span>Invoice #{ticket.invoice_id}</span>}
        {ticket.lease_id && <span>Lease #{ticket.lease_id}</span>}
        <span>Status: {ticket.status.replace(/_/g, " ")}</span>
      </div>

      {original && <blockquote className="ticket__note">“{original}”</blockquote>}
      {log.length > 0 && (
        <details className="ticket__log">
          <summary>{log.length} note{log.length > 1 ? "s" : ""} filed on this ticket</summary>
          <ul>
            {log.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        </details>
      )}

      {run && !running && ran !== null && (
        <div className="ticket__meta">
          Last run {run.run_id} · {duration(ran)} · {kTokens(total)} tokens · ≈ ${estimateCost(tokens).toFixed(4)} on gpt-6-luna
        </div>
      )}
    </section>
  );
}

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [cash, setCash] = useState<Cash | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [events, setEvents] = useState<Record<string, AgentEvent[]>>({});
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState<number | null>(null);
  const [signer, setSignerState] = useState(() => localStorage.getItem("cc-desk-signer") ?? "");
  const [now, setNow] = useState(Date.now());
  const eventsRef = useRef(events);
  eventsRef.current = events;

  const setSigner = (name: string) => {
    setSignerState(name);
    localStorage.setItem("cc-desk-signer", name);
  };

  const refresh = useCallback(async () => {
    try {
      const [t, c, p] = await Promise.all([api.tickets(), api.cash(), api.payments()]);
      setTickets(t);
      setCash(c);
      setPayments(p);
      setError(null);
      setSelected((s) => s ?? t.find((x) => x.running_run_id)?.id ?? t[0]?.id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const mergeEvents = useCallback((runId: string, fresh: AgentEvent[]) => {
    if (!fresh.length) return;
    setEvents((m) => {
      const have = m[runId] ?? [];
      const last = have.length ? have[have.length - 1].seq : -1;
      return { ...m, [runId]: [...have, ...fresh.filter((e) => e.seq > last)] };
    });
  }, []);

  const ticket = tickets.find((t) => t.id === selected) ?? null;
  const run = ticket?.latest_run ?? null;
  const runId = run?.run_id ?? null;

  // Load the transcript for whichever ticket is on the desk.
  useEffect(() => {
    if (runId && !eventsRef.current[runId]) api.events(runId).then((ev) => mergeEvents(runId, ev)).catch(() => {});
  }, [runId, mergeEvents]);

  // While any team is at work, pull new events and check whether the run is finished.
  const running = tickets.flatMap((t) => (t.running_run_id ? [t.running_run_id] : []));
  const runningKey = running.join(",");
  useEffect(() => {
    if (!runningKey) return;
    const ids = runningKey.split(",");
    let busy = false;
    const pull = async (id: string) => {
      const have = eventsRef.current[id] ?? [];
      mergeEvents(id, await api.events(id, have.length ? have[have.length - 1].seq : undefined));
    };
    const tick = async () => {
      if (busy) return;
      busy = true;
      try {
        await Promise.all(ids.map(pull));
        const runs = await Promise.all(ids.map(api.run));
        if (runs.some((r) => r.state !== "running")) {
          await Promise.all(ids.map(pull)); // catch the last few events
          await refresh();
        }
      } catch {
        /* keep polling; a blip shouldn't stop the board */
      } finally {
        busy = false;
      }
    };
    const timer = setInterval(tick, POLL_MS);
    const clockTimer = setInterval(() => setNow(Date.now()), 1000);
    return () => {
      clearInterval(timer);
      clearInterval(clockTimer);
    };
  }, [runningKey, mergeEvents, refresh]);

  async function start(id: number) {
    setStarting(id);
    try {
      const r = await api.runTicket(id);
      setEvents((m) => ({ ...m, [r.run_id]: [] }));
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setStarting(null);
    }
  }

  async function resetDesk() {
    if (!window.confirm("Reset the shop database to its original values? Tickets reopen and cash returns to the starting balance. The audit trail is kept.")) return;
    try {
      await api.reset();
      setEvents({});
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  const runEvents = useMemo(() => (runId ? events[runId] ?? [] : []), [events, runId]);
  const timeline = useMemo(() => (runEvents.length ? buildTimeline(runEvents) : null), [runEvents]);
  const isRunning = !!ticket?.running_run_id;
  const finished = run?.state === "done" || run?.state === "stopped" || run?.state === "error";

  const pending = tickets
    .flatMap((t) => t.latest_run?.decision?.approvals_needed ?? [])
    .filter((a) => a.kind === "payment" && a.amount !== null && a.approval?.status !== "approved")
    .reduce((sum, a) => sum + (a.amount ?? 0), 0);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand__crest">CC</span>
          <div>
            <div className="brand__name">Campus Customs</div>
            <div className="brand__sub">Back office desk · Chapel Street</div>
          </div>
        </div>
        <div className="topbar__date">{cash ? prettyDate(cash.shop_date) : "—"}</div>
        <div className="topbar__right">
          <CashTill balance={cash?.balance ?? null} pending={pending} payments={payments} />
          <button className="btn btn--quiet" onClick={resetDesk} title="Restore the original database for a fresh run">
            Reset desk
          </button>
        </div>
      </header>

      {error && (
        <div className="banner" role="alert">
          {error}
          {error.includes("reach") && (
            <code>cd hw5/backend && source ../.venv/bin/activate && uvicorn main:app --reload --port 8000</code>
          )}
          <button className="btn btn--quiet" onClick={refresh}>
            Try again
          </button>
        </div>
      )}

      <main className="desk">
        <TicketRail tickets={tickets} selected={selected} onSelect={setSelected} />

        <section className="desk__center">
          {ticket ? (
            <>
              <TicketCard
                ticket={ticket}
                run={run}
                onStart={() => start(ticket.id)}
                starting={starting === ticket.id}
                liveFor={isRunning && run ? now - Date.parse(run.started_at) : null}
                tokens={timeline?.tokens ?? { input: 0, output: 0 }}
              />
              <AgentFloor timeline={timeline} running={isRunning} finished={finished} />
              {!run && !isRunning && <p className="hint">The team is seated and ready. Start the team to watch the Boss route this ticket.</p>}
              {run?.state === "done" && run.decision && (
                <>
                  <BossCall decision={run.decision} />
                  <SignOffs
                    decision={run.decision}
                    run={run}
                    ticket={ticket}
                    balance={cash?.balance ?? null}
                    signer={signer}
                    onSigner={setSigner}
                    onPaid={refresh}
                  />
                </>
              )}
              {(run?.state === "stopped" || run?.state === "error") && (
                <div className="notice">
                  The run {run.state === "stopped" ? "hit its token limit and stopped" : `failed: ${run.error}`}. The ticket stays open, so you can run the team again.
                </div>
              )}
              {timeline && finished && <WhoDidWhat timeline={timeline} decision={run?.decision ?? null} />}
            </>
          ) : (
            <p className="hint">{error ? "" : "Loading the inbox…"}</p>
          )}
        </section>

        <Transcript events={runEvents} results={timeline?.results ?? new Map()} live={isRunning} />
      </main>

      <footer className="foot">
        Agents read the shop through MCP and can only recommend. Money moves only when you sign. · API {API_BASE}
      </footer>
    </div>
  );
}
