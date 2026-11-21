"""Targeted unit tests boosting branch coverage across nodes, gateway, rules, and LLM (AG-006)."""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from reroute_agents.gateway import (
    resume_replan,
    run_chat,
    run_plan,
    run_replan,
)
from reroute_agents.llm import (
    FakeLLM,
    ResilientLLMChain,
    TokenBucket,
    create_model_instance,
    get_llm,
)
from reroute_agents.nodes.budget_check import budget_check_node
from reroute_agents.nodes.replanner import create_replanner_node
from reroute_agents.repositories.in_memory import create_in_memory_repositories
from reroute_agents.state import (
    DisruptionEvent,
    DraftItem,
    ItineraryDraft,
    TripSpec,
)

# ============================================================================
# 1. Budget Check Node Coverage (100% target)
# ============================================================================


@pytest.mark.asyncio
async def test_budget_check_node_no_draft() -> None:
    """Verify budget_check_node returns unmodified violations when no draft exists."""
    spec = TripSpec(
        trip_id=uuid4(),
        destination="Darjeeling",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 2),
        budget_total=Decimal(10000),
    )
    res = await budget_check_node({"spec": spec, "violations": []})
    assert res == {"violations": []}


@pytest.mark.asyncio
async def test_budget_check_node_total_budget_and_daily_cap_overrun() -> None:
    """Verify budget_check_node flags total budget overrun and daily cap violations."""
    spec = TripSpec(
        trip_id=uuid4(),
        destination="Darjeeling",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 2),
        budget_total=Decimal(500),
        budget_per_day_cap=Decimal(250),
    )
    items = [
        DraftItem(
            day_index=1,
            position=0,
            title="Expensive Day 1",
            category="cultural",
            setting="indoor",
            start_time=time(9, 0),
            end_time=time(11, 0),
            est_cost=Decimal(300),  # Exceeds per-day cap of 250
        ),
        DraftItem(
            day_index=2,
            position=0,
            title="Expensive Day 2",
            category="cultural",
            setting="indoor",
            start_time=time(9, 0),
            end_time=time(11, 0),
            est_cost=Decimal(300),  # Total is 600 > 500
        ),
    ]
    draft = ItineraryDraft(items=items)
    res = await budget_check_node({"spec": spec, "draft": draft, "violations": []})

    violations = res["violations"]
    assert any(v.code == "over_budget" and v.day_index is None for v in violations)
    assert any(v.code == "over_budget" and v.day_index == 1 for v in violations)
    assert res["events"][0].status == "failed"


# ============================================================================
# 2. Replanner Node Coverage (95%+ target)
# ============================================================================


@pytest.mark.asyncio
async def test_replanner_node_no_candidates_fallback() -> None:
    """Verify replanner keeps the affected item if no suitable replacement candidate is found."""
    repos = create_in_memory_repositories()
    replanner = create_replanner_node(repos.places, repos.trips)

    t_id = uuid4()
    spec = TripSpec(
        trip_id=t_id,
        destination="Darjeeling",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 2),
        budget_total=Decimal(10000),
    )
    await repos.trips.save_trip(spec)

    item1 = DraftItem(
        day_index=1,
        position=0,
        title="Unreplaceable Place",
        category="adventure",
        setting="outdoor",
        start_time=time(9, 0),
        end_time=time(11, 0),
    )
    current_items = [item1]
    affected_ids = {str(item1.stable_key)}
    disruptions = [
        DisruptionEvent(type="closure", severity="high", summary="Road blocked", source="weather")
    ]

    state = {
        "trip_id": str(t_id),
        "current_items": current_items,
        "affected_item_ids": affected_ids,
        "disruptions": disruptions,
        "events": [],
    }

    res = await replanner(state)
    assert len(res["draft"].items) == 1
    assert res["draft"].items[0].title == "Unreplaceable Place"


@pytest.mark.asyncio
async def test_replanner_node_structured_llm_invocation_and_error() -> None:
    """Verify replanner structured LLM refinement branch and graceful exception handling."""
    repos = create_in_memory_repositories()
    t_id = uuid4()
    spec = TripSpec(
        trip_id=t_id,
        destination="Darjeeling",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 2),
        budget_total=Decimal(10000),
    )
    await repos.trips.save_trip(spec)

    item1 = DraftItem(
        day_index=1,
        position=0,
        title="Original Stop",
        category="sightseeing",
        setting="outdoor",
        start_time=time(10, 0),
        end_time=time(12, 0),
    )

    refined_item = item1.model_copy(update={"title": "LLM Refined Stop"})
    mock_runner = MagicMock()
    mock_runner.ainvoke = AsyncMock(return_value=ItineraryDraft(items=[refined_item]))

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_runner

    replanner = create_replanner_node(repos.places, repos.trips, llm_override=mock_llm)

    state = {
        "trip_id": str(t_id),
        "current_items": [item1],
        "affected_item_ids": {str(item1.stable_key)},
        "disruptions": [
            DisruptionEvent(
                type="weather", severity="high", summary="Heavy Monsoon Rain", source="weather"
            )
        ],
        "events": [],
    }

    # 1. Success path
    res_success = await replanner(state)
    assert res_success["draft"].items[0].title == "LLM Refined Stop"

    # 2. Exception path
    mock_runner.ainvoke = AsyncMock(side_effect=RuntimeError("Structured output parsing failed"))
    res_error = await replanner(state)
    assert len(res_error["draft"].items) == 1


