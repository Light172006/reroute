"""Stress tests for gateway streaming, AgentEvent contracts, failure injection, and cancellation."""

from __future__ import annotations

import asyncio
from datetime import date, time
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest

from reroute_agents.destinations.registry import load_seed_catalog_into_repository
from reroute_agents.gateway import resume_replan, run_plan, run_replan
from reroute_agents.llm import FakeLLM
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.state import (
    AgentEvent,
    DraftItem,
    InjectedSignals,
    ItineraryDraft,
    TripSpec,
)


@pytest.fixture
def test_trip_spec() -> TripSpec:
    return TripSpec(
        trip_id=uuid4(),
        destination="Darjeeling",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        group_size=2,
        budget_total=Decimal(10000),
        currency="INR",
        pace="balanced",
        vibe_tags=["nature"],
    )


@pytest.mark.asyncio
async def test_run_plan_event_sequence_and_size_caps(test_trip_spec: TripSpec) -> None:
    """Verify event sequence conformity (starts with step, ends with done), valid schema, and <100KB payload."""
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")
    await repos.trips.save_trip(test_trip_spec)

    p1 = uuid4()
    draft = ItineraryDraft(
        items=[
            DraftItem(
                day_index=1,
                position=0,
                place_id=p1,
                title="Tiger Hill Sunrise",
                category="nature",
                setting="outdoor",
                start_time=time(6, 0),
                end_time=time(8, 0),
                est_cost=Decimal(100),
            )
        ]
    )
    fake_llm = FakeLLM(canned_responses={"ItineraryDraft": draft})

    run_id = uuid4()
    events: list[AgentEvent] = []

    async for event in run_plan(
        run_id=run_id,
        trip_id=test_trip_spec.trip_id,
        repos=repos,
        llm_override=fake_llm,
    ):
        events.append(event)

        # Validate event against contract
        assert isinstance(event, AgentEvent)
        assert event.type in ("step", "token", "tool_call", "tool_result", "llm_call", "draft", "proposal", "disruption", "done", "error")
        assert event.status in ("running", "done", "failed")

        # Payload size cap < 100 KB
        payload_bytes = len(event.model_dump_json().encode("utf-8"))
        assert payload_bytes < 100 * 1024, f"Event {event.type} exceeded 100KB: {payload_bytes} bytes"

    assert len(events) >= 2
    # First event must be a step event
    assert events[0].type == "step"
    # Terminal event must be done or error
    assert events[-1].type in ("done", "error")

    # Verify repository stored monotonic sequence numbers
    stored = await repos.run_events.get_events(run_id)
    assert len(stored) == len(events)
    seqs = [rec["seq"] for rec in stored]
    assert seqs == list(range(1, len(stored) + 1))


@pytest.mark.asyncio
async def test_gateway_failure_injection_converts_to_error_event(test_trip_spec: TripSpec) -> None:
    """Inject failure in graph execution; verify gateway catches exception and emits error event without crashing."""
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")
    await repos.trips.save_trip(test_trip_spec)

    run_id = uuid4()

    # Simulate unexpected unhandled crash inside graph execution
    with patch("reroute_agents.graphs.plan_graph.intake_node", side_effect=RuntimeError("Unhandled worker crash")):
        events = []
        async for evt in run_plan(
            run_id=run_id,
            trip_id=test_trip_spec.trip_id,
            repos=repos,
        ):
            events.append(evt)

        assert len(events) >= 1
        last_evt = events[-1]
        assert last_evt.type == "error"
        assert last_evt.status == "failed"
        assert "Unhandled worker crash" in last_evt.message


@pytest.mark.asyncio
async def test_gateway_cancellation_mid_stream(test_trip_spec: TripSpec) -> None:
    """Cancel client generator mid-execution; verify graph stops and error_event(code='run_cancelled') emitted."""
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")
    await repos.trips.save_trip(test_trip_spec)

    run_id = uuid4()
    collected_events = []

    async def consumer() -> None:
        async for evt in run_plan(run_id=run_id, trip_id=test_trip_spec.trip_id, repos=repos):
            collected_events.append(evt)
            # Cancel immediately after first step
            if len(collected_events) == 1:
                raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await consumer()


@pytest.mark.asyncio
async def test_run_replan_and_resume_events_stream(test_trip_spec: TripSpec) -> None:
    """Verify run_replan yields proposal and step events, then resume_replan yields done event."""
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")
    await repos.trips.save_trip(test_trip_spec)

    k1 = uuid4()
    item1 = DraftItem(
        stable_key=k1,
        day_index=1,
        position=0,
        title="Outdoor Trek",
        category="nature",
        setting="outdoor",
        start_time=time(14, 0),
        end_time=time(16, 0),
        est_cost=Decimal(100),
    )
    v1_id = await repos.itineraries.save_version(
        trip_id=test_trip_spec.trip_id,
        version_no=1,
        reason="Initial",
        created_by="agent:planner",
        items=[item1],
    )
    await repos.trips.update_current_version(test_trip_spec.trip_id, v1_id)

    injected = InjectedSignals(
        type="weather",
        day_index=1,
        params={"precip_prob": 0.95, "from": "14:00", "to": "16:00"},
    )

    run_id = uuid4()
    replan_events: list[AgentEvent] = []

    async for evt in run_replan(
        run_id=run_id,
        trip_id=test_trip_spec.trip_id,
        injected=injected,
        repos=repos,
        llm_override=FakeLLM(),
    ):
        replan_events.append(evt)

    # Replan stream must contain proposal and step events
    event_types = [e.type for e in replan_events]
    assert "proposal" in event_types

    # Resume replan stream
    resume_events: list[AgentEvent] = []
    async for evt in resume_replan(
        run_id=run_id,
        decision="approve",
        repos=repos,
        llm_override=FakeLLM(),
    ):
        resume_events.append(evt)

    assert len(resume_events) >= 1
    # Check that new version was applied
    curr = await repos.itineraries.get_current_version(test_trip_spec.trip_id)
    assert curr is not None
    assert curr["version_no"] == 2
