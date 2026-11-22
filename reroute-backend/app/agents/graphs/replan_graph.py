"""Replan graph: handles disruptions and creates revised itineraries with HITL."""
from __future__ import annotations

import logging
from typing import AsyncIterator

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from app.agents.state import ReplanState, DisruptionEvent, ItineraryDraft, DraftItem
from app.agents.nodes.validator import validator
from app.agents.llm import get_llm, get_structured_llm
from app.agents.tools import search_places, get_weather_forecast, get_travel_time

log = logging.getLogger("reroute.graphs.replan")


class ReplanOutput:
    """Structured output for replan node."""
    # Using a simple class since we return dicts directly
    pass


SYSTEM_PROMPT_REPLANNER = """You are a travel replanner. Given the current itinerary and a disruption event,
create a revised itinerary that addresses the disruption while minimizing changes.
Consider: the type of disruption, affected items, available alternatives, budget impact.
Return a proposal with: changed_items (list of modified items), new_items (list of added items),
removed_item_ids (list of stable_keys removed), budget_delta, confidence (0-1), rationale."""


SYSTEM_PROMPT_IMPACT = """You are a disruption impact analyzer. Given a disruption event and current itinerary,
determine which items are affected and the severity.
Return: affected_item_stable_keys (list), severity (low/medium/high), description."""


def build_replan_graph():
    """Build the replan graph with HITL interrupt."""
    llm = get_llm()
    tools = [search_places, get_weather_forecast, get_travel_time]

    graph = StateGraph(ReplanState)

    # Add nodes
    graph.add_node("collect_signals", collect_signals)
    graph.add_node("impact_analyzer", impact_analyzer(llm, tools))
    graph.add_node("replanner", replanner(llm, tools))
    graph.add_node("validator", validator)
    graph.add_node("build_proposal", build_proposal)
    graph.add_node("hitl_interrupt", hitl_interrupt)

    # Add edges
    graph.add_edge(START, "collect_signals")
    graph.add_edge("collect_signals", "impact_analyzer")
    graph.add_edge("impact_analyzer", "replanner")
    graph.add_edge("replanner", "validator")
    graph.add_edge("validator", "build_proposal")
    graph.add_edge("build_proposal", "hitl_interrupt")
    graph.add_edge("hitl_interrupt", END)

    # Compile with checkpointer for HITL support
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


async def collect_signals(state: ReplanState) -> ReplanState:
    """Collect disruption signals from the database and injected sources."""
    trip_id = state.get("trip_id", "")
    run_id = state.get("run_id", "")

    # In production, this would query the database for disruption_events
    # For now, use injected signals or simulate
    disruptions = state.get("injected_signals", [])

    # Convert to DisruptionEvent objects
    disruption_events = []
    for d in disruptions:
        disruption_events.append(DisruptionEvent(
            id=d.get("id", f"disrupt_{len(disruption_events)}"),
            trip_id=trip_id,
            run_id=run_id,
            kind=d.get("kind", "weather"),
            severity=d.get("severity", "medium"),
            payload=d.get("payload", {}),
            source=d.get("source", "injected"),
            status="new",
        ))

    return {"disruptions": disruption_events, "message": f"Collected {len(disruption_events)} disruptions"}


async def impact_analyzer(llm, tools) -> callable:
    """Analyze the impact of disruptions on the current itinerary."""
    async def _node(state: ReplanState) -> ReplanState:
        disruptions = state.get("disruptions", [])
        current_draft = state.get("current_draft")

        if not disruptions:
            return {"affected_items": [], "message": "No disruptions to analyze"}

        affected_items = []
        max_severity = "low"

        for disruption in disruptions:
            # Simple heuristic-based impact analysis
            if current_draft and current_draft.get("items"):
                for item in current_draft["items"]:
                    # Check if item is affected by disruption
                    if _is_item_affected(item, disruption):
                        affected_items.append(item.get("stable_key"))

            # Track max severity
            severity = disruption.get("severity", "low")
            if severity == "high":
                max_severity = "high"
            elif severity == "medium" and max_severity != "high":
                max_severity = "medium"

        return {
            "affected_items": affected_items,
            "severity": max_severity,
            "message": f"Impact analysis: {len(affected_items)} items affected, severity: {max_severity}"
        }

    return _node


