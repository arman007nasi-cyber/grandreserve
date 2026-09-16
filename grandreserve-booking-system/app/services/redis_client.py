import redis.asyncio as redis

from app.config import settings

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


class TableLock:
    """
    A short-lived Redis lock scoped to one (table_id, slot_start) pair.

    This is the *first* line of defense against double-booking: when 100
    users hit "Book" for the same table/time at once, only one of them
    acquires the lock and proceeds to the database transaction; the other
    99 fail fast (in milliseconds, without ever touching Postgres) and get
    a clear "already booked" response.

    The database UNIQUE constraint on (table_id, slot_start) is the
    *second*, authoritative line of defense -- it guarantees correctness
    even if the lock is skipped, expires early, or the app runs as
    multiple replicas that briefly disagree.
    """

    def __init__(self, table_id: str, slot_start: str, ttl_seconds: int = 10):
        self._key = f"lock:table:{table_id}:{slot_start}"
        self._ttl = ttl_seconds
        self._acquired = False

    async def __aenter__(self) -> bool:
        # NX = only set if not already set -> atomic "acquire lock" check.
        self._acquired = bool(await redis_client.set(self._key, "1", nx=True, ex=self._ttl))
        return self._acquired

    async def __aexit__(self, exc_type, exc, tb):
        if self._acquired:
            await redis_client.delete(self._key)
