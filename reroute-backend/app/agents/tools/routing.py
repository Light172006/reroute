"""Routing/travel time tool with mock mode."""
from __future__ import annotations

import logging

from langchain_core.tools import tool

from app.core.config import settings

log = logging.getLogger("reroute.tools.routing")


MOCK_TRAVEL = {
    # (from_place, to_place) -> (minutes, distance_m, mode)
    ("Batasia Loop", "Tiger Hill"): (15, 4200, "taxi"),
    ("Tiger Hill", "Padmaja Naidu Himalayan Zoological Park"): (10, 3000, "taxi"),
    ("Padmaja Naidu Himalayan Zoological Park", "Tibetan Refugee Self-Help Centre"): (5, 1500, "walk"),
    ("Tibetan Refugee Self-Help Centre", "Glenary's Bakery & Cafe"): (8, 2000, "walk"),
}


@tool(args_schema=None)
def get_travel_time(from_lat: float, from_lng: float, to_lat: float, to_lng: float, mode: str = "taxi") -> dict:
    """Get estimated travel time and distance between two coordinates.

    In mock mode, returns deterministic times based on place names.
    """
    if getattr(settings, "MOCK_TOOLS", True):
        # Mock: just return a fixed estimate based on distance
        import math
        dist = math.hypot(to_lat - from_lat, to_lng - from_lng) * 111000  # rough meters
        if mode == "walk":
            minutes = int(dist / 80)  # 5 km/h
        elif mode == "bike":
            minutes = int(dist / 250)  # 15 km/h
        else:
            minutes = int(dist / 500)  # 30 km/h
        return {"ok": True, "source": "mock", "minutes": max(5, minutes), "distance_m": int(dist), "mode": mode}

    # Real implementation: OSRM, Google Maps, etc.
    return {"ok": False, "error": "Real routing not implemented", "minutes": 15, "distance_m": 4000, "mode": mode}