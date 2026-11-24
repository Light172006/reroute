"""Researcher node: Gathers vetted candidate places using Web Agent research and catalog cache."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid5

from reroute_agents.agents.web.agent import run_web_research
from reroute_agents.config import settings
from reroute_agents.destinations.registry import SEED_UUID_NAMESPACE, resolve_destination
from reroute_agents.events import step_event, tool_call_event, tool_result_event
from reroute_agents.repositories.interfaces import PlaceCatalogRepository
from reroute_agents.state import PlaceCandidate, PlanState

logger = logging.getLogger(__name__)


def create_researcher_node(
    catalog_repo: PlaceCatalogRepository, llm_override: Any | None = None
) -> Any:
    """Factory creating the researcher graph node bound to catalog repository and Web Agent."""

    async def researcher_node(state: PlanState) -> dict[str, Any]:
        spec = state["spec"]
        events = []

        cfg = resolve_destination(spec.destination)

        events.append(
            tool_call_event(
                tool="search_places",
                args={"city": spec.destination, "tags": spec.vibe_tags},
                node="researcher",
            )
        )

        candidates = await catalog_repo.search_places(
            city=spec.destination,
            tags=spec.vibe_tags if spec.vibe_tags else None,
            limit=25,
        )

        # Try resolved destination aliases if sub-region or city name variant was given
        if len(candidates) < 8 and cfg:
            for alias in cfg.aliases:
                alias_matches = await catalog_repo.search_places(
                    city=alias,
                    tags=spec.vibe_tags if spec.vibe_tags else None,
                    limit=25,
                )
                for c in alias_matches:
                    if not any(existing.id == c.id for existing in candidates):
                        candidates.append(c)
                if len(candidates) >= 8:
                    break

        # Fallback to broader catalog search if vibe tags restricted results
        if len(candidates) < 8:
            broader = await catalog_repo.search_places(
                city=spec.destination,
                limit=30,
            )
            for c in broader:
                if not any(existing.id == c.id for existing in candidates):
                    candidates.append(c)

        # In live mode (real tools enabled) or when catalog has insufficient entries,
        # perform live Web Research to discover verified places.
        from reroute_agents.llm import FakeLLM
        is_mock_test = isinstance(llm_override, FakeLLM) or settings.mock_tools
        should_run_web = (not is_mock_test) or len(candidates) < 8
        if should_run_web:
            events.append(
                step_event(
                    node="web_agent.dispatch",
                    message=f"Dispatching Web Agent live research for destination '{spec.destination}'",
                    status="running",
                )
            )
            web_result, web_events = await run_web_research(
                destination=spec.destination,
                vibe_tags=spec.vibe_tags,
                llm_override=llm_override,
            )
            events.extend(web_events)

            web_candidates: list[PlaceCandidate] = []
            for place in web_result.places:
                ext_id = f"web:{spec.destination.lower()}:{place.name}"
                place_uuid = uuid5(SEED_UUID_NAMESPACE, ext_id)
                cand = PlaceCandidate(
                    id=place_uuid,
                    external_id=ext_id,
                    name=place.name,
                    city=spec.destination,
                    country="IN",
                    category=place.category,
                    setting=place.setting,
                    avg_cost=place.avg_cost,
                    currency="INR",
                    avg_duration_min=place.avg_duration_min,
                    opening_hours=place.opening_hours,
                    hours_confidence="verified" if place.verified else "medium",
                    lat=place.lat,
                    lng=place.lng,
                    tags=[place.category, *spec.vibe_tags],
                    description=place.description,
                    raw={
                        "source": place.source_url,
                        "verified": place.verified,
                        "confidence": place.confidence,
                        **place.raw,
                    },
                )
                try:
                    await catalog_repo.upsert_place(cand)
                except Exception as ex:
                    logger.debug("Catalog upsert skipped for %s: %s", cand.name, ex)
                web_candidates.append(cand)

            if not settings.mock_tools and web_candidates:
                # In live mode, web research candidates take precedence with verified provenance
                for wc in web_candidates:
                    if not any(c.name.lower() == wc.name.lower() for c in candidates):
                        candidates.insert(0, wc)
            else:
                for cand in web_candidates:
                    if not any(c.name.lower() == cand.name.lower() for c in candidates):
                        candidates.append(cand)

        events.append(
            tool_result_event(
                tool="search_places",
                ok=True,
                summary=f"Found {len(candidates)} candidate places in {spec.destination}",
                cached=True,
                node="researcher",
            )
        )

        step_msg = (
            f"Researched {len(candidates)} attractions, food spots, and viewpoints matching vibe "
            f"'{', '.join(spec.vibe_tags)}'"
        )
        events.append(step_event(node="researcher", message=step_msg, status="done"))

        return {
            "candidates": candidates,
            "events": events,
        }

    return researcher_node
