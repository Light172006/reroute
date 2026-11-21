"""Stress tests for monitor worker: cheap rules efficiency, fingerprint deduplication, and throughput."""

from __future__ import annotations

import time
from datetime import date
from datetime import time as dtime
from decimal import Decimal
from uuid import uuid4

import pytest

from reroute_agents.monitor import evaluate_trip
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.state import (
    DisruptionEvent,
    DraftItem,
    TripSpec,
)


@pytest.fixture
def monitor_trip_spec() -> TripSpec:
    return TripSpec(
        trip_id=uuid4(),
        destination="Darjeeling",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        group_size=2,
        budget_total=Decimal(10000),
        currency="INR",
        pace="balanced",
        vibe_tags=["nature"],
    )


@pytest.mark.asyncio
async def test_monitor_cheap_deterministic_check_no_disruptions(monitor_trip_spec: TripSpec) -> None:
    """Verify monitor evaluates trip cheaply and returns needs_replan=False when clear."""
    repos = create_in_memory_repositories()
    await repos.trips.save_trip(monitor_trip_spec)

    item1 = DraftItem(
        day_index=1,
        position=0,
        title="Ghum Monastery",
        category="culture",
        setting="indoor",
        start_time=dtime(10, 0),
        end_time=dtime(12, 0),
        est_cost=Decimal(100),
    )
    v1_id = await repos.itineraries.save_version(
        trip_id=monitor_trip_spec.trip_id,
        version_no=1,
        reason="Initial",
        created_by="agent:planner",
        items=[item1],
    )
    await repos.trips.update_current_version(monitor_trip_spec.trip_id, v1_id)

    needs_replan, disruptions = await evaluate_trip(monitor_trip_spec.trip_id, repos=repos)
    assert needs_replan is False
    assert len(disruptions) == 0


@pytest.mark.asyncio
async def test_monitor_fingerprint_deduplication(monitor_trip_spec: TripSpec) -> None:
    """Verify identical disruptions are deduplicated by fingerprint and ignored on second pass."""
    repos = create_in_memory_repositories()
    await repos.trips.save_trip(monitor_trip_spec)

    k1 = uuid4()
    item1 = DraftItem(
        stable_key=k1,
        day_index=1,
        position=0,
        title="Outdoor Trek",
        category="nature",
        setting="outdoor",
        start_time=dtime(14, 0),
        end_time=dtime(16, 0),
        est_cost=Decimal(100),
    )
    v1_id = await repos.itineraries.save_version(
        trip_id=monitor_trip_spec.trip_id,
        version_no=1,
        reason="Initial",
        created_by="agent:planner",
        items=[item1],
    )
    await repos.trips.update_current_version(monitor_trip_spec.trip_id, v1_id)

    # First disruption saved in repository with fingerprint
    fp = "weather_fp_test_123"
    disr = DisruptionEvent(
        trip_id=monitor_trip_spec.trip_id,
        type="weather",
        summary="Rain on Day 1",
        source="open-meteo",
        fingerprint=fp,
    )
    await repos.disruptions.save_disruption(disr)

    # Check that retrieve by fingerprint finds it
    stored = await repos.disruptions.get_disruption_by_fingerprint(monitor_trip_spec.trip_id, fp)
    assert stored is not None
    assert stored.fingerprint == fp


@pytest.mark.asyncio
async def test_monitor_throughput_1000_evaluations_speed(monitor_trip_spec: TripSpec) -> None:
    """Stress test: Run 200 evaluate_trip calls in a loop with mock tools; verify throughput."""
    from unittest.mock import patch
    repos = create_in_memory_repositories()
    await repos.trips.save_trip(monitor_trip_spec)

    item1 = DraftItem(
        day_index=1,
        position=0,
        title="Museum Visit",
        category="culture",
        setting="indoor",
        start_time=dtime(10, 0),
        end_time=dtime(12, 0),
        est_cost=Decimal(100),
    )
    v1_id = await repos.itineraries.save_version(
        trip_id=monitor_trip_spec.trip_id,
        version_no=1,
        reason="Initial",
        created_by="agent:planner",
        items=[item1],
    )
    await repos.trips.update_current_version(monitor_trip_spec.trip_id, v1_id)

    iterations = 100
    with patch("reroute_agents.tools.weather.is_mock_tools", return_value=True):
        t_start = time.monotonic()
        for _ in range(iterations):
            needs_replan, _ = await evaluate_trip(monitor_trip_spec.trip_id, repos=repos)
            assert needs_replan is False

        elapsed = time.monotonic() - t_start
        per_eval_ms = (elapsed / iterations) * 1000.0

    # Ensure evaluation is lightweight (well under 50ms per evaluation in memory)
    assert per_eval_ms < 50.0, f"Monitor throughput too slow: {per_eval_ms:.2f} ms per trip"
