import { useEffect, useRef, useState } from "react";
import { money } from "../timeline";
import type { Payment } from "../types";

const CUSHION = 500;

// Count smoothly from the old balance to the new one, so a payment is felt, not just seen.
function useTweened(target: number, ms = 900): number {
  const [shown, setShown] = useState(target);
  const from = useRef(target);
  useEffect(() => {
    const start = performance.now();
    const begin = from.current;
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ms);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(begin + (target - begin) * eased);
      if (t < 1) frame = requestAnimationFrame(tick);
      else from.current = target;
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, ms]);
  return shown;
}

export function CashTill({ balance, pending, payments }: { balance: number | null; pending: number; payments: Payment[] }) {
  const shown = useTweened(balance ?? 0);
  const [open, setOpen] = useState(false);
  const [drop, setDrop] = useState<{ amount: number; key: number } | null>(null);
  const last = useRef<number | null>(null);
  const peak = useRef(0);

  useEffect(() => {
    if (balance === null) return;
    if (last.current !== null && balance < last.current) setDrop({ amount: last.current - balance, key: Date.now() });
    last.current = balance;
    peak.current = Math.max(peak.current, balance);
  }, [balance]);

  const scale = Math.max(peak.current, balance ?? 0, 1);
  const after = (balance ?? 0) - pending;
  const pct = (n: number) => `${Math.max(0, Math.min(100, (n / scale) * 100))}%`;
  const low = (balance ?? 0) < CUSHION;

  return (
    <div className={`till ${low ? "till--low" : ""}`}>
      <button className="till__face" onClick={() => setOpen((o) => !o)} aria-expanded={open} title="Show the payment ledger">
        <span className="till__label">Checking</span>
        <span className="till__amount" aria-live="polite">{balance === null ? "—" : money(shown)}</span>
        {drop && (
          <span key={drop.key} className="till__drop" onAnimationEnd={() => setDrop(null)}>
            −{money(drop.amount)}
          </span>
        )}
      </button>

      <div className="till__gauge" aria-hidden="true">
        <div className="till__fill" style={{ width: pct(balance ?? 0) }} />
        {pending > 0 && <div className="till__pending" style={{ left: pct(Math.max(after, 0)), width: pct(Math.min(pending, balance ?? 0)) }} />}
        <div className="till__cushion" style={{ left: pct(CUSHION) }} />
      </div>
      <div className="till__note">
        {pending > 0 ? (
          <>
            <b>{money(pending)}</b> waiting for your signature → leaves{" "}
            <b className={after < CUSHION ? "warn" : ""}>{money(after)}</b>
          </>
        ) : (
          <>Cushion line at {money(CUSHION)}</>
        )}
      </div>

      {open && (
        <div className="ledger" role="dialog" aria-label="Payments ledger">
          <div className="ledger__title">Ledger · payments out</div>
          {payments.length === 0 ? (
            <p className="ledger__empty">Nothing paid yet. Every payment needs your signature.</p>
          ) : (
            <ul>
              {payments.map((p) => (
                <li key={p.id}>
                  <span>
                    {p.kind} #{p.ref_id}
                    <small>
                      {p.paid_at} · signed {p.approved_by}
                    </small>
                  </span>
                  <b>−{money(p.amount)}</b>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
