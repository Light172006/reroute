"""Comprehensive unit tests for deterministic validator and impact rules."""

from datetime import date, time
from decimal import Decimal
from uuid import uuid4

from hypothesis import given
from hypothesis import strategies as st

from reroute_agents.rules.altitude import check_altitude_acclimatization
from reroute_agents.rules.impact_rules import analyze_impacts, compute_disruption_fingerprint
from reroute_agents.rules.permits import check_permits
from reroute_agents.rules.seasonal import check_seasonal_access
from reroute_agents.rules.validator_rules import validate_itinerary
from reroute_agents.state import (
    DraftItem,
    InjectedSignals,
    Signals,
    TripSpec,
)


def create_sample_spec(
    budget: float = 15000.0,
    pace: str = "balanced",
    cap: float | None = None,
) -> TripSpec:
    return TripSpec(
        trip_id=uuid4(),
        destination="Darjeeling",
        start_date=date(2026, 12, 12),
        end_date=date(2026, 12, 14),
        group_size=2,
        budget_total=Decimal(str(budget)),
        currency="INR",
        pace=pace,  # type: ignore[arg-type]
        budget_per_day_cap=Decimal(str(cap)) if cap else None,
    )


def test_validator_happy_path() -> None:
    spec = create_sample_spec(budget=10000)
    p1 = uuid4()
    p2 = uuid4()

    meta = {
        p1: {
            "hours_confidence": "verified",
            "opening_hours": {"sat": [["09:00", "18:00"]]},
        },
        p2: {
            "hours_confidence": "verified",
            "opening_hours": {"sat": [["10:00", "20:00"]]},
        },
    }

    item1 = DraftItem(
        day_index=1,
        position=0,
        place_id=p1,
        title="Place 1",
        category="sightseeing",
        setting="indoor",
        start_time=time(10, 0),
        end_time=time(12, 0),
        est_cost=Decimal(500),
    )
    item2 = DraftItem(
        day_index=1,
        position=1,
        place_id=p2,
        title="Place 2",
        category="food",
        setting="indoor",
        start_time=time(12, 30),
        end_time=time(14, 0),
        est_cost=Decimal(600),
        travel_minutes=20,
    )

    violations = validate_itinerary([item1, item2], spec, places_metadata=meta)
    assert len(violations) == 0


def test_validator_overlap_and_travel_gap() -> None:
    spec = create_sample_spec()
    # Case A: start >= end
    bad_time_item = DraftItem(
        day_index=1,
        position=0,
        title="Invalid Item",
        category="sightseeing",
        setting="indoor",
        start_time=time(14, 0),
        end_time=time(13, 0),
        est_cost=Decimal(100),
    )
    v1 = validate_itinerary([bad_time_item], spec)
    assert any(v.code == "overlap" for v in v1)

    # Case B: overlap between items
    item1 = DraftItem(
        day_index=1,
        position=0,
        title="Item 1",
        category="sightseeing",
        setting="indoor",
        start_time=time(10, 0),
        end_time=time(12, 0),
        est_cost=Decimal(100),
    )
    item2 = DraftItem(
        day_index=1,
        position=1,
        title="Item 2",
        category="sightseeing",
        setting="indoor",
        start_time=time(11, 30),
        end_time=time(13, 0),
        est_cost=Decimal(100),
    )
    v2 = validate_itinerary([item1, item2], spec)
    assert any(v.code == "overlap" for v in v2)

    # Case C: travel gap too short
    item3 = DraftItem(
        day_index=1,
        position=1,
        title="Item 3",
        category="sightseeing",
        setting="indoor",
        start_time=time(12, 10),
        end_time=time(13, 0),
        est_cost=Decimal(100),
        travel_minutes=30,  # 10 min gap < 30 min travel
    )
    v3 = validate_itinerary([item1, item3], spec)
    assert any(v.code == "travel_too_long" for v in v3)


