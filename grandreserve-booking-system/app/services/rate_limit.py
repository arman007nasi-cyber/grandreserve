from fastapi import HTTPException, Request, status

from app.services.redis_client import redis_client


async def enforce_rate_limit(request: Request, bucket: str, limit: int, window_seconds: int) -> None:
    """
    Fixed-window rate limiter keyed by client IP + bucket name (e.g.
    "login"). Protects the login and register endpoints from
    brute-force / credential-stuffing attempts without needing any
    extra infrastructure beyond the Redis instance we already run.
    """
    client_ip = request.client.host if request.client else "unknown"
    key = f"ratelimit:{bucket}:{client_ip}"

    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, window_seconds)

    if current > limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Too many attempts. Please try again in a minute.",
        )
