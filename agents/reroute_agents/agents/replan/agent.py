"""Replan Agent: Repairs itineraries when disruptions or weather events occur."""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph

from reroute_agents.state import ReplanState
from reroute_agents.tools.registry import for_agent


def build_replan_agent() -> Any:
    """Build and compile the Replan Agent graph using dedicated replan tools."""
    # Ensure this agent only touches replan-registered tools
    tools = for_agent("replan")
    _ = tools

    builder: StateGraph[ReplanState] = StateGraph(ReplanState)

    async def analyze_and_repair(state: ReplanState) -> dict[str, Any]:
        return {}

    builder.add_node("analyze_and_repair", analyze_and_repair)
    builder.set_entry_point("analyze_and_repair")
    builder.set_finish_point("analyze_and_repair")
    return builder.compile()
