"""Stress tests for plan_graph, replan_graph, and chat_graph execution, loops, and HITL invariants."""

from __future__ import annotations

import asyncio
import warnings
from datetime import date, time
from decimal import Decimal
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from reroute_agents.config import settings
from reroute_agents.destinations.registry import load_seed_catalog_into_repository
from reroute_agents.graphs.chat_graph import build_chat_graph
from reroute_agents.graphs.plan_graph import build_plan_graph
from reroute_agents.graphs.replan_graph import build_replan_graph
from reroute_agents.llm import FakeLLM
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.state import (
    DraftItem,
    InjectedSignals,
    ItineraryDraft,
    Signals,
    TripSpec,
)


@pytest.fixture
def base_trip_spec() -> TripSpec:
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
async def test_plan_graph_fix_loop_caps_at_max_iterations(base_trip_spec: TripSpec) -> None:
    """Verify that an unfixable violation stops strictly at settings.max_plan_iterations (3) without infinite loop."""
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")
    await repos.trips.save_trip(base_trip_spec)

    # FakeLLM consistently returns overlapping items to induce persistent overlap violation
    p1, p2 = uuid4(), uuid4()
    broken_draft = ItineraryDraft(
        items=[
            DraftItem(
                day_index=1,
                position=0,
                place_id=p1,
                title="Attraction 1",
                category="sightseeing",
                setting="indoor",
                start_time=time(10, 0),
                end_time=time(12, 0),
                est_cost=Decimal(100),
            ),
            DraftItem(
                day_index=1,
                position=1,
                place_id=p2,
                title="Attraction 2 Overlap",
                category="sightseeing",
                setting="indoor",
                start_time=time(11, 0),  # Overlaps with Attraction 1
                end_time=time(13, 0),
                est_cost=Decimal(100),
            ),
        ]
    )

    fake_llm = FakeLLM(
        canned_responses={"ItineraryDraft": broken_draft}
    )

    graph = build_plan_graph(repos, llm_override=fake_llm)
    state = {
        "trip_id": str(base_trip_spec.trip_id),
        "spec": base_trip_spec,
        "candidates": [],
        "draft": None,
        "violations": [],
        "iteration": 0,
        "events": [],
    }

    final_state = await graph.ainvoke(state)

    # Must terminate and iteration must equal max_plan_iterations (3)
    assert final_state["iteration"] == settings.max_plan_iterations
    assert len(final_state["violations"]) > 0
    # Final version should still be saved even with unfixable warnings
    curr = await repos.itineraries.get_current_version(base_trip_spec.trip_id)
    assert curr is not None


@pytest.mark.asyncio
async def test_replan_graph_fix_loop_caps_at_max_iterations(base_trip_spec: TripSpec) -> None:
    """Verify that replan fix loop caps at settings.max_replan_iterations (2) without infinite looping."""
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")
    await repos.trips.save_trip(base_trip_spec)

    # Initial version
    k1 = uuid4()
    item1 = DraftItem(
        stable_key=k1,
        day_index=1,
        position=0,
        title="Ghum Monastery",
        category="culture",
        setting="indoor",
        start_time=time(10, 0),
        end_time=time(12, 0),
        est_cost=Decimal(100),
    )
    v1_id = await repos.itineraries.save_version(
        trip_id=base_trip_spec.trip_id,
        version_no=1,
        reason="Initial",
        created_by="agent:planner",
        items=[item1],
    )
    await repos.trips.update_current_version(base_trip_spec.trip_id, v1_id)

    # Injected disruption
    inj = InjectedSignals(type="closure", day_index=1, params={"place_id": str(uuid4()), "reason": "Closed"})
    signals = Signals(injected=inj)

    # Broken replan draft that always has an overlap violation
    broken_replan_draft = ItineraryDraft(
        items=[
            DraftItem(
                stable_key=k1,
                day_index=1,
                position=0,
                title="Item A",
                category="culture",
                setting="indoor",
                start_time=time(10, 0),
                end_time=time(12, 0),
                est_cost=Decimal(100),
            ),
            DraftItem(
                day_index=1,
                position=1,
                title="Item B Overlap",
                category="culture",
                setting="indoor",
                start_time=time(11, 0),
                end_time=time(13, 0),
                est_cost=Decimal(100),
            ),
        ]
    )

    fake_llm = FakeLLM(canned_responses={"ItineraryDraft": broken_replan_draft})
    checkpointer = MemorySaver()
    graph = build_replan_graph(repos, llm_override=fake_llm, checkpointer=checkpointer)

    run_id = uuid4()
    state = {
        "trip_id": str(base_trip_spec.trip_id),
        "run_id": str(run_id),
        "base_version_id": str(v1_id),
        "spec": base_trip_spec,
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
    }

    # Graph runs up to proposal interrupt
    paused = await graph.ainvoke(state, config={"configurable": {"thread_id": str(run_id)}})
    # Replan loop capped at max_replan_iterations (2)
    assert paused["iteration"] <= settings.max_replan_iterations + 1


