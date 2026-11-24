"""Seasonal access and road/pass closure validation rules."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from reroute_agents.state import DraftItem, Violation


def check_seasonal_access(
    items_by_day: dict[int, list[DraftItem]],
    places_metadata: dict[UUID, dict[str, Any]],
    trip_start_date: date,
) -> list[Violation]:
    """Check if any planned place or route is seasonally closed on the itinerary date."""
    violations: list[Violation] = []

    for day_index, day_items in items_by_day.items():
        # Calculate approximate date for day_index (1-based)
        from datetime import timedelta

        item_date = trip_start_date + timedelta(days=day_index - 1)
        month = item_date.month

        for item in day_items:
            if not item.place_id or item.place_id not in places_metadata:
                continue

            meta = places_metadata[item.place_id]
            raw = meta.get("raw", {})
            seasonal = raw.get("seasonal_access") or meta.get("seasonal_access")

            if not seasonal or not isinstance(seasonal, dict):
                continue

            # Check open_months (e.g. [4, 5, 6, 7, 8, 9, 10])
            open_months = seasonal.get("open_months")
            if open_months and month not in open_months:
                note = seasonal.get("note", f"Closed in month {month}")
                violations.append(
                    Violation(
                        code="closed",
                        day_index=day_index,
                        item_stable_key=item.stable_key,
                        detail=(
                            f"{item.title} is seasonally inaccessible in {item_date.strftime('%B')}. "
                            f"Reason: {note}. Verify with official regional sources before travel."
                        ),
                    )
                )

            # Check closed_windows (e.g. [{"from_month": 12, "to_month": 3}])
            closed_windows = seasonal.get("closed_windows", [])
            for window in closed_windows:
                from_m = window.get("from_month", 0)
                to_m = window.get("to_month", 0)
                is_closed = False
                if from_m <= to_m:
                    is_closed = from_m <= month <= to_m
                else:
                    # Year-wrapping window, e.g. December to March (12 to 3)
                    is_closed = month >= from_m or month <= to_m

                if is_closed:
                    note = window.get("reason", seasonal.get("note", "Seasonal road/pass closure"))
                    violations.append(
                        Violation(
                            code="closed",
                            day_index=day_index,
                            item_stable_key=item.stable_key,
                            detail=(
                                f"{item.title} is closed during the seasonal window ({from_m}-{to_m}). "
                                f"Reason: {note}. Verify with official regional sources before travel."
                            ),
                        )
                    )
                    break

    return violations
