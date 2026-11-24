"""Unit test for agent tool ownership isolation and loud authorization failures."""

import pytest

from reroute_agents.agents.chat.tools import get_chat_tools
from reroute_agents.agents.plan.tools import get_plan_tools
from reroute_agents.agents.replan.tools import get_replan_tools
from reroute_agents.agents.web.tools import get_web_tools
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.tools.registry import (
    ToolAccessViolationError,
    registry,
    validate_tool_access,
)


def test_strict_tool_ownership_matrix() -> None:
    """Verify that every tool is strictly accessible only to authorized agent scopes."""
    repos = create_in_memory_repositories()
    registry.clear()

    # Initialize all agent tools
    web_tools = get_web_tools()
    plan_tools = get_plan_tools(repos.places)
    replan_tools = get_replan_tools(repos.places)
    chat_tools = get_chat_tools(repos.places, repos.expenses)

    web_tool_names = {t.name for t in web_tools}
    plan_tool_names = {t.name for t in plan_tools}
    replan_tool_names = {t.name for t in replan_tools}
    chat_tool_names = {t.name for t in chat_tools}

    # 1. Web Agent checks
    assert "web_search" in web_tool_names
    assert "web_fetch" in web_tool_names
    assert "web_geocode" in web_tool_names

    # Web agent must NOT have access to plan/replan/chat tools
    for tool_name in ["estimate_route", "convert_currency", "get_expenses_summary", "weather_forecast"]:
        with pytest.raises(ToolAccessViolationError, match=f"Tool '{tool_name}' is not registered"):
            validate_tool_access("web", tool_name)

    # 2. Plan Agent checks
    assert "search_places" in plan_tool_names
    assert "estimate_route" in plan_tool_names

    # Plan agent must NOT have access to raw web fetch, weather, currency
    for tool_name in ["web_fetch", "convert_currency", "weather_forecast", "inject_disruption"]:
        with pytest.raises(ToolAccessViolationError, match=f"Tool '{tool_name}' is not registered"):
            validate_tool_access("plan", tool_name)

    # 3. Replan Agent checks
    assert "get_weather_forecast" in replan_tool_names
    assert "inject_disruption" in replan_tool_names

    # Replan agent must NOT have access to web_fetch or currency
    for tool_name in ["web_fetch", "convert_currency", "get_expenses_summary"]:
        with pytest.raises(ToolAccessViolationError, match=f"Tool '{tool_name}' is not registered"):
            validate_tool_access("replan", tool_name)

    # 4. Chat Agent checks
    assert "convert_currency" in chat_tool_names
    assert "get_expenses_summary" in chat_tool_names
    assert "estimate_route" in chat_tool_names

    # Chat agent must NOT have access to web_search, web_fetch, or weather
    for tool_name in ["web_search", "web_fetch", "get_weather_forecast", "inject_disruption"]:
        with pytest.raises(ToolAccessViolationError, match=f"Tool '{tool_name}' is not registered"):
            validate_tool_access("chat", tool_name)


def test_calling_unregistered_agent_name_fails_loud() -> None:
    with pytest.raises(ToolAccessViolationError, match="Unknown agent"):
        validate_tool_access("hacker_agent", "web_search")