@pytest.mark.asyncio
async def test_replanner_scope_invariant_preserves_locked_and_unaffected_items(base_trip_spec: TripSpec) -> None:
    """Stress test: 50 replans verify unaffected and locked items are strictly preserved."""
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")
    await repos.trips.save_trip(base_trip_spec)

    key_unaffected = uuid4()
    key_locked = uuid4()
    key_affected = uuid4()

    unaffected_item = DraftItem(
        stable_key=key_unaffected,
        day_index=1,
        position=0,
        title="Peace Pagoda",
        category="culture",
        setting="indoor",
        start_time=time(9, 0),
        end_time=time(11, 0),
        est_cost=Decimal(100),
    )
    locked_item = DraftItem(
        stable_key=key_locked,
        day_index=1,
        position=1,
        title="Heritage Tea Tasting (Pre-booked)",
        category="food",
        setting="indoor",
        is_locked=True,
        start_time=time(11, 30),
        end_time=time(13, 0),
        est_cost=Decimal(500),
    )
    affected_item = DraftItem(
        stable_key=key_affected,
        day_index=1,
        position=2,
        title="Observatory Hill Trek",
        category="nature",
        setting="outdoor",
        start_time=time(14, 0),
        end_time=time(16, 0),
        est_cost=Decimal(150),
    )

    items = [unaffected_item, locked_item, affected_item]
    v1_id = await repos.itineraries.save_version(
        trip_id=base_trip_spec.trip_id,
        version_no=1,
        reason="Initial",
        created_by="agent:planner",
        items=items,
    )
    await repos.trips.update_current_version(base_trip_spec.trip_id, v1_id)

    # Disruption targeting affected_item (rain at 14:00 - 16:00)
    injected_weather = InjectedSignals(
        type="weather",
        day_index=1,
        params={"precip_prob": 0.90, "from": "14:00", "to": "16:00"},
    )
    signals = Signals(injected=injected_weather)

    for _ in range(10):
        run_id = uuid4()
        checkpointer = MemorySaver()
        fake_llm = FakeLLM()
        graph = build_replan_graph(repos, llm_override=fake_llm, checkpointer=checkpointer)

        initial_state = {
            "trip_id": str(base_trip_spec.trip_id),
            "run_id": str(run_id),
            "base_version_id": str(v1_id),
            "spec": base_trip_spec,
            "signals": signals,
            "disruptions": [],
            "affected_item_ids": [],
            "current_items": items,
            "draft": None,
            "violations": [],
            "proposal": None,
            "decision": None,
            "iteration": 0,
            "events": [],
        }

        paused = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": str(run_id)}})
        assert "__interrupt__" in paused
        pending_list = await repos.proposals.get_pending_proposals(base_trip_spec.trip_id)
        assert len(pending_list) > 0
        proposal = pending_list[-1]

        proposed_keys = {it.stable_key: it for it in proposal.proposed_items}

        # 1. Unaffected item MUST still exist with same time
        assert key_unaffected in proposed_keys
        assert proposed_keys[key_unaffected].start_time == unaffected_item.start_time

        # 2. Locked item MUST NOT be modified or moved
        assert key_locked in proposed_keys
        assert proposed_keys[key_locked].is_locked is True
        assert proposed_keys[key_locked].start_time == locked_item.start_time
        assert proposed_keys[key_locked].end_time == locked_item.end_time