def test_validator_budget_boundaries() -> None:
    spec = create_sample_spec(budget=1000, cap=600)
    item1 = DraftItem(
        day_index=1,
        position=0,
        title="Item 1",
        category="sightseeing",
        setting="indoor",
        start_time=time(10, 0),
        end_time=time(11, 0),
        est_cost=Decimal("600.01"),  # Exceeds day cap
    )
    v1 = validate_itinerary([item1], spec)
    assert any(v.code == "over_budget" for v in v1)

    item_ok = DraftItem(
        day_index=1,
        position=0,
        title="Item 1",
        category="sightseeing",
        setting="indoor",
        start_time=time(10, 0),
        end_time=time(11, 0),
        est_cost=Decimal("600.00"),  # Exactly on day cap
    )
    item_day2 = DraftItem(
        day_index=2,
        position=0,
        title="Item 2",
        category="sightseeing",
        setting="indoor",
        start_time=time(10, 0),
        end_time=time(11, 0),
        est_cost=Decimal("400.01"),  # Total is 1000.01 > 1000
    )
    v2 = validate_itinerary([item_ok, item_day2], spec)
    assert any(v.code == "over_budget" and v.day_index is None for v in v2)


def test_validator_locked_items() -> None:
    spec = create_sample_spec()
    locked_key = uuid4()
    base_item = DraftItem(
        stable_key=locked_key,
        day_index=1,
        position=0,
        title="Locked Monastery",
        category="culture",
        setting="indoor",
        start_time=time(9, 0),
        end_time=time(11, 0),
        is_locked=True,
    )

    # Modified time
    mod_item = base_item.model_copy(update={"start_time": time(9, 30)})
    v1 = validate_itinerary([mod_item], spec, base_items=[base_item])
    assert any(v.code == "locked_changed" for v in v1)

    # Missing entirely
    v2 = validate_itinerary([], spec, base_items=[base_item])
    assert any(v.code == "locked_changed" for v in v2)

    # Unchanged
    v3 = validate_itinerary([base_item], spec, base_items=[base_item])
    assert not any(v.code == "locked_changed" for v in v3)


def test_validator_pace_limits() -> None:
    spec = create_sample_spec(pace="relaxed")  # 480 min limit
    # Start at 08:00, end at 17:00 = 9h = 540 min > 480 min
    item1 = DraftItem(
        day_index=1,
        position=0,
        title="Item 1",
        category="sightseeing",
        setting="indoor",
        start_time=time(8, 0),
        end_time=time(12, 0),
    )
    item2 = DraftItem(
        day_index=1,
        position=1,
        title="Item 2",
        category="sightseeing",
        setting="indoor",
        start_time=time(13, 0),
        end_time=time(17, 0),
    )
    violations = validate_itinerary([item1, item2], spec)
    assert any(v.code == "day_too_long" for v in violations)


def test_altitude_acclimatization_rules() -> None:
    p_leh = uuid4()
    p_pangong = uuid4()
    meta = {
        p_leh: {"raw": {"altitude_m": 3500}},
        p_pangong: {"raw": {"altitude_m": 4350}},
    }

    # Day 1 strenuous in Leh (> 3000m)
    item_d1 = DraftItem(
        day_index=1,
        position=0,
        place_id=p_leh,
        title="Trek Leh",
        category="adventure",
        setting="outdoor",
        start_time=time(9, 0),
        end_time=time(12, 0),
    )
    v1 = check_altitude_acclimatization({1: [item_d1]}, meta)
    assert len(v1) == 1
    assert v1[0].code == "day_too_long"
    assert "not medical advice" in v1[0].detail

    # Jump from 2000m to 3500m (1500m gain > 1000m threshold)
    p_kalka = uuid4()
    meta[p_kalka] = {"raw": {"altitude_m": 1500}}
    item_d1_low = DraftItem(
        day_index=1,
        position=0,
        place_id=p_kalka,
        title="Low Valley",
        category="sightseeing",
        setting="indoor",
        start_time=time(9, 0),
        end_time=time(12, 0),
    )
    item_d2_high = DraftItem(
        day_index=2,
        position=0,
        place_id=p_leh,
        title="High Pass",
        category="sightseeing",
        setting="outdoor",
        start_time=time(9, 0),
        end_time=time(12, 0),
    )
    v2 = check_altitude_acclimatization({1: [item_d1_low], 2: [item_d2_high]}, meta)
    assert any("exceeds safe threshold" in v.detail for v in v2)


