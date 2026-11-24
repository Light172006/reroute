"""Weather forecast tool with mock mode and DisruptionInjector."""
from __future__ import annotations

import logging
from typing import Optional

from langchain_core.tools import tool
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

log = logging.getLogger("reroute.tools.weather")

# Mock forecasts for demo cities
MOCK_FORECASTS = {
    "Darjeeling": {
        "daily": [
            {"date": "2026-12-12", "precip_prob": [10, 10, 10, 10, 10, 15, 20, 20, 25, 30, 30, 25, 20, 15, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10], "temp_c": [8, 7, 7, 7, 8, 10, 12, 14, 16, 17, 18, 18, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 9, 8]},
            {"date": "2026-12-13", "precip_prob": [10, 10, 10, 10, 10, 10, 15, 20, 25, 35, 45, 55, 65, 70, 75, 80, 80, 75, 70, 60, 50, 40, 30, 20], "temp_c": [8, 7, 7, 7, 8, 10, 12, 14, 16, 17, 18, 18, 17, 16, 15, 14, 14, 13, 12, 11, 10, 9, 9, 8]},
            {"date": "2026-12-14", "precip_prob": [20, 15, 10, 10, 10, 10, 10, 10, 15, 20, 25, 30, 30, 25, 20, 15, 10, 10, 10, 10, 10, 10, 10, 10], "temp_c": [8, 7, 7, 7, 8, 10, 12, 14, 16, 17, 18, 18, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 9, 8]},
        ]
    },
    "Jaipur": {
        "daily": [
            {"date": "2026-12-12", "precip_prob": [0, 0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 0, 0, 0, 0, 0, 0], "temp_c": [12, 11, 10, 9, 9, 10, 12, 15, 18, 21, 23, 24, 25, 25, 24, 22, 20, 18, 16, 15, 14, 13, 13, 12]},
        ]
    },
}

# Injected disruptions for /demo/simulate — keyed by (city, type, day_index)
_INJECTED: dict[tuple, dict] = {}


def inject_forecast(city: str, day_index: int, precip_prob: int, window: str = "14-18h") -> None:
    """Inject a disruption forecast for demo mode.

    Called by POST /demo/simulate before starting the replan run.
    """
    _INJECTED[(city, day_index)] = {"precip_prob": precip_prob, "window": window}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def _fetch(lat: float, lng: float) -> dict:
    import httpx
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&hourly=precipitation_probability,temperature_2m"
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.json()


def _mock(city: str, day_index: int) -> dict:
    data = _INJECTED.get((city, day_index))
    if data:
        # Build a day with injected precip in the specified window
        daily = MOCK_FORECASTS.get(city, {"daily": [{"precip_prob": [20] * 24, "temp_c": [20] * 24}]})
        base_day = daily["daily"][min(day_index, len(daily["daily"]) - 1)]
        probs = base_day["precip_prob"].copy()
        # Parse window like "14-18h"
        try:
            start_str, end_str = data["window"].replace("h", "").split("-")
            start_h = int(start_str)
            end_h = int(end_str)
            for h in range(start_h, end_h):
                if h < 24:
                    probs[h] = data["precip_prob"]
        except Exception:
            pass
        return {"ok": True, "source": "demo-injector", "precip_prob": probs, "temp_c": base_day["temp_c"]}

    daily = MOCK_FORECASTS.get(city, {"daily": [{"precip_prob": [20] * 24, "temp_c": [20] * 24}]})
    day = daily["daily"][min(day_index, len(daily["daily"]) - 1)]
    return {"ok": True, "source": "seed", "precip_prob": day["precip_prob"], "temp_c": day["temp_c"]}


@tool(args_schema=None)
async def get_weather_forecast(city: str, day_index: int = 1) -> dict:
    """Get the hourly precipitation probability for a city on a given trip day.

    day_index is 1-based (Day 1, Day 2, etc.)
    """
    if getattr(settings, "MOCK_TOOLS", True) or not getattr(settings, "GOOGLE_API_KEY", None):
        return _mock(city, day_index - 1)
    try:
        # Real implementation would geocode city and call open-meteo
        # For now, fall back to mock
        return _mock(city, day_index - 1)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


# For the replan graph's signal collector
@tool(args_schema=None)
async def open_meteo_hourly(city: str, day: int) -> dict:
    """Fetch hourly precipitation probability from Open-Meteo for a specific day."""
    return await get_weather_forecast(city, day)