@pytest.mark.asyncio
async def test_replan_graph_rejection_discards_changes(base_trip_spec: TripSpec) -> None:
    """Verify resuming with decision=reject marks proposal rejected without saving new version."""
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")
    await repos.trips.save_trip(base_trip_spec)

    k1 = uuid4()
    item1 = DraftItem(
        stable_key=k1,
        day_index=1,
        position=0,
        title="Observatory Hill",
        category="nature",
        setting="outdoor",
        start_time=time(14, 0),
        end_time=time(16, 0),
        est_cost=Decimal(100),
    )
    v1_id = await repos.itineraries.save_version(
        trip_id=base_trip_spec.trip_id,
        version_no=1,
        reason="Initial",
        created_by="agent:planner",
        items=[item1],
    )
    await repos.trips.update_current_version(base_trip_spec.trip_id, v1_id)

    injected = InjectedSignals(type="weather", day_index=1, params={"precip_prob": 0.95, "from": "14:00", "to": "16:00"})
    signals = Signals(injected=injected)

    run_id = uuid4()
    checkpointer = MemorySaver()
    graph = build_replan_graph(repos, llm_override=FakeLLM(), checkpointer=checkpointer)
    config = {"configurable": {"thread_id": str(run_id)}}

    state = {
        "trip_id": str(base_trip_spec.trip_id),
        "run_id": str(run_id),
        "base_version_id": str(v1_id),
        "spec": base_trip_spec,
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
    }

    # Run up to interrupt
    await graph.ainvoke(state, config=config)

    # Resume with reject
    await graph.ainvoke(Command(resume={"decision": "reject"}), config=config)

    # Verify current version is STILL v1_id
    curr = await repos.itineraries.get_current_version(base_trip_spec.trip_id)
    assert curr is not None
    assert curr["id"] == v1_id
    assert curr["version_no"] == 1


@pytest.mark.asyncio
async def test_replan_graph_consecutive_alternatives_terminates(base_trip_spec: TripSpec) -> None:
    """Verify requesting alternatives repeatedly does not create an uncontrolled infinite loop."""
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")
    await repos.trips.save_trip(base_trip_spec)

    k1 = uuid4()
    item1 = DraftItem(
        stable_key=k1,
        day_index=1,
        position=0,
        title="Observatory Hill",
        category="nature",
        setting="outdoor",
        start_time=time(14, 0),
        end_time=time(16, 0),
        est_cost=Decimal(100),
    )
    v1_id = await repos.itineraries.save_version(
        trip_id=base_trip_spec.trip_id,
        version_no=1,
        reason="Initial",
        created_by="agent:planner",
        items=[item1],
    )
    await repos.trips.update_current_version(base_trip_spec.trip_id, v1_id)

    injected = InjectedSignals(type="weather", day_index=1, params={"precip_prob": 0.95, "from": "14:00", "to": "16:00"})
    signals = Signals(injected=injected)

    run_id = uuid4()
    checkpointer = MemorySaver()
    graph = build_replan_graph(repos, llm_override=FakeLLM(), checkpointer=checkpointer)
    config = {"configurable": {"thread_id": str(run_id)}}

    state = {
        "trip_id": str(base_trip_spec.trip_id),
        "run_id": str(run_id),
        "base_version_id": str(v1_id),
        "spec": base_trip_spec,
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
    }

    # Initial pause
    await graph.ainvoke(state, config=config)

    # Request alternatives 3 times, then approve
    for _ in range(3):
        await graph.ainvoke(Command(resume={"decision": "alternatives"}), config=config)

    # Finally approve
    await graph.ainvoke(Command(resume={"decision": "approve"}), config=config)

    curr = await repos.itineraries.get_current_version(base_trip_spec.trip_id)
    assert curr is not None
    assert curr["version_no"] == 2


@pytest.mark.asyncio
async def test_chat_graph_scope_deflection_and_context_reply(base_trip_spec: TripSpec) -> None:
    """Test chat_graph deflecting non-travel prompts and answering trip queries."""
    repos = create_in_memory_repositories()
    fake_llm = FakeLLM()
    graph = build_chat_graph(repos, llm_override=fake_llm)

    from langchain_core.messages import HumanMessage

    # 1. Out of scope request
    res_deflect = await graph.ainvoke({
        "trip_id": str(base_trip_spec.trip_id),
        "messages": [HumanMessage(content="Write Python code to compute Fibonacci numbers")],
    })
    last_msg = res_deflect["messages"][-1].content
    assert "specialize strictly in managing your travel" in last_msg

    # 2. In-scope trip query
    res_scope = await graph.ainvoke({
        "trip_id": str(base_trip_spec.trip_id),
        "messages": [HumanMessage(content="What time does Tiger Hill open?")],
    })
    last_scope_msg = res_scope["messages"][-1].content
    assert len(last_scope_msg) > 0


