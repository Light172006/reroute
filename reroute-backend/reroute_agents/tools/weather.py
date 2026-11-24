"""Weather forecast tool via Open-Meteo API with caching and offline mock support."""

from __future__ import annotations

from typing import Any

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from reroute_agents.repositories.interfaces import CacheRepository
from reroute_agents.tools.base import is_mock_tools, safe_tool


class WeatherForecastInput(BaseModel):
    lat: float = Field(description="Latitude coordinate of destination")
    lng: float = Field(description="Longitude coordinate of destination")
    start_date: str = Field(description="Start date in YYYY-MM-DD format")
    end_date: str = Field(description="End date in YYYY-MM-DD format")


def create_weather_tool(cache_repo: CacheRepository | None = None) -> Any:
    """Factory creating get_weather_forecast tool."""

    @tool(args_schema=WeatherForecastInput)
    @safe_tool(timeout_sec=10.0)
    async def get_weather_forecast(
        lat: float,
        lng: float,
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        """Fetch hourly weather forecast (precipitation probability, snowfall, visibility) for dates."""
        round_lat = round(lat, 2)
        round_lng = round(lng, 2)
        cache_key = f"weather:{round_lat},{round_lng}:{start_date}:{end_date}"

        if cache_repo:
            cached = await cache_repo.get(cache_key)
            if cached:
                return {
                    "ok": True,
                    "cached": True,
                    "forecast": cached,
                    "source": "open-meteo:cache",
                }

        if is_mock_tools():
            # Return dry, sunny mock weather
            mock_hourly = [
                {"hour": h, "precip_prob": 0.05, "snowfall": 0.0, "visibility": 10000}
                for h in range(24)
            ]
            mock_data = {
                "latitude": round_lat,
                "longitude": round_lng,
                "daily": [{"date": start_date, "hourly": mock_hourly}],
            }
            return {
                "ok": True,
                "cached": False,
                "forecast": mock_data,
                "source": "mock_tools",
            }

        # Real Open-Meteo call (no API key required)
        url = "https://api.open-meteo.com/v1/forecast"
        params: dict[str, Any] = {
            "latitude": round_lat,
            "longitude": round_lng,
            "hourly": "precipitation_probability,snowfall,visibility",
            "start_date": start_date,
            "end_date": end_date,
            "timezone": "auto",
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            precips = hourly.get("precipitation_probability", [])
            snows = hourly.get("snowfall", [])
            visibilities = hourly.get("visibility", [])

            structured_hourly = []
            for i in range(len(times)):
                t_str = times[i]
                hour = int(t_str.split("T")[1].split(":")[0]) if "T" in t_str else i % 24
                p_prob = (
                    (precips[i] / 100.0) if i < len(precips) and precips[i] is not None else 0.0
                )
                structured_hourly.append(
                    {
                        "time": t_str,
                        "hour": hour,
                        "precip_prob": p_prob,
                        "snowfall": snows[i] if i < len(snows) and snows[i] is not None else 0.0,
                        "visibility": visibilities[i]
                        if i < len(visibilities) and visibilities[i] is not None
                        else 10000,
                    }
                )

            result_forecast = {
                "latitude": round_lat,
                "longitude": round_lng,
                "hourly": structured_hourly,
            }

            if cache_repo:
                await cache_repo.set(cache_key, "open-meteo", result_forecast, ttl_seconds=14400)

            return {
                "ok": True,
                "cached": False,
                "forecast": result_forecast,
                "source": "open-meteo",
            }

        except Exception as e:
            # Graceful degradation to dry fallback
            mock_hourly = [
                {"hour": h, "precip_prob": 0.1, "snowfall": 0.0, "visibility": 10000}
                for h in range(24)
            ]
            return {
                "ok": True,
                "cached": False,
                "forecast": {
                    "hourly": mock_hourly,
                    "fallback": True,
                    "notice": f"Live weather unavailable: {e}",
                },
                "source": "fallback",
            }

    return get_weather_forecast
