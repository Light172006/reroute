"""Graph tests for chat_graph conversational agent."""

from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import MemorySaver

from reroute_agents.destinations.registry import load_seed_catalog_into_repository
from reroute_agents.graphs.chat_graph import build_chat_graph
from reroute_agents.llm import FakeLLM
from reroute_agents.repositories.in_memory import create_in_memory_repositories


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
