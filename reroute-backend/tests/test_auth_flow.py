"""End-to-end auth flow tests using an in-memory SQLite database.

These tests override the global ``get_db`` dependency with a SQLite-backed
session so the signup → login → /me → refresh cycle can be exercised without
a running PostgreSQL instance.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import Base, get_db
from app.db import models  # noqa: F401  – ensure models are registered on Base.metadata

# ---------------------------------------------------------------------------
# SQLite test engine + session factory
# ---------------------------------------------------------------------------
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


@pytest.fixture
def client():
    _create_all()
    app.dependency_overrides[get_db] = _override_get_db()
    test_client = TestClient(app)
    yield test_client
    _drop_all()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_signup_and_login(client):
    # 1. Signup
    r = client.post(
        "/auth/signup",
        params={"email": "alice@example.com", "password": "secret123", "display_name": "Alice"},
    )
    assert r.status_code == 201, r.text
    user = r.json()
    assert user["email"] == "alice@example.com"
    assert user["display_name"] == "Alice"

    # 2. Duplicate signup must fail
    r2 = client.post(
        "/auth/signup",
        params={"email": "alice@example.com", "password": "secret123", "display_name": "Alice"},
    )
    assert r2.status_code == 400

    # 3. Login
    r3 = client.post(
        "/auth/login",
        params={"email": "alice@example.com", "password": "secret123"},
    )
    assert r3.status_code == 200, r3.text
    tokens = r3.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    # 4. /me with valid token
    r4 = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r4.status_code == 200, r4.text
    assert r4.json()["email"] == "alice@example.com"

    # 5. /me without token
    r5 = client.get("/auth/me")
    assert r5.status_code in (401, 403)

    # 6. Refresh
    r6 = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert r6.status_code == 200, r6.text
    new_tokens = r6.json()
    assert new_tokens["access_token"] != tokens["access_token"]

    # 7. Wrong password
    r7 = client.post(
        "/auth/login",
        params={"email": "alice@example.com", "password": "wrong"},
    )
    assert r7.status_code == 400