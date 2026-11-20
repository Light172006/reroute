"""AgentEvent definitions and emission utilities."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from reroute_agents.state import AgentEvent, DisruptionEvent


def step_event(
    node: str,
    message: str,
    status: str = "done",
    payload: dict[str, Any] | None = None,
) -> AgentEvent:
    return AgentEvent(
        type="step",
        node=node,
        message=message,
        status="done" if status == "done" else ("running" if status == "running" else "failed"),
        payload=payload or {},
    )


def tool_call_event(
    tool: str,
    args: dict[str, Any],
    node: str | None = None,
) -> AgentEvent:
    return AgentEvent(
        type="tool_call",
        node=node,
        message=f"Calling tool {tool}",
        status="running",
        payload={"tool": tool, "args": args},
    )


def tool_result_event(
    tool: str,
    ok: bool,
    summary: str,
    cached: bool = False,
    data: Any = None,
    node: str | None = None,
) -> AgentEvent:
    payload: dict[str, Any] = {"tool": tool, "ok": ok, "summary": summary, "cached": cached}
    if data is not None:
        payload["data"] = data
    return AgentEvent(
        type="tool_result",
        node=node,
        message=summary,
        status="done" if ok else "failed",
        payload=payload,
    )


def llm_call_event(
    model: str,
    latency_ms: int,
    tokens_in: int = 0,
    tokens_out: int = 0,
    fallback: bool = False,
    node: str | None = None,
) -> AgentEvent:
    return AgentEvent(
        type="llm_call",
        node=node,
        message=f"LLM call completed via {model}" + (" (fallback)" if fallback else ""),
        status="done",
        payload={
            "model": model,
            "latency_ms": latency_ms,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "fallback": fallback,
        },
    )


def draft_event(days_ready: list[int], node: str | None = "planner") -> AgentEvent:
    return AgentEvent(
        type="draft",
        node=node,
        message=f"Draft itinerary ready for days: {days_ready}",
        status="done",
        payload={"days_ready": days_ready},
    )


def disruption_event(
    event: DisruptionEvent,
    node: str | None = "impact_analyzer",
) -> AgentEvent:
    return AgentEvent(
        type="disruption",
        node=node,
        message=f"Disruption detected: {event.summary}",
        status="done",
        payload=event.model_dump(mode="json"),
    )


def proposal_event(proposal_id: UUID | str, node: str | None = "build_proposal") -> AgentEvent:
    return AgentEvent(
        type="proposal",
        node=node,
        message="Replan proposal ready for review",
        status="done",
        payload={"proposal_id": str(proposal_id)},
    )


def token_event(text: str, node: str | None = "chat") -> AgentEvent:
    return AgentEvent(
        type="token",
        node=node,
        message=None,
        status="running",
        payload={"text": text},
    )


def error_event(
    code: str,
    message: str,
    recoverable: bool = True,
    node: str | None = None,
) -> AgentEvent:
    return AgentEvent(
        type="error",
        node=node,
        message=message,
        status="failed",
        payload={"code": code, "recoverable": recoverable, "message": message},
    )


def done_event(
    status: str = "completed",
    version_id: UUID | str | None = None,
    proposal_id: UUID | str | None = None,
    node: str | None = "finalize",
) -> AgentEvent:
    payload: dict[str, Any] = {"status": status}
    if version_id:
        payload["version_id"] = str(version_id)
    if proposal_id:
        payload["proposal_id"] = str(proposal_id)
    return AgentEvent(
        type="done",
        node=node,
        message=f"Execution finished with status: {status}",
        status="done",
        payload=payload,
    )


def format_sse(event: AgentEvent, seq: int) -> str:
    """Format AgentEvent to SSE wire format."""
    data_dict = {
        "seq": seq,
        "type": event.type,
        "node": event.node,
        "message": event.message,
        "status": event.status,
        "payload": event.payload,
    }
    return f"id: {seq}\nevent: {event.type}\ndata: {json.dumps(data_dict, default=str)}\n\n"
