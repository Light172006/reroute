"""Plan Agent: Builds day-by-day itineraries from vetted places and catalog seeds."""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph

from reroute_agents.state import PlanState
from reroute_agents.tools.registry import for_agent


def build_plan_agent() -> Any:
    """Build and compile the Plan Agent graph using dedicated plan tools."""
    # Ensure this agent only touches plan-registered tools
    tools = for_agent("plan")
    _ = tools

    builder: StateGraph[PlanState] = StateGraph(PlanState)

    async def generate_plan(state: PlanState) -> dict[str, Any]:
        return {}

    builder.add_node("generate_plan", generate_plan)
    builder.set_entry_point("generate_plan")
    builder.set_finish_point("generate_plan")
    return builder.compile()