def _is_item_affected(item: dict, disruption: DisruptionEvent) -> bool:
    """Check if an itinerary item is affected by a disruption."""
    kind = disruption.get("kind", "")
    payload = disruption.get("payload", {})

    if kind == "weather":
        # Weather affects outdoor activities
        if item.get("setting") == "outdoor":
            precip = payload.get("precip_prob", 0)
            if precip >= 60:
                return True

    elif kind == "closure":
        # Closure affects specific place
        place_id = payload.get("place_id")
        if place_id and item.get("place_id") == place_id:
            return True

    elif kind == "travel_delay":
        # Travel delay affects subsequent items
        # Simplified: if item has travel_minutes > 0, it might be affected
        if item.get("travel_minutes", 0) > 0:
            return True

    elif kind == "budget_change":
        # Budget change affects all items if budget is tight
        pass

    return False


async def replanner(llm, tools) -> callable:
    """Create revised itinerary addressing disruptions."""
    async def _node(state: ReplanState) -> ReplanState:
        disruptions = state.get("disruptions", [])
        current_draft = state.get("current_draft")
        affected_items = state.get("affected_items", [])

        if not current_draft or not disruptions:
            return {"proposed_draft": current_draft, "message": "No replanning needed"}

        # For mock mode, create a simple revised draft
        if not llm:
            proposed_draft = _mock_replan(current_draft, disruptions, affected_items)
            return {"proposed_draft": proposed_draft, "message": "Mock replan created"}

        try:
            # Use LLM to create revised itinerary
            structured_llm = llm.with_structured_output(dict)  # Simplified for demo
            prompt = f"""
Current itinerary: {current_draft}
Disruptions: {disruptions}
Affected items: {affected_items}

Create a revised itinerary that addresses the disruptions.
"""
            # For now, fall back to mock
            proposed_draft = _mock_replan(current_draft, disruptions, affected_items)
        except Exception:
            proposed_draft = _mock_replan(current_draft, disruptions, affected_items)

        return {"proposed_draft": proposed_draft, "message": "Revised itinerary created"}

    return _node


def _mock_replan(current_draft: dict, disruptions: list, affected_items: list) -> dict:
    """Create a mock revised itinerary."""
    items = current_draft.get("items", [])

    # Remove affected items
    remaining_items = [item for item in items if item.get("stable_key") not in affected_items]

    # Add replacement items for affected ones
    new_items = []
    for item in items:
        if item.get("stable_key") in affected_items:
            # Create indoor alternative for weather disruption
            new_items.append(DraftItem(
                stable_key=f"{item.get('stable_key')}_alt",
                day_index=item.get("day_index"),
                position=item.get("position"),
                place_id=f"indoor_alt_{item.get('place_id')}",
                title=f"Indoor Alternative: {item.get('title')}",
                category=item.get("category"),
                setting="indoor",
                start_time=item.get("start_time"),
                end_time=item.get("end_time"),
                est_cost=item.get("est_cost"),
                lat=item.get("lat"),
                lng=item.get("lng"),
                is_locked=False,
                travel_mode=item.get("travel_mode"),
                travel_minutes=item.get("travel_minutes"),
            ))

    all_items = remaining_items + new_items

    return {
        "items": [item if isinstance(item, dict) else item for item in all_items],
        "summary": f"Revised: {len(remaining_items)} kept, {len(new_items)} replaced",
    }


