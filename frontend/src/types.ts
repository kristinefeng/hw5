// Shapes returned by the Campus Customs API (backend/main.py).

export type Role = "boss" | "inventory" | "accounting" | "facilities" | "customer_service";
export type Actor = Role | "human" | "system";

export interface ApprovalReceipt {
  status: "approved";
  payment_id: number;
  approved_by: string;
  amount: number;
  paid_at: string;
  balance_before: number;
  balance_after: number;
  effect: string;
  warnings: string[];
}

export interface Approval {
  kind: "payment" | "discount" | "refund" | "customer_message" | "vendor_order" | "other";
  description: string;
  amount: number | null;
  reference: string | null;
  pay_kind: "invoice" | "rent" | "purchase" | null;
  ref_id: number | null;
  payee: string | null;
  approval?: ApprovalReceipt;
}

export interface Decision {
  ticket_id: number;
  status: string;
  summary: string;
  agents_consulted: Role[];
  actions_taken: string[];
  approvals_needed: Approval[];
  customer_reply_draft: string | null;
  next_steps: string[];
}

export interface Run {
  run_id: string;
  ticket_id: number;
  state: "running" | "done" | "stopped" | "error";
  started_at: string;
  finished_at: string | null;
  decision: Decision | null;
  error: string | null;
}

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  lease_id: number | null;
  invoice_id: number | null;
  status: string;
  notes: string | null;
  created_at: string;
  state: "open" | "resolved";
  running_run_id: string | null;
  latest_run: Run | null;
}

export interface ToolCall {
  tool: string;
  tool_call_id: string;
  args: Record<string, unknown>;
}

export interface ToolResult {
  tool: string;
  tool_call_id: string;
  content: string;
}

export interface AgentEvent {
  seq: number;
  ts: string;
  run_id: string;
  ticket_id: number | null;
  agent: Actor;
  chain: Actor[];
  kind:
    | "run_start"
    | "user_prompt"
    | "model_request"
    | "model_response"
    | "end"
    | "delegation_sent"
    | "delegation_returned"
    | "delegation_refused"
    | "error"
    | "human_approval"
    | "database_reset";
  said: string | null;
  tools: ToolCall[];
  tool_results: ToolResult[];
  usage: { input_tokens: number; output_tokens: number; cache_read_tokens: number } | null;
  to: Role | null;
  from: Role | null;
  summary: string | null;
  call_id: string | null;
}

export interface Cash {
  account: string;
  balance: number;
  as_of: string;
  shop_date: string;
}

export interface Payment {
  id: number;
  kind: string;
  ref_id: number;
  amount: number;
  account: string;
  paid_at: string;
  approved_by: string;
}
