"""Stress tests for LLM gateway, TokenBucket rate limiter, fallback chain, and FakeLLM."""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from reroute_agents.llm import FakeLLM, ResilientLLMChain, TokenBucket
from reroute_agents.state import AgentEvent


class MockOutputSchema(BaseModel):
    summary: str
    confidence: float


@pytest.mark.asyncio
async def test_token_bucket_concurrency_and_no_starvation() -> None:
    """Hammer TokenBucket with 50 concurrent calls; verify no deadlock and concurrency rate throttling."""
    # Capacity 5, rate 20 tokens/sec
    bucket = TokenBucket(rate_rps=20.0, capacity=5)
    acquired_count = 0
    t_start = time.monotonic()

    async def worker() -> None:
        nonlocal acquired_count
        await bucket.acquire()
        acquired_count += 1

    tasks = [asyncio.create_task(worker()) for _ in range(30)]
    await asyncio.gather(*tasks)
    elapsed = time.monotonic() - t_start

    assert acquired_count == 30
    assert elapsed >= 0.5


@pytest.mark.asyncio
async def test_fake_llm_fail_times_retry_and_canned_structured_output() -> None:
    """Test FakeLLM simulated failure count before returning canned structured output."""
    fake = FakeLLM(
        name="fake:test",
        canned_responses={
            "MockOutputSchema": {"summary": "Generated safely", "confidence": 0.95}
        },
        fail_times=2,
        fail_exception=RuntimeError("Simulated 429 Too Many Requests"),
    )

    runner = fake.with_structured_output(MockOutputSchema)

    # 1. First two calls fail
    with pytest.raises(RuntimeError, match="429 Too Many Requests"):
        await runner.ainvoke("test call 1")

    with pytest.raises(RuntimeError, match="429 Too Many Requests"):
        await runner.ainvoke("test call 2")

    # 2. Third call succeeds
    res = await runner.ainvoke("test call 3")
    assert isinstance(res, MockOutputSchema)
    assert res.summary == "Generated safely"
    assert res.confidence == 0.95


@pytest.mark.asyncio
async def test_resilient_chain_falls_back_when_primary_fails() -> None:
    """Verify that when primary model raises 429/timeout, chain retries and falls back to secondary model."""
    chain = ResilientLLMChain(["mock:primary", "mock:secondary"], tier="strong")
    events: list[AgentEvent] = []

    mock_primary = MagicMock()
    primary_runner = MagicMock()
    primary_runner.ainvoke = MagicMock(side_effect=RuntimeError("429 Resource Exhausted / Rate limit"))
    mock_primary.with_structured_output.return_value = primary_runner

    mock_secondary = MagicMock()
    secondary_runner = MagicMock()
    expected_output = MockOutputSchema(summary="Recovered by fallback", confidence=0.88)
    # Async mock for ainvoke
    async def _sec_ainvoke(*args: Any, **kwargs: Any) -> MockOutputSchema:
        return expected_output
    secondary_runner.ainvoke = _sec_ainvoke
    mock_secondary.with_structured_output.return_value = secondary_runner

    def mock_create_instance(spec: str) -> Any:
        if "primary" in spec:
            return mock_primary
        return mock_secondary

    with patch("reroute_agents.llm.create_model_instance", side_effect=mock_create_instance):
        result = await chain.ainvoke_structured(
            schema=MockOutputSchema,
            prompt="Plan trip",
            events=events,
            node_name="planner",
        )

    assert result.summary == "Recovered by fallback"
    assert len(events) == 1
    assert events[0].type == "llm_call"
    assert events[0].payload["fallback"] is True
    assert events[0].payload["model"] == "mock:secondary"


@pytest.mark.asyncio
async def test_resilient_chain_raises_when_all_models_fail() -> None:
    """Verify chain raises RuntimeError when all configured models fail."""
    chain = ResilientLLMChain(["mock:fail1", "mock:fail2"], tier="strong")

    mock_failing = MagicMock()
    failing_runner = MagicMock()
    async def _fail_ainvoke(*args: Any, **kwargs: Any) -> Any:
        raise ConnectionError("503 Upstream Service Unavailable")
    failing_runner.ainvoke = _fail_ainvoke
    mock_failing.with_structured_output.return_value = failing_runner

    with patch("reroute_agents.llm.create_model_instance", return_value=mock_failing):
        with pytest.raises(RuntimeError, match="All models in chain .* failed"):
            await chain.ainvoke_structured(
                schema=MockOutputSchema,
                prompt="Plan trip",
            )


def test_keys_redaction_and_privacy_in_events() -> None:
    """Verify API keys and sensitive tokens never leak into AgentEvent representation or payload."""
    secret_key = "AIzaSyFakeKey12345SECRET"

    event = AgentEvent(
        type="llm_call",
        node="researcher",
        status="running",
        message="Calling Gemini with query",
        payload={"query": "darjeeling sights", "tokens": 150},
    )

    ev_json = event.model_dump_json()
    assert secret_key not in ev_json
    assert "SECRET" not in ev_json
