"""Unit tests for the background monitor worker and fingerprint deduplication."""

from datetime import date, time
from decimal import Decimal
from uuid import uuid4

import pytest

from reroute_agents.destinations.registry import load_seed_catalog_into_repository
from reroute_agents.monitor import evaluate_trip
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.state import DraftItem, TripSpec


@pytest.mark.asyncio
async def test_monitor_evaluates_trip_and_deduplicates() -> None:
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")

    trip_id = uuid4()
    spec = TripSpec(
        trip_id=trip_id,
        destination="Darjeeling",
        start_date=date(2026, 12, 12),
        end_date=date(2026, 12, 13),
        budget_total=Decimal(1000),
        currency="INR",
        pace="balanced",
    )
    await repos.trips.save_trip(spec)

    item = DraftItem(
        stable_key=uuid4(),
        day_index=1,
        position=0,
        title="Tiger Hill",
        category="nature",
        setting="outdoor",
        start_time=time(9, 0),
        end_time=time(11, 0),
        est_cost=Decimal(500),
    )

    v1_id = await repos.itineraries.save_version(
        trip_id=trip_id,
        version_no=1,
        reason="Initial plan",
        created_by="agent:planner",
        items=[item],
    )
    await repos.trips.update_current_version(trip_id, v1_id)

    # 1. Log an expense that creates a budget overrun (> 10% overrun)
    await repos.expenses.add_expense(trip_id, "food", Decimal(1500), "INR", "Expensive dinner")

    # First evaluation: cheap rule detects budget overrun
    needs_replan, disruptions = await evaluate_trip(trip_id, repos=repos)
    assert needs_replan is True
    assert len(disruptions) >= 1
    assert any(d.type == "budget_overrun" for d in disruptions)

    # Save disruption in repository (as replanner / impact_analyzer does)
    for d in disruptions:
        await repos.disruptions.save_disruption(d)

    # Second evaluation: fingerprint deduplication should suppress duplicate replan
    needs_replan_again, new_disruptions = await evaluate_trip(trip_id, repos=repos)
    assert needs_replan_again is False
    assert len(new_disruptions) == 0
