"""Performance benchmark script for Reroute agents.

Measures latency (p50, p95) for:
- 1-day plan generation
- 7-day plan generation
- 14-day plan generation
- Replan on 14-day trip
- Call counts and token/budget estimation
"""

from __future__ import annotations

import asyncio
import json
import statistics
import time
from datetime import date, timedelta, time as dtime
from decimal import Decimal
from typing import Any
from unittest.mock import patch
from uuid import uuid4

from reroute_agents.destinations.registry import load_seed_catalog_into_repository
from reroute_agents.gateway import resume_replan, run_plan, run_replan
from reroute_agents.llm import FakeLLM
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.state import (
    DraftItem,
    InjectedSignals,
    ItineraryDraft,
    TripSpec,
)


def _generate_mock_draft(num_days: int) -> ItineraryDraft:
    items = []
    p1 = uuid4()
    p2 = uuid4()
    for d in range(1, num_days + 1):
        items.append(
            DraftItem(
                day_index=d,
                position=0,
                place_id=p1,
                title=f"Morning Sightseeing Day {d}",
                category="culture",
                setting="indoor",
                start_time=dtime(9, 30),
                end_time=dtime(11, 30),
                est_cost=Decimal(100),
            )
        )
        items.append(
            DraftItem(
                day_index=d,
                position=1,
                place_id=p2,
                title=f"Afternoon Excursion Day {d}",
                category="nature",
                setting="outdoor",
                start_time=dtime(14, 0),
                end_time=dtime(16, 0),
                est_cost=Decimal(150),
            )
        )
    return ItineraryDraft(items=items, summary=f"{num_days}-day itinerary")


async def benchmark_plan_duration(num_days: int, repetitions: int = 5) -> dict[str, Any]:
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")

    latencies: list[float] = []
    llm_calls_recorded: list[int] = []

    for _ in range(repetitions):
        trip_id = uuid4()
        run_id = uuid4()
        start = date(2026, 12, 1)
        end = start + timedelta(days=num_days - 1)
        spec = TripSpec(
            trip_id=trip_id,
            destination="Darjeeling",
            start_date=start,
            end_date=end,
            budget_total=Decimal(num_days * 3000),
            currency="INR",
            pace="balanced",
            vibe_tags=["culture", "nature"],
        )
        await repos.trips.save_trip(spec)

        mock_draft = _generate_mock_draft(num_days)
        fake_llm = FakeLLM(canned_responses={"ItineraryDraft": mock_draft})

        with patch("reroute_agents.tools.weather.is_mock_tools", return_value=True):
            t_start = time.monotonic()
            events = []
            async for evt in run_plan(
                run_id=run_id,
                trip_id=trip_id,
                repos=repos,
                llm_override=fake_llm,
            ):
                events.append(evt)
            elapsed_s = time.monotonic() - t_start

        latencies.append(elapsed_s)
        llm_calls_recorded.append(len(fake_llm.calls))

    p50 = statistics.median(latencies)
    sorted_lat = sorted(latencies)
    idx_p95 = min(int(len(sorted_lat) * 0.95), len(sorted_lat) - 1)
    p95 = sorted_lat[idx_p95]

    return {
        "num_days": num_days,
        "repetitions": repetitions,
        "p50_ms": round(p50 * 1000, 2),
        "p95_ms": round(p95 * 1000, 2),
        "avg_llm_calls": round(statistics.mean(llm_calls_recorded), 1),
    }


async def benchmark_replan_14_day(repetitions: int = 5) -> dict[str, Any]:
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")

    num_days = 14
    latencies: list[float] = []

    for _ in range(repetitions):
        trip_id = uuid4()
        run_id = uuid4()
        start = date(2026, 12, 1)
        end = start + timedelta(days=num_days - 1)
        spec = TripSpec(
            trip_id=trip_id,
            destination="Darjeeling",
            start_date=start,
            end_date=end,
            budget_total=Decimal(45000),
            currency="INR",
            pace="balanced",
        )
        await repos.trips.save_trip(spec)

        mock_draft = _generate_mock_draft(num_days)
        v1_id = await repos.itineraries.save_version(
            trip_id=trip_id,
            version_no=1,
            reason="Initial 14 day",
            created_by="agent:planner",
            items=mock_draft.items,
        )
        await repos.trips.update_current_version(trip_id, v1_id)

        injected = InjectedSignals(
            type="weather",
            day_index=5,
            params={"precip_prob": 0.95, "from": "14:00", "to": "16:00"},
        )

        with patch("reroute_agents.tools.weather.is_mock_tools", return_value=True):
            t_start = time.monotonic()
            replan_events = []
            async for evt in run_replan(
                run_id=run_id,
                trip_id=trip_id,
                injected=injected,
                repos=repos,
                llm_override=FakeLLM(),
            ):
                replan_events.append(evt)

            async for evt in resume_replan(
                run_id=run_id,
                decision="approve",
                repos=repos,
                llm_override=FakeLLM(),
            ):
                pass
            elapsed_s = time.monotonic() - t_start

        latencies.append(elapsed_s)

    p50 = statistics.median(latencies)
    sorted_lat = sorted(latencies)
    idx_p95 = min(int(len(sorted_lat) * 0.95), len(sorted_lat) - 1)
    p95 = sorted_lat[idx_p95]

    return {
        "operation": "replan_14_day",
        "repetitions": repetitions,
        "p50_ms": round(p50 * 1000, 2),
        "p95_ms": round(p95 * 1000, 2),
    }


async def run_all_benchmarks() -> dict[str, Any]:
    print("Benchmarking 1-day plan...")
    b1 = await benchmark_plan_duration(1, repetitions=4)
    print("Benchmarking 7-day plan...")
    b7 = await benchmark_plan_duration(7, repetitions=4)
    print("Benchmarking 14-day plan...")
    b14 = await benchmark_plan_duration(14, repetitions=4)
    print("Benchmarking 14-day replan...")
    br = await benchmark_replan_14_day(repetitions=4)

    results = {
        "plan_1_day": b1,
        "plan_7_day": b7,
        "plan_14_day": b14,
        "replan_14_day": br,
    }
    return results


if __name__ == "__main__":
    res = asyncio.run(run_all_benchmarks())
    print(json.dumps(res, indent=2))
