"""Intake node: Normalizes preferences and prepares plan generation state."""

from __future__ import annotations

from typing import Any

from reroute_agents.events import step_event
from reroute_agents.state import PlanState


async def intake_node(state: PlanState) -> dict[str, Any]:
    """Validate and normalize trip preferences into the planning pipeline."""
    spec = state["spec"]
    num_days = (spec.end_date - spec.start_date).days + 1

    msg = f"Preparing plan for {spec.destination} ({num_days} days, {spec.pace} pace, budget: {spec.budget_total} {spec.currency})"
    evt = step_event(node="intake", message=msg, status="done")

    return {
        "iteration": 0,
        "violations": [],
        "events": [evt],
    }
