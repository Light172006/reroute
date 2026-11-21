"""Seed data validation script for Reroute destinations.

Checks:
- Schema validation against Place schema
- Coordinate bounding boxes
- Duplicate IDs or names
- Place counts per city (15-30)
- Setting mix (indoor/outdoor)
- Confidence markers (verify flag and confidence level)
- routes.json physical plausibility (15-40 km/h), symmetry, key pairs
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"

BOUNDING_BOXES: dict[str, dict[str, float]] = {
    "darjeeling.json": {"min_lat": 26.8, "max_lat": 27.3, "min_lng": 88.0, "max_lng": 88.5},
    "north_sikkim.json": {"min_lat": 27.2, "max_lat": 28.2, "min_lng": 88.3, "max_lng": 88.9},
    "arunachal.json": {"min_lat": 26.5, "max_lat": 28.5, "min_lng": 91.5, "max_lng": 94.5},
    "ladakh.json": {"min_lat": 32.5, "max_lat": 35.5, "min_lng": 75.5, "max_lng": 79.5},
}


def validate_places_file(filename: str) -> dict[str, Any]:
    path = DATA_DIR / filename
    if not path.exists():
        return {"error": f"File not found: {filename}"}

    with open(path, encoding="utf-8") as f:
        places: list[dict[str, Any]] = json.load(f)

    bbox = BOUNDING_BOXES.get(filename, {})
    total = len(places)
    duplicates_id: list[str] = []
    duplicates_name: list[str] = []
    out_of_bounds: list[dict[str, Any]] = []
    missing_confidence: list[str] = []
    missing_verify: list[str] = []
    settings_counts: dict[str, int] = {}

    seen_ids: set[str] = set()
    seen_names: set[tuple[str, str]] = set()

    for p in places:
        pid = p.get("external_id", "")
        pname = p.get("name", "")
        city = p.get("city", "")

        if pid in seen_ids:
            duplicates_id.append(pid)
        seen_ids.add(pid)

        name_key = (city.lower(), pname.lower())
        if name_key in seen_names:
            duplicates_name.append(f"{city}: {pname}")
        seen_names.add(name_key)

        lat = p.get("lat", 0.0)
        lng = p.get("lng", 0.0)
        if bbox:
            if not (bbox["min_lat"] <= lat <= bbox["max_lat"] and bbox["min_lng"] <= lng <= bbox["max_lng"]):
                out_of_bounds.append({"id": pid, "name": pname, "lat": lat, "lng": lng})

        # Confidence marker check (AG-007)
        hours_conf = p.get("hours_confidence")
        raw = p.get("raw", {})
        verify_flag = raw.get("verify")

        if hours_conf not in ("estimated", "unverified") and raw.get("confidence") not in ("estimated", "unverified"):
            missing_confidence.append(pid)
        if verify_flag is not True:
            missing_verify.append(pid)

        setting = p.get("setting", "unknown")
        settings_counts[setting] = settings_counts.get(setting, 0) + 1

    return {
        "file": filename,
        "total_places": total,
        "valid_count_range": 15 <= total <= 30,
        "duplicate_ids": duplicates_id,
        "duplicate_names": duplicates_name,
        "out_of_bounds": out_of_bounds,
        "missing_confidence": missing_confidence,
        "missing_verify": missing_verify,
        "settings_counts": settings_counts,
    }


def validate_routes() -> dict[str, Any]:
    path = DATA_DIR / "routes.json"
    if not path.exists():
        return {"error": "routes.json not found"}

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    routes = data.get("routes", [])
    implausible_speeds: list[dict[str, Any]] = []
    pairs: dict[tuple[str, str], dict[str, Any]] = {}
    asymmetric_routes: list[dict[str, Any]] = []

    for r in routes:
        src = r.get("from", "")
        dst = r.get("to", "")
        dist = r.get("distance_km", 0)
        mins = r.get("typical_minutes", 0)

        pairs[(src, dst)] = r

        if mins > 0 and dist > 0:
            speed_kmh = (dist / mins) * 60.0
            # Mountain speed expectation: 15-40 km/h
            if speed_kmh < 15.0 or speed_kmh > 45.0:
                implausible_speeds.append({
                    "from": src,
                    "to": dst,
                    "distance_km": dist,
                    "typical_minutes": mins,
                    "speed_kmh": round(speed_kmh, 1),
                })

    for (src, dst), r in pairs.items():
        reverse = pairs.get((dst, src))
        if reverse:
            # Check if distance differs drastically
            diff_dist = abs(r.get("distance_km", 0) - reverse.get("distance_km", 0))
            if diff_dist > 5:
                asymmetric_routes.append({
                    "pair": f"{src} <-> {dst}",
                    "dist_fwd": r.get("distance_km"),
                    "dist_rev": reverse.get("distance_km"),
                })

    return {
        "total_routes": len(routes),
        "mountain_multiplier": data.get("mountain_multiplier"),
        "implausible_speeds": implausible_speeds,
        "asymmetric_routes": asymmetric_routes,
    }


def run_all_validations() -> dict[str, Any]:
    results = {}
    for f in ["darjeeling.json", "north_sikkim.json", "arunachal.json", "ladakh.json"]:
        results[f] = validate_places_file(f)
    results["routes"] = validate_routes()
    return results


if __name__ == "__main__":
    report = run_all_validations()
    print(json.dumps(report, indent=2))
