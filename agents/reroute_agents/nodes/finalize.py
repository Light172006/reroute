"""Finalize node: Persists finalized itinerary version and emits completion events."""

from __future__ import annotations

from typing import Any

from reroute_agents.events import done_event, step_event
from reroute_agents.repositories.interfaces import ItineraryRepository, TripRepository
from reroute_agents.state import PlanState


def create_finalize_node(
    itinerary_repo: ItineraryRepository,
    trip_repo: TripRepository,
) -> Any:
    """Factory creating finalize node bound to repositories."""

    async def finalize_node(state: PlanState) -> dict[str, Any]:
        draft = state.get("draft")
        spec = state["spec"]
        violations = state.get("violations", [])
        events = []

        if not draft or not draft.items:
            return {
                "events": [
                    step_event(
                        node="finalize",
                        message="No valid draft generated or candidates unavailable",
                        status="failed",
                    ),
                    done_event(status="failed", node="finalize"),
                ]
            }

        is_valid = len(violations) == 0

        # Annotate items with any remaining unresolved violation flags
        for v in violations:
            flag_name = f"warning_{v.code}"
            if v.item_stable_key:
                for it in draft.items:
                    if it.stable_key == v.item_stable_key and flag_name not in it.flags:
                        it.flags.append(flag_name)
            elif v.day_index is not None:
                for it in draft.items:
                    if it.day_index == v.day_index and flag_name not in it.flags:
                        it.flags.append(flag_name)
            else:
                # Trip-wide violation (e.g. total budget overrun)
                for it in draft.items:
                    if flag_name not in it.flags:
                        it.flags.append(flag_name)

        summary_text = draft.summary
        if not is_valid:
            summary_text += f" (Note: {len(violations)} issues flagged for traveler review)"

        # Save immutable version 1
        version_id = await itinerary_repo.save_version(
            trip_id=spec.trip_id,
            version_no=1,
            reason="Initial plan",
            created_by="agent:planner",
            items=draft.items,
            summary=summary_text,
        )

        await trip_repo.update_current_version(spec.trip_id, version_id)

        step_msg = f"Itinerary finalized (v1) with {len(draft.items)} stops"
        if not is_valid:
            step_msg += f" ({len(violations)} unresolved items flagged)"

        events.append(
            step_event(
                node="finalize",
                message=step_msg,
                status="done" if is_valid else "failed",
            )
        )
        events.append(
            done_event(
                status="completed" if is_valid else "failed",
                version_id=version_id,
                node="finalize",
            )
        )

        return {
            "events": events,
        }

    return finalize_node
