"""Deterministic itinerary validation rules."""

from __future__ import annotations

from datetime import time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from reroute_agents.config import settings
from reroute_agents.rules.altitude import check_altitude_acclimatization
from reroute_agents.rules.permits import check_permits
from reroute_agents.rules.seasonal import check_seasonal_access
from reroute_agents.state import DraftItem, TripSpec, Violation

WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _time_to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _minutes_between(start: time, end: time) -> int:
    return _time_to_minutes(end) - _time_to_minutes(start)


def validate_itinerary(
    items: list[DraftItem],
    spec: TripSpec,
    places_metadata: dict[UUID, dict[str, Any]] | None = None,
    base_items: list[DraftItem] | None = None,
) -> list[Violation]:
    """Pure function validating an itinerary against all deterministic rules.

    Rules checked:
    1. Overlap: No overlapping items within a day; start_time < end_time.
    2. Opening hours: Items fall strictly within verified place opening hours.
    3. Travel gap: Gap between consecutive items accommodates travel_minutes.
    4. Daily active time: Active duration within pace limits.
    5. Budget: Total cost <= budget_total, and day costs <= budget_per_day_cap.
    6. Locked items: Items marked is_locked cannot be modified or moved.
    7. Regional altitude, seasonal access, and permits.
    """
    violations: list[Violation] = []
    meta = places_metadata or {}

    # Group items by day_index
    items_by_day: dict[int, list[DraftItem]] = {}
    for item in items:
        items_by_day.setdefault(item.day_index, []).append(item)

    # Sort items within each day by position and start_time
    for day in items_by_day:
        items_by_day[day].sort(key=lambda x: (x.position, x.start_time))

    total_cost = Decimal(0)
    pace_limit_min = settings.pace_limits_minutes.get(spec.pace, 600)

    # 1. Overlap and Start < End, Travel Gap, Opening Hours, Daily Limits
    for day_index, day_items in items_by_day.items():
        day_cost = Decimal(0)
        day_date = spec.start_date + timedelta(days=day_index - 1)
        weekday = WEEKDAY_KEYS[day_date.weekday()]

        for i, item in enumerate(day_items):
            day_cost += item.est_cost

            # Check start < end
            if item.start_time >= item.end_time:
                violations.append(
                    Violation(
                        code="overlap",
                        day_index=day_index,
                        item_stable_key=item.stable_key,
                        detail=f"Item '{item.title}' has invalid time window: start ({item.start_time}) is not before end ({item.end_time}).",
                    )
                )

            # Check opening hours if verified
            if item.place_id and item.place_id in meta:
                place = meta[item.place_id]
                hours_conf = place.get("hours_confidence", "unknown")
                opening_hours = place.get("opening_hours")
                if hours_conf != "unknown" and opening_hours and isinstance(opening_hours, dict):
                    day_windows = opening_hours.get(weekday)
                    if day_windows is not None:
                        if len(day_windows) == 0:
                            # Closed on this day
                            violations.append(
                                Violation(
                                    code="closed",
                                    day_index=day_index,
                                    item_stable_key=item.stable_key,
                                    detail=f"Place '{item.title}' is closed on {day_date.strftime('%A')}s.",
                                )
                            )
                        else:
                            # Verify item is within at least one open window
                            item_start_m = _time_to_minutes(item.start_time)
                            item_end_m = _time_to_minutes(item.end_time)
                            inside = False
                            for win in day_windows:
                                if len(win) == 2:
                                    try:
                                        wh1, wm1 = map(int, win[0].split(":"))
                                        wh2, wm2 = map(int, win[1].split(":"))
                                        w_start_m = wh1 * 60 + wm1
                                        w_end_m = wh2 * 60 + wm2
                                        if w_start_m <= item_start_m and item_end_m <= w_end_m:
                                            inside = True
                                            break
                                    except Exception:
                                        pass
                            if not inside:
                                violations.append(
                                    Violation(
                                        code="closed",
                                        day_index=day_index,
                                        item_stable_key=item.stable_key,
                                        detail=f"Item '{item.title}' window ({item.start_time}-{item.end_time}) falls outside opening hours ({day_windows}) on {day_date.strftime('%A')}.",
                                    )
                                )

            # Check consecutive item relations (overlap & travel gap)
            if i > 0:
                prev_item = day_items[i - 1]
                # Check overlap between prev_item and item
                if prev_item.end_time > item.start_time:
                    violations.append(
                        Violation(
                            code="overlap",
                            day_index=day_index,
                            item_stable_key=item.stable_key,
                            detail=f"Item '{item.title}' start ({item.start_time}) overlaps with previous item '{prev_item.title}' end ({prev_item.end_time}).",
                        )
                    )
                else:
                    # Check travel gap
                    gap_min = _minutes_between(prev_item.end_time, item.start_time)
                    req_travel = item.travel_minutes or 0
                    if req_travel > 0 and gap_min < req_travel:
                        violations.append(
                            Violation(
                                code="travel_too_long",
                                day_index=day_index,
                                item_stable_key=item.stable_key,
                                detail=f"Travel from '{prev_item.title}' to '{item.title}' requires {req_travel} min, but scheduled gap is only {gap_min} min.",
                            )
                        )

        total_cost += day_cost

        # Day active time check
        if day_items:
            first_start = day_items[0].start_time
            last_end = day_items[-1].end_time
            span_min = _minutes_between(first_start, last_end)
            if span_min > pace_limit_min:
                violations.append(
                    Violation(
                        code="day_too_long",
                        day_index=day_index,
                        detail=f"Day {day_index} active span ({span_min} min) exceeds {spec.pace} pace limit ({pace_limit_min} min).",
                    )
                )

        # Per-day budget cap check
        if spec.budget_per_day_cap is not None and day_cost > spec.budget_per_day_cap:
            violations.append(
                Violation(
                    code="over_budget",
                    day_index=day_index,
                    detail=f"Day {day_index} cost ({day_cost} {spec.currency}) exceeds per-day cap ({spec.budget_per_day_cap} {spec.currency}).",
                )
            )

    # Total budget check
    if total_cost > spec.budget_total:
        violations.append(
            Violation(
                code="over_budget",
                detail=f"Total itinerary cost ({total_cost} {spec.currency}) exceeds total budget ({spec.budget_total} {spec.currency}).",
            )
        )

    # 6. Locked items unchanged rule
    if base_items:
        current_by_key = {it.stable_key: it for it in items}
        for base_it in base_items:
            if not base_it.is_locked:
                continue
            curr = current_by_key.get(base_it.stable_key)
            if not curr:
                violations.append(
                    Violation(
                        code="locked_changed",
                        day_index=base_it.day_index,
                        item_stable_key=base_it.stable_key,
                        detail=f"Locked item '{base_it.title}' was removed from the itinerary.",
                    )
                )
            else:
                if (
                    curr.day_index != base_it.day_index
                    or curr.position != base_it.position
                    or curr.start_time != base_it.start_time
                    or curr.end_time != base_it.end_time
                    or curr.title != base_it.title
                    or curr.place_id != base_it.place_id
                ):
                    violations.append(
                        Violation(
                            code="locked_changed",
                            day_index=curr.day_index,
                            item_stable_key=base_it.stable_key,
                            detail=f"Locked item '{base_it.title}' was modified in time, position, or destination.",
                        )
                    )

    # Regional Altitude Acclimatization
    alt_violations = check_altitude_acclimatization(items_by_day, meta)
    violations.extend(alt_violations)

    # Regional Seasonal Access
    seasonal_violations = check_seasonal_access(items_by_day, meta, spec.start_date)
    violations.extend(seasonal_violations)

    # Regional Permits
    permit_violations, _ = check_permits(items_by_day, meta)
    violations.extend(permit_violations)

    return violations
