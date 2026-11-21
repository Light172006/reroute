"""Performance stress tests for plan generation and replan execution."""

from __future__ import annotations

import pytest

import sys
from pathlib import Path

agents_root = str(Path(__file__).resolve().parents[2])
if agents_root not in sys.path:
    sys.path.insert(0, agents_root)

from evaluation.stress.perf_benchmark import (
    benchmark_plan_duration,
    benchmark_replan_14_day,
)


@pytest.mark.asyncio
async def test_plan_generation_latency_bounds() -> None:
    """Test 1-day, 7-day, and 14-day mock plan generation latencies are within sub-second thresholds."""
    res_1 = await benchmark_plan_duration(num_days=1, repetitions=3)
    assert res_1["p50_ms"] < 500.0, f"1-day plan p50 too high: {res_1['p50_ms']}ms"

    res_7 = await benchmark_plan_duration(num_days=7, repetitions=3)
    assert res_7["p50_ms"] < 500.0, f"7-day plan p50 too high: {res_7['p50_ms']}ms"

    res_14 = await benchmark_plan_duration(num_days=14, repetitions=3)
    assert res_14["p50_ms"] < 500.0, f"14-day plan p50 too high: {res_14['p50_ms']}ms"


@pytest.mark.asyncio
async def test_replan_14_day_latency_bounds() -> None:
    """Test 14-day replan pause-and-resume latency is well under 1 second."""
    res_replan = await benchmark_replan_14_day(repetitions=3)
    assert res_replan["p50_ms"] < 500.0, f"14-day replan p50 too high: {res_replan['p50_ms']}ms"
