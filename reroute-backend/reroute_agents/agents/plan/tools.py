"""Plan Agent dedicated tools and registry registration."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from reroute_agents.repositories.interfaces import PlaceCatalogRepository
from reroute_agents.tools.places import create_places_tools
from reroute_agents.tools.registry import registry
from reroute_agents.tools.routing import create_routing_tool


def get_plan_tools(catalog_repo: PlaceCatalogRepository | None = None) -> list[BaseTool]:
    """Instantiate and register dedicated tools for the Plan Agent."""
    tools: list[BaseTool] = []
    if catalog_repo is not None:
        search_places, get_place_details = create_places_tools(catalog_repo)
        tools.extend([search_places, get_place_details])

    routing_tool = create_routing_tool()
    tools.append(routing_tool)

    registry.register("plan", tools)
    return tools
