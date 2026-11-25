"""Background task runner for agent runs.

Bridges the HTTP request (returns 202 immediately) and the long-running
agent generator. Each background task opens its own DB session.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import AgentRun, RunStatus, RunType, Trip
from app.services.agent_gateway import AgentGateway
from app.services import sse_broker
import json

log = logging.getLogger("reroute.runner")


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


async def start_plan_run(
    db: AsyncSession,
    trip_id: uuid.UUID,
    user_id: uuid.UUID,
    idempotency_key: Optional[str] = None,
) -> tuple[AgentRun, bool]:
    """Create the agent_runs row (status=queued) and return (run, is_new).

    The actual generator runs in a background task (see start_run_background).
    Returns (active_run, False) if a run is already active, or (new_run, True).
    """
    # Only one active run per trip.
    existing = await db.execute(
        select(AgentRun)
        .where(
            AgentRun.trip_id == trip_id,
            AgentRun.status.in_([RunStatus.queued, RunStatus.running, RunStatus.awaiting_user]),
        )
        .order_by(AgentRun.created_at.desc())
        .limit(1)
    )
    active = existing.scalar_one_or_none()
    if active:
        stale_cutoff = _now() - timedelta(minutes=5)
        created_at = active.created_at
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if created_at and created_at < stale_cutoff:
            active.status = RunStatus.failed
            active.error = "Run timed out or interrupted by server restart."
            active.finished_at = _now()
            await db.flush()
        else:
            return active, False  # router turns this into a 409

    run = AgentRun(
        id=uuid.uuid4(),
        trip_id=trip_id,
        user_id=user_id,
        type=RunType.plan,
        status=RunStatus.queued,
        trigger="user",
        idempotency_key=idempotency_key,
        input={"trip_id": str(trip_id)},
    )
    db.add(run)
    await db.flush()

    # Trip moves to 'generating' while the run is active.
    trip = await db.get(Trip, trip_id)
    if trip:
        trip.status = "generating"
    await db.commit()
    await db.refresh(run)
    return run, True


async def start_replan_run(
    db: AsyncSession,
    trip_id: uuid.UUID,
    user_id: uuid.UUID,
    injected: Optional[dict] = None,
    idempotency_key: Optional[str] = None,
) -> tuple[AgentRun, bool]:
    """Create a replan run (from check or demo/simulate)."""
    existing = await db.execute(
        select(AgentRun)
        .where(
            AgentRun.trip_id == trip_id,
            AgentRun.status.in_([RunStatus.queued, RunStatus.running, RunStatus.awaiting_user]),
        )
        .order_by(AgentRun.created_at.desc())
        .limit(1)
    )
    active = existing.scalar_one_or_none()
    if active:
        return active, False

    run = AgentRun(
        id=uuid.uuid4(),
        trip_id=trip_id,
        user_id=user_id,
        type=RunType.replan,
        status=RunStatus.queued,
        trigger="user" if not injected else "demo",
        idempotency_key=idempotency_key,
        input={"trip_id": str(trip_id), "injected": injected},
    )
    db.add(run)
    await db.flush()

    trip = await db.get(Trip, trip_id)
    if trip:
        trip.status = "generating"
    await db.commit()
    await db.refresh(run)
    return run, True


async def start_chat_run(
    db: AsyncSession,
    trip_id: uuid.UUID,
    user_id: uuid.UUID,
    message: str,
) -> AgentRun:
    """Create a chat run."""
    run = AgentRun(
        id=uuid.uuid4(),
        trip_id=trip_id,
        user_id=user_id,
        type=RunType.chat,
        status=RunStatus.queued,
        trigger="user",
        input={"trip_id": str(trip_id), "message": message},
    )
    db.add(run)
    await db.flush()

    await db.commit()
    await db.refresh(run)
    return run


async def _execute_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    kind: str,
    **kwargs,
) -> None:
    gw = AgentGateway(db)
    try:
        run_row = await db.get(AgentRun, run_id)
        if run_row and run_row.status == RunStatus.queued:
            run_row.status = RunStatus.running
            run_row.started_at = _now()
            await db.commit()

        if kind == "plan":
            gen = gw.run_plan(run_id, kwargs["trip_id"], kwargs.get("spec", {}))
        elif kind == "replan":
            gen = gw.run_replan(run_id, kwargs["trip_id"], kwargs.get("injected"))
        elif kind == "chat":
            gen = gw.run_chat(run_id, kwargs["trip_id"], kwargs["message"])
        elif kind == "resume_replan":
            gen = gw.resume_replan(run_id, kwargs["trip_id"], kwargs["decision"], kwargs.get("note"))
        else:
            raise ValueError(f"unknown run kind: {kind}")

        last_done_status: Optional[str] = None
        async for ev in gen:
            if ev.get("type") == "done":
                last_done_status = ev.get("status")

        # Mark final run and trip state cleanly
        run = await db.get(AgentRun, run_id)
        if run and run.status in (RunStatus.queued, RunStatus.running):
            run.status = RunStatus.failed if last_done_status == "failed" else RunStatus.completed
            run.finished_at = _now()
        trip_id = kwargs.get("trip_id")
        if trip_id and kind in ("plan", "replan", "resume_replan"):
            trip = await db.get(Trip, trip_id)
            if trip and trip.status == "generating":
                trip.status = "planned" if trip.current_version_id else "draft"
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        log.exception("run %s failed", run_id)
        try:
            await db.rollback()
            run = await db.get(AgentRun, run_id)
            if run:
                run.status = RunStatus.failed
                run.error = str(exc)
                run.finished_at = _now()
            trip_id = kwargs.get("trip_id")
            if trip_id:
                trip = await db.get(Trip, trip_id)
                if trip and trip.status == "generating":
                    trip.status = "planned" if trip.current_version_id else "draft"
            await db.commit()
        except Exception:
            log.exception("failed to persist failure state for run %s", run_id)

        sse_broker._broadcast(str(run_id), {
            "event": "error",
            "data": json.dumps({
                "type": "error", "code": "run_failed", "recoverable": False,
                "message": str(exc),
            }),
        })
        sse_broker._broadcast(str(run_id), {
            "event": "done",
            "data": json.dumps({"type": "done", "status": "failed"}),
        })


async def start_run_background(
    db: Optional[AsyncSession],
    run_id: uuid.UUID,
    kind: str,
    **kwargs,
) -> None:
    """Iterate the agent generator, persist + broadcast each event, and
    finalize the run row. Safe to schedule via BackgroundTasks.
    """
    if db is not None:
        await _execute_run(db, run_id, kind, **kwargs)
    else:
        from app.db.session import async_session_maker
        async with async_session_maker() as session:
            await _execute_run(session, run_id, kind, **kwargs)


async def cancel_run(db: AsyncSession, run_id: uuid.UUID) -> None:
    """Mark run as cancelled and broadcast done event."""
    run = await db.get(AgentRun, run_id)
    if not run:
        return
    if run.status in (RunStatus.completed, RunStatus.failed, RunStatus.cancelled):
        return
    run.status = RunStatus.cancelled
    run.finished_at = _now()
    await db.commit()
    sse_broker._broadcast(str(run_id), {
        "event": "done",
        "data": json.dumps({"status": "cancelled"}),
    })