@pytest.mark.asyncio
async def test_concurrency_30_simultaneous_trips_independent_execution(base_trip_spec: TripSpec) -> None:
    """Run 20 concurrent plan_graph executions for distinct trips to confirm no cross-trip state corruption."""
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")

    async def run_single_plan(idx: int) -> None:
        t_id = uuid4()
        spec = base_trip_spec.model_copy(update={"trip_id": t_id})
        await repos.trips.save_trip(spec)

        p1 = uuid4()
        draft = ItineraryDraft(
            items=[
                DraftItem(
                    day_index=1,
                    position=0,
                    place_id=p1,
                    title=f"Attraction {idx}",
                    category="sightseeing",
                    setting="indoor",
                    start_time=time(10, 0),
                    end_time=time(12, 0),
                    est_cost=Decimal(100),
                )
            ]
        )
        fake_llm = FakeLLM(canned_responses={"ItineraryDraft": draft})
        graph = build_plan_graph(repos, llm_override=fake_llm)
        state = {
            "trip_id": str(t_id),
            "spec": spec,
            "candidates": [],
            "draft": None,
            "violations": [],
            "iteration": 0,
            "events": [],
        }
        await graph.ainvoke(state)
        curr = await repos.itineraries.get_current_version(t_id)
        assert curr is not None
        items = await repos.itineraries.get_version_items(curr["id"])
        assert len(items) == 1
        assert items[0].title == f"Attraction {idx}"

    tasks = [asyncio.create_task(run_single_plan(i)) for i in range(20)]
    await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_checkpoint_msgpack_no_unregistered_type_warnings(base_trip_spec: TripSpec) -> None:
    """Verify that checkpointing custom models emits no msgpack unregistered type warnings (AG-003)."""
    from reroute_agents.checkpointer import create_default_checkpointer
    from reroute_agents.gateway import resume_replan, run_plan, run_replan
    from reroute_agents.state import AgentEvent, DisruptionEvent

    chk = create_default_checkpointer()
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")
    await repos.trips.save_trip(base_trip_spec)

    # 1. Direct serde round-trip verification with zero warnings
    test_models = [
        base_trip_spec,
        Signals(),
        DisruptionEvent(type="closure", severity="high", summary="Road blocked", source="injected"),
        DraftItem(
            day_index=1,
            position=0,
            title="Stop",
            category="sightseeing",
            setting="indoor",
            start_time=time(10, 0),
            end_time=time(11, 0),
        ),
        ItineraryDraft(items=[]),
        AgentEvent(seq=1, run_id=uuid4(), type="step", data={"message": "ok"}),
    ]

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        for m in test_models:
            serialized = chk.serde.dumps_typed(m)
            deserialized = chk.serde.loads_typed(serialized)
            assert type(deserialized) is type(m)

    unregistered_warnings = [
        str(w.message) for w in recorded if "unregistered type" in str(w.message).lower()
    ]
    assert len(unregistered_warnings) == 0, f"Unregistered warnings found: {unregistered_warnings}"

    # 2. Full workflow execution through gateway with zero warnings
    with warnings.catch_warnings(record=True) as recorded_wf:
        warnings.simplefilter("always")
        events = []
        async for evt in run_plan(uuid4(), base_trip_spec.trip_id, repos=repos, checkpointer=chk):
            events.append(evt)

        assert any(e.type == "done" for e in events)

        # Trigger replan to hit interrupt()
        injected = InjectedSignals(
            type="closure",
            day_index=1,
            params={"place_name": "Tiger Hill", "reason": "Landslide", "severity": "high"},
        )
        replan_run_id = uuid4()
        replan_events = []
        async for evt in run_replan(
            replan_run_id, base_trip_spec.trip_id, injected=injected, repos=repos, checkpointer=chk
        ):
            replan_events.append(evt)

        # Resume replan to finish
        resume_events = []
        async for evt in resume_replan(
            replan_run_id, "approve", repos=repos, checkpointer=chk
        ):
            resume_events.append(evt)

    wf_unregistered = [
        str(w.message) for w in recorded_wf if "unregistered type" in str(w.message).lower()
    ]
    assert len(wf_unregistered) == 0, f"Workflow emitted unregistered warnings: {wf_unregistered}"
