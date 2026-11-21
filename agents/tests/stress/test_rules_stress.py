"""Stress tests for deterministic validator and impact rules engine.

Covers Section 4.1:
- Property-based testing via Hypothesis
- Boundary conditions (weather precip 0.59 vs 0.60, budget 9.99% vs 10.0%, delay 29 vs 30 min, pace limits)
- Region rules (Leh altitude acclimatization, seasonal road closures, permits)
- Strict determinism (1,000 runs, order invariance)
- Garbage/adversarial inputs (negative costs, inverted times, 500 items, huge strings)
"""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from uuid import uuid4

from hypothesis import HealthCheck, given, settings
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


def create_spec(
    budget: float = 15000.0,
    pace: str = "balanced",
    per_day_cap: float | None = None,
    destination: str = "Darjeeling",
) -> TripSpec:
    return TripSpec(
        trip_id=uuid4(),
        destination=destination,
        start_date=date(2026, 12, 12),
        end_date=date(2026, 12, 14),
        group_size=2,
        budget_total=Decimal(str(budget)),
        budget_per_day_cap=Decimal(str(per_day_cap)) if per_day_cap is not None else None,
        currency="INR",
        pace=pace,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# 1. Hypothesis Property-Based Tests
# ---------------------------------------------------------------------------


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    num_items=st.integers(min_value=1, max_value=4),
    base_cost=st.integers(min_value=10, max_value=300),
    start_hour=st.integers(min_value=8, max_value=14),
    item_dur=st.integers(min_value=30, max_value=90),
    gap_min=st.integers(min_value=20, max_value=60),
)
def test_hypothesis_valid_itineraries_property(
    num_items: int,
    base_cost: int,
    start_hour: int,
    item_dur: int,
    gap_min: int,
) -> None:
    """Property: any constructed non-overlapping, in-budget itinerary returns 0 fatal violations."""
    spec = create_spec(budget=50000.0, pace="packed")
    items: list[DraftItem] = []
    curr_m = start_hour * 60

    for i in range(num_items):
        s_time = time(curr_m // 60, curr_m % 60)
        end_m = curr_m + item_dur
        if end_m >= 24 * 60:
            break
        e_time = time(end_m // 60, end_m % 60)
        travel = 15 if i > 0 else 0
        items.append(
            DraftItem(
                stable_key=uuid4(),
                day_index=1,
                position=i,
                title=f"Valid Stop {i}",
                category="sightseeing",
                setting="indoor",
                start_time=s_time,
                end_time=e_time,
                est_cost=Decimal(base_cost),
                travel_minutes=travel,
            )
        )
        curr_m = end_m + gap_min  # Gap exceeds travel time

    violations = validate_itinerary(items, spec)
    fatal_codes = {"overlap", "travel_too_long", "over_budget", "locked_changed"}
    assert not any(v.code in fatal_codes for v in violations)


def test_reverse_planted_violations_detected() -> None:
    """Check reverse: planting each specific violation type must be detected."""
    spec = create_spec(budget=1000.0, per_day_cap=600.0, pace="relaxed")  # 480 min cap

    # 1. Overlap plant
    it_overlap1 = DraftItem(
        day_index=1,
        position=0,
        title="Stop 1",
        category="sightseeing",
        setting="indoor",
        start_time=time(9, 0),
        end_time=time(11, 0),
        est_cost=Decimal(100),
    )
    it_overlap2 = DraftItem(
        day_index=1,
        position=1,
        title="Stop 2",
        category="sightseeing",
        setting="indoor",
        start_time=time(10, 30),  # Overlaps with stop 1
        end_time=time(12, 0),
        est_cost=Decimal(100),
    )
    v_overlap = validate_itinerary([it_overlap1, it_overlap2], spec)
    assert any(v.code == "overlap" for v in v_overlap)

    # 2. Travel too long plant (10 min gap, 30 min travel)
    it_travel1 = DraftItem(
        day_index=1,
        position=0,
        title="Stop 1",
        category="sightseeing",
        setting="indoor",
        start_time=time(9, 0),
        end_time=time(10, 0),
        est_cost=Decimal(100),
    )
    it_travel2 = DraftItem(
        day_index=1,
        position=1,
        title="Stop 2",
        category="sightseeing",
        setting="indoor",
        start_time=time(10, 10),
        end_time=time(11, 0),
        est_cost=Decimal(100),
        travel_minutes=30,  # Exceeds 10 min gap
    )
    v_travel = validate_itinerary([it_travel1, it_travel2], spec)
    assert any(v.code == "travel_too_long" for v in v_travel)

    # 3. Budget total overrun plant
    it_expensive = DraftItem(
        day_index=1,
        position=0,
        title="Expensive Stop",
        category="sightseeing",
        setting="indoor",
        start_time=time(9, 0),
        end_time=time(10, 0),
        est_cost=Decimal(1500),  # > 1000 budget
    )
    v_budget = validate_itinerary([it_expensive], spec)
    assert any(v.code == "over_budget" for v in v_budget)

    # 4. Locked item changed plant
    k_locked = uuid4()
    base_locked = DraftItem(
        stable_key=k_locked,
        day_index=1,
        position=0,
        title="Locked Original",
        category="culture",
        setting="indoor",
        start_time=time(9, 0),
        end_time=time(11, 0),
        is_locked=True,
    )
    modified_locked = base_locked.model_copy(update={"start_time": time(9, 30)})
    v_locked = validate_itinerary([modified_locked], spec, base_items=[base_locked])
    assert any(v.code == "locked_changed" for v in v_locked)

    # 5. Day too long plant (relaxed pace limit = 480 min)
    it_long1 = DraftItem(
        day_index=1,
        position=0,
        title="Long 1",
        category="sightseeing",
        setting="indoor",
        start_time=time(8, 0),
        end_time=time(12, 0),
        est_cost=Decimal(100),
    )
    it_long2 = DraftItem(
        day_index=1,
        position=1,
        title="Long 2",
        category="sightseeing",
        setting="indoor",
        start_time=time(13, 0),
        end_time=time(18, 0),  # 08:00 to 18:00 = 600 min > 480 min
        est_cost=Decimal(100),
    )
    v_long = validate_itinerary([it_long1, it_long2], spec)
    assert any(v.code == "day_too_long" for v in v_long)


# ---------------------------------------------------------------------------
# 2. Strict Boundary Tests
# ---------------------------------------------------------------------------


def test_boundary_weather_precipitation() -> None:
    """Precipitation probability boundary: 0.59 (no disruption) vs 0.60 (disruption detected)."""
    spec = create_spec()
    item = DraftItem(
        day_index=1,
        position=0,
        title="Outdoor Viewpoint",
        category="nature",
        setting="outdoor",
        start_time=time(13, 0),
        end_time=time(15, 0),
    )

    # 0.59 precip prob -> Below threshold
    sig_59 = Signals(
        injected=InjectedSignals(
            type="weather",
            day_index=1,
            params={"precip_prob": 0.59, "from": "12:00", "to": "16:00"},
        )
    )
    d_59 = analyze_impacts([item], spec, sig_59)
    assert len(d_59) == 0

    # 0.60 precip prob -> At exact threshold
    sig_60 = Signals(
        injected=InjectedSignals(
            type="weather",
            day_index=1,
            params={"precip_prob": 0.60, "from": "12:00", "to": "16:00"},
        )
    )
    d_60 = analyze_impacts([item], spec, sig_60)
    assert len(d_60) == 1
    assert item.stable_key in d_60[0].affected_stable_keys


def test_boundary_budget_overrun() -> None:
    """Budget overrun boundary: 9.99% (no disruption) vs 10.00% (disruption detected)."""
    spec = create_spec(budget=1000.0)
    item = DraftItem(
        day_index=1,
        position=0,
        title="Sight",
        category="sightseeing",
        setting="indoor",
        start_time=time(10, 0),
        end_time=time(12, 0),
        est_cost=Decimal(500),
    )

    # 9.99% overrun
    sig_999 = Signals(
        injected=InjectedSignals(
            type="budget_overrun",
            day_index=1,
            params={"overrun_pct": 0.0999},
        )
    )
    assert len(analyze_impacts([item], spec, sig_999)) == 0

    # 10.00% overrun
    sig_1000 = Signals(
        injected=InjectedSignals(
            type="budget_overrun",
            day_index=1,
            params={"overrun_pct": 0.1000},
        )
    )
    d_100 = analyze_impacts([item], spec, sig_1000)
    assert len(d_100) == 1
    assert d_100[0].type == "budget_overrun"


def test_boundary_travel_delay() -> None:
    """Travel delay boundary: 29 min (no disruption) vs 30 min (disruption detected)."""
    spec = create_spec()
    it1 = DraftItem(
        day_index=1,
        position=0,
        title="Stop 1",
        category="sightseeing",
        setting="indoor",
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    it2 = DraftItem(
        day_index=1,
        position=1,
        title="Stop 2",
        category="sightseeing",
        setting="indoor",
        start_time=time(11, 0),
        end_time=time(12, 0),
    )

    sig_29 = Signals(
        injected=InjectedSignals(
            type="delay",
            day_index=1,
            params={"delay_minutes": 29},
        )
    )
    assert len(analyze_impacts([it1, it2], spec, sig_29)) == 0

    sig_30 = Signals(
        injected=InjectedSignals(
            type="delay",
            day_index=1,
            params={"delay_minutes": 30},
        )
    )
    d_30 = analyze_impacts([it1, it2], spec, sig_30)
    assert len(d_30) == 1
    assert it2.stable_key in d_30[0].affected_stable_keys


def test_boundary_pace_active_duration() -> None:
    """Pace duration limit: exactly 480 min is valid; 481 min flags day_too_long."""
    spec = create_spec(pace="relaxed")  # 480 min cap

    # 09:00 to 17:00 = 8h = 480 min exactly
    it_exact = DraftItem(
        day_index=1,
        position=0,
        title="Exact 8h",
        category="sightseeing",
        setting="indoor",
        start_time=time(9, 0),
        end_time=time(17, 0),
        est_cost=Decimal(100),
    )
    v_exact = validate_itinerary([it_exact], spec)
    assert not any(v.code == "day_too_long" for v in v_exact)

    # 09:00 to 17:01 = 481 min -> exceeds limit
    it_over = DraftItem(
        day_index=1,
        position=0,
        title="Over 8h",
        category="sightseeing",
        setting="indoor",
        start_time=time(9, 0),
        end_time=time(17, 1),
        est_cost=Decimal(100),
    )
    v_over = validate_itinerary([it_over], spec)
    assert any(v.code == "day_too_long" for v in v_over)


def test_boundary_item_abutting_no_gap() -> None:
    """Item ending exactly when next starts (end == start): valid if travel 0, invalid if travel > 0."""
    spec = create_spec()
    it1 = DraftItem(
        day_index=1,
        position=0,
        title="Stop 1",
        category="sightseeing",
        setting="indoor",
        start_time=time(9, 0),
        end_time=time(10, 0),
        est_cost=Decimal(100),
    )
    # Consecutive stop starts at exactly 10:00 with 0 travel
    it2_zero_travel = DraftItem(
        day_index=1,
        position=1,
        title="Stop 2 (Adjacent)",
        category="sightseeing",
        setting="indoor",
        start_time=time(10, 0),
        end_time=time(11, 0),
        est_cost=Decimal(100),
        travel_minutes=0,
    )
    v_zero = validate_itinerary([it1, it2_zero_travel], spec)
    assert not any(v.code in ("overlap", "travel_too_long") for v in v_zero)

    # Same consecutive stop but requires 5 min travel -> travel gap violation
    it2_travel = it2_zero_travel.model_copy(update={"travel_minutes": 5})
    v_travel = validate_itinerary([it1, it2_travel], spec)
    assert any(v.code == "travel_too_long" for v in v_travel)


def test_boundary_midnight_and_late_hours() -> None:
    """Handling items near or at end of day."""
    spec = create_spec(pace="packed")
    it_late = DraftItem(
        day_index=1,
        position=0,
        title="Night Stroll",
        category="nightlife",
        setting="outdoor",
        start_time=time(22, 0),
        end_time=time(23, 59),
        est_cost=Decimal(50),
    )
    violations = validate_itinerary([it_late], spec)
    assert not any(v.code in ("overlap", "day_too_long") for v in violations)


# ---------------------------------------------------------------------------
# 3. Regional Rules (Altitude, Seasonal, Permits)
# ---------------------------------------------------------------------------


def test_regional_altitude_acclimatization_thresholds() -> None:
    """Test Leh arrival day altitude gain limit (>1000m/day triggers day_too_long with medical disclaimer)."""
    p_leh = uuid4()
    p_pangong = uuid4()
    meta = {
        p_leh: {"raw": {"altitude_m": 3500}},
        p_pangong: {"raw": {"altitude_m": 4350}},  # Gain of 850m
    }

    # Day 1 Leh arrivals strenuous trek
    it_d1_trek = DraftItem(
        day_index=1,
        position=0,
        place_id=p_leh,
        title="Strenuous High Pass Trek",
        category="adventure",
        setting="outdoor",
        start_time=time(9, 0),
        end_time=time(12, 0),
    )
    v_d1 = check_altitude_acclimatization({1: [it_d1_trek]}, meta)
    assert len(v_d1) == 1
    assert v_d1[0].code == "day_too_long"
    assert "guidance, not medical advice" in v_d1[0].detail.lower()

    # Gain > 1000m on Day 1
    p_super_high = uuid4()
    meta[p_super_high] = {"raw": {"altitude_m": 4600}}  # 4600 - 3500 = 1100m > 1000m
    it_d1_climb = DraftItem(
        day_index=1,
        position=1,
        place_id=p_super_high,
        title="Khardung La Pass View",
        category="sightseeing",
        setting="outdoor",
        start_time=time(13, 0),
        end_time=time(15, 0),
    )
    v_climb = check_altitude_acclimatization({1: [it_d1_trek, it_d1_climb]}, meta)
    assert any("altitude gain" in v.detail.lower() for v in v_climb)


def test_regional_altitude_intra_day_boundaries() -> None:
    """Test boundary conditions for intra-day altitude gains on arrival day."""
    p_base = uuid4()
    p_under = uuid4()
    p_over = uuid4()
    p_none = uuid4()

    meta = {
        p_base: {"raw": {"altitude_m": 1500}},
        p_under: {"raw": {"altitude_m": 2450}},  # 950m gain (<= 1000m threshold)
        p_over: {"raw": {"altitude_m": 2550}},  # 1050m gain (> 1000m threshold)
        p_none: {"raw": {"altitude_m": None}},
    }

    it_base = DraftItem(
        day_index=1,
        position=0,
        place_id=p_base,
        title="Valley Base",
        category="cultural",
        setting="indoor",
        start_time=time(9, 0),
        end_time=time(11, 0),
    )
    it_under = DraftItem(
        day_index=1,
        position=1,
        place_id=p_under,
        title="Mid Ridge",
        category="cultural",
        setting="indoor",
        start_time=time(12, 0),
        end_time=time(14, 0),
    )
    it_over = DraftItem(
        day_index=1,
        position=1,
        place_id=p_over,
        title="High Ridge",
        category="cultural",
        setting="indoor",
        start_time=time(12, 0),
        end_time=time(14, 0),
    )
    it_none = DraftItem(
        day_index=1,
        position=1,
        place_id=p_none,
        title="Unknown Alt Stop",
        category="cultural",
        setting="indoor",
        start_time=time(12, 0),
        end_time=time(14, 0),
    )

    # 1. 950m gain on Day 1 -> No violation
    v_under = check_altitude_acclimatization({1: [it_base, it_under]}, meta)
    assert len(v_under) == 0

    # 2. 1050m gain on Day 1 -> Violation with medical disclaimer
    v_over = check_altitude_acclimatization({1: [it_base, it_over]}, meta)
    assert len(v_over) == 1
    assert v_over[0].code == "day_too_long"
    assert "intra-day altitude gain of 1050m" in v_over[0].detail.lower()
    assert "guidance, not medical advice" in v_over[0].detail.lower()

    # 3. Stop with altitude None does not crash or falsely trigger
    v_none = check_altitude_acclimatization({1: [it_base, it_none]}, meta)
    assert len(v_none) == 0

    # 4. Descent on Day 1 (2550m down to 1500m) -> No intra-day gain violation
    it_descend_start = DraftItem(
        day_index=1,
        position=0,
        place_id=p_over,
        title="High Pass Descent Start",
        category="cultural",
        setting="indoor",
        start_time=time(9, 0),
        end_time=time(11, 0),
    )
    it_descend_end = DraftItem(
        day_index=1,
        position=1,
        place_id=p_base,
        title="Valley Floor",
        category="cultural",
        setting="indoor",
        start_time=time(12, 0),
        end_time=time(14, 0),
    )
    v_descend = check_altitude_acclimatization({1: [it_descend_start, it_descend_end]}, meta)
    assert not any("intra-day altitude gain" in v.detail.lower() for v in v_descend)


@given(st.lists(st.integers(min_value=500, max_value=5500), min_size=2, max_size=6))
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_regional_altitude_monotonic_descent_never_triggers_gain_violation(altitudes: list[int]) -> None:
    """Property test: Monotonically decreasing altitudes never produce an intra-day gain violation."""
    sorted_alts = sorted(altitudes, reverse=True)
    meta = {}
    items = []
    for idx, alt in enumerate(sorted_alts):
        pid = uuid4()
        meta[pid] = {"raw": {"altitude_m": alt}}
        items.append(
            DraftItem(
                day_index=1,
                position=idx,
                place_id=pid,
                title=f"Stop {idx}",
                category="cultural",
                setting="indoor",
                start_time=time(8 + idx, 0),
                end_time=time(8 + idx, 45),
            )
        )
    violations = check_altitude_acclimatization({1: items}, meta)
    gain_violations = [v for v in violations if "intra-day altitude gain" in v.detail.lower()]
    assert len(gain_violations) == 0


def test_regional_seasonal_access_closures() -> None:
    """Test seasonal road and pass closures (monsoon and winter)."""
    p_sela = uuid4()
    # Sela Pass closed in winter (Dec - Mar)
    meta = {
        p_sela: {
            "raw": {
                "seasonal_access": {
                    "open_months": [4, 5, 6, 7, 8, 9, 10, 11],
                    "closed_windows": [
                        {"from_month": 12, "to_month": 3, "reason": "Heavy snow on pass"}
                    ],
                }
            }
        }
    }
    it_pass = DraftItem(
        day_index=1,
        position=0,
        place_id=p_sela,
        title="Sela Pass Crossing",
        category="sightseeing",
        setting="outdoor",
        start_time=time(10, 0),
        end_time=time(12, 0),
    )

    # Travel date in December (month 12) -> closed
    v_dec = check_seasonal_access({1: [it_pass]}, meta, trip_start_date=date(2026, 12, 15))
    assert len(v_dec) >= 1
    assert v_dec[0].code == "closed"
    assert "seasonal" in v_dec[0].detail.lower()

    # Travel date in May (month 5) -> open
    v_may = check_seasonal_access({1: [it_pass]}, meta, trip_start_date=date(2026, 5, 15))
    assert len(v_may) == 0


def test_regional_permit_rules() -> None:
    """Test permit detection and disclaimer formatting."""
    p_tawang = uuid4()
    meta = {
        p_tawang: {
            "raw": {
                "permit_required": True,
                "permit_notes": "Inner Line Permit (ILP) required for Arunachal Pradesh.",
                "permit_office_closed": True,
            }
        }
    }
    it = DraftItem(
        day_index=1,
        position=0,
        place_id=p_tawang,
        title="Tawang Monastery",
        category="culture",
        setting="indoor",
        start_time=time(10, 0),
        end_time=time(12, 0),
    )
    violations, summaries = check_permits({1: [it]}, meta)
    assert len(violations) == 1
    assert violations[0].code == "closed"
    assert len(summaries) >= 1
    assert "permit" in summaries[0].lower()
    assert "verify with official government sources" in summaries[0].lower()


# ---------------------------------------------------------------------------
# 4. Determinism & Invariance Tests
# ---------------------------------------------------------------------------


def test_determinism_1000_runs() -> None:
    """Same input evaluated 1,000 times gives byte-identical violations."""
    spec = create_spec(budget=1000.0, pace="relaxed")
    items = [
        DraftItem(
            day_index=1,
            position=0,
            title="Stop 1",
            category="sightseeing",
            setting="indoor",
            start_time=time(9, 0),
            end_time=time(11, 0),
            est_cost=Decimal(600),
        ),
        DraftItem(
            day_index=1,
            position=1,
            title="Stop 2 Overlap",
            category="sightseeing",
            setting="indoor",
            start_time=time(10, 0),
            end_time=time(12, 0),
            est_cost=Decimal(500),
        ),
    ]

    base_res = validate_itinerary(items, spec)
    base_repr = [v.model_dump() for v in base_res]

    for _ in range(1000):
        res = validate_itinerary(items, spec)
        assert [v.model_dump() for v in res] == base_repr


def test_determinism_input_order_shuffled() -> None:
    """Input items in different order yields equivalent violation set."""
    spec = create_spec(budget=500.0)
    it1 = DraftItem(
        day_index=1,
        position=0,
        title="A",
        category="sightseeing",
        setting="indoor",
        start_time=time(9, 0),
        end_time=time(10, 0),
        est_cost=Decimal(300),
    )
    it2 = DraftItem(
        day_index=1,
        position=1,
        title="B",
        category="sightseeing",
        setting="indoor",
        start_time=time(9, 30),
        end_time=time(11, 0),
        est_cost=Decimal(300),
    )

    v_order1 = validate_itinerary([it1, it2], spec)
    v_order2 = validate_itinerary([it2, it1], spec)

    codes1 = sorted([v.code for v in v_order1])
    codes2 = sorted([v.code for v in v_order2])
    assert codes1 == codes2


def test_disruption_fingerprint_order_invariance() -> None:
    """Fingerprint computation produces identical hashes regardless of key ordering."""
    k1, k2, k3 = uuid4(), uuid4(), uuid4()
    fp1 = compute_disruption_fingerprint("weather", 2, [k1, k2, k3])
    fp2 = compute_disruption_fingerprint("weather", 2, [k3, k1, k2])
    fp3 = compute_disruption_fingerprint("weather", 2, [k2, k3, k1])
    assert fp1 == fp2 == fp3


# ---------------------------------------------------------------------------
# 5. Garbage In & Adversarial Input Robustness
# ---------------------------------------------------------------------------


def test_garbage_inputs_no_crash() -> None:
    """Rules must handle extreme or malformed inputs cleanly without unhandled exceptions."""
    spec = create_spec(budget=10000.0)

    # 1. Empty itinerary
    assert validate_itinerary([], spec) == []

    # 2. 500 items in a single day
    items_500 = [
        DraftItem(
            day_index=1,
            position=i,
            title=f"Stop {i}",
            category="sightseeing",
            setting="indoor",
            start_time=time(9, 0),
            end_time=time(9, 1),
            est_cost=Decimal(10),
        )
        for i in range(500)
    ]
    v_500 = validate_itinerary(items_500, spec)
    assert len(v_500) > 0  # Flags overlaps

    # 3. Inverted times (end before start)
    it_inverted = DraftItem(
        day_index=1,
        position=0,
        title="Time Machine",
        category="sightseeing",
        setting="indoor",
        start_time=time(17, 0),
        end_time=time(10, 0),  # End < Start
        est_cost=Decimal(100),
    )
    v_inv = validate_itinerary([it_inverted], spec)
    assert any(v.code == "overlap" for v in v_inv)

    # 4. Massive strings (100,000 characters)
    huge_title = "A" * 100000
    it_huge = DraftItem(
        day_index=1,
        position=0,
        title=huge_title,
        category="custom_unknown",
        setting="mixed",
        start_time=time(9, 0),
        end_time=time(10, 0),
        est_cost=Decimal(100),
    )
    v_huge = validate_itinerary([it_huge], spec)
    assert isinstance(v_huge, list)
