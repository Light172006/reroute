"""Unit tests for tool layer, caching, and error normalization."""

from decimal import Decimal
from uuid import uuid4

import pytest

from reroute_agents.destinations.registry import load_seed_catalog_into_repository
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.tools.base import safe_tool
from reroute_agents.tools.currency import create_currency_tool
from reroute_agents.tools.expenses import create_expenses_tool
from reroute_agents.tools.injector import DisruptionInjector
from reroute_agents.tools.places import create_places_tools
from reroute_agents.tools.routing import create_routing_tool
from reroute_agents.tools.weather import create_weather_tool


@pytest.mark.asyncio
async def test_places_tools_catalog_search() -> None:
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, destination_id="darjeeling")

    search_places, get_place_details = create_places_tools(repos.places)

    # Search for food in Darjeeling
    res = await search_places.ainvoke({"city": "Darjeeling", "category": "food"})
    assert res["ok"] is True
    assert res["count"] >= 1
    p = res["places"][0]
    assert "name" in p

    # Get details
    det = await get_place_details.ainvoke({"place_id": p["id"]})
    assert det["ok"] is True
    assert det["place"]["name"] == p["name"]

    # Invalid UUID error normalization
    bad_det = await get_place_details.ainvoke({"place_id": "not-a-uuid"})
    assert bad_det["ok"] is False
    assert "Invalid UUID" in bad_det["error"]


@pytest.mark.asyncio
async def test_routing_tool_seed_and_multiplier() -> None:
    routing_tool = create_routing_tool()

    # Known seed route: Darjeeling to Tiger Hill
    res = await routing_tool.ainvoke(
        {
            "origin_lat": 27.04,
            "origin_lng": 88.26,
            "dest_lat": 27.00,
            "dest_lng": 88.24,
            "origin_name": "Darjeeling",
            "dest_name": "Tiger Hill",
            "mode": "taxi",
        }
    )
    assert res["ok"] is True
    assert res["travel_minutes"] == 35
    assert res["distance_m"] == 11000

    # Unseeded coordinates
    res_generic = await routing_tool.ainvoke(
        {
            "origin_lat": 27.05,
            "origin_lng": 88.25,
            "dest_lat": 27.10,
            "dest_lng": 88.30,
            "mode": "taxi",
        }
    )
    assert res_generic["ok"] is True
    assert res_generic["travel_minutes"] >= 10


@pytest.mark.asyncio
async def test_weather_and_currency_tools() -> None:
    repos = create_in_memory_repositories()
    weather_tool = create_weather_tool(repos.cache)
    currency_tool = create_currency_tool(repos.cache)

    w_res = await weather_tool.ainvoke(
        {
            "lat": 27.04,
            "lng": 88.26,
            "start_date": "2026-12-12",
            "end_date": "2026-12-13",
        }
    )
    assert w_res["ok"] is True
    assert "forecast" in w_res

    fx_res = await currency_tool.ainvoke(
        {
            "amount": 100.0,
            "from_currency": "USD",
            "to_currency": "INR",
        }
    )
    assert fx_res["ok"] is True
    assert fx_res["converted_amount"] > 100.0


@pytest.mark.asyncio
async def test_expenses_tool() -> None:
    repos = create_in_memory_repositories()
    trip_id = uuid4()
    await repos.expenses.add_expense(trip_id, "food", Decimal("450.00"), "INR", "Lunch")

    expenses_tool = create_expenses_tool(repos.expenses)
    res = await expenses_tool.ainvoke({"trip_id": str(trip_id)})
    assert res["ok"] is True
    assert res["summary"]["total"] == Decimal("450.00")


@pytest.mark.asyncio
async def test_safe_tool_decorator_catches_exceptions() -> None:
    @safe_tool(timeout_sec=1.0)
    async def failing_tool() -> dict[str, str]:
        raise ValueError("Simulated network crash")

    res = await failing_tool()
    assert res["ok"] is False
    assert "Simulated network crash" in res["error"]


def test_disruption_injector() -> None:
    from reroute_agents.state import InjectedSignals

    injected = InjectedSignals(
        type="weather",
        day_index=2,
        params={"precip_prob": 0.95, "from": "14:00", "to": "18:00"},
    )
    signals = DisruptionInjector.inject(injected)
    assert signals.injected == injected
    assert "2" in signals.weather_forecast
    hourly = signals.weather_forecast["2"]["hourly"]
    assert any(h["hour"] == 15 and h["precip_prob"] == 0.95 for h in hourly)
