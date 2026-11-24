"""Replan Agent dedicated tools and registry registration."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from reroute_agents.repositories.interfaces import PlaceCatalogRepository
from reroute_agents.tools.injector import create_injector_tool
from reroute_agents.tools.places import create_places_tools
from reroute_agents.tools.registry import registry
from reroute_agents.tools.weather import create_weather_tool


def get_replan_tools(catalog_repo: PlaceCatalogRepository | None = None) -> list[BaseTool]:
    """Instantiate and register dedicated tools for the Replan Agent."""
    tools: list[BaseTool] = []
    weather_tool = create_weather_tool()
    injector_tool = create_injector_tool()
    tools.extend([weather_tool, injector_tool])

    if catalog_repo is not None:
        search_places, get_place_details = create_places_tools(catalog_repo)
        tools.extend([search_places, get_place_details])

    registry.register("replan", tools)
    return tools
