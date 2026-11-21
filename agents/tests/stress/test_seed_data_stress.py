"""Stress and completeness tests for destination seed data and routing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"

CITIES = ["darjeeling.json", "north_sikkim.json", "arunachal.json", "ladakh.json"]
BOUNDING_BOXES: dict[str, dict[str, float]] = {
    "darjeeling.json": {"min_lat": 26.8, "max_lat": 27.3, "min_lng": 88.0, "max_lng": 88.5},
    "north_sikkim.json": {"min_lat": 27.2, "max_lat": 28.2, "min_lng": 88.3, "max_lng": 88.9},
    "arunachal.json": {"min_lat": 26.5, "max_lat": 28.5, "min_lng": 91.5, "max_lng": 94.5},
    "ladakh.json": {"min_lat": 32.5, "max_lat": 35.5, "min_lng": 75.5, "max_lng": 79.5},
}


@pytest.mark.parametrize("filename", CITIES)
def test_seed_places_count_and_uniqueness(filename: str) -> None:
    path = DATA_DIR / filename
    assert path.exists(), f"Missing seed file {filename}"

    with open(path, "r", encoding="utf-8") as f:
        places: list[dict[str, Any]] = json.load(f)

    assert 15 <= len(places) <= 30, f"{filename} has {len(places)} places, expected 15-30"

    ids = [p["external_id"] for p in places]
    assert len(ids) == len(set(ids)), f"Duplicate external_ids in {filename}"

    names = [(p["city"].lower(), p["name"].lower()) for p in places]
    assert len(names) == len(set(names)), f"Duplicate city+name in {filename}"


@pytest.mark.parametrize("filename", CITIES)
def test_seed_places_bounding_box_and_schema(filename: str) -> None:
    path = DATA_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        places: list[dict[str, Any]] = json.load(f)

    bbox = BOUNDING_BOXES[filename]
    has_indoor = False
    has_outdoor = False

    for p in places:
        # Schema checks
        assert "name" in p and p["name"]
        assert "city" in p and p["city"]
        assert "country" in p and p["country"] == "IN"
        assert "category" in p
        assert p["setting"] in ("indoor", "outdoor", "mixed")
        if p["setting"] == "indoor":
            has_indoor = True
        elif p["setting"] == "outdoor":
            has_outdoor = True

        assert "avg_cost" in p and p["avg_cost"] >= 0
        assert "avg_duration_min" in p and p["avg_duration_min"] > 0
        assert "opening_hours" in p

        # Bounding box
        lat = p["lat"]
        lng = p["lng"]
        assert bbox["min_lat"] <= lat <= bbox["max_lat"], f"Lat {lat} out of bounds in {filename} for {p['name']}"
        assert bbox["min_lng"] <= lng <= bbox["max_lng"], f"Lng {lng} out of bounds in {filename} for {p['name']}"

        # Confidence marker and verify flag
        assert "hours_confidence" in p
        raw = p.get("raw", {})
        assert "verify" in raw, f"Missing raw.verify in {filename} for {p['name']}"
        assert "altitude_m" in raw, f"Missing raw.altitude_m in {filename} for {p['name']}"

    assert has_indoor, f"No indoor places in {filename}"
    assert has_outdoor, f"No outdoor places in {filename}"


def test_routes_plausibility_and_symmetry() -> None:
    path = DATA_DIR / "routes.json"
    assert path.exists()

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("mountain_multiplier") >= 1.0
    routes = data.get("routes", [])
    assert len(routes) >= 15

    pairs: dict[tuple[str, str], dict[str, Any]] = {}
    for r in routes:
        src = r["from"]
        dst = r["to"]
        dist = r["distance_km"]
        mins = r["typical_minutes"]

        assert dist > 0
        assert mins > 0
        speed_kmh = (dist / mins) * 60.0
        # Mountain speeds should be plausible (15-45 km/h)
        assert 15.0 <= speed_kmh <= 45.0, f"Implausible speed {speed_kmh:.1f} km/h for route {src} -> {dst}"
        pairs[(src, dst)] = r

    # Symmetry check for pairs that define bidirectional routes
    for (src, dst), fwd in pairs.items():
        if (dst, src) in pairs:
            rev = pairs[(dst, src)]
            assert abs(fwd["distance_km"] - rev["distance_km"]) <= 2
            assert abs(fwd["typical_minutes"] - rev["typical_minutes"]) <= 10
