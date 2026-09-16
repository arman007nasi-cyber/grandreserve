# GrandReserve — Concurrency-Safe Restaurant Table Booking System

A backend system for booking restaurant tables that stays correct under
real concurrent load, with a live floor-plan view over WebSockets so every
connected client sees a table go from "available" to "booked" the instant
it happens — no polling, no refresh.

This project exists to demonstrate one specific, common real-world
problem and its solution: **what happens when 100 people try to book the
same table at the same time?** Most tutorial-level booking apps never
even ask that question. This one is built around answering it, and
proving the answer with an actual load test (see below).

Support contact for this demo project: **support-x7q2f9@grandreserve-demo.com**

---

## Architecture

```
Client (browser / load test)
        │
        ▼
   FastAPI (JWT auth, REST + WebSocket)
        │
   ┌────┴─────┐
   ▼          ▼
Postgres    Redis
(source     (short-lived locks,
 of truth,  pub/sub for live
 UNIQUE     updates, rate
 constraint limiting)
 backstop)
```

**How double-booking is actually prevented (defense in depth):**

1. **Idempotency key** — every booking request carries a client-generated
   key. A retried or double-clicked request returns the original
   reservation instead of creating a second one.
2. **Redis lock** (`app/services/redis_client.py`) — the first user to
   reach the lock for a given `(table_id, slot_start)` proceeds; everyone
   else fails fast, in milliseconds, without touching the database.
3. **Re-check inside the DB transaction** — belt-and-suspenders in case
   the lock expired under extreme load.
4. **PostgreSQL `UNIQUE(table_id, slot_start)` constraint** — the final,
   authoritative guarantee. Even if the first three layers were bypassed
   entirely (a bug, or the app running as multiple replicas that
   briefly disagree), the database itself will reject a second confirmed
   booking for the same table and time. This is what makes the "no
   double booking" claim actually true, not just probable.

## Security

- Passwords are hashed with **bcrypt** (`passlib`) — plaintext passwords
  are never stored or logged anywhere, including in backups.
- Authentication uses short-lived **JWT access tokens** (15 min) plus
  longer-lived **refresh tokens** (7 days), so a leaked access token has
  a small blast radius.
- `/auth/login` and `/auth/register` are **rate-limited per IP** via
  Redis to blunt brute-force and credential-stuffing attempts.
- Login responses take the same code path (and run `verify_password`
  against a dummy hash) whether or not the email exists, to avoid
  leaking which emails are registered via timing or error differences.
- All input is validated with Pydantic before it reaches business logic.

## Backups (so a failure never means losing user data)

`scripts/backup_db.sh` runs `pg_dump` on a schedule (wire it to cron) and
prunes backups older than 14 days. Because passwords are stored as
bcrypt hashes, a backup file is safe to keep around or copy off-site
without turning into a password leak if it's ever exposed. For real
production use, point the script at S3 / Backblaze B2 / another
off-site target right after the local dump completes.

## Running it locally

```bash
cp .env.example .env
docker compose up --build
```

This starts Postgres, Redis, and the API on `http://localhost:8000`
(interactive docs at `/docs`). Then seed some demo data:

```bash
docker compose exec api python -m scripts.seed_demo_data
```

Copy the printed `restaurant_id` into `frontend/app.js`
(`RESTAURANT_ID`), then open `frontend/index.html` in a browser for the
live floor-plan demo.

## Proving it under load

This is the part that actually answers "can it take the pressure":

```bash
export HOT_TABLE_ID=<table_id printed by the seed script>
locust -f load_test/locustfile.py --host http://localhost:8000 \
       --users 100 --spawn-rate 100 --run-time 30s --headless
```

100 simulated users all race to book the exact same table at the exact
same time. Expected (and actual) result: **one `201 Created`, ninety-nine
`409 Conflict`** — zero duplicates, zero crashes. `tests/test_reservation_concurrency.py`
turns this into an automated assertion you can run in CI.

## Project layout

```
app/
  main.py              FastAPI app, startup, CORS, routing
  config.py            All settings, loaded from .env
  security.py          Password hashing, JWT issuing/verification
  dependencies.py      get_current_user / get_current_admin
  models/              SQLAlchemy models (User, Restaurant, Table, Reservation)
  schemas/             Pydantic request/response models
  routers/             auth, users, restaurants, reservations, websocket
  services/            reservation_service (the concurrency logic),
                        redis_client (lock + pub/sub), rate_limit
frontend/              Minimal demo UI (no build step) for the live floor plan
load_test/locustfile.py   The 100-concurrent-user race test
scripts/               seed_demo_data.py, backup_db.sh
tests/                 Automated concurrency proof
```

## Roadmap / what a next iteration would add

- Alembic migrations (currently the demo auto-creates tables on startup
  for a one-command setup; a real deployment would use versioned
  migrations instead).
- Payment integration and a cancellation-window policy.
- 2FA (TOTP or email one-time codes) as an optional login step.
- Structured logging + Prometheus/Grafana dashboards.
