"""The agent loop and delegation between agents.

run_agent() drives one agent through PydanticAI's loop with agent.iter() and
writes every node to the audit trail: the prompt in, each model request (with
tool results going back), each model response (with text, tool calls, and
tokens), and the end. A delegated agent is run through run_agent() too, so the
whole team's work lands in one trail under one run_id.

delegate() is a tool every agent has, which is what gives the team full
connectivity: any agent can hand a question to any other agent. Guards keep
that from turning into loops or runaway spend (see config.py for the limits).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, UsageLimitExceeded
from pydantic_ai.messages import (
    RetryPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.usage import RunUsage

from backend import audit
from backend.config import (
    MAX_DELEGATION_DEPTH,
    MAX_DELEGATIONS_PER_RUN,
    MODEL_SETTINGS,
    TEAM_USAGE_LIMITS,
    build_model,
)
from backend.models import AuditEntry, Role, TeamDeps


def _log(deps: TeamDeps, step: int, kind: str, **fields: Any) -> None:
    audit.append(
        AuditEntry(
            ts=audit.now(),
            run_id=deps.run_id,
            ticket_id=deps.ticket_id,
            agent=deps.role,
            chain=deps.chain,
            depth=deps.depth,
            step=step,
            kind=kind,
            **fields,
        )
    )


def _usage(usage: Any) -> dict[str, int]:
    return {
        "input_tokens": usage.input_tokens or 0,
        "output_tokens": usage.output_tokens or 0,
        "cache_read_tokens": usage.cache_read_tokens or 0,
    }


def _describe(node: Any) -> tuple[str, dict] | None:
    """Turn one PydanticAI loop node into audit fields."""
    if Agent.is_user_prompt_node(node):
        return "user_prompt", {"text": audit.clip(node.user_prompt)}

    if Agent.is_model_request_node(node):
        parts = node.request.parts
        results = [
            {"tool": p.tool_name, "tool_call_id": p.tool_call_id, "content": audit.clip(p.model_response_str())}
            for p in parts
            if isinstance(p, ToolReturnPart)
        ]
        retries = [audit.clip(p.model_response(), 500) for p in parts if isinstance(p, RetryPromptPart)]
        return "model_request", {"tool_results": results, "detail": {"retries": retries} if retries else {}}

    if Agent.is_call_tools_node(node):
        resp = node.model_response
        text = "".join(p.content for p in resp.parts if isinstance(p, TextPart))
        thinking = "".join(p.content for p in resp.parts if isinstance(p, ThinkingPart))
        calls = [
            {"tool": p.tool_name, "tool_call_id": p.tool_call_id, "args": p.args_as_dict()}
            for p in resp.parts
            if isinstance(p, ToolCallPart)
        ]
        return "model_response", {
            "model": resp.model_name,
            "text": audit.clip(text) if text else None,
            "tool_calls": calls,
            "usage": _usage(resp.usage),
            "detail": {"thinking": audit.clip(thinking, 500)} if thinking else {},
        }

    if Agent.is_end_node(node):
        output = node.data.output
        dumped = output.model_dump(mode="json") if isinstance(output, BaseModel) else output
        return "end", {"text": audit.clip(dumped)}

    return None


async def run_agent(role: Role, task: str, deps: TeamDeps, usage: RunUsage | None = None) -> Any:
    """Run one agent's loop on `task`, auditing every step. Returns its typed output.

    Pass the caller's `usage` so a delegated run counts against the same team
    budget; TEAM_USAGE_LIMITS then caps the whole ticket, not each agent.
    """
    from backend.agents import AGENTS  # imported here: agent files import delegate() from this module

    agent = AGENTS[role]
    _log(deps, 0, "run_start", text=audit.clip(task))
    step = 0
    try:
        async with agent.iter(
            task,
            deps=deps,
            model=build_model(),
            model_settings=MODEL_SETTINGS,
            usage=usage,
            usage_limits=TEAM_USAGE_LIMITS,
        ) as run:
            async for node in run:
                described = _describe(node)
                if described is None:
                    continue
                step += 1
                deps.step = step
                kind, fields = described
                _log(deps, step, kind, **fields)
            return run.result.output
    except Exception as exc:
        _log(deps, step + 1, "error", text=audit.clip(f"{type(exc).__name__}: {exc}", 800))
        raise


async def delegate(ctx: RunContext[TeamDeps], to: Role, request: str) -> dict:
    """Hand a specific question or task to another Campus Customs agent and get its report back.

    Agents:
      boss             - owns the ticket, sets its status, decides what goes to a human
      inventory        - stock by SKU and size, shelf location, restock timing from vendors
      accounting       - cash balance, vendor invoices, payment history, prices and margins
      facilities       - the shop lease, landlord, rent notices and due dates
      customer_service - customer-facing replies, order options, quotes at list price

    Args:
        to: The agent to ask. Must be a different agent from you.
        request: A self-contained request. Include the ticket number, SKU/size/qty or
            record ids, and exactly what you need back. The other agent cannot see
            your conversation.
    """
    deps = ctx.deps
    step = deps.step  # the model_response step that asked for this delegation
    call = {"tool_call_id": ctx.tool_call_id}
    refusal = None
    if to == deps.role:
        refusal = "You cannot delegate to yourself."
    elif to in deps.chain:
        refusal = (
            f"{to} is already working on this further up the chain ({' -> '.join(deps.chain)}). "
            "Answer from what you have and put any open question in your report."
        )
    elif deps.depth >= MAX_DELEGATION_DEPTH:
        refusal = "Delegation depth limit reached. Answer from what you have and list open questions."
    elif deps.counters["delegations"] >= MAX_DELEGATIONS_PER_RUN:
        refusal = "This ticket has used all its delegations. Answer from what you have."
    if refusal:
        _log(deps, step, "delegation_refused", detail={**call, "to": to, "request": audit.clip(request, 500), "reason": refusal})
        return {"ok": False, "message": refusal}

    deps.counters["delegations"] += 1
    _log(deps, step, "delegation_sent", detail={**call, "to": to, "request": audit.clip(request)})
    task = f"Request from the {deps.role} agent (ticket {deps.ticket_id}):\n{request}"
    try:
        report = await run_agent(to, task, deps.for_delegate(to), usage=ctx.usage)
    except UsageLimitExceeded:
        raise  # the whole ticket is out of budget; stop the team, don't keep asking
    except Exception as exc:
        _log(deps, step, "delegation_returned", detail={**call, "from": to, "ok": False, "error": audit.clip(str(exc), 500)})
        return {"ok": False, "message": f"The {to} agent failed: {audit.clip(str(exc), 300)}"}

    body = report.model_dump(mode="json") if isinstance(report, BaseModel) else report
    summary = body.get("summary") if isinstance(body, dict) else None
    _log(deps, step, "delegation_returned", detail={**call, "from": to, "ok": True, "summary": audit.clip(summary or "", 600)})
    return {"ok": True, "from": to, "report": body}
