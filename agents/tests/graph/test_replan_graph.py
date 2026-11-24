"""Graph tests for replan_graph: HITL interrupt, resume, approval, rejection, and invariants."""

from datetime import date, time
from decimal import Decimal
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from reroute_agents.destinations.registry import load_seed_catalog_into_repository
from reroute_agents.graphs.replan_graph import build_replan_graph
from reroute_agents.llm import FakeLLM
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.state import (
    DraftItem,
    InjectedSignals,
    Signals,
    TripSpec,
)


@pytest.mark.asyncio
async def test_replan_graph_interrupt_and_approve() -> None:
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

    # Create initial version 1 with an outdoor item on Day 2
    outdoor_item_key = uuid4()
    unaffected_item_key = uuid4()

    item_d1 = DraftItem(
        stable_key=unaffected_item_key,
        day_index=1,
        position=0,
        title="Ghum Monastery",
        category="culture",
        setting="indoor",
        start_time=time(10, 0),
        end_time=time(12, 0),
        est_cost=Decimal(100),
    )
    item_d2 = DraftItem(
        stable_key=outdoor_item_key,
        day_index=2,
        position=0,
        title="Tiger Hill Walk",
        category="nature",
        setting="outdoor",
        start_time=time(14, 0),
        end_time=time(16, 0),
        est_cost=Decimal(200),
    )

    v1_id = await repos.itineraries.save_version(
        trip_id=trip_id,
        version_no=1,
        reason="Initial plan",
        created_by="agent:planner",
        items=[item_d1, item_d2],
    )
    await repos.trips.update_current_version(trip_id, v1_id)

    # Injected rain disruption on Day 2 from 14:00 to 18:00
    injected_weather = InjectedSignals(
        type="weather",
        day_index=2,
        params={"precip_prob": 0.85, "from": "14:00", "to": "18:00"},
    )
    signals = Signals(injected=injected_weather)

    run_id = uuid4()
    fake_llm = FakeLLM()
    checkpointer = MemorySaver()
    graph = build_replan_graph(repos, llm_override=fake_llm, checkpointer=checkpointer)

    config = {"configurable": {"thread_id": str(run_id)}}
    initial_state = {
        "trip_id": str(trip_id),
        "run_id": str(run_id),
        "base_version_id": str(v1_id),
        "spec": spec,
        "signals": signals,
        "disruptions": [],
        "affected_item_ids": [],
        "current_items": [item_d1, item_d2],
        "draft": None,
        "violations": [],
        "proposal": None,
        "decision": None,
        "iteration": 0,
        "events": [],
    }

    # First run up to interrupt()
    _paused_state = await graph.ainvoke(initial_state, config=config)

    # Graph must be paused waiting for user input
    pending_proposals = await repos.proposals.get_pending_proposals(trip_id)
    assert len(pending_proposals) == 1
    proposal = pending_proposals[0]
    assert proposal.status == "pending"
    assert proposal.items_changed == 1

    # Resume with approval
    _resumed_state = await graph.ainvoke(
        Command(resume={"decision": "approve"}),
        config=config,
    )

    # Verify Version 2 was created
    curr_v = await repos.itineraries.get_current_version(trip_id)
    assert curr_v is not None
    assert curr_v["version_no"] == 2
    assert curr_v["parent_version_id"] == v1_id

    # Invariant: Unaffected item on Day 1 MUST be identical
    v2_items = await repos.itineraries.get_version_items(curr_v["id"])
    v2_d1_item = next(it for it in v2_items if it.stable_key == unaffected_item_key)
    assert v2_d1_item.title == item_d1.title
    assert v2_d1_item.start_time == item_d1.start_time
    assert v2_d1_item.end_time == item_d1.end_time
    assert v2_d1_item.est_cost == item_d1.est_cost

    # Affected Day 2 item was substituted
    v2_d2_item = next(it for it in v2_items if it.stable_key == outdoor_item_key)
    assert v2_d2_item.title != item_d2.title