def test_seasonal_access_rules() -> None:
    p_pass = uuid4()
    meta = {
        p_pass: {
            "raw": {
                "seasonal_access": {
                    "open_months": [5, 6, 7, 8, 9, 10],
                    "closed_windows": [
                        {"from_month": 11, "to_month": 4, "reason": "Heavy snow on pass"}
                    ],
                }
            }
        }
    }
    item = DraftItem(
        day_index=1,
        position=0,
        place_id=p_pass,
        title="Sela Pass",
        category="nature",
        setting="outdoor",
        start_time=time(10, 0),
        end_time=time(12, 0),
    )
    # Trip date in December (month 12)
    v = check_seasonal_access({1: [item]}, meta, trip_start_date=date(2026, 12, 10))
    assert len(v) >= 1
    assert v[0].code == "closed"
    assert "seasonally" in v[0].detail or "seasonal window" in v[0].detail


def test_permit_rules() -> None:
    p_tawang = uuid4()
    meta = {
        p_tawang: {
            "raw": {
                "permit_required": True,
                "permit_notes": "Inner Line Permit required for Arunachal Pradesh.",
                "permit_office_closed": True,
            }
        }
    }
    item = DraftItem(
        day_index=1,
        position=0,
        place_id=p_tawang,
        title="Tawang Monastery",
        category="culture",
        setting="indoor",
        start_time=time(10, 0),
        end_time=time(12, 0),
    )
    v, summaries = check_permits({1: [item]}, meta)
    assert len(v) == 1
    assert v[0].code == "closed"
    assert len(summaries) == 1
    assert "Inner Line Permit" in summaries[0]


def test_impact_weather_boundary() -> None:
    spec = create_sample_spec()
    item = DraftItem(
        day_index=2,
        position=0,
        title="Tiger Hill",
        category="nature",
        setting="outdoor",
        start_time=time(14, 0),
        end_time=time(16, 0),
    )

    # 0.59 precip_prob (Below 0.60 threshold)
    sig_low = Signals(
        injected=InjectedSignals(
            type="weather",
            day_index=2,
            params={"precip_prob": 0.59, "from": "13:00", "to": "17:00"},
        )
    )
    d_low = analyze_impacts([item], spec, sig_low)
    assert len(d_low) == 0

    # 0.60 precip_prob (At threshold)
    sig_at = Signals(
        injected=InjectedSignals(
            type="weather",
            day_index=2,
            params={"precip_prob": 0.60, "from": "13:00", "to": "17:00"},
        )
    )
    d_at = analyze_impacts([item], spec, sig_at)
    assert len(d_at) == 1
    assert d_at[0].type == "weather"
    assert item.stable_key in d_at[0].affected_stable_keys


def test_impact_delay_and_budget_boundaries() -> None:
    spec = create_sample_spec(budget=1000)
    it1 = DraftItem(
        day_index=1,
        position=0,
        title="Stop 1",
        category="sightseeing",
        setting="indoor",
        start_time=time(9, 0),
        end_time=time(10, 0),
        est_cost=Decimal(500),
    )
    it2 = DraftItem(
        day_index=1,
        position=1,
        title="Stop 2",
        category="sightseeing",
        setting="indoor",
        start_time=time(11, 0),
        end_time=time(12, 0),
        est_cost=Decimal(500),
    )

    # Delay boundary: 29 min (below 30 min threshold) vs 30 min (at threshold)
    sig_del_29 = Signals(
        injected=InjectedSignals(
            type="delay",
            day_index=1,
            params={"delay_minutes": 29},
        )
    )
    assert len(analyze_impacts([it1, it2], spec, sig_del_29)) == 0

    sig_del_30 = Signals(
        injected=InjectedSignals(
            type="delay",
            day_index=1,
            params={"delay_minutes": 30},
        )
    )
    d_del_30 = analyze_impacts([it1, it2], spec, sig_del_30)
    assert len(d_del_30) == 1
    assert it2.stable_key in d_del_30[0].affected_stable_keys

    # Budget overrun boundary: 9.99% (below 10% threshold) vs 10% (at threshold)
    sig_bg_9 = Signals(
        injected=InjectedSignals(
            type="budget_overrun",
            day_index=1,
            params={"overrun_pct": 0.0999},
        )
    )
    assert len(analyze_impacts([it1, it2], spec, sig_bg_9)) == 0

    sig_bg_10 = Signals(
        injected=InjectedSignals(
            type="budget_overrun",
            day_index=1,
            params={"overrun_pct": 0.10},
        )
    )
    d_bg_10 = analyze_impacts([it1, it2], spec, sig_bg_10)
    assert len(d_bg_10) == 1
    assert d_bg_10[0].type == "budget_overrun"