async def build_proposal(state: ReplanState) -> ReplanState:
    """Build a ReplanProposal from the validated draft."""
    proposed_draft = state.get("proposed_draft")
    current_draft = state.get("current_draft")
    disruptions = state.get("disruptions", [])

    if not proposed_draft:
        return {"proposal": None, "message": "No proposal to build"}

    # Calculate changes
    current_items = current_draft.get("items", []) if current_draft else []
    proposed_items = proposed_draft.get("items", [])

    current_keys = {item.get("stable_key") for item in current_items}
    proposed_keys = {item.get("stable_key") for item in proposed_items}

    changed_items = []
    new_items = []
    removed_keys = current_keys - proposed_keys

    for item in proposed_items:
        key = item.get("stable_key")
        if key in current_keys:
            # Check if modified
            current_item = next((i for i in current_items if i.get("stable_key") == key), None)
            if current_item and current_item != item:
                changed_items.append(item)
        else:
            new_items.append(item)

    # Calculate budget delta
    current_cost = sum(item.get("est_cost", 0) for item in current_items)
    proposed_cost = sum(item.get("est_cost", 0) for item in proposed_items)
    budget_delta = proposed_cost - current_cost

    proposal = ReplanProposal(
        proposal_id=f"prop_{len(disruptions)}_{hash(str(proposed_draft)) % 10000}",
        trip_id=state.get("trip_id", ""),
        run_id=state.get("run_id", ""),
        disruption_ids=[d.get("id") for d in disruptions],
        changed_items=changed_items,
        new_items=new_items,
        removed_item_ids=list(removed_keys),
        budget_delta=budget_delta,
        confidence=0.85,
        rationale="Automated replan addressing disruptions",
    )

    return {"proposal": proposal, "message": "Proposal built"}


async def hitl_interrupt(state: ReplanState) -> ReplanState:
    """Interrupt for human-in-the-loop decision."""
    proposal = state.get("proposal")

    if not proposal:
        return {"hitl_status": "no_proposal", "message": "No proposal for HITL"}

    # This is where the graph pauses and waits for human decision
    # The interrupt will be resumed via Command(resume={...})
    decision = interrupt({
        "type": "proposal",
        "proposal": proposal.model_dump() if hasattr(proposal, 'model_dump') else proposal,
        "message": "Please review and approve/reject/modify the replan proposal"
    })

    # Decision comes back via Command(resume=...)
    action = decision.get("action", "reject")  # approve, reject, modify
    modified_proposal = decision.get("proposal")

    if action == "approve":
        final_proposal = modified_proposal or proposal
        return {"hitl_status": "approved", "final_proposal": final_proposal, "message": "Proposal approved"}
    elif action == "modify" and modified_proposal:
        return {"hitl_status": "modified", "final_proposal": modified_proposal, "message": "Proposal modified and approved"}
    else:
        return {"hitl_status": "rejected", "final_proposal": None, "message": "Proposal rejected"}


async def run_replan_graph(run_id: str, trip_id: str, current_draft: dict, injected_signals: list = None) -> AsyncIterator[dict]:
    """Execute the replan graph and yield events."""
    graph = build_replan_graph()

    initial_state: ReplanState = {
        "trip_id": trip_id,
        "run_id": run_id,
        "current_draft": current_draft,
        "injected_signals": injected_signals or [],
        "disruptions": [],
        "affected_items": [],
        "severity": "low",
        "proposed_draft": None,
        "proposal": None,
        "hitl_status": "pending",
        "final_proposal": None,
        "message": "",
    }

    config = {"configurable": {"thread_id": run_id}}

    try:
        async for step in graph.astream(initial_state, config=config):
            for node_name, node_output in step.items():
                if node_output:
                    if node_name == "collect_signals":
                        yield {"type": "step", "node": "collect_signals", "message": node_output.get("message", ""), "status": "done"}
                    elif node_name == "impact_analyzer":
                        yield {"type": "step", "node": "impact_analyzer", "message": node_output.get("message", ""), "status": "done"}
                    elif node_name == "replanner":
                        yield {"type": "draft", "node": "replanner", "message": node_output.get("message", ""), "status": "running", "payload": {"days_ready": []}}
                    elif node_name == "validator":
                        yield {"type": "step", "node": "validator", "message": node_output.get("message", ""), "status": "done"}
                    elif node_name == "build_proposal":
                        proposal = node_output.get("proposal")
                        if proposal:
                            yield {"type": "proposal", "node": "build_proposal", "message": "Proposal ready for review", "status": "done", "payload": proposal.model_dump() if hasattr(proposal, 'model_dump') else proposal}
                    elif node_name == "hitl_interrupt":
                        hitl_status = node_output.get("hitl_status")
                        yield {"type": "hitl", "node": "hitl_interrupt", "message": f"HITL: {hitl_status}", "status": hitl_status, "payload": node_output}
    except Exception as e:
        log.exception("Replan graph failed")
        yield {"type": "error", "message": str(e), "payload": {"code": "graph_failed", "recoverable": False}}

    yield {"type": "done", "message": "Replan complete", "payload": {"status": "completed"}}