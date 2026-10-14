import { useState } from "react";
import { api } from "../api";
import { AgentIcon, SEATS, SPECIALISTS, toolPhrase } from "../agents";
import { money, type Timeline } from "../timeline";
import type { Approval, Decision, Role, Run, Ticket } from "../types";

const STATUS_LABEL: Record<string, string> = {
  needs_approval: "Needs your approval",
  waiting_on_vendor: "Waiting on a vendor",
  waiting_on_customer: "Waiting on the customer",
  in_progress: "More work needed",
  resolved: "Nothing left to do",
  open: "Open",
};

export function BossCall({ decision }: { decision: Decision }) {
  return (
    <section className="memo" style={{ ["--ink" as string]: SEATS.boss.ink }}>
      <header>
        <span className="memo__from">
          <AgentIcon who="boss" size={18} /> Memo from the Boss
        </span>
        <span className={`pill pill--${decision.status}`}>Recommends: {STATUS_LABEL[decision.status] ?? decision.status}</span>
      </header>
      <p className="memo__summary">{decision.summary}</p>
      {decision.next_steps.length > 0 && (
        <>
          <h4>Next steps</h4>
          <ul>
            {decision.next_steps.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function Cheque({ approval, index, run, ticket, balance, signer, onSigner, onPaid }: {
  approval: Approval;
  index: number;
  run: Run;
  ticket: Ticket;
  balance: number | null;
  signer: string;
  onSigner: (name: string) => void;
  onPaid: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const paid = approval.approval?.status === "approved";
  const payable = approval.pay_kind && approval.ref_id !== null && approval.amount !== null;
  const after = balance !== null && approval.amount !== null ? balance - approval.amount : null;

  async function sign() {
    setBusy(true);
    setError(null);
    try {
      await api.approve({ approval, approvedBy: signer.trim(), ticketId: ticket.id, runId: run.run_id, index });
      onPaid();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className={`cheque ${paid ? "cheque--paid" : ""}`}>
      <div className="cheque__top">
        <span className="cheque__bank">Campus Customs · Checking</span>
        <span className="cheque__no">No. {run.run_id.slice(0, 4).toUpperCase()}-{index + 1}</span>
      </div>
      <div className="cheque__row">
        <span className="cheque__label">Pay to the order of</span>
        <span className="cheque__payee">{approval.payee ?? approval.reference ?? "—"}</span>
        <span className="cheque__amount">{approval.amount !== null ? money(approval.amount) : "amount TBD"}</span>
      </div>
      <div className="cheque__memo">
        <span className="cheque__label">Memo</span> {approval.description}
      </div>
      {!paid && after !== null && (
        <div className={`cheque__after ${after < 500 ? "warn" : ""}`}>
          Checking after this: <b>{money(after)}</b>
          {after < 500 && " · below the $500 cushion"}
        </div>
      )}
      <div className="cheque__sign">
        {paid ? (
          <span className="cheque__signature">{approval.approval!.approved_by}</span>
        ) : (
          <input
            value={signer}
            onChange={(e) => onSigner(e.target.value)}
            placeholder="Sign your name"
            aria-label="Your name, as the approver"
          />
        )}
        <span className="cheque__label">Authorized signature</span>
      </div>
      {!paid && (
        <div className="cheque__actions">
          <button className="btn btn--ink" disabled={!payable || !signer.trim() || busy} onClick={sign}>
            {busy ? "Paying…" : `Sign & pay ${approval.amount !== null ? money(approval.amount) : ""}`}
          </button>
          {!payable && <span className="muted">This one has no payable record attached, so it can't be paid from here.</span>}
        </div>
      )}
      {error && <p className="cheque__error">Refused: {error}</p>}
      {paid && (
        <>
          <span className="stamp stamp--paid">Paid</span>
          <p className="cheque__receipt">
            {approval.approval!.effect} Checking now {money(approval.approval!.balance_after)}.
            {approval.approval!.warnings.map((w) => (
              <span key={w} className="warn"> {w}</span>
            ))}
          </p>
        </>
      )}
    </article>
  );
}

function Letter({ to, text }: { to: string; text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <section className="letter">
      <header>
        <span>Draft reply to {to}</span>
        <button
          className="btn btn--ghost"
          onClick={() => navigator.clipboard.writeText(text).then(() => setCopied(true))}
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </header>
      <p>{text}</p>
      <footer>Not sent. Agents draft, you decide.</footer>
    </section>
  );
}

const KIND_LABEL: Record<string, string> = {
  discount: "Discount",
  refund: "Refund",
  customer_message: "Customer reply",
  vendor_order: "Vendor order",
  other: "Other",
};

export function SignOffs(props: {
  decision: Decision;
  run: Run;
  ticket: Ticket;
  balance: number | null;
  signer: string;
  onSigner: (name: string) => void;
  onPaid: () => void;
}) {
  const { decision, ticket } = props;
  const cards = decision.approvals_needed.map((a, index) => ({ a, index }));
  const cheques = cards.filter(({ a }) => a.kind === "payment");
  const slips = cards.filter(({ a }) => a.kind !== "payment");
  if (!cards.length && !decision.customer_reply_draft) return null;

  return (
    <section className="signoffs">
      <h3>Waiting for your signature</h3>
      {cheques.length > 0 && (
        <div className="cheques">
          {cheques.map(({ a, index }) => (
            <Cheque key={index} approval={a} index={index} {...props} />
          ))}
        </div>
      )}
      {slips.length > 0 && (
        <ul className="slips">
          {slips.map(({ a, index }) => (
            <li key={index} className="slip">
              <b>{KIND_LABEL[a.kind] ?? a.kind}</b>
              <span>{a.description}</span>
              {a.amount !== null && <em>{money(a.amount)}</em>}
            </li>
          ))}
        </ul>
      )}
      {decision.customer_reply_draft && <Letter to={ticket.requester} text={decision.customer_reply_draft} />}
    </section>
  );
}

export function WhoDidWhat({ timeline, decision }: { timeline: Timeline; decision: Decision | null }) {
  const roles: Role[] = ["boss", ...SPECIALISTS];
  const worked = roles.filter((r) => timeline.seats[r].calls > 0);
  const out = roles.filter((r) => timeline.seats[r].calls === 0);
  return (
    <section className="crew">
      <h3>Who did what</h3>
      <div className="crew__cards">
        {worked.map((r) => {
          const s = timeline.seats[r];
          const summary = r === "boss" ? decision?.summary ?? s.line : s.summary ?? s.line;
          return (
            <article key={r} className="crew__card" style={{ ["--ink" as string]: SEATS[r].ink, ["--wash" as string]: SEATS[r].wash }}>
              <header>
                <span className="crew__icon">
                  <AgentIcon who={r} size={18} />
                </span>
                <b>{SEATS[r].name}</b>
                {s.askedBy.length > 0 && <small>asked by {s.askedBy.map((a) => SEATS[a].name).join(", ")}</small>}
              </header>
              <p>{summary}</p>
              <div className="crew__tools">
                {Object.entries(s.tools).map(([tool, n]) => (
                  <span key={tool} title={toolPhrase(tool)}>
                    {tool}
                    {n > 1 && <i>×{n}</i>}
                  </span>
                ))}
                {s.askedOut.map((a) => (
                  <span key={a} className="crew__handoff">
                    → {SEATS[a].name}
                  </span>
                ))}
              </div>
            </article>
          );
        })}
      </div>
      {out.length > 0 && (
        <p className="crew__out">
          Sat this one out: {out.map((r) => SEATS[r].name).join(", ")}. Not every ticket needs every desk.
        </p>
      )}
    </section>
  );
}
