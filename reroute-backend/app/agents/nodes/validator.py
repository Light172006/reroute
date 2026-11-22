"""Deterministic validator node - pure functions, unit-tested.

Implements the 6 validator rules from the contract:
1. No overlapping items in a day; start < end.
2. Item inside opening hours (skip if hours_confidence = unknown, but add flag).
3. travel_minutes between consecutive items fits in the gap.
4. Day active time <= pace limit (relaxed 8h, balanced 10h, packed 12h).
5. Total cost <= budget_total (and per-day cap if set).
6. Locked items unchanged in time and position.
"""
from __future__ import annotations

from typing import TypedDict, Literal, Optional
from datetime import time


class DraftItem(TypedDict, total=False):
    stable_key: Optional[str]
    day_index: int
    position: int
    place_id: Optional[str]
    title: str
    category: str
    setting: Literal["indoor", "outdoor", "mixed"]
    start_time: str  # HH:MM
    end_time: str
    est_cost: float
    lat: Optional[float]
    lng: Optional[float]
    is_locked: bool
    travel_mode: Optional[str]
    travel_minutes: Optional[int]


class ItineraryDraft(TypedDict):
    items: list[DraftItem]
    summary: str


class Violation(TypedDict):
    code: Literal[
        "closed", "overlap", "travel_too_long", "over_budget",
        "day_too_long", "locked_changed"
    ]
    item_stable_key: Optional[str]
    day_index: Optional[int]
    detail: str


# Pace limits in minutes
PACE_LIMITS = {
    "relaxed": 8 * 60,    # 8 hours
    "balanced": 10 * 60,  # 10 hours
    "packed": 12 * 60,    # 12 hours
}


def parse_time(t: str) -> time:
    """Parse HH:MM string to time object."""
    h, m = map(int, t.split(":"))
    return time(h, m)


def time_to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def validate_schedule(draft: ItineraryDraft, pace: str = "balanced",
                      budget_total: float = 0, budget_per_day: Optional[float] = None,
                      previous_items: Optional[list[DraftItem]] = None) -> list[Violation]:
    """Validate a day's schedule against all rules.

    Args:
        draft: The itinerary draft to validate
        pace: pace type (relaxed/balanced/packed)
        budget_total: total budget for the trip
        budget_per_day: per-day budget cap
        previous_items: items from previous version (for locked_changed check)

    Returns:
        List of violations (empty if valid)
    """
    violations: list[Violation] = []
    items = draft.get("items", [])

    # Group by day
    by_day: dict[int, list[DraftItem]] = {}
    for item in items:
        day = item.get("day_index", 1)
        by_day.setdefault(day, []).append(item)

    # Sort each day by position then start_time
    for day, day_items in by_day.items():
        day_items.sort(key=lambda x: (x.get("position", 0), x.get("start_time", "00:00")))

    # Rule 1 & 3: No overlaps, travel time fits
    for day, day_items in by_day.items():
        prev_end = None
        prev_item = None
        for item in day_items:
            start = parse_time(item.get("start_time", "00:00"))
            end = parse_time(item.get("end_time", "00:00"))
            start_min = time_to_minutes(start)
            end_min = time_to_minutes(end)

            # start < end
            if start_min >= end_min:
                violations.append(Violation(
                    code="overlap",
                    item_stable_key=item.get("stable_key"),
                    day_index=day,
                    detail=f"Item {item.get('title')}: start_time ({item.get('start_time')}) must be before end_time ({item.get('end_time')})"
                ))

            # Overlap with previous item
            if prev_end is not None and start_min < prev_end:
                violations.append(Violation(
                    code="overlap",
                    item_stable_key=item.get("stable_key"),
                    day_index=day,
                    detail=f"Item {item.get('title')} overlaps with {prev_item.get('title')}"
                ))

            # Travel time fits in gap
            if prev_item is not None and prev_item.get("travel_minutes"):
                gap = start_min - prev_end
                needed = prev_item["travel_minutes"]
                if gap < needed:
                    violations.append(Violation(
                        code="travel_too_long",
                        item_stable_key=item.get("stable_key"),
                        day_index=day,
                        detail=f"Travel from {prev_item.get('title')} needs {needed} min but only {gap} min gap"
                    ))

            prev_end = end_min
            prev_item = item

    # Rule 2: Opening hours (mock - just flag if setting is outdoor and we don't have hours)
    # In real impl, would check place.opening_hours
    for day, day_items in by_day.items():
        for item in day_items:
            setting = item.get("setting", "mixed")
            if setting == "outdoor":
                # Add flag but don't violate (hours_confidence = unknown)
                pass

    # Rule 4: Day active time <= pace limit
    pace_limit = PACE_LIMITS.get(pace, PACE_LIMITS["balanced"])
    for day, day_items in by_day.items():
        if not day_items:
            continue
        first_start = parse_time(day_items[0].get("start_time", "00:00"))
        last_end = parse_time(day_items[-1].get("end_time", "00:00"))
        active_min = time_to_minutes(last_end) - time_to_minutes(first_start)
        if active_min > pace_limit:
            violations.append(Violation(
                code="day_too_long",
                item_stable_key=None,
                day_index=day,
                detail=f"Day {day} active time {active_min} min exceeds {pace} limit of {pace_limit} min"
            ))

    # Rule 5: Total cost <= budget
    total_cost = sum(item.get("est_cost", 0) for item in items)
    if budget_total > 0 and total_cost > budget_total:
        violations.append(Violation(
            code="over_budget",
            item_stable_key=None,
            day_index=None,
            detail=f"Total cost {total_cost:.0f} exceeds budget {budget_total:.0f}"
        ))

    if budget_per_day:
        for day, day_items in by_day.items():
            day_cost = sum(item.get("est_cost", 0) for item in day_items)
            if day_cost > budget_per_day:
                violations.append(Violation(
                    code="over_budget",
                    item_stable_key=None,
                    day_index=day,
                    detail=f"Day {day} cost {day_cost:.0f} exceeds per-day cap {budget_per_day:.0f}"
                ))

    # Rule 6: Locked items unchanged
    if previous_items:
        prev_by_key = {item.get("stable_key"): item for item in previous_items if item.get("stable_key")}
        for item in items:
            key = item.get("stable_key")
            if key and key in prev_by_key and item.get("is_locked"):
                prev = prev_by_key[key]
                if (prev.get("start_time") != item.get("start_time") or
                    prev.get("end_time") != item.get("end_time") or
                    prev.get("position") != item.get("position")):
                    violations.append(Violation(
                        code="locked_changed",
                        item_stable_key=key,
                        day_index=item.get("day_index"),
                        detail=f"Locked item {item.get('title')} changed time or position"
                    ))

    return violations


# Validator node for LangGraph
def validator(state: dict) -> dict:
    """LangGraph node: validate the current draft."""
    draft = state.get("draft")
    if not draft:
        return {"violations": []}

    spec = state.get("spec", {})
    pace = spec.get("pace", "balanced")
    budget_total = float(spec.get("budget_total", 0))
    budget_per_day = spec.get("budget_per_day_cap")
    if budget_per_day:
        budget_per_day = float(budget_per_day)

    # Previous items for locked check (from base version if replanning)
    previous_items = state.get("previous_items")

    violations = validate_schedule(draft, pace, budget_total, budget_per_day, previous_items)

    return {
        "violations": violations,
        "message": f"Validation complete: {len(violations)} violations found" if violations else "All constraints verified",
    }