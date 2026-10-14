import { clock } from "../timeline";
import type { Ticket } from "../types";

const TYPE_LABEL: Record<string, string> = {
  customer_order: "Customer order",
  rent_notice: "Rent notice",
  price_override: "Price request",
};

export function unsigned(t: Ticket): number {
  const cards = t.latest_run?.decision?.approvals_needed ?? [];
  return cards.filter((a) => a.kind === "payment" && a.approval?.status !== "approved").length;
}

function Stamp({ t }: { t: Ticket }) {
  if (t.running_run_id) return <span className="stamp stamp--working">Working</span>;
  if (t.state === "resolved") return <span className="stamp stamp--resolved">Resolved</span>;
  const run = t.latest_run;
  if (run && (run.state === "stopped" || run.state === "error")) return <span className="stamp stamp--stopped">Stopped</span>;
  return <span className="stamp stamp--open">Open</span>;
}

export function TicketRail({ tickets, selected, onSelect }: { tickets: Ticket[]; selected: number | null; onSelect: (id: number) => void }) {
  const open = tickets.filter((t) => t.state === "open").length;
  return (
    <aside className="inbox" aria-label="Tickets">
      <div className="inbox__head">
        <h2>Inbox</h2>
        <span>
          {open} open · {tickets.length - open} resolved
        </span>
      </div>
      <ul className="stubs">
        {tickets.map((t) => {
          const toSign = unsigned(t);
          return (
            <li key={t.id}>
              <button
                className={`stub stub--${t.type} ${selected === t.id ? "stub--selected" : ""} ${t.state === "resolved" ? "stub--resolved" : ""}`}
                onClick={() => onSelect(t.id)}
                aria-pressed={selected === t.id}
              >
                <span className="stub__no">No. {t.id}</span>
                <span className="stub__type">{TYPE_LABEL[t.type] ?? t.type}</span>
                <span className="stub__subject">{t.subject}</span>
                <span className="stub__from">
                  {t.requester} · {clock(t.created_at)}
                </span>
                {toSign > 0 && <span className="stub__sign">✍ {toSign} to sign</span>}
                <Stamp t={t} />
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
