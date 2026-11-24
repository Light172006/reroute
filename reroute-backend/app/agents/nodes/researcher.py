"""Researcher node: searches places and fetches weather."""
from __future__ import annotations

from typing import Optional, Callable
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.agents.state import PlanState


SYSTEM_PROMPT = """You are a travel researcher. Given a TripSpec, find relevant places and weather.
Use the available tools to search for places matching the vibe tags and get weather forecasts.
Return a summary of findings."""


def researcher(llm: Optional[BaseChatModel] = None, tools: Optional[list[BaseTool]] = None):
    """Create the researcher node function."""
    async def _node(state: PlanState) -> PlanState:
        spec = state.get("spec", {})
        destination = spec.get("destination", "Darjeeling")
        start_date = spec.get("start_date", "2026-12-12")
        end_date = spec.get("end_date", "2026-12-14")
        vibe_tags = spec.get("vibe_tags", [])

        # Calculate number of days
        from datetime import datetime
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        num_days = (end - start).days + 1

        tool_results = {"tool_calls": []}

        # Search places
        if tools:
            places_tool = next((t for t in tools if t.name == "search_places"), None)
            if places_tool:
                result = await places_tool.ainvoke({"city": destination, "vibe": vibe_tags, "limit": 20})
                tool_results["tool_calls"].append({
                    "name": "search_places", "args": {"city": destination, "vibe": vibe_tags}, "result": result
                })
                if result.get("ok"):
                    state["places"] = result.get("places", [])

            # Get weather for each day
            weather_tool = next((t for t in tools if t.name == "get_weather_forecast"), None)
            if weather_tool:
                weather_data = {}
                for day in range(1, num_days + 1):
                    result = await weather_tool.ainvoke({"city": destination, "day_index": day})
                    tool_results["tool_calls"].append({
                        "name": "get_weather_forecast", "args": {"city": destination, "day_index": day}, "result": result
                    })
                    weather_data[f"day_{day}"] = result
                state["weather"] = weather_data

        message = f"Found {len(state.get('places', []))} places, weather fetched for {num_days} days"
        return {**state, "message": message, "tool_calls": tool_results["tool_calls"]}

    return _node