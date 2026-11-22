"""Places and catalog lookup tools."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from reroute_agents.repositories.interfaces import PlaceCatalogRepository
from reroute_agents.tools.base import safe_tool


class SearchPlacesInput(BaseModel):
    city: str = Field(description="Name of the city or destination to search within")
    query: str | None = Field(
        default=None, description="Optional search keywords or attraction name"
    )
    category: str | None = Field(
        default=None, description="Category filter (sightseeing, food, culture, nature, etc.)"
    )
    tags: list[str] | None = Field(
        default=None, description="Optional vibe or activity tags to filter by"
    )
    limit: int = Field(default=15, description="Maximum number of places to return")


class PlaceDetailsInput(BaseModel):
    place_id: str = Field(description="UUID string of the place to inspect")


def create_places_tools(
    catalog_repo: PlaceCatalogRepository,
) -> tuple[Any, Any]:
    """Factory returning LangChain tools bound to the active PlaceCatalogRepository."""

    @tool(args_schema=SearchPlacesInput)
    @safe_tool(timeout_sec=8.0)
    async def search_places(
        city: str,
        query: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        limit: int = 15,
    ) -> dict[str, Any]:
        """Search curated catalog places for attractions, food, culture, and nature."""
        places = await catalog_repo.search_places(
            city=city,
            query=query,
            category=category,
            tags=tags,
            limit=limit,
        )

        results = [p.model_dump(mode="json") for p in places]
        return {
            "ok": True,
            "count": len(results),
            "places": results,
            "cached": True,
            "source": "seed_catalog",
        }

    @tool(args_schema=PlaceDetailsInput)
    @safe_tool(timeout_sec=5.0)
    async def get_place_details(place_id: str) -> dict[str, Any]:
        """Retrieve detailed information about a place, including opening hours, coordinates, and permit rules."""
        try:
            p_uuid = UUID(place_id)
        except ValueError:
            return {"ok": False, "error": f"Invalid UUID: {place_id}"}

        place = await catalog_repo.get_place_by_id(p_uuid)
        if not place:
            return {"ok": False, "error": f"Place not found for id: {place_id}"}

        return {
            "ok": True,
            "place": place.model_dump(mode="json"),
            "cached": True,
        }

    return search_places, get_place_details
