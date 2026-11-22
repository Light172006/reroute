"""Places search tool with mock mode."""
from __future__ import annotations

import logging
from typing import Optional

from langchain_core.tools import tool

from app.core.config import settings

log = logging.getLogger("reroute.tools.places")

# Mock data for demo cities
MOCK_PLACES = {
    "Darjeeling": [
        {"id": "1", "name": "Batasia Loop", "category": "sightseeing", "setting": "outdoor",
         "lat": 27.036, "lng": 88.262, "avg_cost": 150, "duration_min": 60,
         "opening_hours": {"mon": "09:00-17:00", "tue": "09:00-17:00", "wed": "09:00-17:00",
                          "thu": "09:00-17:00", "fri": "09:00-17:00", "sat": "09:00-17:00", "sun": "09:00-17:00"},
         "tags": ["viewpoint", "toy_train"], "rating": 4.5},
        {"id": "2", "name": "Tiger Hill", "category": "sightseeing", "setting": "outdoor",
         "lat": 27.007, "lng": 88.262, "avg_cost": 200, "duration_min": 90,
         "opening_hours": {"mon": "04:00-10:00", "tue": "04:00-10:00", "wed": "04:00-10:00",
                          "thu": "04:00-10:00", "fri": "04:00-10:00", "sat": "04:00-10:00", "sun": "04:00-10:00"},
         "tags": ["sunrise", "viewpoint"], "rating": 4.7},
        {"id": "3", "name": "Padmaja Naidu Himalayan Zoological Park", "category": "sightseeing", "setting": "outdoor",
         "lat": 27.034, "lng": 88.257, "avg_cost": 100, "duration_min": 120,
         "opening_hours": {"mon": "09:00-16:00", "tue": "09:00-16:00", "wed": "09:00-16:00",
                          "thu": "09:00-16:00", "fri": "09:00-16:00", "sat": "09:00-16:00", "sun": "09:00-16:00"},
         "tags": ["zoo", "red_panda"], "rating": 4.3},
        {"id": "4", "name": "Tibetan Refugee Self-Help Centre", "category": "culture", "setting": "indoor",
         "lat": 27.038, "lng": 88.255, "avg_cost": 50, "duration_min": 90,
         "opening_hours": {"mon": "09:00-17:00", "tue": "09:00-17:00", "wed": "09:00-17:00",
                          "thu": "09:00-17:00", "fri": "09:00-17:00", "sat": "09:00-17:00", "sun": "closed"},
         "tags": ["handicrafts", "tibetan_culture"], "rating": 4.2},
        {"id": "5", "name": "Glenary's Bakery & Cafe", "category": "food", "setting": "indoor",
         "lat": 27.039, "lng": 88.263, "avg_cost": 500, "duration_min": 60,
         "opening_hours": {"mon": "07:00-21:00", "tue": "07:00-21:00", "wed": "07:00-21:00",
                          "thu": "07:00-21:00", "fri": "07:00-21:00", "sat": "07:00-21:00", "sun": "07:00-21:00"},
         "tags": ["bakery", "continental"], "rating": 4.4},
    ],
    "Jaipur": [
        {"id": "10", "name": "Amber Fort", "category": "sightseeing", "setting": "outdoor",
         "lat": 26.985, "lng": 75.851, "avg_cost": 500, "duration_min": 180,
         "opening_hours": {"mon": "08:00-17:30", "tue": "08:00-17:30", "wed": "08:00-17:30",
                          "thu": "08:00-17:30", "fri": "08:00-17:30", "sat": "08:00-17:30", "sun": "08:00-17:30"},
         "tags": ["fort", "unesco"], "rating": 4.6},
        {"id": "11", "name": "City Palace", "category": "sightseeing", "setting": "mixed",
         "lat": 26.926, "lng": 75.823, "avg_cost": 300, "duration_min": 120,
         "opening_hours": {"mon": "09:30-17:00", "tue": "09:30-17:00", "wed": "09:30-17:00",
                          "thu": "09:30-17:00", "fri": "09:30-17:00", "sat": "09:30-17:00", "sun": "09:30-17:00"},
         "tags": ["palace", "museum"], "rating": 4.5},
    ],
}


@tool(args_schema=None)
def search_places(city: str, vibe: Optional[list[str]] = None, limit: int = 20) -> dict:
    """Search for places in a city matching the given vibe tags.

    Returns a list of places with name, category, setting, coordinates, cost, duration, opening hours, tags, and rating.
    """
    if getattr(settings, "MOCK_TOOLS", True):
        places = MOCK_PLACES.get(city, MOCK_PLACES["Darjeeling"])
        if vibe:
            places = [p for p in places if any(v.lower() in [t.lower() for t in p.get("tags", [])] for v in vibe)]
        return {"ok": True, "source": "mock", "places": places[:limit]}

    # Real implementation would call Google Places API or similar
    return {"ok": False, "error": "Real places search not implemented", "places": []}