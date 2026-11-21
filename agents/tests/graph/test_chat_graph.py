"""Graph tests for chat_graph conversational agent and bounded ReAct tool loop."""

from datetime import date, time
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import MemorySaver

from reroute_agents.destinations.registry import load_seed_catalog_into_repository
from reroute_agents.graphs.chat_graph import build_chat_graph
from reroute_agents.llm import FakeLLM
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.state import DraftItem, TripSpec


@pytest.mark.asyncio
async def test_chat_graph_conversational_response() -> None:
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")

    trip_id = uuid4()
    run_id = uuid4()
    fake_llm = FakeLLM(
        canned_responses={"text": "I am monitoring your Darjeeling trip. Everything looks clear!"}
    )

    graph = build_chat_graph(repos, llm_override=fake_llm, checkpointer=MemorySaver())

    initial_state = {
        "trip_id": str(trip_id),
        "run_id": str(run_id),
        "messages": [{"role": "user", "content": "What is scheduled for tomorrow?"}],
        "current_items": [],
        "spec": None,
        "proposal": None,
        "events": [],
    }

    config = {"configurable": {"thread_id": str(run_id)}}
    final_state = await graph.ainvoke(initial_state, config=config)

    assert len(final_state["messages"]) >= 2
    # Verify token event emission
    event_types = [e.type for e in final_state["events"]]
    assert "token" in event_types
    assert "done" in event_types


@pytest.mark.asyncio
async def test_chat_graph_out_of_scope_redirection() -> None:
    repos = create_in_memory_repositories()
    trip_id = uuid4()
    run_id = uuid4()

    graph = build_chat_graph(repos, checkpointer=MemorySaver())

    initial_state = {
        "trip_id": str(trip_id),
        "run_id": str(run_id),
        "messages": [
            {"role": "user", "content": "Can you write python code to solve math equations?"}
        ],
        "current_items": [],
        "spec": None,
        "proposal": None,
        "events": [],
    }

    config = {"configurable": {"thread_id": str(run_id)}}
    final_state = await graph.ainvoke(initial_state, config=config)

    last_ai = final_state["messages"][-1]
    assert "strictly in managing your travel itinerary" in str(last_ai.content)


@pytest.mark.asyncio
async def test_chat_graph_executes_get_itinerary_tool_call() -> None:
    """Verify ReAct loop executes get_itinerary tool call and returns tool results."""
    repos = create_in_memory_repositories()
    trip_id = uuid4()
    run_id = uuid4()

    # Save a trip and an itinerary
    spec = TripSpec(
        trip_id=trip_id,
        destination="Darjeeling",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 2),
        budget_total=Decimal(10000),
    )
    await repos.trips.save_trip(spec)

    item1 = DraftItem(
        day_index=1,
        position=0,
        title="Tiger Hill Sunrise",
        category="sightseeing",
        setting="outdoor",
        start_time=time(4, 30),
        end_time=time(7, 30),
        est_cost=Decimal(100),
    )
    await repos.itineraries.save_version(
        trip_id=trip_id,
        version_no=1,
        reason="initial",
        created_by="agent",
        items=[item1],
    )

    canned_calls = [
        {
            "name": "get_itinerary",
            "args": {"trip_id": str(trip_id)},
            "id": "call_itin_1",
        }
    ]
    fake_llm = FakeLLM(
        canned_responses={
            "tool_calls": canned_calls,
            "text": "You have 1 stop scheduled: Tiger Hill Sunrise at 04:30.",
        }
    )

    graph = build_chat_graph(repos, llm_override=fake_llm, checkpointer=MemorySaver())

    initial_state = {
        "trip_id": str(trip_id),
        "run_id": str(run_id),
        "messages": [{"role": "user", "content": "Can you check my current itinerary?"}],
        "current_items": [],
        "spec": None,
        "proposal": None,
        "events": [],
    }

    config = {"configurable": {"thread_id": str(run_id)}}
    final_state = await graph.ainvoke(initial_state, config=config)

    event_types = [e.type for e in final_state["events"]]
    assert "tool_call" in event_types
    assert "tool_result" in event_types
    assert "token" in event_types
    assert "done" in event_types

    # Verify tool result contains itinerary stop
    tool_results = [e for e in final_state["events"] if e.type == "tool_result"]
    assert any("Tiger Hill" in str(tr.payload) for tr in tool_results)


