"""Invariant tests: Verifies immutability of unaffected and locked items, catalog integrity, and cost sums."""

from datetime import date, time
from decimal import Decimal
from uuid import uuid4

import pytest

from reroute_agents.destinations.registry import load_seed_catalog_into_repository
from reroute_agents.gateway import resume_replan, run_plan, run_replan
from reroute_agents.llm import FakeLLM
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.state import (
    DraftItem,
    InjectedSignals,
    TripSpec,
)


@pytest.mark.asyncio
async def test_replan_preserves_unaffected_items_byte_identical() -> None:
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")

    trip_id = uuid4()
    spec = TripSpec(
        trip_id=trip_id,
        destination="Darjeeling",
        start_date=date(2026, 12, 12),
        end_date=date(2026, 12, 14),
        budget_total=Decimal(20000),
        currency="INR",
        pace="balanced",
    )
    await repos.trips.save_trip(spec)

    # Initial plan
    async for _ in run_plan(uuid4(), trip_id, repos=repos, llm_override=FakeLLM()):
        pass

    v1 = await repos.itineraries.get_current_version(trip_id)
    assert v1 is not None
    v1_items = await repos.itineraries.get_version_items(v1["id"])

    # Disruption targeting Day 2 only
    injected_disruption = InjectedSignals(
        type="weather",
        day_index=2,
        params={"precip_prob": 0.95, "from": "09:00", "to": "18:00"},
    )

    replan_run_id = uuid4()
    async for _ in run_replan(
        replan_run_id,
        trip_id,
        injected=injected_disruption,
        repos=repos,
        llm_override=FakeLLM(),
    ):
        pass

    # Approve proposal
    async for _ in resume_replan(
        replan_run_id,
        decision="approve",
        repos=repos,
        llm_override=FakeLLM(),
    ):
        pass

    v2 = await repos.itineraries.get_current_version(trip_id)
    assert v2 is not None
    assert v2["version_no"] == 2
    v2_items = await repos.itineraries.get_version_items(v2["id"])

    # INVARIANT 1: Items on Day 1 and Day 3 (unaffected days) must be 100% byte-identical
    v1_unaffected = [it for it in v1_items if it.day_index in (1, 3)]
    v2_by_key = {it.stable_key: it for it in v2_items}

    for before_it in v1_unaffected:
        after_it = v2_by_key.get(before_it.stable_key)
        assert after_it is not None, f"Item {before_it.title} was removed"
        assert before_it.model_dump() == after_it.model_dump(), (
            f"Item {before_it.title} was mutated even though Day {before_it.day_index} was unaffected!"
        )


@pytest.mark.asyncio
async def test_replan_locked_items_never_change() -> None:
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")

    trip_id = uuid4()
    spec = TripSpec(
        trip_id=trip_id,
        destination="Darjeeling",
        start_date=date(2026, 12, 12),
        end_date=date(2026, 12, 13),
        budget_total=Decimal(20000),
        currency="INR",
        pace="balanced",
    )
    await repos.trips.save_trip(spec)

    locked_key = uuid4()
    locked_item = DraftItem(
        stable_key=locked_key,
        day_index=1,
        position=0,
        title="Locked Sacred Site",
        category="culture",
        setting="indoor",
        start_time=time(10, 0),
        end_time=time(12, 0),
        est_cost=Decimal(500),
        is_locked=True,
    )
    mutable_item = DraftItem(
        stable_key=uuid4(),
        day_index=1,
        position=1,
        title="Outdoor Garden",
        category="nature",
        setting="outdoor",
        start_time=time(14, 0),
        end_time=time(16, 0),
        est_cost=Decimal(100),
        is_locked=False,
    )

    v1_id = await repos.itineraries.save_version(
        trip_id=trip_id,
        version_no=1,
        reason="Initial plan",
        created_by="agent:planner",
        items=[locked_item, mutable_item],
    )
    await repos.trips.update_current_version(trip_id, v1_id)

    # Disruption covering all of Day 1
    injected_weather = InjectedSignals(
        type="weather",
        day_index=1,
        params={"precip_prob": 0.95, "from": "09:00", "to": "18:00"},
    )

    replan_run_id = uuid4()
    async for _ in run_replan(
        replan_run_id,
        trip_id,
        injected=injected_weather,
        repos=repos,
        llm_override=FakeLLM(),
    ):
        pass

    async for _ in resume_replan(
        replan_run_id,
        decision="approve",
        repos=repos,
        llm_override=FakeLLM(),
    ):
        pass

    v2 = await repos.itineraries.get_current_version(trip_id)
    v2_items = await repos.itineraries.get_version_items(v2["id"])

    # INVARIANT 2: Locked item must remain completely identical
    v2_locked = next(it for it in v2_items if it.stable_key == locked_key)
    assert v2_locked.model_dump() == locked_item.model_dump()


@pytest.mark.asyncio
async def test_cost_sum_and_catalog_referential_integrity() -> None:
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")

    trip_id = uuid4()
    spec = TripSpec(
        trip_id=trip_id,
        destination="Darjeeling",
        start_date=date(2026, 12, 12),
        end_date=date(2026, 12, 13),
        budget_total=Decimal(15000),
        currency="INR",
        pace="balanced",
    )
    await repos.trips.save_trip(spec)

    async for _ in run_plan(uuid4(), trip_id, repos=repos, llm_override=FakeLLM()):
        pass

    curr_v = await repos.itineraries.get_current_version(trip_id)
    assert curr_v is not None
    items = await repos.itineraries.get_version_items(curr_v["id"])

    # INVARIANT 3: Total cost matches exact sum of items
    expected_sum = sum((it.est_cost for it in items), Decimal(0))
    assert curr_v["total_cost"] == expected_sum

    # INVARIANT 4: Every place_id referenced must exist in catalog repository
    for it in items:
        if it.place_id:
            place = await repos.places.get_place_by_id(it.place_id)
            assert place is not None, f"Item {it.title} references non-existent place {it.place_id}"
