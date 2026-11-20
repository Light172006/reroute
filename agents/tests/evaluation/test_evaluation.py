"""Evaluation tests asserting system performance against PRD Section 9 targets."""

import pytest

from reroute_agents.evaluation.run_eval import run_evaluation_benchmark


@pytest.mark.asyncio
async def test_evaluation_metrics_meet_prd_targets() -> None:
    results = await run_evaluation_benchmark()

    # PRD Target 1: Plan generation success rate >= 95%
    assert results["plan_success_rate"] >= 95.0, (
        f"Plan generation success {results['plan_success_rate']}% below 95% target"
    )

    # PRD Target 2: Constraint satisfaction >= 90%
    assert results["constraint_satisfaction_rate"] >= 90.0, (
        f"Constraint satisfaction {results['constraint_satisfaction_rate']}% below 90% target"
    )

    # PRD Target 3: Replan proposals that touch only affected items >= 85%
    assert results["replan_purity_rate"] >= 85.0, (
        f"Replan purity {results['replan_purity_rate']}% below 85% target"
    )

    # PRD Target 4: Median plan generation time <= 40s
    assert results["median_latency"] <= 40.0, (
        f"Median latency {results['median_latency']}s exceeds 40s limit"
    )
