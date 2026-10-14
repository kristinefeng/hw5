import { AgentIcon, SEATS, SPECIALISTS } from "../agents";
import type { Timeline } from "../timeline";
import type { Role } from "../types";

// Seat positions on a 1000 × 380 floor plan (x as a share of width, y in px).
const SPOT: Record<Role, { x: number; y: number }> = {
  boss: { x: 500, y: 58 },
  inventory: { x: 125, y: 200 },
  accounting: { x: 375, y: 200 },
  facilities: { x: 625, y: 200 },
  customer_service: { x: 875, y: 200 },
};

function edgePath(from: Role, to: Role): string {
  const a = SPOT[from];
  const b = SPOT[to];
  if (a.y === b.y) {
    // specialist to specialist: arc up over the row
    return `M ${a.x} ${a.y - 30} Q ${(a.x + b.x) / 2} ${a.y - 110} ${b.x} ${b.y - 30}`;
  }
  return `M ${a.x} ${a.y} L ${b.x} ${b.y}`;
}

const STATUS_WORD = { idle: "", working: "working", waiting: "waiting", done: "done", error: "error" } as const;

export function AgentFloor({ timeline, running, finished }: { timeline: Timeline | null; running: boolean; finished: boolean }) {
  const roles: Role[] = ["boss", ...SPECIALISTS];
  const used = new Set(timeline?.edges.map((e) => `${e.from}>${e.to}`));

  return (
    <div className={`floor ${running ? "floor--live" : ""}`}>
      <svg className="floor__wires" viewBox="0 0 1000 380" preserveAspectRatio="none" aria-hidden="true">
        {SPECIALISTS.filter((r) => !used.has(`boss>${r}`)).map((r) => (
          <path key={r} d={edgePath("boss", r)} className="wire wire--idle" />
        ))}
        {timeline?.edges.map((e) => (
          <path
            key={`${e.from}>${e.to}`}
            d={edgePath(e.from, e.to)}
            className={`wire wire--${e.state}`}
            style={{ stroke: SEATS[e.to].ink }}
          />
        ))}
      </svg>

      {roles.map((role) => {
        const seat = timeline?.seats[role];
        const status = seat?.status ?? "idle";
        const satOut = finished && status === "idle";
        const spot = SPOT[role];
        return (
          <div
            key={role}
            className={`seat seat--${role} seat--${status} ${satOut ? "seat--out" : ""}`}
            style={{ left: `${spot.x / 10}%`, top: spot.y - 36, ["--ink" as string]: SEATS[role].ink, ["--wash" as string]: SEATS[role].wash }}
          >
            <div className="seat__avatar">
              <AgentIcon who={role} size={30} />
              {status !== "idle" && <span className={`seat__badge seat__badge--${status}`}>{STATUS_WORD[status]}</span>}
            </div>
            <div className="seat__name">{SEATS[role].name}</div>
            <div className="seat__desk">{satOut ? "Sat this one out" : SEATS[role].desk}</div>
            {seat?.line && (
              <div className="seat__bubble" key={seat.line}>
                {seat.line}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