def test_compute_disruption_fingerprint() -> None:
    k1 = uuid4()
    k2 = uuid4()
    fp1 = compute_disruption_fingerprint("weather", 2, [k1, k2])
    fp2 = compute_disruption_fingerprint("weather", 2, [k2, k1])
    # Order-independent hash
    assert fp1 == fp2


# Hypothesis property-based test: Any randomly generated valid non-overlapping items under budget have 0 overlap violations
@given(
    costs=st.lists(st.integers(min_value=10, max_value=200), min_size=1, max_size=3),
    durations=st.lists(st.integers(min_value=30, max_value=90), min_size=3, max_size=3),
)
def test_hypothesis_valid_schedule_no_violations(costs: list[int], durations: list[int]) -> None:
    spec = create_sample_spec(budget=100000, pace="packed")
    items: list[DraftItem] = []
    current_m = 9 * 60  # Start at 09:00

    for i in range(len(costs)):
        dur = durations[i]
        start_t = time(current_m // 60, current_m % 60)
        end_m = current_m + dur
        end_t = time(end_m // 60, end_m % 60)
        items.append(
            DraftItem(
                day_index=1,
                position=i,
                title=f"Auto Place {i}",
                category="sightseeing",
                setting="indoor",
                start_time=start_t,
                end_time=end_t,
                est_cost=Decimal(costs[i]),
                travel_minutes=15 if i > 0 else 0,
            )
        )
        current_m = end_m + 20  # 20 min gap > 15 min travel

    violations = validate_itinerary(items, spec)
    assert not any(v.code in ("overlap", "travel_too_long", "over_budget") for v in violations)


def test_impact_weather_forecast_snow_and_visibility() -> None:
    spec = create_sample_spec()
    it1 = DraftItem(
        day_index=1,
        position=0,
        title="Pass Viewpoint",
        category="sightseeing",
        setting="outdoor",
        start_time=time(10, 0),
        end_time=time(12, 0),
    )
    # Forecast with snow and low visibility at 11:00
    forecast_data = {
        "1": {
            "hourly": [
                {
                    "hour": 11,
                    "precip_prob": 0.40,
                    "snowfall": 1.2,
                    "visibility": 500,
                }
            ]
        }
    }
    sig = Signals(weather_forecast=forecast_data)
    disruptions = analyze_impacts([it1], spec, sig)
    assert len(disruptions) == 1
    assert disruptions[0].type == "weather"
    assert disruptions[0].severity == "high"
    assert it1.stable_key in disruptions[0].affected_stable_keys
    assert disruptions[0].data.get("snow") is True
    assert disruptions[0].data.get("low_vis") is True


def test_impact_opening_hours_updates() -> None:
    spec = create_sample_spec()
    p_id = uuid4()
    it1 = DraftItem(
        day_index=1,
        position=0,
        place_id=p_id,
        title="Heritage Museum",
        category="culture",
        setting="indoor",
        start_time=time(14, 0),
        end_time=time(16, 0),
    )
    # Museum is closed on Day 1
    sig = Signals(opening_hours_updates={str(p_id): {"closed": True, "reason": "Restoration work"}})
    disruptions = analyze_impacts([it1], spec, sig)
    assert len(disruptions) == 1
    assert disruptions[0].type == "closure"
    assert it1.stable_key in disruptions[0].affected_stable_keys


def test_impact_actual_expenses_budget_overrun() -> None:
    spec = create_sample_spec(budget=1000)
    it1 = DraftItem(
        day_index=1,
        position=0,
        title="Sight 1",
        category="sightseeing",
        setting="indoor",
        start_time=time(10, 0),
        end_time=time(12, 0),
        est_cost=Decimal(500),
    )
    # Spent 1150 > 1000 * 1.10 (15% overrun)
    sig = Signals(
        expenses_summary={
            "actual_total": Decimal(1150),
            "planned_total": Decimal(1000),
            "overrun_pct": 0.15,
        }
    )
    disruptions = analyze_impacts([it1], spec, sig)
    assert len(disruptions) == 1
    assert disruptions[0].type == "budget_overrun"
