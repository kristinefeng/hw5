// Who sits at the desk, and how each one looks and talks on the board.
import type { Actor, Role } from "./types";

export interface Seat {
  name: string;
  desk: string; // where they sit / what they own
  ink: string; // their colour on the board
  wash: string; // pale background for their bubbles
}

export const SEATS: Record<Actor, Seat> = {
  boss: { name: "Boss", desk: "Runs the desk", ink: "#16335e", wash: "#e7edf7" },
  inventory: { name: "Inventory", desk: "The stockroom", ink: "#2c6e4f", wash: "#e3f1ea" },
  accounting: { name: "Accounting", desk: "The ledger", ink: "#9a6a12", wash: "#f8eed7" },
  facilities: { name: "Facilities", desk: "Lease & landlord", ink: "#9c4527", wash: "#f7e6df" },
  customer_service: { name: "Customer Service", desk: "Front counter", ink: "#8e2f62", wash: "#f5e3ed" },
  human: { name: "You", desk: "Owner", ink: "#1f1f1f", wash: "#eeeeee" },
  system: { name: "Desk", desk: "System", ink: "#6b6b6b", wash: "#f0f0f0" },
};

export const SPECIALISTS: Role[] = ["inventory", "accounting", "facilities", "customer_service"];

const paths: Record<Actor, string> = {
  // briefcase
  boss: "M9 6V4.5A1.5 1.5 0 0 1 10.5 3h3A1.5 1.5 0 0 1 15 4.5V6h4.5A1.5 1.5 0 0 1 21 7.5v10a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5v-10A1.5 1.5 0 0 1 4.5 6H9Zm1.5 0h3V4.5h-3V6ZM3 11.5h18M10.5 11.5v2h3v-2",
  // box
  inventory: "M12 2.8 20.5 7v10L12 21.2 3.5 17V7L12 2.8Zm0 0v0M3.5 7 12 11.2 20.5 7M12 11.2v10M7.8 4.9l8.5 4.2",
  // ledger with coin
  accounting: "M5 3.5h10.5A1.5 1.5 0 0 1 17 5v14.5H6.5A1.5 1.5 0 0 1 5 18V3.5Zm0 14.5a1.5 1.5 0 0 1 1.5-1.5H17M8 7.5h6M8 10.5h4M19.5 12.5a2.5 2.5 0 1 1 0 .01",
  // key
  facilities: "M14.5 3.5a5 5 0 1 1-3.9 8.1L3.5 18.7v2.3h2.8v-1.8h1.9v-1.9h1.9l1.6-1.6a5 5 0 0 1 2.8-12.2Zm1.5 3a1.3 1.3 0 1 0 0 .01",
  // speech bubble
  customer_service: "M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H11l-4.5 4v-4h0A2.5 2.5 0 0 1 4 13.5v-8ZM8 8.5h8M8 11.5h5",
  // pen nib
  human: "M4 20l4.5-1 10-10-3.5-3.5-10 10L4 20Zm11-14.5 3.5 3.5",
  // gear-ish dot
  system: "M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8Z",
};

export function AgentIcon({ who, size = 22 }: { who: Actor; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={paths[who]} />
    </svg>
  );
}

// How a tool call reads in plain English on the board.
const TOOL_PHRASES: Record<string, string> = {
  get_today: "Checking today's date",
  list_open_tickets: "Looking over the open tickets",
  list_tickets: "Looking over the tickets",
  get_ticket: "Reading the ticket",
  update_ticket: "Filing a note on the ticket",
  check_stock: "Checking the shelf",
  check_all_sizes: "Counting every size",
  get_pricing: "Looking up the price",
  list_vendors: "Going through the vendor list",
  get_invoice: "Pulling the invoice",
  list_open_invoices: "Reviewing every open bill",
  get_cash_balance: "Checking the bank balance",
  list_payments: "Checking past payments",
  list_leases: "Reviewing the leases",
  get_lease: "Pulling the lease",
  delegate: "Handing off",
};

export function toolPhrase(tool: string): string {
  return TOOL_PHRASES[tool] ?? tool.replace(/_/g, " ");
}

export function toolArgs(args: Record<string, unknown>): string {
  const shown = Object.entries(args).filter(([k]) => k !== "note" && k !== "request");
  return shown.map(([, v]) => String(v)).join(", ");
}
