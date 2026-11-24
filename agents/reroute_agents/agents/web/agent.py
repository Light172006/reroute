"""Web Agent: Searches the web, fetches pages, geocodes places, and structures research."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import StateGraph

from reroute_agents.tools.registry import for_agent


class WebState(TypedDict, total=False):
    destination: str
    query: str
    results: list[dict[str, Any]]


def build_web_agent() -> Any:
    """Build and compile the Web Research Agent graph using dedicated web tools."""
    # Ensure this agent only touches web-registered tools
    tools = for_agent("web")
    _ = tools

    builder: StateGraph[WebState] = StateGraph(WebState)

    async def search_and_extract(state: WebState) -> dict[str, Any]:
        return {}

    builder.add_node("search_and_extract", search_and_extract)
    builder.set_entry_point("search_and_extract")
    builder.set_finish_point("search_and_extract")
    return builder.compile()
