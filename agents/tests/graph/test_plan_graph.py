"""Graph tests for plan_graph with FakeLLM and in-memory persistence."""

from datetime import date, time
from decimal import Decimal
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import MemorySaver

from reroute_agents.destinations.registry import load_seed_catalog_into_repository
from reroute_agents.graphs.plan_graph import build_plan_graph
from reroute_agents.llm import FakeLLM
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.state import DraftItem, ItineraryDraft, PlanState, TripSpec


@pytest.mark.asyncio
async def test_plan_graph_happy_path() -> None:
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")

    trip_id = uuid4()
    spec = TripSpec(
        trip_id=trip_id,
        destination="Darjeeling",
        start_date=date(2026, 12, 12),
        end_date=date(2026, 12, 13),
        group_size=2,
        budget_total=Decimal(15000),
        currency="INR",
        pace="balanced",
        vibe_tags=["nature", "food"],
    )
    await repos.trips.save_trip(spec)

    # Setup FakeLLM with scripted response
    p1 = uuid4()
    p2 = uuid4()
    mock_draft = ItineraryDraft(
        items=[
            DraftItem(
                day_index=1,
                position=0,
                place_id=p1,
                title="Tiger Hill",
                category="nature",
                setting="outdoor",
                start_time=time(6, 0),
                end_time=time(8, 0),
                est_cost=Decimal(200),
            ),
            DraftItem(
                day_index=1,
                position=1,
                place_id=p2,
                title="Glenary's Bakery",
                category="food",
                setting="indoor",
                start_time=time(9, 0),
                end_time=time(10, 30),
                est_cost=Decimal(600),
                travel_minutes=25,
            ),
        ],
        summary="Darjeeling highlights weekend plan.",
    )

    fake_llm = FakeLLM(canned_responses={"ItineraryDraft": mock_draft})
    checkpointer = MemorySaver()
    graph = build_plan_graph(repos, llm_override=fake_llm, checkpointer=checkpointer)

    initial_state: PlanState = {
        "trip_id": str(trip_id),
        "spec": spec,
        "candidates": [],
        "draft": None,
        "violations": [],
        "iteration": 0,
        "events": [],
    }

    config = {"configurable": {"thread_id": str(uuid4())}}
    final_state = await graph.ainvoke(initial_state, config=config)

    assert final_state["draft"] is not None
    assert len(final_state["draft"].items) == 2

    # Check persistence
    curr_v = await repos.itineraries.get_current_version(trip_id)
    assert curr_v is not None
    assert curr_v["version_no"] == 1
    assert curr_v["created_by"] == "agent:planner"

    # Verify event stream
    event_types = [e.type for e in final_state["events"]]
    assert "step" in event_types
    assert "draft" in event_types
    assert "done" in event_types


@pytest.mark.asyncio
async def test_plan_graph_bounded_loop_exhaustion() -> None:
    repos = create_in_memory_repositories()
    trip_id = uuid4()
    spec = TripSpec(
        trip_id=trip_id,
        destination="Darjeeling",
        start_date=date(2026, 12, 12),
        end_date=date(2026, 12, 12),
        budget_total=Decimal(100),  # Intentionally tiny budget to force violations
        pace="balanced",
    )
    await repos.trips.save_trip(spec)

    # Return draft with cost 500 > 100 on every iteration
    bad_draft = ItineraryDraft(
        items=[
            DraftItem(
                day_index=1,
                position=0,
                title="Costly Place",
                category="sightseeing",
                setting="indoor",
                start_time=time(10, 0),
                end_time=time(12, 0),
                est_cost=Decimal(500),
            )
        ],
        summary="Overbudget plan",
    )

    fake_llm = FakeLLM(canned_responses={"ItineraryDraft": bad_draft})
    graph = build_plan_graph(repos, llm_override=fake_llm, checkpointer=MemorySaver())

    config = {"configurable": {"thread_id": str(uuid4())}}
    initial_state: PlanState = {
        "trip_id": str(trip_id),
        "spec": spec,
        "candidates": [],
        "draft": None,
        "violations": [],
        "iteration": 0,
        "events": [],
    }
    final_state = await graph.ainvoke(initial_state, config=config)

    # Must terminate within max 3 iterations
    assert final_state["iteration"] <= 3
    # Check that finalize was reached and flagged the issue
    curr_v = await repos.itineraries.get_current_version(trip_id)
    assert curr_v is not None
    items = await repos.itineraries.get_version_items(curr_v["id"])
    assert any("warning_over_budget" in it.flags for it in items)
    # Validation failure must NOT report completed status in done event
    done_evts = [e for e in final_state["events"] if e.type == "done"]
    assert len(done_evts) > 0
    assert done_evts[-1].payload.get("status") == "failed"


@pytest.mark.asyncio
async def test_plan_graph_no_candidates_fails_explicitly() -> None:
    """Verify that when no candidate places are found, planner does not fabricate places."""
    repos = create_in_memory_repositories()
    trip_id = uuid4()
    spec = TripSpec(
        trip_id=trip_id,
        destination="UnknownNonexistentLocation123",
        start_date=date(2026, 12, 12),
        end_date=date(2026, 12, 13),
        budget_total=Decimal(15000),
        pace="balanced",
    )
    await repos.trips.save_trip(spec)

    graph = build_plan_graph(repos, checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": str(uuid4())}}
    initial_state: PlanState = {
        "trip_id": str(trip_id),
        "spec": spec,
        "candidates": [],
        "draft": None,
        "violations": [],
        "iteration": 0,
        "events": [],
    }
    final_state = await graph.ainvoke(initial_state, config=config)

    # Must fail cleanly and not invent stops
    assert final_state["draft"] is not None
    assert len(final_state["draft"].items) == 0

    event_types = [e.type for e in final_state["events"]]
    assert "error" in event_types
    err_evts = [e for e in final_state["events"] if e.type == "error"]
    assert any(e.payload.get("code") == "no_candidates_found" for e in err_evts)

    done_evts = [e for e in final_state["events"] if e.type == "done"]
    assert len(done_evts) > 0
    assert done_evts[-1].payload.get("status") == "failed"

