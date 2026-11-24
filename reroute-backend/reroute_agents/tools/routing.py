"""Travel route and duration estimation tool."""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any, cast

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from reroute_agents.tools.base import is_mock_tools, safe_tool

logger = logging.getLogger(__name__)


class EstimateRouteInput(BaseModel):
    origin_lat: float = Field(description="Latitude of starting point")
    origin_lng: float = Field(description="Longitude of starting point")
    dest_lat: float = Field(description="Latitude of destination point")
    dest_lng: float = Field(description="Longitude of destination point")
    origin_name: str | None = Field(default=None, description="Optional name of origin place")
    dest_name: str | None = Field(default=None, description="Optional name of destination place")
    mode: str = Field(default="taxi", description="Travel mode (walk, taxi, car, bus)")


def _haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great circle distance between two points on Earth."""
    r = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def _load_seed_routes() -> list[dict[str, Any]]:
    routes_file = Path(__file__).resolve().parent.parent.parent / "data" / "seed" / "routes.json"
    if routes_file.exists():
        try:
            with open(routes_file, encoding="utf-8") as f:
                data = json.load(f)
                return cast(list[dict[str, Any]], data.get("routes", []))
        except (json.JSONDecodeError, OSError) as err:
            logger.warning(
                "Failed to load seed routes from %s: %s; falling back to mountain default",
                routes_file,
                err,
            )
    return []


_SEED_ROUTES = _load_seed_routes()


def create_routing_tool() -> Any:
    """Factory creating estimate_route tool."""

    @tool(args_schema=EstimateRouteInput)
    @safe_tool(timeout_sec=6.0)
    async def estimate_route(
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        origin_name: str | None = None,
        dest_name: str | None = None,
        mode: str = "taxi",
    ) -> dict[str, Any]:
        """Estimate travel minutes and distance between stops on mountain roads."""
        # 1. Match seed routes if names provided
        if origin_name and dest_name:
            orig_lower = origin_name.lower().strip()
            dest_lower = dest_name.lower().strip()
            for r in _SEED_ROUTES:
                r_from = r["from"].lower()
                r_to = r["to"].lower()
                if (r_from in orig_lower and r_to in dest_lower) or (
                    r_to in orig_lower and r_from in dest_lower
                ):
                    dist_m = int(r["distance_km"] * 1000)
                    mins = int(r["typical_minutes"])
                    return {
                        "ok": True,
                        "travel_minutes": mins,
                        "distance_m": dist_m,
                        "confidence": "estimated",
                        "mode": mode,
                        "source": "routes_catalog",
                    }

        # 2. Mock mode fast return
        if is_mock_tools():
            straight_km = _haversine_distance_km(origin_lat, origin_lng, dest_lat, dest_lng)
            # Default city speed 20 km/h with 1.4 winding road multiplier
            est_dist_km = max(straight_km * 1.4, 1.0)
            mins = max(int((est_dist_km / 20.0) * 60), 10)
            return {
                "ok": True,
                "travel_minutes": mins,
                "distance_m": int(est_dist_km * 1000),
                "confidence": "estimated",
                "mode": mode,
                "source": "mock_tools",
            }

        # 3. Calculation with mountain multiplier
        straight_km = _haversine_distance_km(origin_lat, origin_lng, dest_lat, dest_lng)
        # Mountain roads are significantly windier than direct distance
        mountain_dist_km = max(straight_km * 1.6, 1.0)

        # Speed depends on mode and terrain
        if mode == "walk":
            speed_kmh = 4.0
        elif mode in ("car", "taxi"):
            speed_kmh = 25.0  # Conservative mountain average
        else:
            speed_kmh = 20.0

        travel_minutes = max(int((mountain_dist_km / speed_kmh) * 60), 10)

        return {
            "ok": True,
            "travel_minutes": travel_minutes,
            "distance_m": int(mountain_dist_km * 1000),
            "confidence": "estimated",
            "mode": mode,
            "source": "mountain_model",
        }

    return estimate_route
