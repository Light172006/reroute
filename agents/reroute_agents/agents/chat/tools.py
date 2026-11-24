"""Chat Agent dedicated tools and registry registration."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from reroute_agents.repositories.interfaces import (
    CacheRepository,
    ExpenseRepository,
    PlaceCatalogRepository,
)
from reroute_agents.tools.currency import create_currency_tool
from reroute_agents.tools.expenses import create_expenses_tool
from reroute_agents.tools.places import create_places_tools
from reroute_agents.tools.registry import registry
from reroute_agents.tools.routing import create_routing_tool


def get_chat_tools(
    catalog_repo: PlaceCatalogRepository | None = None,
    expense_repo: ExpenseRepository | None = None,
    cache_repo: CacheRepository | None = None,
) -> list[BaseTool]:
    """Instantiate and register dedicated tools for the Chat Agent."""
    tools: list[BaseTool] = []
    if catalog_repo is not None:
        search_places, get_place_details = create_places_tools(catalog_repo)
        tools.extend([search_places, get_place_details])

    routing_tool = create_routing_tool()
    tools.append(routing_tool)

    currency_tool = create_currency_tool(cache_repo)
    tools.append(currency_tool)

    if expense_repo is not None:
        expenses_tool = create_expenses_tool(expense_repo)
        tools.append(expenses_tool)

    registry.register("chat", tools)
    return tools
