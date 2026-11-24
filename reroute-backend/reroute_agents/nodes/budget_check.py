"""Budget check node: Pure code verification of costs against user budget allocations."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from reroute_agents.events import step_event
from reroute_agents.state import PlanState, Violation


async def budget_check_node(state: PlanState) -> dict[str, Any]:
    """Verify itinerary budget totals and per-day caps."""
    draft = state.get("draft")
    spec = state["spec"]
    violations = list(state.get("violations", []))

    if not draft:
        return {"violations": violations}

    total_cost = sum((it.est_cost for it in draft.items), Decimal(0))
    budget_violations: list[Violation] = []

    if total_cost > spec.budget_total:
        budget_violations.append(
            Violation(
                code="over_budget",
                detail=f"Total cost ({total_cost} {spec.currency}) exceeds total budget ({spec.budget_total} {spec.currency}).",
            )
        )

    if spec.budget_per_day_cap is not None:
        day_totals: dict[int, Decimal] = {}
        for it in draft.items:
            day_totals[it.day_index] = day_totals.get(it.day_index, Decimal(0)) + it.est_cost

        for d_idx, d_cost in day_totals.items():
            if d_cost > spec.budget_per_day_cap:
                budget_violations.append(
                    Violation(
                        code="over_budget",
                        day_index=d_idx,
                        detail=f"Day {d_idx} cost ({d_cost} {spec.currency}) exceeds per-day cap ({spec.budget_per_day_cap} {spec.currency}).",
                    )
                )

    all_violations = violations + budget_violations
    if budget_violations:
        msg = f"Budget check flagged overrun: {total_cost} {spec.currency} vs limit {spec.budget_total} {spec.currency}"
        status = "failed"
    else:
        msg = f"Budget check passed: total {total_cost} {spec.currency} within {spec.budget_total} {spec.currency}"
        status = "done"

    return {
        "violations": all_violations,
        "events": [step_event(node="budget_check", message=msg, status=status)],
    }
