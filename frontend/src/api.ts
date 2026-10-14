// The desk talks to the Campus Customs API. Set VITE_API_BASE in frontend/.env to move it.
import type { AgentEvent, Approval, ApprovalReceipt, Cash, Payment, Run, Ticket } from "./types";

export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(0, `Can't reach the backend at ${API_BASE}. Is uvicorn running?`);
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = body?.detail;
    const message = typeof detail === "string" ? detail : Array.isArray(detail) ? detail[0]?.msg : res.statusText;
    throw new ApiError(res.status, message ?? `Request failed (${res.status})`);
  }
  return body as T;
}

export const api = {
  tickets: () => call<Ticket[]>("/tickets"),
  runTicket: (ticketId: number) => call<Run>(`/tickets/${ticketId}/run`, { method: "POST" }),
  run: (runId: string) => call<Run>(`/runs/${runId}`),
  events: (runId: string, after?: number) =>
    call<AgentEvent[]>(`/events?run_id=${runId}&limit=1000${after !== undefined ? `&after=${after}` : ""}`),
  cash: () => call<Cash>("/cash"),
  payments: () => call<Payment[]>("/payments"),
  reset: () => call<{ ok: boolean; message: string }>("/reset", { method: "POST" }),
  approve: (args: {
    approval: Approval;
    approvedBy: string;
    ticketId: number;
    runId: string;
    index: number;
  }) =>
    call<ApprovalReceipt>("/payments/approve", {
      method: "POST",
      body: JSON.stringify({
        kind: args.approval.pay_kind,
        ref_id: args.approval.ref_id,
        amount: args.approval.amount,
        approved_by: args.approvedBy,
        ticket_id: args.ticketId,
        run_id: args.runId,
        approval_index: args.index,
        description: args.approval.description,
      }),
    }),
};
