"""Researcher node: Gathers vetted candidate places and operational metadata."""

from __future__ import annotations

from typing import Any

from reroute_agents.destinations.registry import resolve_destination
from reroute_agents.events import step_event, tool_call_event, tool_result_event
from reroute_agents.repositories.interfaces import PlaceCatalogRepository
from reroute_agents.state import PlanState


def create_researcher_node(catalog_repo: PlaceCatalogRepository) -> Any:
    """Factory creating the researcher graph node bound to catalog repository."""

    async def researcher_node(state: PlanState) -> dict[str, Any]:
        spec = state["spec"]
        events = []

        resolve_destination(spec.destination)
        city_query = spec.destination

        events.append(
            tool_call_event(
                tool="search_places",
                args={"city": city_query, "tags": spec.vibe_tags},
                node="researcher",
            )
        )

        candidates = await catalog_repo.search_places(
            city=city_query,
            tags=spec.vibe_tags if spec.vibe_tags else None,
            limit=25,
        )

        # Fallback to broader destination search if vibe tags restricted results too much
        if len(candidates) < 8:
            candidates = await catalog_repo.search_places(
                city=city_query,
                limit=30,
            )

        events.append(
            tool_result_event(
                tool="search_places",
                ok=True,
                summary=f"Found {len(candidates)} candidate places in {spec.destination}",
                cached=True,
                node="researcher",
            )
        )

        step_msg = f"Researched {len(candidates)} attractions, food spots, and viewpoints matching vibe '{', '.join(spec.vibe_tags)}'"
        events.append(step_event(node="researcher", message=step_msg, status="done"))

        return {
            "candidates": candidates,
            "events": events,
        }

    return researcher_node