@pytest.mark.asyncio
async def test_replan_graph_reject_preserves_current() -> None:
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

    item = DraftItem(
        stable_key=uuid4(),
        day_index=2,
        position=0,
        title="Tiger Hill Walk",
        category="nature",
        setting="outdoor",
        start_time=time(14, 0),
        end_time=time(16, 0),
        est_cost=Decimal(200),
    )

    v1_id = await repos.itineraries.save_version(
        trip_id=trip_id,
        version_no=1,
        reason="Initial plan",
        created_by="agent:planner",
        items=[item],
    )
    await repos.trips.update_current_version(trip_id, v1_id)

    injected_weather = InjectedSignals(
        type="weather",
        day_index=2,
        params={"precip_prob": 0.85, "from": "14:00", "to": "18:00"},
    )
    signals = Signals(injected=injected_weather)

    run_id = uuid4()
    graph = build_replan_graph(repos, checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": str(run_id)}}

    # Run up to interrupt
    await graph.ainvoke(
        {
            "trip_id": str(trip_id),
            "run_id": str(run_id),
            "base_version_id": str(v1_id),
            "spec": spec,
            "signals": signals,
            "disruptions": [],
            "affected_item_ids": [],
            "current_items": [item],
            "draft": None,
            "violations": [],
            "proposal": None,
            "decision": None,
            "iteration": 0,
            "events": [],
        },
        config=config,
    )

    # Resume with rejection
    await graph.ainvoke(Command(resume={"decision": "reject"}), config=config)

    # Current version is still v1
    curr_v = await repos.itineraries.get_current_version(trip_id)
    assert curr_v is not None
    assert curr_v["version_no"] == 1


@pytest.mark.asyncio
async def test_replan_graph_locked_items_are_never_changed() -> None:
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

    locked_key = uuid4()
    locked_item = DraftItem(
        stable_key=locked_key,
        day_index=2,
        position=0,
        title="Locked Outdoor Sunrise",
        category="nature",
        setting="outdoor",
        start_time=time(14, 0),
        end_time=time(16, 0),
        is_locked=True,  # User explicitly locked this stop
    )

    v1_id = await repos.itineraries.save_version(
        trip_id=trip_id,
        version_no=1,
        reason="Initial plan",
        created_by="agent:planner",
        items=[locked_item],
    )
    await repos.trips.update_current_version(trip_id, v1_id)

    injected_weather = InjectedSignals(
        type="weather",
        day_index=2,
        params={"precip_prob": 0.85, "from": "14:00", "to": "18:00"},
    )
    signals = Signals(injected=injected_weather)

    run_id = uuid4()
    graph = build_replan_graph(repos, checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": str(run_id)}}

    # Since the only affected item is locked, affected_item_ids becomes empty
    # and the graph finishes with NO changes!
    final_state = await graph.ainvoke(
        {
            "trip_id": str(trip_id),
            "run_id": str(run_id),
            "base_version_id": str(v1_id),
            "spec": spec,
            "signals": signals,
            "disruptions": [],
            "affected_item_ids": [],
            "current_items": [locked_item],
            "draft": None,
            "violations": [],
            "proposal": None,
            "decision": None,
            "iteration": 0,
            "events": [],
        },
        config=config,
    )

    # Locked item was not changed
    assert len(final_state.get("affected_item_ids", [])) == 0
    curr_v = await repos.itineraries.get_current_version(trip_id)
    assert curr_v["version_no"] == 1


@pytest.mark.asyncio
async def test_replan_graph_stale_proposal_cannot_be_applied() -> None:
    """Verify that if an itinerary advances version in parallel, a stale proposal is rejected."""
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

    item1 = DraftItem(
        day_index=2,
        position=0,
        title="Tiger Hill Walk",
        category="nature",
        setting="outdoor",
        start_time=time(14, 0),
        end_time=time(16, 0),
        est_cost=Decimal(200),
    )
    v1_id = await repos.itineraries.save_version(
        trip_id=trip_id,
        version_no=1,
        reason="Initial plan",
        created_by="agent:planner",
        items=[item1],
    )
    await repos.trips.update_current_version(trip_id, v1_id)

    injected_weather = InjectedSignals(
        type="weather",
        day_index=2,
        params={"precip_prob": 0.85, "from": "14:00", "to": "18:00"},
    )
    signals = Signals(injected=injected_weather)

    run_id = uuid4()
    checkpointer = MemorySaver()
    graph = build_replan_graph(repos, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": str(run_id)}}

    # Pause at interrupt
    await graph.ainvoke(
        {
            "trip_id": str(trip_id),
            "run_id": str(run_id),
            "base_version_id": str(v1_id),
            "spec": spec,
            "signals": signals,
            "disruptions": [],
            "affected_item_ids": [],
            "current_items": [item1],
            "draft": None,
            "violations": [],
            "proposal": None,
            "decision": None,
            "iteration": 0,
            "events": [],
        },
        config=config,
    )

    # In parallel, someone advances the trip to version 2
    v2_id = await repos.itineraries.save_version(
        trip_id=trip_id,
        version_no=2,
        parent_version_id=v1_id,
        reason="Concurrent manual edit",
        created_by="user",
        items=[item1],
    )
    await repos.trips.update_current_version(trip_id, v2_id)

    # Now attempt to resume approval on the stale proposal
    resume_state = await graph.ainvoke(Command(resume={"decision": "approve"}), config=config)

    # The stale approval must fail and the trip must remain at v2
    curr_v = await repos.itineraries.get_current_version(trip_id)
    assert curr_v is not None
    assert curr_v["id"] == v2_id
    assert curr_v["version_no"] == 2

    # Events must reflect failure
    done_evts = [e for e in resume_state["events"] if e.type == "done"]
    assert any(e.payload.get("status") == "failed" for e in done_evts)

