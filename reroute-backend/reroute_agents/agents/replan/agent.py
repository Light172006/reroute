"""Replan Agent: Disruption detection, impact assessment, and HITL repair proposals."""

from __future__ import annotations

from typing import Any, Literal, cast

from langgraph.graph import END, START, StateGraph

from reroute_agents.agents.replan.tools import get_replan_tools
from reroute_agents.checkpointer import configure_checkpointer
from reroute_agents.config import settings
from reroute_agents.nodes.apply_changes import create_apply_changes_node
from reroute_agents.nodes.build_proposal import create_build_proposal_node
from reroute_agents.nodes.collect_signals import create_collect_signals_node
from reroute_agents.nodes.impact_analyzer import create_impact_analyzer_node
from reroute_agents.nodes.replanner import create_replanner_node
from reroute_agents.nodes.validator import validator_node
from reroute_agents.repositories.interfaces import RepositoriesBundle
from reroute_agents.state import ReplanState


def route_after_impact(state: ReplanState) -> Literal["replanner", "__end__"]:
    """Route to replanner if disruptions exist, otherwise finish cleanly."""
    disruptions = state.get("disruptions", [])
    affected_ids = state.get("affected_item_ids", [])
    if not disruptions or not affected_ids:
        return "__end__"
    return "replanner"


def route_after_validator(state: ReplanState) -> Literal["replanner", "build_proposal"]:
    """Determine whether validator requires another iteration or proceeds to proposal."""
    violations = state.get("violations", [])
    iteration = state.get("iteration", 0)

    if violations and iteration < settings.max_replan_iterations:
        return "replanner"

    return "build_proposal"


def route_after_apply(state: ReplanState) -> Literal["replanner", "__end__"]:
    """If user requested alternatives, loop back to replanner, else finish."""
    if state.get("decision") == "alternatives":
        return "replanner"
    return "__end__"


def build_replan_agent(
    repos: RepositoriesBundle,
    llm_override: Any | None = None,
    checkpointer: Any | None = None,
) -> Any:
    """Build and compile the Replan Agent graph with HITL interrupt support."""
    # Register and bound dedicated replan tools
    get_replan_tools(repos.places)

    builder = StateGraph(cast(Any, ReplanState))

    collect_signals = create_collect_signals_node(repos.expenses)
    impact_analyzer = create_impact_analyzer_node(repos.disruptions, repos.trips)
    replanner = create_replanner_node(repos.places, repos.trips, llm_override=llm_override)
    build_proposal = create_build_proposal_node(repos.proposals)
    apply_changes = create_apply_changes_node(repos.itineraries, repos.proposals, repos.trips)

    builder.add_node("collect_signals", collect_signals)
    builder.add_node("impact_analyzer", impact_analyzer)
    builder.add_node("replanner", replanner)
    builder.add_node("validator", validator_node)
    builder.add_node("build_proposal", build_proposal)
    builder.add_node("apply_changes", apply_changes)

    # Wire Edges
    builder.add_edge(START, "collect_signals")
    builder.add_edge("collect_signals", "impact_analyzer")

    builder.add_conditional_edges(
        "impact_analyzer",
        route_after_impact,
        {
            "replanner": "replanner",
            "__end__": END,
        },
    )

    builder.add_edge("replanner", "validator")

    builder.add_conditional_edges(
        "validator",
        route_after_validator,
        {
            "replanner": "replanner",
            "build_proposal": "build_proposal",
        },
    )

    builder.add_edge("build_proposal", "apply_changes")

    builder.add_conditional_edges(
        "apply_changes",
        route_after_apply,
        {
            "replanner": "replanner",
            "__end__": END,
        },
    )

    chk = configure_checkpointer(checkpointer) if checkpointer is not None else None
    return builder.compile(checkpointer=chk)
