"""Contract tests: Validates event emission stream, sequencing, and payload schemas."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from reroute_agents.destinations.registry import load_seed_catalog_into_repository
from reroute_agents.gateway import resume_replan, run_plan, run_replan
from reroute_agents.llm import FakeLLM
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.state import (
    AgentEvent,
    InjectedSignals,
    TripSpec,
)


@pytest.mark.asyncio
async def test_event_stream_contract_compliance() -> None:
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")

    trip_id = uuid4()
    run_id = uuid4()
    spec = TripSpec(
        trip_id=trip_id,
        destination="Darjeeling",
        start_date=date(2026, 12, 12),
        end_date=date(2026, 12, 13),
        group_size=2,
        budget_total=Decimal(15000),
        currency="INR",
        pace="balanced",
    )
    await repos.trips.save_trip(spec)

    events: list[AgentEvent] = []
    async for event in run_plan(run_id, trip_id, repos=repos, llm_override=FakeLLM()):
        # Every emitted event must strictly validate against AgentEvent
        assert isinstance(event, AgentEvent)
        assert event.type in (
            "step",
            "tool_call",
            "tool_result",
            "llm_call",
            "draft",
            "disruption",
            "proposal",
            "token",
            "error",
            "done",
        )
        events.append(event)

    assert len(events) >= 3

    # Sequencing rule: Stream starts with a step event and ends with a done event
    assert events[0].type == "step"
    assert events[-1].type == "done"

    # Validate specific payload shapes
    for evt in events:
        if evt.type == "draft":
            assert "days_ready" in evt.payload
            assert isinstance(evt.payload["days_ready"], list)
        elif evt.type == "tool_call":
            assert "tool" in evt.payload
            assert "args" in evt.payload
        elif evt.type == "tool_result":
            assert "tool" in evt.payload
            assert "ok" in evt.payload
            assert "summary" in evt.payload
        elif evt.type == "done":
            assert "status" in evt.payload
            assert evt.payload["status"] == "completed"


@pytest.mark.asyncio
async def test_proposal_event_precedes_decision() -> None:
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")

    trip_id = uuid4()
    spec = TripSpec(
        trip_id=trip_id,
        destination="Darjeeling",
        start_date=date(2026, 12, 12),
        end_date=date(2026, 12, 13),
        budget_total=Decimal(15000),
        currency="INR",
        pace="balanced",
    )
    await repos.trips.save_trip(spec)

    # Initial plan
    async for _ in run_plan(uuid4(), trip_id, repos=repos, llm_override=FakeLLM()):
        pass

    replan_run_id = uuid4()
    injected_weather = InjectedSignals(
        type="weather",
        day_index=1,
        params={"precip_prob": 0.88, "from": "09:00", "to": "12:00"},
    )

    replan_events: list[AgentEvent] = []
    async for event in run_replan(
        replan_run_id,
        trip_id,
        injected=injected_weather,
        repos=repos,
        llm_override=FakeLLM(),
    ):
        replan_events.append(event)

    types = [e.type for e in replan_events]
    assert "disruption" in types
    assert "proposal" in types

    prop_evt = next(e for e in replan_events if e.type == "proposal")
    assert "proposal_id" in prop_evt.payload

    # Now resume with approval
    resume_events: list[AgentEvent] = []
    async for event in resume_replan(
        replan_run_id,
        decision="approve",
        repos=repos,
        llm_override=FakeLLM(),
    ):
        resume_events.append(event)

    assert resume_events[-1].type == "done"
    assert resume_events[-1].payload["status"] == "completed"
