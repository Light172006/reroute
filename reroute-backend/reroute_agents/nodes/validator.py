"""Validator node: Deterministic constraint verification."""

from __future__ import annotations

from typing import Any

from reroute_agents.events import step_event
from reroute_agents.rules.validator_rules import validate_itinerary
from reroute_agents.state import Violation


async def validator_node(state: Any) -> dict[str, Any]:
    """Execute pure-function deterministic validation against the current itinerary draft."""
    draft = state.get("draft")
    spec = state.get("spec")
    candidates = state.get("candidates", [])

    if not draft or not draft.items:
        v = Violation(code="day_too_long", day_index=1, detail="Itinerary has no items scheduled.")
        return {
            "violations": [v],
            "events": [
                step_event(
                    node="validator", message="Validation failed: empty itinerary", status="failed"
                )
            ],
        }

    if not spec:
        return {
            "violations": [],
            "events": [
                step_event(
                    node="validator", message="Skipped validation: spec missing", status="done"
                )
            ],
        }

    # Build place metadata lookup
    meta = {c.id: c.model_dump(mode="python") for c in candidates}

    violations = validate_itinerary(
        items=draft.items,
        spec=spec,
        places_metadata=meta,
    )

    if violations:
        msg = f"Validation found {len(violations)} constraint issue(s) to resolve"
        status = "failed"
    else:
        msg = "All constraint checks passed (hours, gaps, pace, altitude, and seasonal access)"
        status = "done"

    evt = step_event(node="validator", message=msg, status=status)

    return {
        "violations": violations,
        "events": [evt],
    }
