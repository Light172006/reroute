"""Comprehensive authentication flow test suite.

Exercises the complete signup, login, refresh, /me, CORS, and failure recovery
lifecycle using the identical JSON payloads sent by the frontend API client.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import Base, get_db
from app.db import models  # noqa: F401
from app.core.config import settings
from app.utils.jwt import create_access_token, create_refresh_token

# ---------------------------------------------------------------------------
# SQLite test engine + session factory
# ---------------------------------------------------------------------------
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
)
test_session_maker = sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


async def _init_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def _cleanup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _override_get_db():
    async def _get_db():
        async with test_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    return _get_db


@pytest.fixture(autouse=True)
def setup_teardown_db():
    asyncio.run(_init_test_db())
    app.dependency_overrides[get_db] = _override_get_db()
    yield
    asyncio.run(_cleanup_test_db())
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# 1. Successful Signup (JSON body matching frontend contract)
# ---------------------------------------------------------------------------
def test_successful_signup_json(client):
    payload = {
        "email": "meera@reroute.ai",
        "password": "password123",
        "display_name": "Meera Rao",
    }
    r = client.post("/api/v1/auth/signup", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["email"] == "meera@reroute.ai"
    assert data["display_name"] == "Meera Rao"
    assert "access_token" in data and len(data["access_token"]) > 10
    assert "refresh_token" in data and len(data["refresh_token"]) > 10
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "meera@reroute.ai"


# ---------------------------------------------------------------------------
# 2. Successful Login (JSON body matching frontend contract)
# ---------------------------------------------------------------------------
def test_successful_login_json(client):
    # Signup first
    client.post("/api/v1/auth/signup", json={
        "email": "aarav@reroute.ai",
        "password": "password123",
        "display_name": "Aarav Sharma",
    })

    # Login
    r = client.post("/api/v1/auth/login", json={
        "email": "aarav@reroute.ai",
        "password": "password123",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["email"] == "aarav@reroute.ai"
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


# ---------------------------------------------------------------------------
# 3. Duplicate Email Signup Rejection
# ---------------------------------------------------------------------------
def test_signup_existing_email_duplicate(client):
    payload = {
        "email": "duplicate@reroute.ai",
        "password": "password123",
        "display_name": "User One",
    }
    r1 = client.post("/api/v1/auth/signup", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/api/v1/auth/signup", json=payload)
    assert r2.status_code == 400
    assert "already registered" in r2.json().get("detail", "").lower()


# ---------------------------------------------------------------------------
# 4. Signup with Malformed Email
# ---------------------------------------------------------------------------
def test_signup_malformed_email(client):
    payload = {
        "email": "not-an-email",
        "password": "password123",
        "display_name": "Bad Email",
    }
    r = client.post("/api/v1/auth/signup", json=payload)
    assert r.status_code in (400, 422)


# ---------------------------------------------------------------------------
# 5. Signup with Missing Required Fields
# ---------------------------------------------------------------------------
def test_signup_missing_fields(client):
    # Missing display_name
    r = client.post("/api/v1/auth/signup", json={
        "email": "missing@reroute.ai",
        "password": "password123",
    })
    assert r.status_code in (400, 422)

    # Missing password
    r2 = client.post("/api/v1/auth/signup", json={
        "email": "missing@reroute.ai",
        "display_name": "Missing Password",
    })
    assert r2.status_code in (400, 422)


# ---------------------------------------------------------------------------
# 6. Signup with Short/Invalid Password
# ---------------------------------------------------------------------------
def test_signup_invalid_short_password(client):
    payload = {
        "email": "shortpw@reroute.ai",
        "password": "123",  # Under 6 chars
        "display_name": "Short Password",
    }
    r = client.post("/api/v1/auth/signup", json=payload)
    assert r.status_code in (400, 422)


# ---------------------------------------------------------------------------
# 7. Login with Incorrect Password
# ---------------------------------------------------------------------------
def test_login_incorrect_password(client):
    client.post("/api/v1/auth/signup", json={
        "email": "user@reroute.ai",
        "password": "correctpassword",
        "display_name": "Valid User",
    })
    r = client.post("/api/v1/auth/login", json={
        "email": "user@reroute.ai",
        "password": "wrongpassword",
    })
    assert r.status_code in (400, 401)
    assert "credential" in r.json().get("detail", "").lower()


# ---------------------------------------------------------------------------
# 8. Login with Nonexistent Account
# ---------------------------------------------------------------------------
def test_login_nonexistent_account(client):
    r = client.post("/api/v1/auth/login", json={
        "email": "ghost@reroute.ai",
        "password": "password123",
    })
    assert r.status_code in (400, 401)


# ---------------------------------------------------------------------------
# 9. Login with Malformed Request Body
# ---------------------------------------------------------------------------
def test_login_malformed_request(client):
    r = client.post(
        "/api/v1/auth/login",
        content="not-json",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code in (400, 422)


# ---------------------------------------------------------------------------
# 10. Authenticated /me Request
# ---------------------------------------------------------------------------
def test_authenticated_me(client):
    signup_res = client.post("/api/v1/auth/signup", json={
        "email": "me_test@reroute.ai",
        "password": "password123",
        "display_name": "Me Tester",
    }).json()
    token = signup_res["access_token"]

    r = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["email"] == "me_test@reroute.ai"
    assert data["display_name"] == "Me Tester"


# ---------------------------------------------------------------------------
# 11. Unauthenticated /me Request
# ---------------------------------------------------------------------------
def test_unauthenticated_me(client):
    r = client.get("/api/v1/me")
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 12. Valid Refresh Token Exchange
# ---------------------------------------------------------------------------
def test_valid_refresh_token(client):
    signup_res = client.post("/api/v1/auth/signup", json={
        "email": "refresh_user@reroute.ai",
        "password": "password123",
        "display_name": "Refresh User",
    }).json()

    r = client.post("/api/v1/auth/refresh", json={
        "refresh_token": signup_res["refresh_token"],
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    assert data["access_token"] != signup_res["access_token"]


# ---------------------------------------------------------------------------
# 13. Invalid Refresh Token
# ---------------------------------------------------------------------------
def test_invalid_refresh_token(client):
    r = client.post("/api/v1/auth/refresh", json={
        "refresh_token": "totally-invalid-jwt-token",
    })
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 14. Expired Access Token
# ---------------------------------------------------------------------------
def test_expired_access_token(client):
    signup_res = client.post("/api/v1/auth/signup", json={
        "email": "expired@reroute.ai",
        "password": "password123",
        "display_name": "Expired Tester",
    }).json()

    user_id = signup_res["user"]["id"]
    now = datetime.now(tz=UTC)
    expired_payload = {
        "sub": str(user_id),
        "exp": now - timedelta(minutes=5),
        "iat": int((now - timedelta(minutes=10)).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    expired_token = create_access_token(expired_payload)

    r = client.get("/api/v1/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 15. Expired Refresh Token
# ---------------------------------------------------------------------------
def test_expired_refresh_token(client):
    signup_res = client.post("/api/v1/auth/signup", json={
        "email": "exp_refresh@reroute.ai",
        "password": "password123",
        "display_name": "Exp Refresh",
    }).json()

    user_id = signup_res["user"]["id"]
    now = datetime.now(tz=UTC)
    expired_payload = {
        "sub": str(user_id),
        "exp": now - timedelta(days=1),
        "iat": int((now - timedelta(days=2)).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    expired_token = create_refresh_token(expired_payload)

    r = client.post("/api/v1/auth/refresh", json={"refresh_token": expired_token})
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 16. Email Case-Insensitive Normalization
# ---------------------------------------------------------------------------
def test_email_case_insensitivity(client):
    # Register with uppercase
    client.post("/api/v1/auth/signup", json={
        "email": "CaseSensitive@Reroute.AI",
        "password": "password123",
        "display_name": "Case User",
    })

    # Login with all lowercase
    r = client.post("/api/v1/auth/login", json={
        "email": "casesensitive@reroute.ai",
        "password": "password123",
    })
    assert r.status_code == 200, r.text

    # Duplicate check with mixed case
    r_dup = client.post("/api/v1/auth/signup", json={
        "email": "CASESENSITIVE@reroute.ai",
        "password": "password123",
        "display_name": "Duplicate Case",
    })
    assert r_dup.status_code == 400


# ---------------------------------------------------------------------------
# 17. CORS Preflight from Configured Origin
# ---------------------------------------------------------------------------
def test_cors_preflight_configured_origin(client):
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type, Authorization",
    }
    r = client.options("/api/v1/auth/signup", headers=headers)
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "POST" in r.headers.get("access-control-allow-methods", "")


# ---------------------------------------------------------------------------
# 18. Unauthorized Origin CORS Rejection
# ---------------------------------------------------------------------------
def test_cors_unauthorized_origin_rejection(client):
    headers = {
        "Origin": "http://malicious-attacker.com",
        "Access-Control-Request-Method": "POST",
    }
    r = client.options("/api/v1/auth/signup", headers=headers)
    # The Access-Control-Allow-Origin header must NOT match the malicious origin
    assert r.headers.get("access-control-allow-origin") != "http://malicious-attacker.com"


# ---------------------------------------------------------------------------
# 19. Concurrent Token Refresh Simulation
# ---------------------------------------------------------------------------
def test_concurrent_refresh_tokens(client):
    signup_res = client.post("/api/v1/auth/signup", json={
        "email": "concurrent@reroute.ai",
        "password": "password123",
        "display_name": "Concurrent User",
    }).json()

    token = signup_res["refresh_token"]

    # Multiple successive refresh calls with valid token must succeed
    r1 = client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert r1.status_code == 200
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert r2.status_code == 200


# ---------------------------------------------------------------------------
# 20. Database Session Error Handling during Signup
# ---------------------------------------------------------------------------
def test_database_failure_during_signup():
    # Simulate database error by forcing a mock dependency that raises
    async def failing_db():
        raise RuntimeError("Simulated database failure")
        yield  # noqa: unreachable

    app.dependency_overrides[get_db] = failing_db
    try:
        with TestClient(app, raise_server_exceptions=False) as failing_client:
            r = failing_client.post("/api/v1/auth/signup", json={
                "email": "fail@reroute.ai",
                "password": "password123",
                "display_name": "Fail Test",
            })
            assert r.status_code >= 500
    finally:
        app.dependency_overrides.clear()
