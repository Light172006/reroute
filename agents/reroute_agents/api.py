"""API: FastAPI router and application exposing official Reroute agent endpoints.

Implements all endpoints defined in docs/05_API_AND_AGENT_CONTRACT.md:
- POST /trips/{id}/generate (202 Accepted, start plan_graph)
- POST /trips/{id}/check (202 Accepted, start replan_graph)
- POST /trips/{id}/chat (start chat_graph)
- GET /agent/runs/{run_id} (run status and event summary)
- GET /agent/runs/{run_id}/stream (SSE event stream with Last-Event-ID resume)
- POST /agent/runs/{run_id}/cancel (cancel active run)
- GET /trips/{id}/proposals (list pending proposals)
- GET /proposals/{id} (full proposal with diff)
- POST /proposals/{id}/decision (HITL approve / reject / alternatives)
- POST /demo/simulate (synthetic disruption injection)
- GET /health (liveness)
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from reroute_agents.destinations.registry import load_seed_catalog_into_repository
from reroute_agents.events import error_event, format_sse
from reroute_agents.gateway import (
    resume_replan,
    run_chat,
    run_plan,
    run_replan,
)
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.repositories.interfaces import RepositoriesBundle
from reroute_agents.state import (
    AgentEvent,
    InjectedSignals,
    ReplanProposal,
    TripSpec,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request & Response Models (adhering strictly to docs/05 contract)
# ---------------------------------------------------------------------------


class RunStartedResponse(BaseModel):
    run_id: str


class ChatRequest(BaseModel):
    message: str


class ChatStartedResponse(BaseModel):
    run_id: str
    message_id: str


class DecisionRequest(BaseModel):
    decision: Literal["approve", "reject", "alternatives"]
    note: str | None = None


class DecisionResponse(BaseModel):
    status: str
    version_id: str | None = None
    run_id: str | None = None


class SimulateRequest(BaseModel):
    trip_id: UUID
    type: Literal["weather", "closure", "delay", "budget_overrun"]
    day_index: int = 2
    params: dict[str, Any] = Field(default_factory=dict)


class TripCreateRequest(BaseModel):
    title: str = "Darjeeling Exploration"
    destination: str = "Darjeeling"
    start_date: date = Field(default_factory=lambda: date(2026, 12, 12))
    end_date: date = Field(default_factory=lambda: date(2026, 12, 14))
    group_size: int = 2
    budget_total: Decimal = Decimal("15000")
    budget_per_day_cap: Decimal | None = None
    currency: str = "INR"
    pace: Literal["relaxed", "balanced", "packed"] = "balanced"
    vibe_tags: list[str] = Field(default_factory=lambda: ["nature", "food"])
    notes: str | None = None


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    event_count: int
    last_event: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Run Manager for Asynchronous Background Execution and Real-time SSE
# ---------------------------------------------------------------------------


class RunManager:
    """Coordinates background agent execution and real-time event broadcasting."""

    def __init__(self, repos: RepositoriesBundle) -> None:
        self.repos = repos
        self._active_runs: dict[UUID, UUID] = {}  # trip_id -> run_id
        self._tasks: dict[UUID, asyncio.Task[None]] = {}  # run_id -> Task
        self._subscribers: dict[UUID, list[asyncio.Queue[AgentEvent | None]]] = {}
        self._lock = asyncio.Lock()

    async def is_trip_active(self, trip_id: UUID) -> UUID | None:
        async with self._lock:
            run_id = self._active_runs.get(trip_id)
            if not run_id:
                return None
            task = self._tasks.get(run_id)
            if task and task.done():
                self._active_runs.pop(trip_id, None)
                self._tasks.pop(run_id, None)
                return None
            return run_id

    async def register_run(
        self,
        run_id: UUID,
        trip_id: UUID,
        generator: AsyncIterator[AgentEvent],
    ) -> None:
        """Register and start a background agent run task."""
        async with self._lock:
            active_run_id = self._active_runs.get(trip_id)
            if active_run_id:
                task = self._tasks.get(active_run_id)
                if task and task.done():
                    self._active_runs.pop(trip_id, None)
                    self._tasks.pop(active_run_id, None)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={"detail": "run_in_progress", "run_id": str(active_run_id)},
                    )
            self._active_runs[trip_id] = run_id
            self._subscribers[run_id] = []

        task = asyncio.create_task(self._worker(run_id, trip_id, generator))
        self._tasks[run_id] = task

    async def _worker(
        self,
        run_id: UUID,
        trip_id: UUID,
        generator: AsyncIterator[AgentEvent],
    ) -> None:
        try:
            async for event in generator:
                # Log event in repository
                await self.repos.run_events.log_event(run_id, event)
                # Broadcast event to active SSE subscribers
                subscribers = self._subscribers.get(run_id, [])
                for q in list(subscribers):
                    await q.put(event)
                if event.type in ("done", "error", "proposal"):
                    async with self._lock:
                        if trip_id in self._active_runs and self._active_runs[trip_id] == run_id:
                            del self._active_runs[trip_id]
        except asyncio.CancelledError:
            cancel_evt = error_event(
                "run_cancelled",
                "Agent run was cancelled by user",
                recoverable=False,
            )
            await self.repos.run_events.log_event(run_id, cancel_evt)
            subscribers = self._subscribers.get(run_id, [])
            for q in list(subscribers):
                await q.put(cancel_evt)
        except Exception as e:
            logger.exception("Worker run failed: %s", e)
            err_evt = error_event("internal_error", str(e), recoverable=True)
            await self.repos.run_events.log_event(run_id, err_evt)
            subscribers = self._subscribers.get(run_id, [])
            for q in list(subscribers):
                await q.put(err_evt)
        finally:
            async with self._lock:
                if trip_id in self._active_runs and self._active_runs[trip_id] == run_id:
                    del self._active_runs[trip_id]
                self._tasks.pop(run_id, None)

            # Signal EOF to subscribers
            subscribers = self._subscribers.get(run_id, [])
            for q in list(subscribers):
                await q.put(None)

    async def subscribe(self, run_id: UUID) -> asyncio.Queue[AgentEvent | None]:
        q: asyncio.Queue[AgentEvent | None] = asyncio.Queue()
        async with self._lock:
            if run_id in self._subscribers:
                self._subscribers[run_id].append(q)
            else:
                self._subscribers[run_id] = [q]
        return q

    async def unsubscribe(self, run_id: UUID, q: asyncio.Queue[AgentEvent | None]) -> None:
        async with self._lock:
            if run_id in self._subscribers and q in self._subscribers[run_id]:
                self._subscribers[run_id].remove(q)

    async def cancel_run(self, run_id: UUID) -> bool:
        task = self._tasks.get(run_id)
        if task and not task.done():
            task.cancel()
            return True
        return False


# ---------------------------------------------------------------------------
# Router Factory
# ---------------------------------------------------------------------------


def create_agent_router(
    repos: RepositoriesBundle | None = None,
    llm_override: Any | None = None,
) -> APIRouter:
    """Create FastAPI router for all agent operations."""
    bundle = repos or create_in_memory_repositories()
    run_manager = RunManager(bundle)
    router = APIRouter(tags=["agents"])

    @router.post("/trips/{trip_id}/generate", status_code=status.HTTP_202_ACCEPTED)
    async def generate_plan(
        trip_id: UUID,
        idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    ) -> RunStartedResponse:
        """Start plan_graph for initial itinerary generation."""
        trip = await bundle.trips.get_trip(trip_id)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trip {trip_id} not found",
            )

        active = await run_manager.is_trip_active(trip_id)
        if active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"detail": "run_in_progress", "run_id": str(active)},
            )

        run_id = uuid4()
        gen = run_plan(run_id, trip_id, repos=bundle, llm_override=llm_override)
        await run_manager.register_run(run_id, trip_id, gen)
        return RunStartedResponse(run_id=str(run_id))

    @router.post("/trips/{trip_id}/check", status_code=status.HTTP_202_ACCEPTED)
    async def check_plan(
        trip_id: UUID,
        idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    ) -> RunStartedResponse:
        """Start replan_graph to inspect live disruptions against the current itinerary."""
        trip = await bundle.trips.get_trip(trip_id)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trip {trip_id} not found",
            )

        curr_v = await bundle.itineraries.get_current_version(trip_id)
        if not curr_v:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No itinerary exists for trip {trip_id} to check",
            )

        active = await run_manager.is_trip_active(trip_id)
        if active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"detail": "run_in_progress", "run_id": str(active)},
            )

        run_id = uuid4()
        gen = run_replan(run_id, trip_id, repos=bundle, llm_override=llm_override)
        await run_manager.register_run(run_id, trip_id, gen)
        return RunStartedResponse(run_id=str(run_id))

    @router.post("/trips/{trip_id}/chat", status_code=status.HTTP_202_ACCEPTED)
    async def chat_with_agent(
        trip_id: UUID,
        req: ChatRequest,
    ) -> ChatStartedResponse:
        """Execute chat_graph conversational assistant."""
        run_id = uuid4()
        message_id = uuid4()
        gen = run_chat(run_id, trip_id, req.message, repos=bundle, llm_override=llm_override)
        await run_manager.register_run(run_id, trip_id, gen)
        return ChatStartedResponse(run_id=str(run_id), message_id=str(message_id))

    @router.get("/agent/runs/{run_id}")
    async def get_run_status(run_id: UUID) -> RunStatusResponse:
        """Retrieve execution status and latest events for a given run."""
        events = await bundle.run_events.get_events(run_id)
        if not events:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Run {run_id} not found",
            )

        last_ev = events[-1]
        ev_type = last_ev.get("type", "running")
        status_val = (
            "completed" if ev_type == "done" else ("failed" if ev_type == "error" else "running")
        )
        return RunStatusResponse(
            run_id=str(run_id),
            status=status_val,
            event_count=len(events),
            last_event=last_ev,
        )

    @router.get("/agent/runs/{run_id}/stream")
    async def stream_run_events(
        run_id: UUID,
        last_event_id: str | None = Header(None, alias="Last-Event-ID"),
    ) -> StreamingResponse:
        """Stream real-time Server-Sent Events (SSE) for the specified run."""
        start_seq = 0
        if last_event_id:
            try:
                start_seq = int(last_event_id)
            except ValueError:
                start_seq = 0

        async def event_generator() -> AsyncIterator[str]:
            # 1. Replay past stored events
            existing_events = await bundle.run_events.get_events(run_id, after_seq=start_seq)
            is_done = False
            for rec in existing_events:
                rec_seq = rec.get("seq", 0)
                evt = AgentEvent(
                    type=rec["type"],
                    node=rec.get("node"),
                    message=rec.get("message"),
                    status=rec.get("status"),
                    payload=rec.get("payload", {}),
                )
                yield format_sse(evt, rec_seq)
                if evt.type in ("done", "error"):
                    is_done = True

            if is_done:
                return

            # 2. Stream live events from active queue
            sub_queue = await run_manager.subscribe(run_id)
            current_seq = len(existing_events)
            try:
                while True:
                    try:
                        item = await asyncio.wait_for(sub_queue.get(), timeout=15.0)
                    except TimeoutError:
                        # Send keepalive ping per contract section 2
                        yield ": ping\n\n"
                        continue

                    if item is None:
                        break

                    current_seq += 1
                    yield format_sse(item, current_seq)
                    if item.type in ("done", "error"):
                        break
            finally:
                await run_manager.unsubscribe(run_id, sub_queue)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @router.post("/agent/runs/{run_id}/cancel")
    async def cancel_run(run_id: UUID) -> dict[str, Any]:
        """Cancel an in-flight agent execution run."""
        cancelled = await run_manager.cancel_run(run_id)
        return {"run_id": str(run_id), "status": "cancelled" if cancelled else "not_running"}

    @router.get("/trips/{trip_id}/proposals")
    async def list_proposals(
        trip_id: UUID,
        status_filter: str | None = Query("pending", alias="status"),
    ) -> list[ReplanProposal]:
        """List proposals for a given trip."""
        if status_filter == "pending":
            return await bundle.proposals.get_pending_proposals(trip_id)
        # Fallback to pending if unspecified
        return await bundle.proposals.get_pending_proposals(trip_id)

    @router.get("/proposals/{proposal_id}")
    async def get_proposal(proposal_id: UUID) -> ReplanProposal:
        """Fetch full proposal details with diff."""
        proposal = await bundle.proposals.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proposal {proposal_id} not found",
            )
        return proposal

    @router.post("/proposals/{proposal_id}/decision")
    async def submit_proposal_decision(
        proposal_id: UUID,
        req: DecisionRequest,
    ) -> DecisionResponse:
        """Human-In-The-Loop decision on a proposal."""
        proposal = await bundle.proposals.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proposal {proposal_id} not found",
            )

        if proposal.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Proposal {proposal_id} already has status: {proposal.status}",
            )

        if req.decision == "approve":
            # Resume graph with approval
            async for _ in resume_replan(
                proposal.run_id,
                decision="approve",
                note=req.note,
                repos=bundle,
                llm_override=llm_override,
            ):
                pass
            curr_v = await bundle.itineraries.get_current_version(proposal.trip_id)
            version_id_str = str(curr_v["id"]) if curr_v else None
            return DecisionResponse(status="approved", version_id=version_id_str)

        elif req.decision == "reject":
            async for _ in resume_replan(
                proposal.run_id,
                decision="reject",
                note=req.note,
                repos=bundle,
                llm_override=llm_override,
            ):
                pass
            return DecisionResponse(status="rejected")

        elif req.decision == "alternatives":
            async for _ in resume_replan(
                proposal.run_id,
                decision="alternatives",
                note=req.note,
                repos=bundle,
                llm_override=llm_override,
            ):
                pass
            # Start a new run producing alternatives
            alt_run_id = uuid4()
            gen = run_replan(alt_run_id, proposal.trip_id, repos=bundle, llm_override=llm_override)
            await run_manager.register_run(alt_run_id, proposal.trip_id, gen)
            return DecisionResponse(status="alternatives_requested", run_id=str(alt_run_id))

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown decision: {req.decision}",
        )

    @router.post("/demo/simulate", status_code=status.HTTP_202_ACCEPTED)
    async def simulate_disruption(
        req: SimulateRequest,
    ) -> RunStartedResponse:
        """Inject synthetic disruptions for live demonstrations."""
        trip = await bundle.trips.get_trip(req.trip_id)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trip {req.trip_id} not found",
            )

        injected = InjectedSignals(
            type=req.type,
            day_index=req.day_index,
            params=req.params,
        )

        run_id = uuid4()
        gen = run_replan(
            run_id,
            req.trip_id,
            injected=injected,
            repos=bundle,
            llm_override=llm_override,
        )
        await run_manager.register_run(run_id, req.trip_id, gen)
        return RunStartedResponse(run_id=str(run_id))

    # Helper CRUD endpoints for test isolation and demo operations
    @router.post("/trips", status_code=status.HTTP_201_CREATED)
    async def create_trip(req: TripCreateRequest) -> TripSpec:
        """Create a new trip in the repository."""
        trip = TripSpec(
            trip_id=uuid4(),
            destination=req.destination,
            start_date=req.start_date,
            end_date=req.end_date,
            group_size=req.group_size,
            budget_total=req.budget_total,
            budget_per_day_cap=req.budget_per_day_cap,
            currency=req.currency,
            pace=req.pace,
            vibe_tags=req.vibe_tags,
            notes=req.notes,
        )
        await bundle.trips.save_trip(trip)
        return trip

    @router.get("/trips/{trip_id}")
    async def get_trip(trip_id: UUID) -> TripSpec:
        """Retrieve trip specifications."""
        trip = await bundle.trips.get_trip(trip_id)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trip {trip_id} not found",
            )
        return trip

    @router.get("/trips/{trip_id}/itinerary")
    async def get_itinerary(trip_id: UUID) -> dict[str, Any]:
        """Fetch current version with items grouped by day."""
        curr_v = await bundle.itineraries.get_current_version(trip_id)
        if not curr_v:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No itinerary found for trip {trip_id}",
            )
        items = await bundle.itineraries.get_version_items(curr_v["id"])

        # Group items by day
        by_day: dict[int, list[dict[str, Any]]] = {}
        for it in items:
            by_day.setdefault(it.day_index, []).append(it.model_dump())

        days_list: list[dict[str, Any]] = []
        for day_idx in sorted(by_day.keys()):
            day_items = by_day[day_idx]
            cost_sum = sum(float(i.get("est_cost", 0)) for i in day_items)
            days_list.append(
                {
                    "day_index": day_idx,
                    "summary": {"cost": cost_sum, "stops": len(day_items)},
                    "items": day_items,
                }
            )

        return {
            "trip_id": str(trip_id),
            "version": curr_v,
            "days": days_list,
        }

    @router.get("/health")
    async def health() -> dict[str, str]:
        """Liveness probe."""
        return {"status": "ok", "service": "reroute-agents"}

    return router


def create_app(
    repos: RepositoriesBundle | None = None,
    llm_override: Any | None = None,
) -> FastAPI:
    """Application factory for standalone HTTP execution."""
    bundle = repos or create_in_memory_repositories()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            await load_seed_catalog_into_repository(bundle.places)
        except Exception as e:
            logger.warning("Could not pre-load seed catalog: %s", e)
        yield

    app = FastAPI(
        title="Reroute Agent API",
        version="0.1.0",
        description="FastAPI REST and SSE endpoints for Reroute autonomous agent runtime",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    router = create_agent_router(repos=bundle, llm_override=llm_override)
    app.include_router(router, prefix="/api/v1")
    app.include_router(router)
    return app


# Shared standalone application instance
app = create_app()
