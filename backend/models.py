"""Data types shared by the Campus Customs agent team.

- Role                 the five agents
- TeamDeps             per-ticket run state passed to every agent (delegation chain, counters)
- ApprovalRequest      something only a human may sign off on (payments, discounts, ...)
- SpecialistReport     what inventory / accounting / facilities / customer service hand back
- TicketDecision       the boss's final answer for one ticket
- AuditEntry           one line in output/audit_trail.json
- PaymentApproval      what the dashboard sends when a human clicks approve
- PaymentReceipt       what the API returns after the money actually moves
- RunInfo              status of one agent-team run started from the API
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
ROLES: tuple[Role, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")
Actor = Role | Literal["human", "system"]  # who an audit entry is about

TicketStatus = Literal[
    "open",
    "in_progress",
    "waiting_on_vendor",
    "waiting_on_customer",
    "needs_approval",
    "resolved",
]


@dataclass
class TeamDeps:
    """Run state for one ticket, shared by the boss and every agent it reaches.

    `chain` is the delegation path to the agent currently running, e.g.
    ["boss", "inventory"]. The counters live in a dict so every delegated run
    updates the same totals.
    """

    run_id: str
    ticket_id: int | None
    chain: list[Role]
    counters: dict[str, int] = field(default_factory=lambda: {"delegations": 0})
    step: int = 0  # this agent's latest audit step, so delegation events line up with it

    @property
    def role(self) -> Role:
        return self.chain[-1]

    @property
    def depth(self) -> int:
        return len(self.chain) - 1

    def for_delegate(self, role: Role) -> TeamDeps:
        return TeamDeps(self.run_id, self.ticket_id, [*self.chain, role], self.counters)


class ApprovalRequest(BaseModel):
    """An action the agents recommend but are not allowed to take themselves."""

    kind: Literal["payment", "discount", "refund", "customer_message", "vendor_order", "other"]
    description: str = Field(description="What a human is being asked to approve, in one or two sentences.")
    amount: float | None = Field(default=None, description="Dollar amount involved, taken from a tool result.")
    reference: str | None = Field(default=None, description="Record it concerns, e.g. 'invoice 501' or 'lease 1'.")
    pay_kind: Literal["invoice", "rent", "purchase"] | None = Field(
        default=None,
        description="For payments only: 'invoice' (ref_id = invoice id), 'rent' (ref_id = lease id), "
        "or 'purchase' (ref_id = vendor id). Lets the owner pay it with one click.",
    )
    ref_id: int | None = Field(default=None, description="For payments only: the invoice, lease, or vendor id.")
    payee: str | None = Field(default=None, description="For payments only: who receives the money, from the records.")


class SpecialistReport(BaseModel):
    """What a specialist returns to whoever delegated to it."""

    summary: str = Field(description="Two to four sentences answering the request.")
    facts: list[str] = Field(
        default_factory=list,
        description="Facts used, each naming its source, e.g. 'inventory: CC-TEE-WHITE S qty 0 (check_stock)'.",
    )
    recommended_actions: list[str] = Field(default_factory=list)
    approvals_needed: list[ApprovalRequest] = Field(default_factory=list)
    customer_message_draft: str | None = Field(
        default=None, description="Draft text for the customer, if one is needed. Never sent by an agent."
    )
    open_questions: list[str] = Field(
        default_factory=list, description="Anything the tools could not answer. Never fill these gaps by guessing."
    )


class TicketDecision(BaseModel):
    """The boss's final word on one ticket."""

    ticket_id: int
    status: TicketStatus
    summary: str = Field(description="What was found and decided, in plain language for the shop owner.")
    agents_consulted: list[Role] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list, description="Only actions actually done via tools.")
    approvals_needed: list[ApprovalRequest] = Field(default_factory=list)
    customer_reply_draft: str | None = None
    next_steps: list[str] = Field(default_factory=list)


class AuditEntry(BaseModel):
    """One agent-loop step (or delegation event) in the audit trail."""

    ts: str
    run_id: str
    ticket_id: int | None
    agent: Actor
    chain: list[Actor]
    depth: int
    step: int
    kind: Literal[
        "run_start",
        "user_prompt",
        "model_request",
        "model_response",
        "end",
        "delegation_sent",
        "delegation_returned",
        "delegation_refused",
        "error",
        "human_approval",
        "database_reset",
    ]
    model: str | None = None
    text: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    usage: dict[str, int] | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


class PaymentApproval(BaseModel):
    """A human's approval of a payment the agents prepared (or a purchase)."""

    kind: Literal["invoice", "rent", "purchase"] = Field(
        description="invoice: pay a vendor invoice (ref_id = invoice id). rent: pay a lease (ref_id = lease id). "
        "purchase: a new vendor purchase (ref_id = vendor id)."
    )
    ref_id: int
    amount: float = Field(gt=0, description="Must equal the invoice amount or monthly rent exactly.")
    approved_by: str = Field(min_length=1, description="The person who clicked approve. Agents cannot approve.")
    account: str = "checking"
    ticket_id: int | None = Field(default=None, description="Ticket that asked for this, to note the approval on it.")
    description: str | None = Field(default=None, description="Required for a purchase: what is being bought.")
    run_id: str | None = Field(default=None, description="Run whose approval card this came from.")
    approval_index: int | None = Field(default=None, description="Which of that run's approvals_needed this settles.")


class PaymentReceipt(BaseModel):
    payment_id: int
    kind: str
    ref_id: int
    amount: float
    account: str
    approved_by: str
    paid_at: str
    balance_before: float
    balance_after: float
    effect: str
    warnings: list[str] = Field(default_factory=list)


class RunInfo(BaseModel):
    run_id: str
    ticket_id: int
    state: Literal["running", "done", "stopped", "error"]
    started_at: str
    finished_at: str | None = None
    decision: dict[str, Any] | None = None
    error: str | None = None
