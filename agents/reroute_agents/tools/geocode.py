"""Geocoding tool using Nominatim (OpenStreetMap) with rate limiting and bbox checks."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any

from langchain_core.tools import BaseTool, tool

from reroute_agents.config import settings

logger = logging.getLogger(__name__)

# Known geographic bounding boxes for validation [min_lat, max_lat, min_lng, max_lng]
REGION_BOUNDING_BOXES: dict[str, dict[str, float]] = {
    "arunachal": {"min_lat": 26.5, "max_lat": 29.5, "min_lng": 91.5, "max_lng": 97.5},
    "sikkim": {"min_lat": 27.0, "max_lat": 28.2, "min_lng": 88.0, "max_lng": 89.0},
    "darjeeling": {"min_lat": 26.8, "max_lat": 27.3, "min_lng": 88.0, "max_lng": 88.6},
    "meghalaya": {"min_lat": 25.0, "max_lat": 26.2, "min_lng": 89.8, "max_lng": 92.8},
    "india": {"min_lat": 8.0, "max_lat": 37.0, "min_lng": 68.0, "max_lng": 97.5},
}

# Pre-populated coordinates for known attractions to support mock mode and instant hits
_KNOWN_COORDINATES: dict[str, tuple[float, float, str]] = {
    "tawang monastery": (27.5861, 91.8594, "arunachal"),
    "sela pass": (27.5034, 92.1037, "arunachal"),
    "jaswant garh": (27.5142, 92.0514, "arunachal"),
    "sangetsar lake": (27.7258, 91.7825, "arunachal"),
    "madhuri lake": (27.7258, 91.7825, "arunachal"),
    "ziro valley": (27.5447, 93.8294, "arunachal"),
    "dirang dzong": (27.3597, 92.2417, "arunachal"),
    "bomdila monastery": (27.2644, 92.4167, "arunachal"),
    "mg marg": (27.3297, 88.6122, "sikkim"),
    "rumtek monastery": (27.3047, 88.5639, "sikkim"),
    "gurudongmar lake": (28.0258, 88.7097, "sikkim"),
    "yumthang valley": (27.8258, 88.6961, "sikkim"),
    "nathula pass": (27.3867, 88.8308, "sikkim"),
    "tsomgo lake": (27.3742, 88.7619, "sikkim"),
    "lachen": (27.7167, 88.5500, "sikkim"),
    "lachung": (27.6833, 88.7500, "sikkim"),
    "tiger hill": (27.0089, 88.2864, "darjeeling"),
    "batasia loop": (27.0167, 88.2467, "darjeeling"),
    "happy valley tea estate": (27.0547, 88.2611, "darjeeling"),
    "himalayan mountaineering institute": (27.0583, 88.2536, "darjeeling"),
    "living root bridge": (25.2447, 91.6744, "meghalaya"),
    "nohkalikai falls": (25.2758, 91.6853, "meghalaya"),
    "dawki river": (25.1833, 92.0167, "meghalaya"),
    "mawlynnong": (25.2014, 91.9167, "meghalaya"),
}


class NominatimRateLimiter:
    """Strict 1 request/second rate limiter for OSM Nominatim usage policy."""

    def __init__(self) -> None:
        self._last_call: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            elapsed = now - self._last_call
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)
            self._last_call = loop.time()


_global_nominatim_limiter = NominatimRateLimiter()


def validate_bounding_box(lat: float, lng: float, destination_hint: str | None = None) -> tuple[bool, str]:
    """Check if coordinates fall within the expected region bounding box."""
    if destination_hint:
        dest_lower = destination_hint.lower()
        for region_key, bbox in REGION_BOUNDING_BOXES.items():
            if region_key in dest_lower:
                if not (bbox["min_lat"] <= lat <= bbox["max_lat"] and bbox["min_lng"] <= lng <= bbox["max_lng"]):
                    return False, f"Coordinate ({lat}, {lng}) falls outside expected {region_key} bounding box: {bbox}"
                return True, "OK"

    # Default check: within India
    india_bbox = REGION_BOUNDING_BOXES["india"]
    if not (india_bbox["min_lat"] <= lat <= india_bbox["max_lat"] and india_bbox["min_lng"] <= lng <= india_bbox["max_lng"]):
        return False, f"Coordinate ({lat}, {lng}) is outside India regional bounds."
    return True, "OK"


class GeocodingService:
    """Service resolving place names to verified geographic coordinates."""

    def __init__(self, use_mock: bool | None = None) -> None:
        self.use_mock = use_mock if use_mock is not None else settings.mock_tools

    async def geocode(self, place_name: str, destination_hint: str | None = None) -> dict[str, Any]:
        p_lower = place_name.lower().strip()

        # 1. Check known lookup dictionary
        for key, (lat, lng, reg) in _KNOWN_COORDINATES.items():
            if key in p_lower or p_lower in key:
                is_valid, reason = validate_bounding_box(lat, lng, destination_hint or reg)
                return {
                    "ok": True,
                    "place_name": place_name,
                    "lat": lat,
                    "lng": lng,
                    "verified": is_valid,
                    "source": "known_cache",
                    "region": reg,
                }

        # 2. If in mock mode, generate deterministic coordinate within destination bbox
        if self.use_mock:
            bbox = REGION_BOUNDING_BOXES.get(
                (destination_hint or "india").lower(),
                REGION_BOUNDING_BOXES["india"],
            )
            # Hash place name for deterministic offset within bounding box
            h = int(hashlib.sha256(place_name.encode("utf-8")).hexdigest()[:8], 16)
            lat_span = bbox["max_lat"] - bbox["min_lat"]
            lng_span = bbox["max_lng"] - bbox["min_lng"]
            lat = round(bbox["min_lat"] + (h % 1000) / 1000.0 * lat_span, 4)
            lng = round(bbox["min_lng"] + ((h // 1000) % 1000) / 1000.0 * lng_span, 4)
            return {
                "ok": True,
                "place_name": place_name,
                "lat": lat,
                "lng": lng,
                "verified": True,
                "source": "mock_deterministic",
                "region": destination_hint or "india",
            }

        # 3. Live Nominatim query
        await _global_nominatim_limiter.acquire()
        import httpx

        headers = {
            "User-Agent": "RerouteAgent/1.0 (travel-planner; https://reroute.travel)"
        }
        search_query = f"{place_name}, {destination_hint}" if destination_hint else place_name
        params = {"q": search_query, "format": "json", "limit": "1"}

        try:
            async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
                res = await client.get("https://nominatim.openstreetmap.org/search", params=params)
                res.raise_for_status()
                data = res.json()
                if not data:
                    return {
                        "ok": False,
                        "place_name": place_name,
                        "error": "No geocoding match found on Nominatim",
                    }

                lat = float(data[0]["lat"])
                lng = float(data[0]["lon"])
                is_valid, reason = validate_bounding_box(lat, lng, destination_hint)
                return {
                    "ok": True,
                    "place_name": place_name,
                    "lat": lat,
                    "lng": lng,
                    "verified": is_valid,
                    "display_name": data[0].get("display_name", ""),
                    "source": "nominatim",
                    "bbox_valid": is_valid,
                    "bbox_reason": reason,
                }
        except Exception as exc:
            logger.warning("Nominatim lookup failed for '%s': %s", place_name, exc)
            return {
                "ok": False,
                "place_name": place_name,
                "error": str(exc),
            }


def create_web_geocode_tool(geocoder: GeocodingService | None = None) -> BaseTool:
    """Create LangChain BaseTool for geocoding."""
    service = geocoder or GeocodingService()

    @tool
    async def web_geocode(place_name: str, destination_hint: str | None = None) -> dict[str, Any]:
        """Convert a place name to verified latitude and longitude coordinates."""
        return await service.geocode(place_name=place_name, destination_hint=destination_hint)

    return web_geocode
