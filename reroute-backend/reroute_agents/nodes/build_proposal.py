"""Build proposal node: Constructs diff, saves proposal, and pauses via interrupt() for HITL."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from langgraph.types import interrupt

from reroute_agents.events import step_event
from reroute_agents.repositories.interfaces import ProposalRepository
from reroute_agents.state import DiffItem, ReplanProposal, ReplanState


def create_build_proposal_node(proposal_repo: ProposalRepository) -> Any:
    """Factory creating build_proposal node bound to ProposalRepository."""

    async def build_proposal_node(state: ReplanState) -> dict[str, Any]:
        trip_id = UUID(state["trip_id"])
        run_id = UUID(state["run_id"])
        base_version_id = UUID(state["base_version_id"])
        current_items = state["current_items"]
        draft = state.get("draft")
        disruptions = state.get("disruptions", [])

        if not draft or not draft.items:
            return {
                "proposal": None,
                "events": [
                    step_event(
                        node="build_proposal",
                        message="No draft items to build proposal",
                        status="failed",
                    )
                ],
            }

        # Match items by stable_key to construct diff
        current_map = {it.stable_key: it for it in current_items}
        proposed_map = {it.stable_key: it for it in draft.items}

        diff: list[DiffItem] = []
        old_cost = Decimal(0)
        new_cost = Decimal(0)

        for it in current_items:
            old_cost += it.est_cost
        for it in draft.items:
            new_cost += it.est_cost

        cost_delta = new_cost - old_cost

        for key, before_it in current_map.items():
            after_it = proposed_map.get(key)
            if not after_it:
                diff.append(
                    DiffItem(
                        op="remove",
                        day=before_it.day_index,
                        stable_key=key,
                        before={
                            "title": before_it.title,
                            "start": str(before_it.start_time),
                            "end": str(before_it.end_time),
                            "cost": float(before_it.est_cost),
                        },
                        after=None,
                        why="Removed to accommodate route adjustments",
                    )
                )
            elif (
                before_it.place_id != after_it.place_id
                or before_it.title != after_it.title
                or before_it.start_time != after_it.start_time
                or before_it.end_time != after_it.end_time
                or before_it.day_index != after_it.day_index
            ):
                why_reason = "Substituted to resolve real-world disruption"
                if disruptions:
                    why_reason = f"Adapted due to: {disruptions[0].summary}"
                diff.append(
                    DiffItem(
                        op="replace",
                        day=after_it.day_index,
                        stable_key=key,
                        before={
                            "title": before_it.title,
                            "start": str(before_it.start_time),
                            "end": str(before_it.end_time),
                            "cost": float(before_it.est_cost),
                        },
                        after={
                            "title": after_it.title,
                            "place_id": after_it.place_id,
                            "start": str(after_it.start_time),
                            "end": str(after_it.end_time),
                            "cost": float(after_it.est_cost),
                        },
                        why=why_reason,
                    )
                )

        # Check for newly added items
        for key, after_it in proposed_map.items():
            if key not in current_map:
                diff.append(
                    DiffItem(
                        op="add",
                        day=after_it.day_index,
                        stable_key=key,
                        before=None,
                        after={
                            "title": after_it.title,
                            "place_id": after_it.place_id,
                            "start": str(after_it.start_time),
                            "end": str(after_it.end_time),
                            "cost": float(after_it.est_cost),
                        },
                        why="Added to itinerary",
                    )
                )

        reason_text = disruptions[0].summary if disruptions else "Itinerary optimization"
        explanation_text = f"Proposing {len(diff)} modification(s) to adapt to disruptions while preserving locked stops."

        proposal = ReplanProposal(
            id=uuid4(),
            trip_id=trip_id,
            run_id=run_id,
            base_version_id=base_version_id,
            status="pending",
            reason=reason_text,
            explanation=explanation_text,
            disruptions=disruptions,
            diff=diff,
            proposed_items=draft.items,
            cost_delta=cost_delta,
            time_delta_min=0,
            items_changed=len(diff),
        )

        await proposal_repo.save_proposal(proposal)

        # Human-In-The-Loop Pause: graph stops here until user decides via API Command(resume=...)
        resume_payload: Any = interrupt(
            {
                "proposal_id": str(proposal.id),
                "status": "awaiting_user",
                "items_changed": len(diff),
                "cost_delta": float(cost_delta),
            }
        )

        decision_val = "approve"
        if isinstance(resume_payload, dict):
            decision_val = resume_payload.get("decision", "approve")
        elif isinstance(resume_payload, str):
            decision_val = resume_payload

        return {
            "proposal": proposal,
            "decision": decision_val,
            "events": [
                step_event(
                    node="build_proposal",
                    message=f"Proposal resumed with traveler decision: {decision_val}",
                    status="done",
                )
            ],
        }

    return build_proposal_node
