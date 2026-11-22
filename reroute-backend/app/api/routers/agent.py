"""Agent router: SSE streaming and run management endpoints."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies import get_current_user, get_optional_current_user
from app.db.models import (
    AgentRun, AgentRunEvent, RunStatus, Trip, ReplanProposal, ProposalStatus,
    ChatMessage, DisruptionEvent, User,
)
from app.db.session import get_db
from app.services import sse_broker
from app.services.run_runner import (
    start_plan_run, start_replan_run, start_chat_run, cancel_run,
    start_run_background,
)
from app.api.schemas.agent import (
    GenerateRequest, CheckRequest, ChatRequest, ProposalDecisionRequest, SimulateRequest,
)

log = logging.getLogger("reroute.agent")

router = APIRouter(prefix="/agent", tags=["agent"])
trip_agent_router = APIRouter(tags=["trips-agent"])
proposal_router = APIRouter(prefix="/proposals", tags=["proposals"])
demo_router = APIRouter(tags=["demo"])


# ---------------------------------------------------------------------
# SSE Stream & Run Info
# ---------------------------------------------------------------------
@router.get("/runs/{run_id}/stream")
async def run_stream(
    run_id: uuid.UUID,
    request: Request,
    last_event_id: Optional[int] = Query(None, alias="last-event-id"),
    user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE stream for an agent run."""
    run = await db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # If authenticated, verify run belongs to user
    if user and run.user_id and run.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    hdr_last = request.headers.get("last-event-id")
    if last_event_id is None and hdr_last is not None:
        try:
            last_event_id = int(hdr_last)
        except ValueError:
            pass

    return sse_broker.make_sse_response(
        run_id=str(run_id),
        last_event_id=last_event_id or 0,
    )


