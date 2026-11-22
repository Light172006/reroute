"""SSE broker: persists agent events, broadcasts to subscribers, and
replays missed events on reconnect."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator, Awaitable, Callable, Optional

from sse_starlette import EventSourceResponse
from sse_starlette.sse import ServerSentEvent

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, update, func

from app.db.models import AgentRun, AgentRunEvent, RunStatus

log = logging.getLogger("reroute.sse")

# In-process pub-sub. Swap for Redis (aioredis) later; the interface stays identical.
_SUBSCRIBERS: dict[str, set[asyncio.Queue]] = {}
_MAX_QUEUE_SIZE = 256


def _queue_for(run_id: str) -> asyncio.Queue:
    run_key = str(run_id)
    q = asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)
    _SUBSCRIBERS.setdefault(run_key, set()).add(q)
    return q


def _broadcast(run_id, event: dict) -> None:
    run_key = str(run_id)
    # Ensure event ID is a string if present (sse-starlette requirement)
    if "id" in event and event["id"] is not None:
        event["id"] = str(event["id"])
    for q in list(_SUBSCRIBERS.get(run_key, set())):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            log.warning("SSE queue full for run %s; dropping event", run_key)


def _unsub(run_id, q: asyncio.Queue) -> None:
    run_key = str(run_id)
    s = _SUBSCRIBERS.get(run_key)
    if s:
        s.discard(q)
        if not s:
            _SUBSCRIBERS.pop(run_key, None)


async def persist_event(
    db: AsyncSession,
    run_id,
    seq: int,
    ev_type: str,
    node: Optional[str] = None,
    message: Optional[str] = None,
    status: Optional[str] = None,
    payload: Optional[dict] = None,
    latency_ms: Optional[int] = None,
) -> None:
    """INSERT one agent_run_events row and flush so seq is visible to a
    reconnecting client before we yield it on the wire."""
    stmt = insert(AgentRunEvent).values(
        run_id=run_id,
        seq=seq,
        type=ev_type,
        node=node,
        message=message,
        status=status,
        payload=payload or {},
        latency_ms=latency_ms,
    )
    await db.execute(stmt)
    await db.flush()


async def replay_after(
    db: AsyncSession,
    run_id,
    last_event_id: int,
) -> list[dict]:
    """Return all persisted events with seq > last_event_id, ordered."""
    result = await db.execute(
        select(AgentRunEvent)
        .where(AgentRunEvent.run_id == run_id, AgentRunEvent.seq > last_event_id)
        .order_by(AgentRunEvent.seq)
    )
    rows = result.scalars().all()
    return [_event_to_dict(r) for r in rows]


def _event_to_dict(row: AgentRunEvent) -> dict:
    return {
        "id": str(row.seq),
        "event": row.type,
        "data": json.dumps(
            {
                "seq": row.seq,
                "type": row.type,
                "node": row.node,
                "message": row.message,
                "status": row.status,
                "payload": row.payload or {},
            }
        ),
    }


async def event_generator(
    run_id,
    last_event_id: int,
    db_factory: Callable[[], AsyncIterator[AsyncSession]],
) -> AsyncIterator[dict]:
    """Async generator yielding sse-starlette event dicts.

    1. Replay any persisted events newer than last_event_id.
    2. Subscribe to the pub-sub queue and yield live events.
    3. On client disconnect the generator is simply abandoned — the
       broker keeps broadcasting to remaining subscribers.
    """
    # 1. Replay missed events.
    async for db in db_factory():
        for ev in await replay_after(db, run_id, last_event_id):
            yield ev
        break

    # 2. Live subscription.
    q = _queue_for(run_id)
    try:
        while True:
            ev = await q.get()
            yield ev
    except asyncio.CancelledError:
        # Client disconnected — normal, not an error
        raise
    finally:
        _unsub(run_id, q)


def make_sse_response(
    run_id,
    last_event_id: int = 0,
    db_factory: Optional[Callable[[], AsyncIterator[AsyncSession]]] = None,
    headers: Optional[dict] = None,
) -> EventSourceResponse:
    """Build the EventSourceResponse for GET /agent/runs/{run_id}/stream."""
    async def _db_factory():
        from app.db.session import async_session_maker
        async with async_session_maker() as session:
            yield session

    factory = db_factory or _db_factory

    return EventSourceResponse(
        content=event_generator(run_id, last_event_id, factory),
        media_type="text/event-stream",
        ping=15,                       # keep-alive comment every 15s
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx must not buffer
            **(headers or {}),
        },
    )