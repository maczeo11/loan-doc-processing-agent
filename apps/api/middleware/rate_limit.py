"""
Redis sliding-window rate limiting and client identity middleware for FinScan AI.

Core Rules:
- Enforce MAX_SUBMISSIONS_PER_MIN for document uploads.
- Enforce MAX_STATUS_POLLS_PER_MIN for job status polling.
- Identity: X-User-Id header, falling back to client IP in local development.
- Key namespacing and sha256 hashing for tenant isolation.
- Atomic sliding-window evaluation via Redis WATCH / MULTI / EXEC.
- Fail-closed in production with HTTP 503 Service Unavailable on Redis outage.
"""

import time
import uuid
import hashlib
import logging
from typing import Optional, Tuple
from fastapi import Request, HTTPException, status, Depends
import redis.asyncio as aioredis

from apps.api.config import settings

logger = logging.getLogger("finscan.rate_limit")

_redis_client: Optional[aioredis.Redis] = None
_local_fake_redis: Optional[any] = None
_last_test_db_override: Optional[int] = None


async def get_redis_client() -> aioredis.Redis:
    """
    FastAPI dependency and lifecycle provider for async Redis client.
    In local development, falls back to in-memory fake if local Redis is offline.
    In cloud/production, strictly connects to configured REDIS_URL.
    """
    global _redis_client, _local_fake_redis, _last_test_db_override

    if _redis_client is not None:
        return _redis_client

    if settings.ENVIRONMENT in ("cloud", "production"):
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
            socket_timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
        )
        return _redis_client

    # Local development / CI mode: Try real Redis, fall back to fakeredis if offline
    try:
        candidate = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )
        await candidate.ping()
        _redis_client = candidate
        return _redis_client
    except Exception:
        # In test environments where each test configures an isolated DB session fixture,
        # automatically provide an aligned fresh in-memory FakeRedis instance
        try:
            from apps.api.main import app
            from apps.api.db.session import get_db

            current_db_override = app.dependency_overrides.get(get_db)
            if current_db_override is not None:
                override_id = id(current_db_override)
                if _last_test_db_override != override_id:
                    import fakeredis.aioredis
                    _last_test_db_override = override_id
                    _local_fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
                    return _local_fake_redis
        except Exception:
            pass

        if _local_fake_redis is None:
            import fakeredis.aioredis
            logger.info("Local Redis offline. Using in-memory FakeRedis for local development.")
            _local_fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        return _local_fake_redis


async def close_redis_client():
    """Safely closes active Redis connection on application shutdown."""
    global _redis_client, _local_fake_redis, _last_test_db_override
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception as err:
            logger.warning(f"Error closing Redis client: {err}")
        _redis_client = None
    _local_fake_redis = None
    _last_test_db_override = None


def resolve_user_identity(request: Request) -> str:
    """
    Resolves client identity for rate limiting and spend guard controls.

    Strategy:
    - Extracts non-empty X-User-Id header when supplied.
    - In development/local mode, falls back to request.client.host if X-User-Id is absent.
    - In production/cloud mode, strictly requires a non-empty X-User-Id header; raises HTTP 400 Bad Request
      if absent or empty, explaining that the demo identity header is required until JWT/OIDC integration exists.
      Never uses a shared 'anonymous' identity in production to prevent noisy-neighbor lockouts.

    TEMPORARY NOTE:
    This header-based identity strategy is a development / buildathon demo mechanism.
    Production deployments must replace this with verified JWT/OIDC claims
    (e.g., Cognito, Keycloak, or Auth0) extracted from Authorization tokens.
    """
    user_id = request.headers.get("x-user-id")
    if user_id and user_id.strip():
        raw_id = user_id.strip()
    elif settings.ENVIRONMENT in ("local", "development"):
        raw_id = request.client.host if request.client else "127.0.0.1"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Missing required 'X-User-Id' header. "
                "Demo identity header is required in production until JWT/OIDC integration exists."
            ),
        )

    # Safely hash identity to prevent key injection and special character collisions
    identity_hash = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:16]
    return identity_hash


async def check_sliding_window_rate_limit(
    redis_client: aioredis.Redis,
    key: str,
    limit: int,
    window_seconds: float = 60.0,
    max_retries: int = 5,
) -> Tuple[bool, int, int]:
    """
    Evaluates sliding-window rate limit using atomic Redis WATCH / MULTI / EXEC.
    Returns: (allowed: bool, remaining_tokens: int, retry_after_seconds: int)
    """
    for _ in range(max_retries):
        try:
            async with redis_client.pipeline(transaction=True) as pipe:
                await pipe.watch(key)
                now = time.time()
                cutoff = now - window_seconds
                req_id = f"{now}:{uuid.uuid4().hex[:8]}"

                current_entries = await redis_client.zrangebyscore(key, cutoff, "+inf", withscores=True)
                current_count = len(current_entries)

                if current_count >= limit:
                    await pipe.unwatch()
                    oldest_time = current_entries[0][1]
                    retry_after = max(1, int(oldest_time + window_seconds - now) + 1)
                    return False, 0, retry_after

                pipe.multi()
                pipe.zremrangebyscore(key, "-inf", cutoff)
                pipe.zadd(key, {req_id: now})
                pipe.expire(key, int(window_seconds) + 5)
                await pipe.execute()
                remaining = max(0, limit - current_count - 1)
                return True, remaining, 0
        except Exception as e:
            # Handle concurrent conflict retry
            if "WatchError" in str(type(e)):
                continue
            raise

    return False, 0, int(window_seconds)


async def rate_limit_upload(
    request: Request,
    redis_client: aioredis.Redis = Depends(get_redis_client),
):
    """
    FastAPI dependency enforcing upload submission rate limit (MAX_SUBMISSIONS_PER_MIN).
    Fails closed with 503 on Redis outage.
    """
    identity = resolve_user_identity(request)
    key = f"rate_limit:upload:{identity}"
    limit = settings.MAX_SUBMISSIONS_PER_MIN

    try:
        allowed, remaining, retry_after = await check_sliding_window_rate_limit(
            redis_client=redis_client,
            key=key,
            limit=limit,
            window_seconds=60.0,
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Upload rate limit exceeded ({limit} per minute). Please retry in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Redis rate limiter error for upload: {err}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Coordination service temporarily unavailable. Cannot verify upload rate limit.",
        )


async def rate_limit_polling(
    request: Request,
    redis_client: aioredis.Redis = Depends(get_redis_client),
):
    """
    FastAPI dependency enforcing job status polling rate limit (MAX_STATUS_POLLS_PER_MIN).
    Fails closed with 503 on Redis outage.
    """
    identity = resolve_user_identity(request)
    key = f"rate_limit:poll:{identity}"
    limit = settings.MAX_STATUS_POLLS_PER_MIN

    try:
        allowed, remaining, retry_after = await check_sliding_window_rate_limit(
            redis_client=redis_client,
            key=key,
            limit=limit,
            window_seconds=60.0,
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Job polling rate limit exceeded ({limit} per minute). Please retry in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Redis rate limiter error for polling: {err}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Coordination service temporarily unavailable. Cannot verify polling rate limit.",
        )