@router.get("/runs/{run_id}")
async def get_run(
    run_id: uuid.UUID,
    user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    run = await db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if user and run.user_id and run.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return {
        "run_id": str(run.id),
        "trip_id": str(run.trip_id),
        "type": run.type.value if run.type else None,
        "status": run.status.value if run.status else None,
        "trigger": run.trigger,
        "idempotency_key": run.idempotency_key,
        "input": run.input,
        "output": run.output,
        "error": run.error,
        "model_used": run.model_used,
        "tokens_in": run.tokens_in,
        "tokens_out": run.tokens_out,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


@router.post("/runs/{run_id}/cancel")
async def cancel_run_endpoint(
    run_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run = await db.get(AgentRun, run_id)
    if not run or run.user_id != user.id:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status in (RunStatus.completed, RunStatus.failed, RunStatus.cancelled):
        return {"status": run.status.value}
    await cancel_run(db, run_id)
    return {"status": "cancelled"}


# ---------------------------------------------------------------------
# Trip Generation Endpoints (mounted under /trips)
# ---------------------------------------------------------------------
@trip_agent_router.post("/{trip_id}/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_trip(
    trip_id: uuid.UUID,
    request: Request,
    background: BackgroundTasks,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a plan generation run."""
    trip = await db.get(Trip, trip_id)
    if not trip or trip.user_id != user.id:
        raise HTTPException(status_code=404, detail="Trip not found")

    run, created = await start_plan_run(db, trip_id, user.id)
    if not created:
        return JSONResponse(
            status_code=409,
            content={"detail": "run_in_progress", "run_id": str(run.id)},
        )

    background.add_task(
        _bg_run,
        str(run.id), "plan", str(trip_id), {}
    )
    return {"run_id": str(run.id)}


@trip_agent_router.post("/{trip_id}/check", status_code=status.HTTP_202_ACCEPTED)
async def check_trip(
    trip_id: uuid.UUID,
    request: Request,
    background: BackgroundTasks,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a replan check run (manual 'Check my plan now')."""
    trip = await db.get(Trip, trip_id)
    if not trip or trip.user_id != user.id:
        raise HTTPException(status_code=404, detail="Trip not found")

    run, created = await start_replan_run(db, trip_id, user.id)
    if not created:
        return JSONResponse(
            status_code=409,
            content={"detail": "run_in_progress", "run_id": str(run.id)},
        )

    background.add_task(
        _bg_run,
        str(run.id), "replan", str(trip_id), {}
    )
    return {"run_id": str(run.id)}


@trip_agent_router.post("/{trip_id}/chat", status_code=status.HTTP_202_ACCEPTED)
async def chat_trip(
    trip_id: uuid.UUID,
    payload: ChatRequest,
    background: BackgroundTasks,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a chat run."""
    trip = await db.get(Trip, trip_id)
    if not trip or trip.user_id != user.id:
        raise HTTPException(status_code=404, detail="Trip not found")

    run = await start_chat_run(db, trip_id, user.id, payload.message)
    background.add_task(
        _bg_run,
        str(run.id), "chat", str(trip_id), {"message": payload.message}
    )
    return {"run_id": str(run.id), "message_id": str(run.id)}


@trip_agent_router.get("/{trip_id}/chat")
async def get_chat_history(
    trip_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get chat history for a trip."""
    trip = await db.get(Trip, trip_id)
    if not trip or trip.user_id != user.id:
        raise HTTPException(status_code=404, detail="Trip not found")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.trip_id == trip_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()

    return [
        {
            "id": str(m.id),
            "trip_id": str(m.trip_id),
            "run_id": str(m.run_id) if m.run_id else None,
            "role": m.role,
            "content": m.content,
            "metadata": m.message_metadata if m.message_metadata else {},
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


# ---------------------------------------------------------------------
# Proposals Helpers & Handlers
# ---------------------------------------------------------------------
def _format_proposal(p: ReplanProposal, disruptions_list: list = None) -> dict:
    diff_val = p.diff
    if isinstance(diff_val, dict):
        diff_val = diff_val.get("items", [])
    elif not isinstance(diff_val, list):
        diff_val = []

    return {
        "id": str(p.id),
        "trip_id": str(p.trip_id),
        "run_id": str(p.run_id),
        "base_version_id": str(p.base_version_id),
        "status": p.status.value if p.status else "pending",
        "reason": p.reason,
        "explanation": p.explanation or "",
        "disruptions": disruptions_list or [],
        "cost_delta": float(p.cost_delta) if p.cost_delta else 0,
        "time_delta_min": p.time_delta_min or 0,
        "items_changed": p.items_changed or 0,
        "diff": diff_val,
        "proposed_items": p.proposed_items or {},
        "resulting_version_id": str(p.resulting_version_id) if p.resulting_version_id else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


async def _handle_get_proposal(proposal_id: uuid.UUID, user, db: AsyncSession) -> dict:
    result = await db.execute(
        select(ReplanProposal).where(ReplanProposal.id == proposal_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")

    trip = await db.get(Trip, p.trip_id)
    if not trip or trip.user_id != user.id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    disruptions = []
    if p.disruption_ids:
        dis_res = await db.execute(
            select(DisruptionEvent).where(DisruptionEvent.id.in_(p.disruption_ids))
        )
        disruptions = [
            {
                "id": str(d.id),
                "type": d.type.value if hasattr(d.type, "value") else str(d.type),
                "severity": d.severity.value if hasattr(d.severity, "value") else str(d.severity),
                "summary": d.summary,
            }
            for d in dis_res.scalars().all()
        ]

    return _format_proposal(p, disruptions)


async def _handle_decide_proposal(
    proposal_id: uuid.UUID,
    payload: ProposalDecisionRequest,
    background: BackgroundTasks,
    user,
    db: AsyncSession,
) -> dict:
    result = await db.execute(
        select(ReplanProposal).where(ReplanProposal.id == proposal_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")

    trip = await db.get(Trip, p.trip_id)
    if not trip or trip.user_id != user.id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if p.status != ProposalStatus.pending:
        raise HTTPException(status_code=400, detail="Proposal already decided")

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    if payload.decision == "approve":
        p.status = ProposalStatus.approved
        p.decided_at = now
        p.decision_note = payload.note
        background.add_task(
            _bg_run,
            str(p.run_id), "resume_replan", str(p.trip_id),
            {"decision": "approve", "note": payload.note}
        )
        return {"status": "approved", "version_id": str(p.resulting_version_id) if p.resulting_version_id else None}
    elif payload.decision == "reject":
        p.status = ProposalStatus.rejected
        p.decided_at = now
        p.decision_note = payload.note
        background.add_task(
            _bg_run,
            str(p.run_id), "resume_replan", str(p.trip_id),
            {"decision": "reject", "note": payload.note}
        )
        return {"status": "rejected"}
    elif payload.decision == "alternatives":
        p.status = ProposalStatus.superseded
        p.decided_at = now
        p.decision_note = payload.note
        new_run, _ = await start_replan_run(db, p.trip_id, user.id, injected={
            "type": "user_request", "day_index": 1, "alternatives_of": str(p.id)
        })
        background.add_task(
            _bg_run,
            str(new_run.id), "replan", str(p.trip_id), {"alternatives_of": str(p.id)}
        )
        return {"status": "superseded", "run_id": str(new_run.id)}
    else:
        raise HTTPException(status_code=400, detail="Invalid decision")


# ---------------------------------------------------------------------
# Proposal Routes
# ---------------------------------------------------------------------
@trip_agent_router.get("/{trip_id}/proposals")
async def list_proposals(
    trip_id: uuid.UUID,
    status: Optional[str] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trip = await db.get(Trip, trip_id)
    if not trip or trip.user_id != user.id:
        raise HTTPException(status_code=404, detail="Trip not found")

    q = select(ReplanProposal).where(ReplanProposal.trip_id == trip_id)
    if status:
        try:
            q = q.where(ReplanProposal.status == ProposalStatus(status))
        except ValueError:
            pass
    result = await db.execute(q.order_by(ReplanProposal.created_at.desc()))
    proposals = result.scalars().all()

    return [_format_proposal(p) for p in proposals]


# Endpoints mounted on proposal_router (/proposals/{id} - frontend contract)
@proposal_router.get("/{proposal_id}")
async def get_proposal_standalone(
    proposal_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _handle_get_proposal(proposal_id, user, db)


@proposal_router.post("/{proposal_id}/decision")
async def decide_proposal_standalone(
    proposal_id: uuid.UUID,
    payload: ProposalDecisionRequest,
    background: BackgroundTasks,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _handle_decide_proposal(proposal_id, payload, background, user, db)


# Also mounted on trip_agent_router (/trips/proposals/{id}) for backward compatibility
@trip_agent_router.get("/proposals/{proposal_id}")
async def get_proposal(
    proposal_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _handle_get_proposal(proposal_id, user, db)


@trip_agent_router.post("/proposals/{proposal_id}/decision")
async def decide_proposal(
    proposal_id: uuid.UUID,
    payload: ProposalDecisionRequest,
    background: BackgroundTasks,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _handle_decide_proposal(proposal_id, payload, background, user, db)


# ---------------------------------------------------------------------
# Demo Simulation Endpoint (/demo/simulate)
# ---------------------------------------------------------------------
@demo_router.post("/simulate", status_code=status.HTTP_202_ACCEPTED)
async def simulate_disruption(
    request: Request,
    payload: Optional[SimulateRequest] = None,
    trip_id: Optional[uuid.UUID] = Query(None),
    type: Optional[str] = Query(None),
    day_index: Optional[int] = Query(None),
    params: Optional[dict] = None,
    background: BackgroundTasks = None,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Inject a simulated disruption and start a replan run."""
    target_trip_id = payload.trip_id if (payload and payload.trip_id) else trip_id
    target_type = payload.type if (payload and payload.type) else (type or "weather")
    target_day_index = payload.day_index if (payload and payload.day_index is not None) else (day_index if day_index is not None else 1)
    target_params = payload.params if (payload and payload.params is not None) else (params or {})

    if not target_trip_id:
        try:
            body = await request.json()
            if isinstance(body, dict):
                target_trip_id = uuid.UUID(body.get("trip_id")) if body.get("trip_id") else None
                target_type = body.get("type", target_type)
                target_day_index = int(body.get("day_index", target_day_index))
                target_params = body.get("params", target_params)
        except Exception:
            pass

    if not target_trip_id:
        raise HTTPException(status_code=400, detail="trip_id is required")

    trip = await db.get(Trip, target_trip_id)
    if not trip or trip.user_id != user.id:
        raise HTTPException(status_code=404, detail="Trip not found")

    injected = {"type": target_type, "day_index": target_day_index, "params": target_params}

    run, created = await start_replan_run(db, target_trip_id, user.id, injected=injected)
    if not created:
        return JSONResponse(
            status_code=409,
            content={"detail": "run_in_progress", "run_id": str(run.id)},
        )

    background.add_task(
        _bg_run,
        str(run.id), "replan", str(target_trip_id), {"injected": injected}
    )
    return {"run_id": str(run.id)}


# ---------------------------------------------------------------------
# Background Task Runner
# ---------------------------------------------------------------------
async def _bg_run(run_id: str, kind: str, trip_id: str, kwargs: dict):
    from app.db.session import async_session_maker, get_db
    from app.main import app

    if get_db in app.dependency_overrides:
        override = app.dependency_overrides[get_db]
        async for session in override():
            await start_run_background(session, uuid.UUID(run_id), kind, trip_id=uuid.UUID(trip_id), **kwargs)
            return

    async with async_session_maker() as db:
        await start_run_background(db, uuid.UUID(run_id), kind, trip_id=uuid.UUID(trip_id), **kwargs)
