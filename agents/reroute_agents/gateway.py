"""Gateway: Public asynchronous streaming interface connecting API routers to LangGraph agents."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any, Literal
from uuid import UUID

from langgraph.types import Command

from reroute_agents.checkpointer import configure_checkpointer, create_default_checkpointer
from reroute_agents.destinations.registry import load_seed_catalog_into_repository
from reroute_agents.events import done_event, error_event, proposal_event, step_event
from reroute_agents.graphs.chat_graph import build_chat_graph
from reroute_agents.graphs.plan_graph import build_plan_graph
from reroute_agents.graphs.replan_graph import build_replan_graph
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.repositories.interfaces import RepositoriesBundle
from reroute_agents.state import (
    AgentEvent,
    InjectedSignals,
    Signals,
)

logger = logging.getLogger(__name__)

# Shared default in-memory bundle for standalone CLI/API execution when no DB adapter is provided
_default_repos = create_in_memory_repositories()
_default_checkpointer = create_default_checkpointer()
_seed_loaded = False


async def get_or_create_repositories(
    repos: RepositoriesBundle | None = None,
) -> RepositoriesBundle:
    """Return provided repositories bundle or initialize in-memory repository with seed data."""
    global _seed_loaded
    bundle = repos or _default_repos
    if not _seed_loaded:
        await load_seed_catalog_into_repository(bundle.places)
        _seed_loaded = True
    return bundle


async def run_plan(
    run_id: UUID,
    trip_id: UUID,
    db: Any = None,
    repos: RepositoriesBundle | None = None,
    llm_override: Any | None = None,
    checkpointer: Any | None = None,
) -> AsyncIterator[AgentEvent]:
    """Execute plan_graph and yield typed AgentEvents for SSE streaming."""
    bundle = await get_or_create_repositories(repos)
    chk = configure_checkpointer(checkpointer or _default_checkpointer)
    graph = build_plan_graph(bundle, llm_override=llm_override, checkpointer=chk)

    yielded_done = False
    try:
        spec = await bundle.trips.get_trip(trip_id)
        if not spec:
            err = error_event(
                code="not_found",
                message=f"Trip with id {trip_id} not found",
                recoverable=False,
                node="intake",
            )
            await bundle.run_events.log_event(run_id, err)
            yield err
            return

        initial_state = {
            "trip_id": str(trip_id),
            "spec": spec,
            "candidates": [],
            "draft": None,
            "violations": [],
            "iteration": 0,
            "events": [
                step_event(
                    node="intake",
                    message=f"Starting plan generation for {spec.destination}",
                    status="running",
                )
            ],
        }

        config = {"configurable": {"thread_id": str(run_id)}}
        emitted_event_ids: set[int] = set()

        async for chunk in graph.astream(initial_state, config=config, stream_mode="updates"):
            for _node_name, update in chunk.items():
                if isinstance(update, dict) and "events" in update:
                    for evt in update["events"]:
                        evt_id = id(evt)
                        if evt_id not in emitted_event_ids:
                            emitted_event_ids.add(evt_id)
                            await bundle.run_events.log_event(run_id, evt)
                            if evt.type in ("done", "error"):
                                yielded_done = True
                            yield evt

        if not yielded_done:
            final_curr = await bundle.itineraries.get_current_version(trip_id)
            fin_evt = done_event(
                status="completed",
                version_id=final_curr["id"] if final_curr else None,
                node="finalize",
            )
            await bundle.run_events.log_event(run_id, fin_evt)
            yield fin_evt

    except asyncio.CancelledError:
        cancel_evt = error_event(
            code="run_cancelled",
            message="Plan generation was cancelled",
            recoverable=False,
            node="plan_graph",
        )
        await bundle.run_events.log_event(run_id, cancel_evt)
        yield cancel_evt
    except Exception as e:
        logger.exception("Error executing run_plan: %s", e)
        fail_evt = error_event(
            code="internal_error",
            message=f"Plan generation failed: {e}",
            recoverable=True,
            node="plan_graph",
        )
        await bundle.run_events.log_event(run_id, fail_evt)
        yield fail_evt


async def run_replan(
    run_id: UUID,
    trip_id: UUID,
    db: Any = None,
    injected: InjectedSignals | None = None,
    repos: RepositoriesBundle | None = None,
    llm_override: Any | None = None,
    checkpointer: Any | None = None,
) -> AsyncIterator[AgentEvent]:
    """Execute replan_graph and pause at proposal interrupt() for user decision."""
    bundle = await get_or_create_repositories(repos)
    chk = configure_checkpointer(checkpointer or _default_checkpointer)
    graph = build_replan_graph(bundle, llm_override=llm_override, checkpointer=chk)

    yielded_done = False
    try:
        spec = await bundle.trips.get_trip(trip_id)
        if not spec:
            err = error_event("not_found", f"Trip {trip_id} not found", recoverable=False)
            await bundle.run_events.log_event(run_id, err)
            yield err
            return

        curr_v = await bundle.itineraries.get_current_version(trip_id)
        if not curr_v:
            err = error_event(
                "not_found", f"No itinerary exists for trip {trip_id} to replan", recoverable=False
            )
            await bundle.run_events.log_event(run_id, err)
            yield err
            return

        current_items = await bundle.itineraries.get_version_items(curr_v["id"])
        signals = Signals(injected=injected)

        initial_state = {
            "trip_id": str(trip_id),
            "run_id": str(run_id),
            "base_version_id": str(curr_v["id"]),
            "spec": spec,
            "signals": signals,
            "disruptions": [],
            "affected_item_ids": [],
            "current_items": current_items,
            "draft": None,
            "violations": [],
            "proposal": None,
            "decision": None,
            "iteration": 0,
            "events": [],
        }

        config = {"configurable": {"thread_id": str(run_id)}}
        emitted_event_ids: set[int] = set()
        is_interrupted = False

        async for chunk in graph.astream(initial_state, config=config, stream_mode="updates"):
            for node_name, update in chunk.items():
                if node_name == "__interrupt__":
                    is_interrupted = True
                    interrupt_list = update if isinstance(update, (list, tuple)) else [update]
                    for intr in interrupt_list:
                        val = getattr(intr, "value", intr)
                        if isinstance(val, dict) and "proposal_id" in val:
                            prop_id = UUID(str(val["proposal_id"]))
                            prop_evt = proposal_event(prop_id, node="build_proposal")
                            await bundle.run_events.log_event(run_id, prop_evt)
                            yield prop_evt
                            step_evt = step_event(
                                node="build_proposal",
                                message=f"Proposal created ({val.get('items_changed', 0)} changes). Awaiting traveler decision.",
                                status="done",
                            )
                            await bundle.run_events.log_event(run_id, step_evt)
                            yield step_evt
                elif isinstance(update, dict) and "events" in update:
                    for evt in update["events"]:
                        evt_id = id(evt)
                        if evt_id not in emitted_event_ids:
                            emitted_event_ids.add(evt_id)
                            await bundle.run_events.log_event(run_id, evt)
                            if evt.type in ("done", "error"):
                                yielded_done = True
                            yield evt

        # If graph finished cleanly without disruptions and was not interrupted
        if not yielded_done and not is_interrupted:
            fin_evt = done_event(
                status="completed", version_id=curr_v["id"], node="impact_analyzer"
            )
            await bundle.run_events.log_event(run_id, fin_evt)
            yield fin_evt

    except asyncio.CancelledError:
        cancel_evt = error_event(
            "run_cancelled", "Replan was cancelled", recoverable=False, node="replan_graph"
        )
        await bundle.run_events.log_event(run_id, cancel_evt)
        yield cancel_evt
    except Exception as e:
        logger.exception("Error executing run_replan: %s", e)
        fail_evt = error_event(
            "internal_error", f"Replan failed: {e}", recoverable=True, node="replan_graph"
        )
        await bundle.run_events.log_event(run_id, fail_evt)
        yield fail_evt


async def resume_replan(
    run_id: UUID,
    decision: Literal["approve", "reject", "alternatives"],
    note: str | None = None,
    repos: RepositoriesBundle | None = None,
    llm_override: Any | None = None,
    checkpointer: Any | None = None,
) -> AsyncIterator[AgentEvent]:
    """Resume a paused replan graph after traveler decision."""
    bundle = await get_or_create_repositories(repos)
    chk = configure_checkpointer(checkpointer or _default_checkpointer)
    graph = build_replan_graph(bundle, llm_override=llm_override, checkpointer=chk)

    config = {"configurable": {"thread_id": str(run_id)}}
    emitted_event_ids: set[int] = set()

    try:
        resume_cmd: Any = Command(resume={"decision": decision, "note": note})
        async for chunk in graph.astream(resume_cmd, config=config, stream_mode="updates"):
            for _node_name, update in chunk.items():
                if isinstance(update, dict) and "events" in update:
                    for evt in update["events"]:
                        evt_id = id(evt)
                        if evt_id not in emitted_event_ids:
                            emitted_event_ids.add(evt_id)
                            await bundle.run_events.log_event(run_id, evt)
                            yield evt

    except asyncio.CancelledError:
        cancel_evt = error_event(
            "run_cancelled", "Resume operation was cancelled", recoverable=False
        )
        await bundle.run_events.log_event(run_id, cancel_evt)
        yield cancel_evt
    except Exception as e:
        logger.exception("Error resuming replan: %s", e)
        fail_evt = error_event("internal_error", f"Resume failed: {e}", recoverable=True)
        await bundle.run_events.log_event(run_id, fail_evt)
        yield fail_evt


async def run_chat(
    run_id: UUID,
    trip_id: UUID,
    message: str,
    db: Any = None,
    repos: RepositoriesBundle | None = None,
    llm_override: Any | None = None,
    checkpointer: Any | None = None,
) -> AsyncIterator[AgentEvent]:
    """Execute conversational chat agent and yield token/step events."""
    bundle = await get_or_create_repositories(repos)
    chk = configure_checkpointer(checkpointer or _default_checkpointer)
    graph = build_chat_graph(bundle, llm_override=llm_override, checkpointer=chk)

    try:
        from langchain_core.messages import HumanMessage

        initial_state = {
            "trip_id": str(trip_id),
            "run_id": str(run_id),
            "messages": [HumanMessage(content=message)],
            "current_items": [],
            "spec": None,
            "proposal": None,
            "events": [],
        }

        config = {"configurable": {"thread_id": str(run_id)}}
        emitted_event_ids: set[int] = set()

        async for chunk in graph.astream(initial_state, config=config, stream_mode="updates"):
            for _node_name, update in chunk.items():
                if isinstance(update, dict) and "events" in update:
                    for evt in update["events"]:
                        evt_id = id(evt)
                        if evt_id not in emitted_event_ids:
                            emitted_event_ids.add(evt_id)
                            await bundle.run_events.log_event(run_id, evt)
                            yield evt

    except asyncio.CancelledError:
        cancel_evt = error_event("run_cancelled", "Chat was cancelled", recoverable=False)
        await bundle.run_events.log_event(run_id, cancel_evt)
        yield cancel_evt
    except Exception as e:
        logger.exception("Error in run_chat: %s", e)
        fail_evt = error_event("internal_error", f"Chat failed: {e}", recoverable=True)
        await bundle.run_events.log_event(run_id, fail_evt)
        yield fail_evt
