"""Apply changes node: Handles user approval, rejection, or alternative request."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from reroute_agents.events import done_event, step_event
from reroute_agents.repositories.interfaces import (
    ItineraryRepository,
    ProposalRepository,
    TripRepository,
)
from reroute_agents.state import ReplanState


def create_apply_changes_node(
    itinerary_repo: ItineraryRepository,
    proposal_repo: ProposalRepository,
    trip_repo: TripRepository,
) -> Any:
    """Factory creating apply_changes node bound to repositories."""

    async def apply_changes_node(state: ReplanState) -> dict[str, Any]:
        trip_id = UUID(state["trip_id"])
        run_id = UUID(state["run_id"])
        base_version_id = UUID(state["base_version_id"])
        proposal = state.get("proposal")
        decision = state.get("decision", "reject")
        events = []

        if not proposal:
            return {"events": [done_event(status="completed", node="apply_changes")]}

        if decision == "approve":
            # Retrieve latest version number
            base_ver = await itinerary_repo.get_version_by_id(base_version_id)
            new_version_no = (base_ver["version_no"] + 1) if base_ver else 2

            new_v_id = await itinerary_repo.save_version(
                trip_id=trip_id,
                version_no=new_version_no,
                parent_version_id=base_version_id,
                reason=proposal.reason,
                created_by="agent:replanner",
                proposal_id=proposal.id,
                run_id=run_id,
                items=proposal.proposed_items,
                summary=proposal.explanation,
            )

            await trip_repo.update_current_version(trip_id, new_v_id)
            await proposal_repo.update_proposal_status(
                proposal_id=proposal.id,
                status="approved",
                resulting_version_id=new_v_id,
            )

            events.append(
                step_event(
                    node="apply_changes",
                    message=f"Changes approved. Itinerary successfully updated to v{new_version_no}.",
                    status="done",
                )
            )
            events.append(
                done_event(
                    status="completed",
                    version_id=new_v_id,
                    proposal_id=proposal.id,
                    node="apply_changes",
                )
            )

        elif decision == "reject":
            await proposal_repo.update_proposal_status(
                proposal_id=proposal.id,
                status="rejected",
            )
            events.append(
                step_event(
                    node="apply_changes",
                    message="Proposal rejected. Existing itinerary preserved unchanged.",
                    status="done",
                )
            )
            events.append(
                done_event(
                    status="completed",
                    proposal_id=proposal.id,
                    node="apply_changes",
                )
            )

        elif decision == "alternatives":
            await proposal_repo.update_proposal_status(
                proposal_id=proposal.id,
                status="superseded",
            )
            events.append(
                step_event(
                    node="apply_changes",
                    message="Proposal superseded. Preparing alternative suggestions.",
                    status="running",
                )
            )

        return {
            "events": events,
        }

    return apply_changes_node
