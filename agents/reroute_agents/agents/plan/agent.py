"""Plan Agent: Day-by-day itinerary construction from researched places and catalog seeds."""

from __future__ import annotations

from typing import Any, Literal, cast

from langgraph.graph import END, START, StateGraph

from reroute_agents.agents.plan.tools import get_plan_tools
from reroute_agents.checkpointer import configure_checkpointer
from reroute_agents.config import settings
from reroute_agents.nodes.budget_check import budget_check_node
from reroute_agents.nodes.finalize import create_finalize_node
from reroute_agents.nodes.intake import intake_node
from reroute_agents.nodes.planner import create_planner_node
from reroute_agents.nodes.researcher import create_researcher_node
from reroute_agents.nodes.validator import validator_node
from reroute_agents.repositories.interfaces import RepositoriesBundle
from reroute_agents.state import PlanState


def route_after_validator(state: PlanState) -> Literal["planner", "budget_check", "finalize"]:
    """Determine whether to re-plan, proceed to budget check, or finalize."""
    violations = state.get("violations", [])
    iteration = state.get("iteration", 0)
    draft = state.get("draft")
    candidates = state.get("candidates", [])

    if not candidates or not draft or not draft.items:
        return "finalize"

    if violations:
        if iteration < settings.max_plan_iterations:
            return "planner"
        return "finalize"

    return "budget_check"


def route_after_budget(state: PlanState) -> Literal["planner", "finalize"]:
    """Determine whether budget check passed or requires refinement."""
    violations = state.get("violations", [])
    iteration = state.get("iteration", 0)
    draft = state.get("draft")
    candidates = state.get("candidates", [])

    if not candidates or not draft or not draft.items:
        return "finalize"

    if violations:
        if iteration < settings.max_plan_iterations:
            return "planner"
        return "finalize"

    return "finalize"


def build_plan_agent(
    repos: RepositoriesBundle,
    llm_override: Any | None = None,
    checkpointer: Any | None = None,
) -> Any:
    """Build and compile the Plan Agent graph using dedicated plan tools."""
    # Register and bound dedicated plan tools
    get_plan_tools(repos.places)

    builder = StateGraph(cast(Any, PlanState))

    # Instantiate nodes with injected dependencies
    import reroute_agents.graphs.plan_graph as pg

    intake_fn = getattr(pg, "intake_node", intake_node)
    researcher = create_researcher_node(repos.places, llm_override=llm_override)
    planner = create_planner_node(llm_override)
    finalize = create_finalize_node(repos.itineraries, repos.trips)

    builder.add_node("intake", intake_fn)
    builder.add_node("researcher", researcher)
    builder.add_node("planner", planner)
    builder.add_node("validator", validator_node)
    builder.add_node("budget_check", budget_check_node)
    builder.add_node("finalize", finalize)

    # Wire Edges
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "researcher")
    builder.add_edge("researcher", "planner")
    builder.add_edge("planner", "validator")

    builder.add_conditional_edges(
        "validator",
        route_after_validator,
        {
            "planner": "planner",
            "budget_check": "budget_check",
            "finalize": "finalize",
        },
    )

    builder.add_conditional_edges(
        "budget_check",
        route_after_budget,
        {
            "planner": "planner",
            "finalize": "finalize",
        },
    )

    builder.add_edge("finalize", END)

    chk = configure_checkpointer(checkpointer) if checkpointer is not None else None
    return builder.compile(checkpointer=chk)