# ============================================================================
# 3. Gateway Error Handling Coverage (85%+ target)
# ============================================================================


@pytest.mark.asyncio
async def test_gateway_run_plan_trip_not_found() -> None:
    """Verify run_plan yields a not_found error event when trip_id does not exist."""
    run_id = uuid4()
    missing_trip_id = uuid4()
    events = [e async for e in run_plan(run_id, missing_trip_id)]
    assert len(events) == 1
    assert events[0].type == "error"
    assert events[0].payload["code"] == "not_found"


@pytest.mark.asyncio
async def test_gateway_run_replan_missing_trip_or_itinerary() -> None:
    """Verify run_replan yields not_found errors when itinerary or spec is missing."""
    repos = create_in_memory_repositories()
    run_id = uuid4()
    missing_trip_id = uuid4()

    # 1. Missing trip spec
    events_no_spec = [
        e async for e in run_replan(run_id, missing_trip_id, repos=repos)
    ]
    assert any(e.type == "error" and e.payload["code"] == "not_found" for e in events_no_spec)

    # 2. Has spec but missing itinerary
    spec = TripSpec(
        trip_id=missing_trip_id,
        destination="Darjeeling",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 2),
        budget_total=Decimal(10000),
    )
    await repos.trips.save_trip(spec)
    events_no_itin = [
        e async for e in run_replan(run_id, missing_trip_id, repos=repos)
    ]
    assert any(e.type == "error" and e.payload["code"] == "not_found" for e in events_no_itin)


@pytest.mark.asyncio
async def test_gateway_resume_replan_execution_failed_on_invalid_thread() -> None:
    """Verify resume_replan yields error when attempting to resume non-existent thread."""
    repos = create_in_memory_repositories()
    run_id = uuid4()
    events = [e async for e in resume_replan(run_id, decision="approve", repos=repos)]
    assert any(e.type == "error" for e in events)
    assert events[-1].type == "error"
    assert events[-1].payload["code"] in ("internal_error", "execution_failed")


@pytest.mark.asyncio
async def test_gateway_run_chat_exception_handling() -> None:
    """Verify run_chat handles unexpected exceptions during execution by yielding an error event."""
    repos = create_in_memory_repositories()
    run_id = uuid4()
    trip_id = uuid4()

    with patch("reroute_agents.gateway.build_chat_graph") as mock_build:
        mock_graph = MagicMock()

        async def failing_stream(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("Graph crash")
            yield None

        mock_graph.astream = failing_stream
        mock_build.return_value = mock_graph

        events = [e async for e in run_chat(run_id, trip_id, "Hello", repos=repos)]
        assert len(events) == 1
        assert events[0].type == "error"
        assert "Graph crash" in events[0].payload["message"]


# ============================================================================
# 4. LLM Providers and Edge Cases Coverage (85%+ target)
# ============================================================================


@pytest.mark.asyncio
async def test_llm_token_bucket_edge_cases() -> None:
    """Verify TokenBucket capacity and acquisition."""
    tb = TokenBucket(rate_rps=100.0, capacity=2)
    await tb.acquire()
    assert tb.tokens < 2.0


def test_llm_provider_resolution() -> None:
    """Verify create_model_instance resolves configured models or falls back."""
    # Ollama provider
    with patch("reroute_agents.llm.settings") as mock_settings:
        mock_settings.ollama_base_url = "http://localhost:11434"
        ollama = create_model_instance("ollama:llama3")
        assert ollama is not None
        assert ollama.model == "llama3"

    # Gemini missing key raises ValueError
    with patch("reroute_agents.llm.settings") as mock_settings:
        mock_settings.google_api_key = None
        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            create_model_instance("gemini:gemini-2.5-flash")

    # Groq missing key raises ValueError
    with patch("reroute_agents.llm.settings") as mock_settings:
        mock_settings.groq_api_key = None
        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            create_model_instance("groq:llama-3.3-70b-versatile")

    # Unknown tier in get_llm
    with pytest.raises(ValueError, match="Unknown LLM tier"):
        get_llm("nonexistent_tier")


@pytest.mark.asyncio
async def test_resilient_llm_chain_all_fail_exhaustion() -> None:
    """Verify ResilientLLMChain raises RuntimeError when all configured models fail."""
    failing_llm1 = FakeLLM(fail_times=5)
    failing_llm2 = FakeLLM(fail_times=5)

    chain = ResilientLLMChain(chain_specs=["fake:m1", "fake:m2"])
    chain._providers = {"fake:m1": failing_llm1, "fake:m2": failing_llm2}

    with pytest.raises(RuntimeError, match="All models in chain"):
        await chain.ainvoke_structured(ItineraryDraft, [{"role": "user", "content": "hi"}])
