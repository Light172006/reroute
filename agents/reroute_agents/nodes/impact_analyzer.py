"""Impact analyzer node: Evaluates signals to deterministically identify disruptions."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from reroute_agents.events import disruption_event, step_event
from reroute_agents.repositories.interfaces import DisruptionRepository, TripRepository
from reroute_agents.rules.impact_rules import analyze_impacts
from reroute_agents.state import ReplanState


def create_impact_analyzer_node(
    disruption_repo: DisruptionRepository,
    trip_repo: TripRepository,
) -> Any:
    """Factory creating impact_analyzer graph node."""

    async def impact_analyzer_node(state: ReplanState) -> dict[str, Any]:
        trip_id_str = state["trip_id"]
        trip_id = UUID(trip_id_str)
        spec = await trip_repo.get_trip(trip_id)
        current_items = state["current_items"]
        signals = state["signals"]
        events = []

        if not spec:
            return {
                "disruptions": [],
                "affected_item_ids": [],
                "events": [
                    step_event(
                        node="impact_analyzer", message="Trip spec not found", status="failed"
                    )
                ],
            }

        disruptions = analyze_impacts(current_items, spec, signals)

        # Map affected keys and exclude locked items from items to be mutated
        locked_keys = {it.stable_key for it in current_items if it.is_locked}
        affected_set: set[UUID] = set()

        for d in disruptions:
            d.trip_id = trip_id
            await disruption_repo.save_disruption(d)
            events.append(disruption_event(d, node="impact_analyzer"))
            for k in d.affected_stable_keys:
                affected_set.add(k)

        # Locked items are never marked as items to change
        mutable_affected_keys = [str(k) for k in affected_set if k not in locked_keys]

        if not disruptions:
            step_msg = "No disruptions detected. Itinerary remains optimal."
        else:
            step_msg = f"Detected {len(disruptions)} disruption(s) affecting {len(mutable_affected_keys)} stop(s)"
            if any(k in locked_keys for k in affected_set):
                step_msg += " (Locked stops preserved)"

        events.append(step_event(node="impact_analyzer", message=step_msg, status="done"))

        return {
            "disruptions": disruptions,
            "affected_item_ids": mutable_affected_keys,
            "events": events,
        }

    return impact_analyzer_node
