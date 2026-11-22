"""Comprehensive tests for the /api/v1 prefix and frontend-backend contracts."""
from __future__ import annotations

import uuid
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import Base, get_db
from app.db.models import User, Trip, Place, ItemType, Expense, ChatMessage, AgentRun, ReplanProposal

test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
test_session_maker = sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


def _create_all():
    import asyncio
    async def _go():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    asyncio.get_event_loop().run_until_complete(_go())


def _drop_all():
    import asyncio
    async def _go():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    asyncio.get_event_loop().run_until_complete(_go())


@pytest.fixture
def client():
    _create_all()
    async def _override():
        async with test_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    app.dependency_overrides[get_db] = _override
    with TestClient(app) as test_client:
        yield test_client
    _drop_all()


def test_cors_preflight(client):
    """Test CORS preflight response for frontend origin."""
    response = client.options(
        "/api/v1/trips",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") in ["http://localhost:3000", "*"]


def test_v1_auth_json_contract(client):
    """Frontend sends JSON body to /api/v1/auth/signup and /api/v1/auth/login."""
    # 1. Signup with JSON body
    signup_data = {
        "email": "priya@example.com",
        "password": "mypassword123",
        "display_name": "Priya Sharma",
    }
    r = client.post("/api/v1/auth/signup", json=signup_data)
    assert r.status_code == 201, r.text
    res = r.json()
    assert "access_token" in res
    assert "refresh_token" in res
    assert res["user"]["email"] == "priya@example.com"
    assert res["user"]["display_name"] == "Priya Sharma"

    # 2. Login with JSON body
    login_data = {
        "email": "priya@example.com",
        "password": "mypassword123",
    }
    r_login = client.post("/api/v1/auth/login", json=login_data)
    assert r_login.status_code == 200, r_login.text
    tokens = r_login.json()
    assert tokens["access_token"]
    assert tokens["user"]["email"] == "priya@example.com"

    auth_headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # 3. /api/v1/me
    r_me = client.get("/api/v1/me", headers=auth_headers)
    assert r_me.status_code == 200
    assert r_me.json()["email"] == "priya@example.com"

    # 4. /api/v1/trips CRUD with full schema
    trip_payload = {
        "title": "Goa Beach Retreat",
        "destination": "Goa, India",
        "start_date": "2026-12-01",
        "end_date": "2026-12-05",
        "group_size": 2,
        "budget_total": 50000.0,
        "budget_per_day_cap": 12000.0,
        "currency": "INR",
        "pace": "relaxed",
        "vibe_tags": ["beach", "food", "sunset"],
        "notes": "Looking for beachfront stays and seafood",
    }
    r_trip = client.post("/api/v1/trips/", json=trip_payload, headers=auth_headers)
    assert r_trip.status_code == 201, r_trip.text
    trip = r_trip.json()
    assert trip["title"] == "Goa Beach Retreat"
    assert trip["pace"] == "relaxed"
    assert "beach" in trip["vibe_tags"]
    trip_id = trip["id"]

    # 5. Patch trip
    r_patch = client.patch(
        f"/api/v1/trips/{trip_id}",
        json={"title": "Goa Sunshine Retreat", "budget_total": 55000.0},
        headers=auth_headers,
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["title"] == "Goa Sunshine Retreat"
    assert r_patch.json()["budget_total"] == 55000.0

    # 6. List trips
    r_list = client.get("/api/v1/trips/", headers=auth_headers)
    assert r_list.status_code == 200
    assert len(r_list.json()) >= 1

    # 7. Simulate endpoint with JSON body (contract: SimulateRequest)
    sim_data = {
        "trip_id": trip_id,
        "type": "weather",
        "day_index": 2,
        "params": {"condition": "heavy_rain"},
    }
    r_sim = client.post("/api/v1/demo/simulate", json=sim_data, headers=auth_headers)
    assert r_sim.status_code in [202, 409], r_sim.text

    # 8. Delete trip
    r_del = client.delete(f"/api/v1/trips/{trip_id}", headers=auth_headers)
    assert r_del.status_code == 204

    # 9. Verify trip is gone
    r_gone = client.get(f"/api/v1/trips/{trip_id}", headers=auth_headers)
    assert r_gone.status_code == 404
