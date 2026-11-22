"""Agent gateway: facade over the LangGraph graphs.

Exposes four async generators that yield AgentEvent dicts.
The router's background task persists + broadcasts each event.

This module wraps the reroute_agents.gateway functions, adapting their
typed AgentEvent output to the dict format expected by the backend services.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator, Any, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.models import (
    AgentRun, AgentRunEvent, DisruptionEvent as DisruptionModel,
    RunStatus, ReplanProposal as ProposalModel,
    ItineraryVersion, Trip,
)
from app.services import sse_broker
from reroute_agents.gateway import (
    run_plan as _run_plan,
    run_replan as _run_replan,
    run_chat as _run_chat,
    resume_replan as _resume_replan,
)
from reroute_agents.repositories.interfaces import RepositoriesBundle
from app.services.agent_repositories import RepositoriesBundle as SQLAlchemyRepositoriesBundle
from reroute_agents.state import AgentEvent as TypedAgentEvent, InjectedSignals

log = logging.getLogger("reroute.gateway")


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _evt(seq, type, node=None, message=None, status=None, payload=None, latency_ms=None) -> dict:
    return {
        "seq": seq, "type": type, "node": node, "message": message,
        "status": status, "payload": payload or {}, "latency_ms": latency_ms,
    }


class AgentGateway:
    """Thin facade over the LangGraph graphs.

    Every method is an async generator yielding event dicts. The router's
    background task persists + broadcasts each one. Agents never write
    to HTTP or to the DB directly — they yield, the services layer acts.
    """

    def __init__(self, db: AsyncSession, checkpointer: Any = None):
        self.db = db
        self._checkpointer = checkpointer
        # Use provided checkpointer or fall back to MemorySaver
        # PostgresSaver can be passed in for production persistence
        self._default_checkpointer = checkpointer or MemorySaver()

    async def _get_repositories(self) -> RepositoriesBundle:
        """Create SQLAlchemy-backed repository bundle for this session."""
        return SQLAlchemyRepositoriesBundle(self.db)

    async def _seq(self, run_id: uuid.UUID) -> int:
        """Next monotonically increasing seq for this run."""
        result = await self.db.execute(
            select(func.max(AgentRunEvent.seq))
            .where(AgentRunEvent.run_id == run_id)
        )
        n = result.scalar_one_or_none()
        return (n or 0) + 1

    async def _publish(self, run_id: uuid.UUID, ev: dict) -> dict:
        """Persist + broadcast. Returns the event so callers can branch."""
        await sse_broker.persist_event(
            self.db, run_id=run_id, seq=ev["seq"], ev_type=ev["type"],
            node=ev.get("node"), message=ev.get("message"),
            status=ev.get("status"), payload=ev.get("payload"),
            latency_ms=ev.get("latency_ms"),
        )
        sse_broker._broadcast(str(run_id), {
            "id": str(ev["seq"]), "event": ev["type"],
            "data": json.dumps(ev),
        })
        return ev

    async def run_plan(
        self,
        run_id: uuid.UUID,
        trip_id: uuid.UUID,
        spec: dict,
        llm_override: Any = None,
    ) -> AsyncIterator[dict]:
        """Execute plan_graph and yield event dicts for SSE streaming."""
        repos = await self._get_repositories()
        async for evt in _run_plan(
            run_id=run_id,
            trip_id=trip_id,
            repos=repos,
            llm_override=llm_override,
            checkpointer=self._default_checkpointer,
        ):
            seq = await self._seq(run_id)
            ev = _evt(
                seq=seq,
                type=evt.type,
                node=evt.node,
                message=evt.message,
                status=evt.status,
                payload=evt.payload,
            )
            await self._publish(run_id, ev)
            yield ev

    async def run_replan(
        self,
        run_id: uuid.UUID,
        trip_id: uuid.UUID,
        injected: Optional[dict] = None,
        llm_override: Any = None,
    ) -> AsyncIterator[dict]:
        """Execute replan_graph and yield event dicts for SSE streaming."""
        injected_obj = None
        if injected:
            injected_obj = InjectedSignals(
                type=injected.get("type", "weather"),
                day_index=injected.get("day_index", 2),
                params=injected.get("params", {}),
            )

        repos = await self._get_repositories()
        async for evt in _run_replan(
            run_id=run_id,
            trip_id=trip_id,
            repos=repos,
            injected=injected_obj,
            llm_override=llm_override,
            checkpointer=self._default_checkpointer,
        ):
            seq = await self._seq(run_id)
            ev = _evt(
                seq=seq,
                type=evt.type,
                node=evt.node,
                message=evt.message,
                status=evt.status,
                payload=evt.payload,
            )
            await self._publish(run_id, ev)
            yield ev

    async def run_chat(
        self,
        run_id: uuid.UUID,
        trip_id: uuid.UUID,
        message: str,
        llm_override: Any = None,
    ) -> AsyncIterator[dict]:
        """Execute chat_graph and yield event dicts for SSE streaming."""
        repos = await self._get_repositories()
        async for evt in _run_chat(
            run_id=run_id,
            trip_id=trip_id,
            message=message,
            repos=repos,
            llm_override=llm_override,
            checkpointer=self._default_checkpointer,
        ):
            seq = await self._seq(run_id)
            ev = _evt(
                seq=seq,
                type=evt.type,
                node=evt.node,
                message=evt.message,
                status=evt.status,
                payload=evt.payload,
            )
            await self._publish(run_id, ev)
            yield ev

    async def resume_replan(
        self,
        run_id: uuid.UUID,
        trip_id: uuid.UUID,
        decision: str,
        note: Optional[str] = None,
        llm_override: Any = None,
    ) -> AsyncIterator[dict]:
        """Resume a paused replan graph after traveler decision."""
        repos = await self._get_repositories()
        async for evt in _resume_replan(
            run_id=run_id,
            decision=decision,  # type: ignore[arg-type]
            note=note,
            repos=repos,
            llm_override=llm_override,
            checkpointer=self._default_checkpointer,
        ):
            seq = await self._seq(run_id)
            ev = _evt(
                seq=seq,
                type=evt.type,
                node=evt.node,
                message=evt.message,
                status=evt.status,
                payload=evt.payload,
            )
            await self._publish(run_id, ev)
            yield ev