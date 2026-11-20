"""Altitude and acclimatization validation rules for high-altitude destinations."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from reroute_agents.config import settings
from reroute_agents.state import DraftItem, Violation

MEDICAL_DISCLAIMER = "This is informational travel guidance, not medical advice. Consult medical professionals regarding high-altitude acclimatization."


def check_altitude_acclimatization(
    items_by_day: dict[int, list[DraftItem]],
    places_metadata: dict[UUID, dict[str, Any]],
    threshold_gain_m: int = settings.altitude_acclimatization_threshold_m,
    high_risk_threshold_m: int = settings.altitude_high_risk_threshold_m,
) -> list[Violation]:
    """Check that itinerary does not gain altitude faster than safe thresholds.

    Flag itineraries where:
    - Day 1 begins directly at extreme high altitude without acclimatization rest.
    - Consecutive day elevation jump exceeds the conservative acclimatization threshold.
    """
    violations: list[Violation] = []
    prev_max_alt: int | None = None

    for day_index in sorted(items_by_day.keys()):
        day_items = items_by_day[day_index]
        if not day_items:
            continue

        day_altitudes: list[int] = []
        for item in day_items:
            alt: int | None = None
            if item.place_id and item.place_id in places_metadata:
                raw = places_metadata[item.place_id].get("raw", {})
                alt = raw.get("altitude_m") or places_metadata[item.place_id].get("altitude_m")
            if alt is not None:
                day_altitudes.append(alt)

        if not day_altitudes:
            continue

        day_max_alt = max(day_altitudes)

        # Day 1 Arrival Day high altitude rule:
        # If Day 1 has high-exertion or extreme altitude (> 3000m) without rest
        if day_index == 1 and day_max_alt >= high_risk_threshold_m:
            # Check if Day 1 contains strenuous sightseeing or far travel
            if len(day_items) > 2 or any(
                item.category in ("adventure", "nature") and item.setting == "outdoor"
                for item in day_items
            ):
                violations.append(
                    Violation(
                        code="day_too_long",
                        day_index=1,
                        item_stable_key=day_items[0].stable_key,
                        detail=(
                            f"Day 1 reaches {day_max_alt}m without sufficient acclimatization rest. "
                            f"Rest or light activity is recommended upon arrival at high altitude. {MEDICAL_DISCLAIMER}"
                        ),
                    )
                )

        # Multi-day elevation jump rule:
        if prev_max_alt is not None:
            gain = day_max_alt - prev_max_alt
            if gain > threshold_gain_m:
                # Find the item responsible for the jump
                high_item = next(
                    (
                        it
                        for it in day_items
                        if places_metadata.get(it.place_id or UUID(int=0), {})
                        .get("raw", {})
                        .get("altitude_m", 0)
                        == day_max_alt
                    ),
                    day_items[0],
                )
                violations.append(
                    Violation(
                        code="day_too_long",
                        day_index=day_index,
                        item_stable_key=high_item.stable_key,
                        detail=(
                            f"Altitude gain of {gain}m from Day {day_index - 1} ({prev_max_alt}m) to Day {day_index} ({day_max_alt}m) "
                            f"exceeds safe threshold of {threshold_gain_m}m/day. Acclimatization buffer recommended. {MEDICAL_DISCLAIMER}"
                        ),
                    )
                )

        prev_max_alt = day_max_alt

    return violations
