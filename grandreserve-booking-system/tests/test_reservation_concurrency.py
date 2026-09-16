"""
Integration test: proves the core promise of this project.

Requires the full stack running (docker compose up) and a seeded
restaurant (scripts/seed_demo_data.py), since it exercises the real
Postgres unique constraint and Redis lock end-to-end rather than mocking
them.

Run with:
    HOT_TABLE_ID=<uuid> pytest tests/test_reservation_concurrency.py -v
"""

import asyncio
import os
import uuid

import httpx
import pytest

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
HOT_TABLE_ID = os.environ.get("HOT_TABLE_ID")
SLOT_START = "2026-12-31T21:00:00+00:00"


async def _register_and_login(client: httpx.AsyncClient) -> str:
    email = f"race-{uuid.uuid4().hex[:10]}@example.com"
    await client.post(
        "/auth/register",
        json={"email": email, "password": "SuperSecret123", "full_name": "Racer"},
    )
    res = await client.post("/auth/login", json={"email": email, "password": "SuperSecret123"})
    return res.json()["access_token"]


async def _attempt_booking(client: httpx.AsyncClient) -> int:
    token = await _register_and_login(client)
    res = await client.post(
        "/reservations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "table_id": HOT_TABLE_ID,
            "slot_start": SLOT_START,
            "party_size": 2,
            "idempotency_key": str(uuid.uuid4()),
        },
    )
    return res.status_code


@pytest.mark.skipif(not HOT_TABLE_ID, reason="Set HOT_TABLE_ID env var to a real table id first.")
@pytest.mark.asyncio
async def test_only_one_of_fifty_concurrent_bookings_succeeds():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        results = await asyncio.gather(*[_attempt_booking(client) for _ in range(50)])

    successes = results.count(201)
    conflicts = results.count(409)

    assert successes == 1, f"Expected exactly 1 confirmed booking, got {successes}"
    assert conflicts == 49, f"Expected 49 conflicts, got {conflicts}"
