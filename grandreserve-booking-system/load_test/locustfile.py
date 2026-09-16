"""
Concurrency proof-of-work load test.

This is the whole point of the "does it actually hold up under load"
requirement: it points every simulated user at the SAME table and the
SAME time slot, all at once, and verifies that exactly one booking
succeeds (HTTP 201) while the rest get a clean 409 Conflict -- never a
duplicate, a crash, or a 500.

Usage:
    export HOT_TABLE_ID=<uuid printed by scripts/seed_demo_data.py>
    locust -f load_test/locustfile.py --host http://localhost:8000 \
           --users 100 --spawn-rate 100 --run-time 30s --headless

Then check the Locust summary: you should see 201s and 409s, and the
project's own /reservations/me check (or a quick SQL query) will show
exactly one CONFIRMED reservation for that table/slot no matter how
many users attacked it.
"""

import os
import uuid

from locust import HttpUser, between, task

HOT_TABLE_ID = os.environ.get("HOT_TABLE_ID", "00000000-0000-0000-0000-000000000000")
SLOT_START = "2026-12-31T20:00:00+00:00"  # every user targets this exact slot


class DinerRacingForATable(HttpUser):
    wait_time = between(0, 0.2)

    def on_start(self):
        email = f"loadtest-{uuid.uuid4().hex[:12]}@example.com"
        password = "SuperSecret123"

        self.client.post(
            "/auth/register",
            json={"email": email, "password": password, "full_name": "Load Test User"},
        )
        resp = self.client.post("/auth/login", json={"email": email, "password": password})
        self.token = resp.json().get("access_token")

    @task
    def book_the_same_table(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.post(
            "/reservations",
            headers=headers,
            json={
                "table_id": HOT_TABLE_ID,
                "slot_start": SLOT_START,
                "party_size": 2,
                # A fresh key per request: we WANT every user to be a
                # genuinely distinct booking attempt, competing for the
                # one real table -- not deduplicated by idempotency.
                "idempotency_key": str(uuid.uuid4()),
            },
            name="/reservations (race for hot table)",
        )
