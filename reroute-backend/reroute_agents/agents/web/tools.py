"""Web Agent dedicated tools and registry registration."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from reroute_agents.tools.fetch import create_web_fetch_tool
from reroute_agents.tools.geocode import create_web_geocode_tool
from reroute_agents.tools.registry import registry
from reroute_agents.tools.search import create_web_search_tool


def get_web_tools() -> list[BaseTool]:
    """Instantiate and register dedicated tools for the Web Research Agent."""
    search_tool = create_web_search_tool()
    fetch_tool = create_web_fetch_tool()
    geocode_tool = create_web_geocode_tool()

    tools = [search_tool, fetch_tool, geocode_tool]
    registry.register("web", tools)
    return tools
