"""Unit tests for the deterministic validator.

These tests verify the 6 validator rules work correctly.
"""
import pytest

from app.agents.nodes.validator import validate_schedule, Violation


def make_item(stable_key: str, day: int, pos: int, start: str, end: str,
              cost: float = 100, setting: str = "indoor", locked: bool = False,
              travel_min: int = 0, travel_mode: str = "taxi") -> dict:
    return {
        "stable_key": stable_key,
        "day_index": day,
        "position": pos,
        "title": f"Item {stable_key}",
        "category": "sightseeing",
        "setting": setting,
        "start_time": start,
        "end_time": end,
        "est_cost": cost,
        "lat": 0.0,
        "lng": 0.0,
        "is_locked": locked,
        "travel_mode": travel_mode,
        "travel_minutes": travel_min,
    }


def make_draft(items: list[dict]) -> dict:
    return {"items": items, "summary": "test"}


def test_no_overlapping_items():
    """Items that touch at boundaries should not overlap."""
    items = [
        make_item("a", 1, 0, "09:00", "10:30"),
        make_item("b", 1, 1, "10:30", "12:00"),  # touches, does not overlap
    ]
    v = validate_schedule(make_draft(items))
    overlap = [x for x in v if x["code"] == "overlap"]
    assert len(overlap) == 0


def test_detects_overlap():
    """Items with overlapping times should be flagged."""
    items = [
        make_item("a", 1, 0, "09:00", "11:00"),
        make_item("b", 1, 1, "10:00", "12:00"),  # overlaps with a
    ]
    v = validate_schedule(make_draft(items))
    overlap = [x for x in v if x["code"] == "overlap"]
    assert len(overlap) == 1
    assert "overlap" in overlap[0]["detail"].lower()


def test_detects_start_after_end():
    """start_time must be before end_time."""
    items = [
        make_item("a", 1, 0, "10:00", "09:00"),  # invalid
    ]
    v = validate_schedule(make_draft(items))
    overlap = [x for x in v if x["code"] == "overlap"]
    assert len(overlap) == 1
    assert "start_time" in overlap[0]["detail"]


def test_travel_time_fits():
    """Travel time must fit in the gap between items."""
    items = [
        make_item("a", 1, 0, "09:00", "10:00", travel_min=15),
        make_item("b", 1, 1, "10:10", "11:10"),  # 10 min gap, needs 15 -> violation
    ]
    v = validate_schedule(make_draft(items))
    travel = [x for x in v if x["code"] == "travel_too_long"]
    assert len(travel) == 1


def test_travel_time_fits_ok():
    """Travel time fits when gap is sufficient."""
    items = [
        make_item("a", 1, 0, "09:00", "10:00", travel_min=15),
        make_item("b", 1, 1, "10:30", "11:30"),  # 30 min gap, needs 15 -> OK
    ]
    v = validate_schedule(make_draft(items))
    travel = [x for x in v if x["code"] == "travel_too_long"]
    assert len(travel) == 0


def test_day_active_time_limit():
    """Day active time should not exceed pace limit."""
    items = [
        make_item("a", 1, 0, "08:00", "20:00"),  # 12 hours
    ]
    # balanced limit is 10 hours (600 min), 12 hours = 720 min
    v = validate_schedule(make_draft(items), pace="balanced")
    day_long = [x for x in v if x["code"] == "day_too_long"]
    assert len(day_long) == 1


def test_day_active_time_within_limit():
    """Day active time within pace limit should pass."""
    items = [
        make_item("a", 1, 0, "09:00", "17:00"),  # 8 hours
    ]
    v = validate_schedule(make_draft(items), pace="balanced")
    day_long = [x for x in v if x["code"] == "day_too_long"]
    assert len(day_long) == 0


def test_total_cost_over_budget():
    """Total cost exceeding budget should be flagged."""
    items = [
        make_item("a", 1, 0, "09:00", "10:00", cost=6000),
        make_item("b", 1, 1, "10:00", "11:00", cost=6000),
    ]
    v = validate_schedule(make_draft(items), budget_total=10000)
    over = [x for x in v if x["code"] == "over_budget"]
    assert len(over) == 1


def test_total_cost_within_budget():
    """Total cost within budget should pass."""
    items = [
        make_item("a", 1, 0, "09:00", "10:00", cost=3000),
        make_item("b", 1, 1, "10:00", "11:00", cost=3000),
    ]
    v = validate_schedule(make_draft(items), budget_total=10000)
    over = [x for x in v if x["code"] == "over_budget"]
    assert len(over) == 0


def test_per_day_cap():
    """Per-day budget cap should be enforced."""
    items = [
        make_item("a", 1, 0, "09:00", "10:00", cost=6000),
    ]
    v = validate_schedule(make_draft(items), budget_per_day=5000)
    over = [x for x in v if x["code"] == "over_budget" and x.get("day_index") == 1]
    assert len(over) == 1


def test_locked_item_unchanged():
    """Locked items must not change time or position."""
    prev = [
        make_item("a", 1, 0, "09:00", "10:30", locked=True),
    ]
    curr = [
        make_item("a", 1, 0, "10:00", "11:30", locked=True),  # time changed
    ]
    v = validate_schedule(make_draft(curr), previous_items=prev)
    locked = [x for x in v if x["code"] == "locked_changed"]
    assert len(locked) == 1


def test_locked_item_unchanged_position():
    """Locked items must not change position."""
    prev = [
        make_item("a", 1, 0, "09:00", "10:30", locked=True),
    ]
    curr = [
        make_item("a", 1, 1, "09:00", "10:30", locked=True),  # position changed
    ]
    v = validate_schedule(make_draft(curr), previous_items=prev)
    locked = [x for x in v if x["code"] == "locked_changed"]
    assert len(locked) == 1


def test_unlocked_item_can_change():
    """Unlocked items can change freely."""
    prev = [
        make_item("a", 1, 0, "09:00", "10:30", locked=False),
    ]
    curr = [
        make_item("a", 1, 1, "10:00", "11:30", locked=False),
    ]
    v = validate_schedule(make_draft(curr), previous_items=prev)
    locked = [x for x in v if x["code"] == "locked_changed"]
    assert len(locked) == 0


def test_multi_day():
    """Validation works across multiple days."""
    items = [
        make_item("a", 1, 0, "09:00", "10:00"),
        make_item("b", 2, 0, "09:00", "11:00"),  # Day 2, 2 hours
    ]
    v = validate_schedule(make_draft(items), pace="balanced")
    day_long = [x for x in v if x["code"] == "day_too_long"]
    assert len(day_long) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])