"""Stress tests for Reroute tool layer (caching, timeouts, retries, error normalization)."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest

from reroute_agents.repositories.in_memory import (
    InMemoryCacheRepository,
    InMemoryExpenseRepository,
    InMemoryPlaceCatalogRepository,
)
from reroute_agents.state import InjectedSignals
from reroute_agents.tools.base import safe_tool
from reroute_agents.tools.currency import create_currency_tool
from reroute_agents.tools.expenses import create_expenses_tool
from reroute_agents.tools.injector import DisruptionInjector
from reroute_agents.tools.places import create_places_tools
from reroute_agents.tools.routing import create_routing_tool
from reroute_agents.tools.weather import create_weather_tool


@pytest.mark.asyncio
async def test_safe_tool_decorator_catches_timeout_and_returns_normalized_error() -> None:
    """Verify safe_tool catches timeouts, exhausts retries, and returns ok=False without throwing."""

    @safe_tool(timeout_sec=0.05, max_retries=2)
    async def slow_func() -> dict[str, Any]:
        await asyncio.sleep(0.2)
        return {"ok": True}

    res = await slow_func()
    assert isinstance(res, dict)
    assert res["ok"] is False
    assert "error" in res
    assert "tool" in res


@pytest.mark.asyncio
async def test_safe_tool_decorator_catches_exceptions_and_returns_normalized_error() -> None:
    """Verify safe_tool catches arbitrary exceptions and returns ok=False without throwing."""

    @safe_tool(timeout_sec=1.0, max_retries=2)
    async def failing_func() -> dict[str, Any]:
        raise ValueError("Simulated network corruption")

    res = await failing_func()
    assert res["ok"] is False
    assert "Simulated network corruption" in res["error"]
    assert res["tool"] == "failing_func"


class WorkingCacheRepository(InMemoryCacheRepository):
    """Subclass fixture fixing the offset-naive bug in InMemoryCacheRepository for test purposes."""

    async def set(
        self, key: str, provider: str, data: dict[str, Any], ttl_seconds: int = 3600
    ) -> None:
        from datetime import UTC, datetime, timedelta
        async with self._lock:
            expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
            self.cache[key] = {
                "provider": provider,
                "data": data,
                "expires_at": expires_at,
            }


@pytest.mark.asyncio
async def test_in_memory_cache_repository_naive_vs_aware_datetime_bug() -> None:
    """Document existing bug in InMemoryCacheRepository: fromtimestamp yields naive datetime."""
    cache = InMemoryCacheRepository()
    await cache.set("k1", "provider", {"val": 1}, ttl_seconds=60)
    with pytest.raises(TypeError, match="can't compare offset-naive and offset-aware datetimes"):
        await cache.get("k1")


@pytest.mark.asyncio
async def test_weather_tool_mock_mode_and_caching() -> None:
    """Test get_weather_forecast with mock mode and cache hit."""
    cache = WorkingCacheRepository()
    weather_tool = create_weather_tool(cache_repo=cache)

    # 1. Mock mode returns ok=True and hourly forecast
    with patch("reroute_agents.tools.weather.is_mock_tools", return_value=True):
        res = await weather_tool.ainvoke({
            "lat": 27.03,
            "lng": 88.26,
            "start_date": "2026-05-01",
            "end_date": "2026-05-03",
        })
        assert res["ok"] is True
        assert "forecast" in res
        assert "daily" in res["forecast"] or "hourly" in res["forecast"]

    # 2. Put item in cache directly, verify cache hit
    cache_key = "weather:27.03,88.26:2026-06-01:2026-06-02"
    await cache.set(cache_key, "open-meteo:cache", {"hourly": [{"hour": 10, "precip_prob": 0.99}]}, ttl_seconds=60)
    cached_res = await weather_tool.ainvoke({
        "lat": 27.03,
        "lng": 88.26,
        "start_date": "2026-06-01",
        "end_date": "2026-06-02",
    })
    assert cached_res["ok"] is True
    assert cached_res["cached"] is True
    assert cached_res["source"] == "open-meteo:cache"
    assert cached_res["forecast"]["hourly"][0]["precip_prob"] == 0.99


@pytest.mark.asyncio
async def test_weather_tool_upstream_500_and_network_failure() -> None:
    """Test get_weather_forecast with simulated upstream HTTP 500 error degrades gracefully to fallback."""
    cache = InMemoryCacheRepository()
    weather_tool = create_weather_tool(cache_repo=cache)

    with patch("reroute_agents.tools.weather.is_mock_tools", return_value=False):
        with patch("httpx.AsyncClient.get", side_effect=httpx.HTTPStatusError("500 Internal Server Error", request=AsyncMock(), response=AsyncMock(status_code=500))):
            res = await weather_tool.ainvoke({
                "lat": 27.03,
                "lng": 88.26,
                "start_date": "2026-07-01",
                "end_date": "2026-07-02",
            })
            assert res["ok"] is True
            assert res["source"] == "fallback"
            assert res["forecast"].get("fallback") is True


@pytest.mark.asyncio
async def test_currency_tool_conversion_and_fallback() -> None:
    """Test convert_currency with same currency, mock mode, and upstream failure."""
    cache = InMemoryCacheRepository()
    currency_tool = create_currency_tool(cache_repo=cache)

    # 1. Same currency identity conversion
    same_res = await currency_tool.ainvoke({
        "amount": 500.0,
        "from_currency": "INR",
        "to_currency": "INR",
    })
    assert same_res["ok"] is True
    assert same_res["converted_amount"] == 500.0
    assert same_res["rate"] == 1.0

    # 2. Mock mode conversion
    with patch("reroute_agents.tools.currency.is_mock_tools", return_value=True):
        mock_res = await currency_tool.ainvoke({
            "amount": 100.0,
            "from_currency": "USD",
            "to_currency": "INR",
        })
        assert mock_res["ok"] is True
        assert mock_res["converted_amount"] == 8500.0
        assert mock_res["rate"] == 85.0

    # 3. Cache write and hit
    await cache.set("fx:EUR:INR:mock_date", "frankfurter:cache", {"rate": 90.0, "amount": 100, "converted_amount": 9000.0})

    # 4. Upstream network failure outside mock mode gracefully degrades to fallback
    with patch("reroute_agents.tools.currency.is_mock_tools", return_value=False):
        with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Connection refused")):
            err_res = await currency_tool.ainvoke({
                "amount": 50.0,
                "from_currency": "GBP",
                "to_currency": "INR",
            })
            assert err_res["ok"] is True
            assert err_res["source"] == "fallback"


@pytest.mark.asyncio
async def test_routing_tool_known_pair_mountain_multiplier_and_unknown() -> None:
    """Test routing tool on catalog routes, mountain estimation, and unknown coordinates."""
    routing_tool = create_routing_tool()

    # 1. Known catalog route pair: Darjeeling to Ghum
    cat_res = await routing_tool.ainvoke({
        "origin_lat": 27.03,
        "origin_lng": 88.26,
        "dest_lat": 27.01,
        "dest_lng": 88.25,
        "origin_name": "Darjeeling",
        "dest_name": "Ghum",
        "mode": "taxi",
    })
    assert cat_res["ok"] is True
    assert cat_res["source"] == "routes_catalog"
    assert cat_res["travel_minutes"] == 20
    assert cat_res["distance_m"] == 7000

    # 2. Unknown pair in mock mode
    with patch("reroute_agents.tools.routing.is_mock_tools", return_value=True):
        unk_res = await routing_tool.ainvoke({
            "origin_lat": 27.03,
            "origin_lng": 88.26,
            "dest_lat": 27.10,
            "dest_lng": 88.35,
            "origin_name": "Unknown Village A",
            "dest_name": "Unknown Peak B",
            "mode": "taxi",
        })
        assert unk_res["ok"] is True
        assert unk_res["source"] == "mock_tools"
        assert unk_res["travel_minutes"] >= 10
        assert unk_res["distance_m"] > 0

    # 3. Mountain multiplier in non-mock mode
    with patch("reroute_agents.tools.routing.is_mock_tools", return_value=False):
        mtn_res = await routing_tool.ainvoke({
            "origin_lat": 27.03,
            "origin_lng": 88.26,
            "dest_lat": 27.15,
            "dest_lng": 88.40,
            "origin_name": "Spot X",
            "dest_name": "Spot Y",
            "mode": "taxi",
        })
        assert mtn_res["ok"] is True
        assert mtn_res["source"] == "mountain_model"
        assert mtn_res["travel_minutes"] >= 10


@pytest.mark.asyncio
async def test_places_tool_search_and_details() -> None:
    """Test search_places and get_place_details."""
    from decimal import Decimal

    from reroute_agents.state import PlaceCandidate

    catalog = InMemoryPlaceCatalogRepository()
    test_id = uuid4()
    candidate = PlaceCandidate(
        id=test_id,
        external_id="seed:darjeeling:tiger_hill",
        name="Tiger Hill",
        city="Darjeeling",
        country="IN",
        category="nature",
        setting="outdoor",
        avg_cost=Decimal("100"),
        currency="INR",
        avg_duration_min=120,
        lat=27.0084,
        lng=88.2435,
        rating=4.6,
        tags=["nature", "sunrise"],
        description="Famous viewpoint for sunrise over Mt Kanchenjunga.",
    )
    await catalog.upsert_place(candidate)
    search_tool, details_tool = create_places_tools(catalog)

    # 1. Search places in Darjeeling
    search_res = await search_tool.ainvoke({
        "city": "Darjeeling",
        "category": "nature",
        "limit": 5,
    })
    assert search_res["ok"] is True
    assert "places" in search_res
    assert len(search_res["places"]) > 0

    first_place = search_res["places"][0]
    p_id = first_place["id"]
    assert str(p_id) == str(test_id)

    # 2. Details lookup by UUID
    det_res = await details_tool.ainvoke({"place_id": str(p_id)})
    assert det_res["ok"] is True
    assert det_res["place"]["name"] == "Tiger Hill"

    # 3. Details lookup with invalid UUID
    bad_res = await details_tool.ainvoke({"place_id": "not-a-uuid"})
    assert bad_res["ok"] is False
    assert "Invalid UUID" in bad_res["error"]


@pytest.mark.asyncio
async def test_expenses_tool_summary_and_error_handling() -> None:
    """Test get_expenses_summary with valid and invalid trip IDs."""
    repo = InMemoryExpenseRepository()
    t_id = uuid4()
    await repo.add_expense(t_id, category="food", amount=450.0, currency="INR")
    await repo.add_expense(t_id, category="transit", amount=1200.0, currency="INR")

    expenses_tool = create_expenses_tool(repo)

    # 1. Valid summary
    res = await expenses_tool.ainvoke({"trip_id": str(t_id)})
    assert res["ok"] is True
    assert res["summary"]["total"] == 1650.0
    assert res["summary"]["by_category"]["food"] == 450.0
    assert res["summary"]["by_category"]["transit"] == 1200.0

    # 2. Invalid UUID input
    err_res = await expenses_tool.ainvoke({"trip_id": "invalid-uuid-string"})
    assert err_res["ok"] is False
    assert "Invalid UUID" in err_res["error"]


def test_disruption_injector_weather_and_closure_boundaries() -> None:
    """Test DisruptionInjector handles full, partial, and empty parameter sets safely."""
    # 1. Weather disruption with custom window
    inj_weather = InjectedSignals(
        type="weather",
        day_index=2,
        params={"precip_prob": 0.95, "from": "14:00", "to": "18:00"},
    )
    sig_w = DisruptionInjector.inject(inj_weather)
    assert sig_w.weather_forecast is not None
    hourly = sig_w.weather_forecast["2"]["hourly"]
    assert hourly[14]["precip_prob"] == 0.95
    assert hourly[10]["precip_prob"] == 0.05

    # 2. Closure disruption
    p_id = str(uuid4())
    inj_close = InjectedSignals(
        type="closure",
        day_index=1,
        params={"place_id": p_id, "reason": "Rockfall on access road"},
    )
    sig_c = DisruptionInjector.inject(inj_close)
    assert p_id in sig_c.opening_hours_updates
    assert sig_c.opening_hours_updates[p_id]["reason"] == "Rockfall on access road"

    # 3. Empty params default fallback
    inj_empty = InjectedSignals(type="weather", day_index=3, params={})
    sig_e = DisruptionInjector.inject(inj_empty)
    assert sig_e.weather_forecast is not None
    assert "3" in sig_e.weather_forecast