@pytest.mark.asyncio
async def test_chat_graph_modify_item_creates_proposal_only_preserving_hitl() -> None:
    """Verify modify_item creates a pending proposal and never writes directly to DB."""
    repos = create_in_memory_repositories()
    trip_id = uuid4()
    run_id = uuid4()

    spec = TripSpec(
        trip_id=trip_id,
        destination="Darjeeling",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 2),
        budget_total=Decimal(10000),
    )
    await repos.trips.save_trip(spec)

    item1 = DraftItem(
        day_index=1,
        position=0,
        title="Morning Tea Walk",
        category="sightseeing",
        setting="outdoor",
        start_time=time(8, 0),
        end_time=time(10, 0),
        est_cost=Decimal(50),
    )
    await repos.itineraries.save_version(
        trip_id=trip_id,
        version_no=1,
        reason="initial",
        created_by="agent",
        items=[item1],
    )

    canned_calls = [
        {
            "name": "modify_item",
            "args": {
                "item_stable_key": str(item1.stable_key),
                "reason": "Push tea walk by 1 hour for breakfast",
                "start_time": "09:00",
                "end_time": "11:00",
            },
            "id": "call_mod_1",
        }
    ]
    fake_llm = FakeLLM(
        canned_responses={
            "tool_calls": canned_calls,
            "text": "I have drafted a proposal to shift your tea walk to 09:00. Please review and approve it.",
        }
    )

    graph = build_chat_graph(repos, llm_override=fake_llm, checkpointer=MemorySaver())

    initial_state = {
        "trip_id": str(trip_id),
        "run_id": str(run_id),
        "messages": [{"role": "user", "content": "Please delay my tea walk to 9am"}],
        "current_items": [],
        "spec": None,
        "proposal": None,
        "events": [],
    }

    config = {"configurable": {"thread_id": str(run_id)}}
    final_state = await graph.ainvoke(initial_state, config=config)

    # 1. Invariant: Database version 1 was NOT modified
    curr_v = await repos.itineraries.get_current_version(trip_id)
    assert curr_v is not None
    assert curr_v["version_no"] == 1
    stored_items = await repos.itineraries.get_version_items(curr_v["id"])
    assert stored_items[0].start_time == time(8, 0), "DB item was modified without approval!"

    # 2. A pending proposal was saved
    assert final_state.get("proposal") is not None
    saved_proposal = await repos.proposals.get_proposal(final_state["proposal"].id)
    assert saved_proposal is not None
    assert saved_proposal.status == "pending"

    # 3. proposal_event was emitted
    event_types = [e.type for e in final_state["events"]]
    assert "proposal" in event_types


@pytest.mark.asyncio
async def test_chat_graph_bounded_tool_loop_caps_at_max_iterations() -> None:
    """Verify tool execution loop strictly caps at settings.max_chat_iterations without looping infinitely."""
    repos = create_in_memory_repositories()
    trip_id = uuid4()
    run_id = uuid4()

    # Create a mock LLM that always requests tools
    infinite_tool_calls = [
        {
            "name": "get_itinerary",
            "args": {"trip_id": str(trip_id)},
            "id": "call_loop",
        }
    ]

    class LoopingLLM:
        def bind_tools(self, tools: Any) -> Any:
            return self

        async def ainvoke(self, messages: Any, config: Any = None) -> Any:
            from langchain_core.messages import AIMessage

            return AIMessage(content="", tool_calls=infinite_tool_calls)

    looping_llm = LoopingLLM()
    graph = build_chat_graph(repos, llm_override=looping_llm, checkpointer=MemorySaver())

    initial_state = {
        "trip_id": str(trip_id),
        "run_id": str(run_id),
        "messages": [{"role": "user", "content": "Loop test"}],
        "current_items": [],
        "spec": None,
        "proposal": None,
        "events": [],
    }

    config = {"configurable": {"thread_id": str(run_id)}}
    final_state = await graph.ainvoke(initial_state, config=config)

    # Must terminate cleanly and not loop forever
    assert final_state["iteration"] >= 5
    last_msg = final_state["messages"][-1]
    assert "maximum reasoning steps" in str(last_msg.content)
    event_types = [e.type for e in final_state["events"]]
    assert "done" in event_types


@pytest.mark.asyncio
async def test_chat_graph_handles_unknown_tool_and_exceptions_gracefully() -> None:
    """Verify unknown tool calls and exceptions yield recoverable error events without crashing."""
    repos = create_in_memory_repositories()
    trip_id = uuid4()
    run_id = uuid4()

    canned_calls = [
        {
            "name": "nonexistent_unknown_tool",
            "args": {"foo": "bar"},
            "id": "call_bad_1",
        }
    ]
    fake_llm = FakeLLM(
        canned_responses={
            "tool_calls": canned_calls,
            "text": "Handled unknown tool gracefully.",
        }
    )

    graph = build_chat_graph(repos, llm_override=fake_llm, checkpointer=MemorySaver())

    initial_state = {
        "trip_id": str(trip_id),
        "run_id": str(run_id),
        "messages": [{"role": "user", "content": "Run unknown tool"}],
        "current_items": [],
        "spec": None,
        "proposal": None,
        "events": [],
    }

    config = {"configurable": {"thread_id": str(run_id)}}
    final_state = await graph.ainvoke(initial_state, config=config)

    event_types = [e.type for e in final_state["events"]]
    assert "error" in event_types
    err_events = [e for e in final_state["events"] if e.type == "error"]
    assert any("tool_not_found" in str(e.payload) for e in err_events)
    assert "done" in event_types
