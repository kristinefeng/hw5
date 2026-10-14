// Turn a run's audit events into what the board shows: where each agent is,
// which hand-offs are live, and a per-agent summary of what they did.
import { SEATS, toolArgs, toolPhrase } from "./agents";
import type { AgentEvent, Role, ToolCall } from "./types";

export type SeatStatus = "idle" | "working" | "waiting" | "done" | "error";

export interface SeatState {
  status: SeatStatus;
  line: string; // what they're saying / doing right now
  tools: Record<string, number>; // shop tools used, with counts
  askedBy: Role[];
  askedOut: Role[];
  summary: string | null; // their report, in one line
  calls: number; // times they were brought in
}

export interface Edge {
  from: Role;
  to: Role;
  state: "active" | "done";
}

export interface Timeline {
  seats: Record<Role, SeatState>;
  edges: Edge[];
  tokens: { input: number; output: number };
  results: Map<string, string>; // tool_call_id -> tool result text
  startedAt: number | null;
  lastAt: number | null;
}

const ROLES: Role[] = ["boss", "inventory", "accounting", "facilities", "customer_service"];

function blank(): SeatState {
  return { status: "idle", line: "", tools: {}, askedBy: [], askedOut: [], summary: null, calls: 0 };
}

function describeCalls(calls: ToolCall[]): string {
  const shop = calls.filter((c) => c.tool !== "delegate");
  if (!shop.length) return "";
  const first = shop[0];
  const extra = shop.length > 1 ? ` (+${shop.length - 1} more)` : "";
  const args = toolArgs(first.args);
  return `${toolPhrase(first.tool)}${args ? ` · ${args}` : ""}${extra}`;
}

const isRole = (a: string | null | undefined): a is Role => !!a && (ROLES as string[]).includes(a);

export function buildTimeline(events: AgentEvent[]): Timeline {
  const seats = Object.fromEntries(ROLES.map((r) => [r, blank()])) as Record<Role, SeatState>;
  const edges = new Map<string, Edge>();
  const pending: Record<Role, number> = { boss: 0, inventory: 0, accounting: 0, facilities: 0, customer_service: 0 };
  const results = new Map<string, string>();
  const tokens = { input: 0, output: 0 };
  let startedAt: number | null = null;
  let lastAt: number | null = null;

  for (const e of events) {
    const at = Date.parse(e.ts);
    startedAt ??= at;
    lastAt = at;
    if (e.usage) {
      tokens.input += e.usage.input_tokens;
      tokens.output += e.usage.output_tokens;
    }
    for (const r of e.tool_results) results.set(r.tool_call_id, r.content);
    if (!isRole(e.agent)) continue;
    const seat = seats[e.agent];

    switch (e.kind) {
      case "run_start": {
        seat.calls += 1;
        seat.status = "working";
        const caller = e.chain[e.chain.length - 2];
        if (isRole(caller) && !seat.askedBy.includes(caller)) seat.askedBy.push(caller);
        seat.line = isRole(caller) ? `Picked up a request from ${SEATS[caller].name}` : "Opened the ticket";
        break;
      }
      case "model_response": {
        for (const c of e.tools) if (c.tool !== "delegate") seat.tools[c.tool] = (seat.tools[c.tool] ?? 0) + 1;
        const doing = describeCalls(e.tools);
        if (doing) seat.line = doing;
        else if (e.said) seat.line = e.said;
        break;
      }
      case "model_request":
        if (e.tool_results.length && pending[e.agent] === 0) seat.line = "Reading what came back";
        break;
      case "delegation_sent":
        if (isRole(e.to)) {
          edges.set(`${e.agent}>${e.to}`, { from: e.agent, to: e.to, state: "active" });
          if (!seat.askedOut.includes(e.to)) seat.askedOut.push(e.to);
          pending[e.agent] += 1;
          seat.status = "waiting";
          seat.line = `Asked ${SEATS[e.to].name} for help`;
        }
        break;
      case "delegation_returned":
        if (isRole(e.from)) {
          const edge = edges.get(`${e.agent}>${e.from}`);
          if (edge) edge.state = "done";
          pending[e.agent] = Math.max(0, pending[e.agent] - 1);
          if (pending[e.agent] === 0) seat.status = "working";
          seat.line = `${SEATS[e.from].name} reported back`;
          if (e.summary) {
            seats[e.from].summary = e.summary;
            seats[e.from].line = e.summary;
          }
        }
        break;
      case "delegation_refused":
        seat.line = e.said ?? "A hand-off was refused";
        break;
      case "end":
        seat.status = "done";
        seat.line = e.agent === "boss" ? "Decision filed" : seat.summary ?? "Report filed";
        break;
      case "error":
        seat.status = "error";
        seat.line = e.said ?? "Something went wrong";
        break;
    }
  }
  return { seats, edges: [...edges.values()], tokens, results, startedAt, lastAt };
}

// gpt-6-luna list price, USD per million tokens (input / output).
export function estimateCost(tokens: { input: number; output: number }): number {
  return (tokens.input * 0.1 + tokens.output * 0.5) / 1_000_000;
}

export const money = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });

export function prettyDate(iso: string): string {
  const d = new Date(`${iso.slice(0, 10)}T12:00:00`);
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
}

export function clock(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}
