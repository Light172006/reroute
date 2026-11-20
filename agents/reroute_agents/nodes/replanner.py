"""Replanner node: Proposes targeted substitutions for disrupted items."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from reroute_agents.events import step_event
from reroute_agents.llm import FakeLLM, ResilientLLMChain, get_llm
from reroute_agents.repositories.interfaces import PlaceCatalogRepository, TripRepository
from reroute_agents.state import DraftItem, ItineraryDraft, ReplanState

logger = logging.getLogger(__name__)


def _load_replanner_prompt() -> str:
    path = Path(__file__).resolve().parent.parent / "prompts" / "replanner_v1.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "You are an itinerary replanner. Replace ONLY affected items with suitable alternatives."


def create_replanner_node(
    catalog_repo: PlaceCatalogRepository,
    trip_repo: TripRepository,
    llm_override: Any | None = None,
) -> Any:
    """Factory creating replanner node with injected catalog repository and LLM."""
    system_prompt = _load_replanner_prompt()

    async def replanner_node(state: ReplanState) -> dict[str, Any]:
        trip_id = UUID(state["trip_id"])
        spec = await trip_repo.get_trip(trip_id)
        current_items = state["current_items"]
        affected_ids = set(state.get("affected_item_ids", []))
        disruptions = state.get("disruptions", [])
        decision = state.get("decision")
        iteration = state.get("iteration", 0) + 1
        events = []

        step_msg = f"Evaluating substitutions for {len(affected_ids)} affected stop(s)"
        if decision == "alternatives":
            step_msg = f"Generating alternative substitutions (different options) for {len(affected_ids)} stop(s)"
        events.append(step_event(node="replanner", message=step_msg, status="running"))

        # Fetch candidate places for substitutions (prefer indoor for weather)
        city_name = spec.destination if spec else "Darjeeling"
        indoor_candidates = await catalog_repo.search_places(
            city=city_name,
            limit=20,
        )

        # Invariant: Unaffected items MUST remain completely identical
        # Construct proposed items list starting from current_items
        proposed_items: list[DraftItem] = []
        replacement_idx = 0 if decision != "alternatives" else 1

        for it in current_items:
            it_key_str = str(it.stable_key)
            if it_key_str not in affected_ids or it.is_locked:
                # Keep completely identical
                proposed_items.append(it.model_copy(deep=True))
            else:
                # Find an appropriate alternative place
                # If weather disruption: prefer indoor/mixed
                cand = None
                for c in indoor_candidates:
                    if c.id != it.place_id:
                        if any(d.type == "weather" for d in disruptions) and c.setting == "indoor":
                            cand = c
                            break
                        if (
                            any(d.type == "budget_overrun" for d in disruptions)
                            and c.avg_cost < it.est_cost
                        ):
                            cand = c
                            break
                        cand = c

                # If alternatives was requested, pick subsequent candidate
                if decision == "alternatives" and len(indoor_candidates) > 1:
                    cand = indoor_candidates[(replacement_idx + 1) % len(indoor_candidates)]

                if cand:
                    new_item = it.model_copy(
                        deep=True,
                        update={
                            "place_id": cand.id,
                            "title": cand.name,
                            "category": cand.category,
                            "setting": cand.setting,
                            "est_cost": cand.avg_cost,
                            "lat": cand.lat,
                            "lng": cand.lng,
                            "notes": f"Replaced due to {disruptions[0].summary if disruptions else 'disruption'}",
                        },
                    )
                    proposed_items.append(new_item)
                else:
                    proposed_items.append(it.model_copy(deep=True))

        summary_reason = "Substituted outdoor stops with indoor cultural alternatives."
        if any(d.type == "weather" for d in disruptions):
            summary_reason = "Swapped outdoor attractions with verified indoor alternatives due to weather forecast."
        elif any(d.type == "closure" for d in disruptions):
            summary_reason = "Rerouted around closed attractions."
        elif any(d.type == "budget_overrun" for d in disruptions):
            summary_reason = (
                "Substituted high-cost stops with economical local attractions to recover budget."
            )

        proposed_draft = ItineraryDraft(
            items=proposed_items,
            summary=summary_reason,
        )

        # If LLM is active and not FakeLLM, optionally refine proposed draft
        llm = llm_override or get_llm("strong")
        if not isinstance(llm, FakeLLM) and not isinstance(llm, ResilientLLMChain):
            try:
                runner = llm.with_structured_output(ItineraryDraft)
                llm_draft = await runner.ainvoke(
                    [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": f"Affected IDs: {list(affected_ids)}\nCurrent items: {[it.model_dump(mode='json') for it in current_items]}",
                        },
                    ]
                )
                # Ensure unaffected items are kept identical
                refined_items = []
                for it in current_items:
                    if str(it.stable_key) not in affected_ids:
                        refined_items.append(it.model_copy(deep=True))
                    else:
                        match = next(
                            (li for li in llm_draft.items if li.stable_key == it.stable_key), None
                        )
                        refined_items.append(match if match else it.model_copy(deep=True))
                proposed_draft.items = refined_items
            except Exception as e:
                logger.warning("LLM refinement failed in replanner: %s", e)

        events.append(
            step_event(
                node="replanner",
                message=f"Prepared substitution proposal modifying {len(affected_ids)} stop(s)",
                status="done",
            )
        )

        return {
            "draft": proposed_draft,
            "iteration": iteration,
            "events": events,
        }

    return replanner_node
