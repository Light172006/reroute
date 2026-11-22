"""Plan graph: creates initial itinerary from user preferences."""
from __future__ import annotations

import logging
from typing import AsyncIterator

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.state import PlanState
from app.agents.nodes.intake import intake
from app.agents.nodes.researcher import researcher
from app.agents.nodes.planner import planner
from app.agents.nodes.validator import validator
from app.agents.llm import get_llm, get_structured_llm
from app.agents.tools import search_places, get_weather_forecast

log = logging.getLogger("reroute.graphs.plan")


def build_plan_graph():
    """Build the plan generation graph."""
    llm = get_llm()
    tools = [search_places, get_weather_forecast]

    graph = StateGraph(PlanState)

    # Add nodes
    graph.add_node("intake", intake(llm))
    graph.add_node("researcher", researcher(llm, tools))
    graph.add_node("planner", planner(llm))
    graph.add_node("validator", validator)

    # Add edges
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "researcher")
    graph.add_edge("researcher", "planner")
    graph.add_edge("planner", "validator")
    graph.add_edge("validator", END)

    # Compile with checkpointer for HITL support
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


async def run_plan_graph(run_id: str, trip_id: str, spec: dict) -> AsyncIterator[dict]:
    """Execute the plan graph and yield events.

    This is the entry point called by AgentGateway.run_plan().
    """
    graph = build_plan_graph()

    initial_state: PlanState = {
        "trip_id": trip_id,
        "spec": spec,
        "iteration": 0,
        "places": [],
        "weather": {},
        "draft": None,
        "violations": [],
        "message": "",
        "tool_calls": [],
    }

    config = {"configurable": {"thread_id": run_id}}

    try:
        async for step in graph.astream(initial_state, config=config):
            for node_name, node_output in step.items():
                if node_output:
                    # Yield events based on node type
                    if node_name == "intake":
                        yield {"type": "step", "node": "intake", "message": node_output.get("message", ""), "status": "done"}
                    elif node_name == "researcher":
                        tool_calls = node_output.get("tool_calls", [])
                        for tc in tool_calls:
                            yield {"type": "tool_call", "node": "researcher", "message": f"Calling {tc['name']}", "payload": {"tool": tc["name"], "args": tc["args"]}}
                            yield {"type": "tool_result", "node": "researcher", "message": f"{tc['name']} returned", "payload": {"tool": tc["name"], "ok": True, "summary": "Done"}}
                        if node_output.get("places"):
                            yield {"type": "step", "node": "researcher", "message": f"Found {len(node_output['places'])} places", "status": "done"}
                        if node_output.get("weather"):
                            yield {"type": "step", "node": "researcher", "message": f"Weather fetched for {len(node_output['weather'])} days", "status": "done"}
                    elif node_name == "planner":
                        if node_output.get("draft"):
                            yield {"type": "draft", "node": "planner", "message": node_output.get("message", ""), "status": "running", "payload": {"days_ready": [1, 2, 3]}}
                    elif node_name == "validator":
                        violations = node_output.get("violations", [])
                        if violations:
                            yield {"type": "step", "node": "validator", "message": f"Found {len(violations)} violations", "status": "running"}
                        else:
                            yield {"type": "step", "node": "validator", "message": node_output.get("message", ""), "status": "done"}
    except Exception as e:
        log.exception("Plan graph failed")
        yield {"type": "error", "message": str(e), "payload": {"code": "graph_failed", "recoverable": False}}

    yield {"type": "done", "message": "Plan generation complete", "payload": {"status": "completed"}}