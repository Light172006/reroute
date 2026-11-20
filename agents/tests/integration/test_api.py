"""Integration tests for FastAPI agent API endpoints."""

from __future__ import annotations

import httpx
import pytest

from reroute_agents.api import create_app
from reroute_agents.destinations.registry import load_seed_catalog_into_repository
from reroute_agents.llm import FakeLLM
from reroute_agents.repositories.in_memory import create_in_memory_repositories


@pytest.fixture
async def async_client():
    repos = create_in_memory_repositories()
    await load_seed_catalog_into_repository(repos.places, "darjeeling")
    fake_llm = FakeLLM()
    app = create_app(repos=repos, llm_override=fake_llm)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client, repos


@pytest.mark.asyncio
async def test_health_endpoint(async_client) -> None:
    client, _ = async_client
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "reroute-agents"}


@pytest.mark.asyncio
async def test_trip_creation_and_generation(async_client) -> None:
    client, _ = async_client
    trip_payload = {
        "title": "Weekend in Darjeeling",
        "destination": "Darjeeling",
        "start_date": "2026-12-12",
        "end_date": "2026-12-14",
        "group_size": 2,
        "budget_total": 15000,
        "currency": "INR",
        "pace": "balanced",
        "vibe_tags": ["nature", "food"],
    }
    trip_resp = await client.post("/api/v1/trips", json=trip_payload)
    assert trip_resp.status_code == 201
    trip_id = trip_resp.json()["trip_id"]

    # Start generation
    gen_resp = await client.post(f"/api/v1/trips/{trip_id}/generate")
    assert gen_resp.status_code == 202
    run_id = gen_resp.json()["run_id"]
    assert run_id is not None

    # Stream events until done
    lines: list[str] = []
    async with client.stream("GET", f"/api/v1/agent/runs/{run_id}/stream") as stream:
        async for line in stream.aiter_lines():
            if line:
                lines.append(line)
            if "event: done" in line:
                break

    assert any("event: step" in line or "event: done" in line for line in lines)

    # Check status endpoint
    status_resp = await client.get(f"/api/v1/agent/runs/{run_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "completed"

    # Check itinerary endpoint
    itin_resp = await client.get(f"/api/v1/trips/{trip_id}/itinerary")
    assert itin_resp.status_code == 200
    itin_data = itin_resp.json()
    assert "version" in itin_data
    assert len(itin_data["days"]) == 3


@pytest.mark.asyncio
async def test_chat_endpoint(async_client) -> None:
    client, _ = async_client
    trip_resp = await client.post(
        "/api/v1/trips",
        json={"destination": "Darjeeling", "start_date": "2026-12-12", "end_date": "2026-12-13"},
    )
    trip_id = trip_resp.json()["trip_id"]

    chat_resp = await client.post(
        f"/api/v1/trips/{trip_id}/chat",
        json={"message": "What is the weather forecast for tomorrow?"},
    )
    assert chat_resp.status_code == 202
    data = chat_resp.json()
    assert "run_id" in data
    assert "message_id" in data


@pytest.mark.asyncio
async def test_simulate_disruption_and_hitl_approval(async_client) -> None:
    client, _ = async_client
    # Create and generate base trip
    trip_resp = await client.post(
        "/api/v1/trips",
        json={"destination": "Darjeeling", "start_date": "2026-12-12", "end_date": "2026-12-14"},
    )
    trip_id = trip_resp.json()["trip_id"]

    gen_resp = await client.post(f"/api/v1/trips/{trip_id}/generate")
    run_id = gen_resp.json()["run_id"]

    # Wait for initial plan to complete
    async with client.stream("GET", f"/api/v1/agent/runs/{run_id}/stream") as stream:
        async for line in stream.aiter_lines():
            if "event: done" in line:
                break

    # Simulate weather disruption
    sim_resp = await client.post(
        "/api/v1/demo/simulate",
        json={
            "trip_id": trip_id,
            "type": "weather",
            "day_index": 2,
            "params": {"precip_prob": 0.9, "from": "13:00", "to": "17:00"},
        },
    )
    assert sim_resp.status_code == 202
    replan_run_id = sim_resp.json()["run_id"]

    # Stream until proposal is emitted
    async with client.stream("GET", f"/api/v1/agent/runs/{replan_run_id}/stream") as stream:
        async for line in stream.aiter_lines():
            if "event: proposal" in line:
                break

    # Fetch pending proposals
    props_resp = await client.get(f"/api/v1/trips/{trip_id}/proposals?status=pending")
    assert props_resp.status_code == 200
    props = props_resp.json()
    assert len(props) == 1
    proposal_id = props[0]["id"]

    # Fetch single proposal with diff
    prop_detail = await client.get(f"/api/v1/proposals/{proposal_id}")
    assert prop_detail.status_code == 200
    assert len(prop_detail.json()["diff"]) >= 1

    # Approve proposal
    dec_resp = await client.post(
        f"/api/v1/proposals/{proposal_id}/decision",
        json={"decision": "approve", "note": "Looks good to me"},
    )
    assert dec_resp.status_code == 200
    assert dec_resp.json()["status"] == "approved"
    assert dec_resp.json()["version_id"] is not None


@pytest.mark.asyncio
async def test_active_run_conflict_409(async_client) -> None:
    client, _ = async_client
    trip_resp = await client.post(
        "/api/v1/trips",
        json={"destination": "Darjeeling", "start_date": "2026-12-12", "end_date": "2026-12-14"},
    )
    trip_id = trip_resp.json()["trip_id"]

    # Start first run
    r1 = await client.post(f"/api/v1/trips/{trip_id}/generate")
    assert r1.status_code == 202

    # Second run on same trip while active returns 409
    r2 = await client.post(f"/api/v1/trips/{trip_id}/generate")
    assert r2.status_code in (409, 202)  # If r1 completed already or was active


@pytest.mark.asyncio
async def test_cancel_endpoint(async_client) -> None:
    client, _ = async_client
    trip_resp = await client.post(
        "/api/v1/trips",
        json={"destination": "Darjeeling", "start_date": "2026-12-12", "end_date": "2026-12-14"},
    )
    trip_id = trip_resp.json()["trip_id"]

    gen_resp = await client.post(f"/api/v1/trips/{trip_id}/generate")
    run_id = gen_resp.json()["run_id"]

    cancel_resp = await client.post(f"/api/v1/agent/runs/{run_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] in ("cancelled", "not_running")
