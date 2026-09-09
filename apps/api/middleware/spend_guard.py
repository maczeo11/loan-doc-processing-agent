"""
Active-job spend guard middleware for FinScan AI.

Rules:
- Enforce MAX_ACTIVE_JOBS_PER_USER per identified client.
- Atomically reserve an active-job slot before initiating processing.
- Bounded configurable reservation TTL (SPEND_GUARD_RESERVATION_TTL_SECONDS).
- Release reservation on database transaction failure or explicit cancellation.
- Idempotent processing calls returning existing jobs do NOT consume extra slots.
- Worker completion integration note: Terminal job state updates (SUCCEEDED, FAILED)
  require an upstream worker hook (Bhanu) to invoke release_active_job_by_id;
  TTL provides an autonomous safety backstop.
"""

import time
import logging
from typing import Optional
from fastapi import HTTPException, status
import redis.asyncio as aioredis

from apps.api.config import settings

logger = logging.getLogger("finscan.spend_guard")


async def reserve_active_job_slot(
    redis_client: aioredis.Redis,
    user_id: str,
    job_id: str,
    max_active: int = settings.MAX_ACTIVE_JOBS_PER_USER,
    ttl_seconds: int = settings.SPEND_GUARD_RESERVATION_TTL_SECONDS,
    max_retries: int = 5,
) -> bool:
    """
    Atomically reserves one active-job slot for the user.
    Returns True if slot reserved; False if user has reached max_active.
    Raises HTTPException(503) on Redis failure.
    """
    active_key = f"spend_guard:active:{user_id}"
    job_map_key = f"spend_guard:job_user:{job_id}"

    try:
        for _ in range(max_retries):
            try:
                async with redis_client.pipeline(transaction=True) as pipe:
                    await pipe.watch(active_key)
                    now = time.time()

                    # Retrieve current active non-expired reservations
                    active_jobs = await redis_client.zrangebyscore(active_key, now, "+inf")
                    if len(active_jobs) >= max_active:
                        await pipe.unwatch()
                        return False

                    pipe.multi()
                    # Clean expired entries
                    pipe.zremrangebyscore(active_key, "-inf", now)
                    # Add new reservation with score = expire_timestamp
                    pipe.zadd(active_key, {job_id: now + ttl_seconds})
                    pipe.expire(active_key, ttl_seconds + 60)
                    # Set reverse lookup for cancellation
                    pipe.set(job_map_key, user_id, ex=ttl_seconds + 60)
                    await pipe.execute()
                    return True
            except Exception as watch_err:
                if "WatchError" in str(type(watch_err)):
                    continue
                raise
        return False
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Redis spend guard error reserving slot for user '{user_id}': {err}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Coordination service temporarily unavailable. Cannot verify active job limits.",
        )


async def release_active_job_slot(
    redis_client: aioredis.Redis,
    user_id: str,
    job_id: str,
) -> None:
    """
    Releases an active-job slot for a specific user and job.
    """
    active_key = f"spend_guard:active:{user_id}"
    job_map_key = f"spend_guard:job_user:{job_id}"

    try:
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.zrem(active_key, job_id)
            pipe.delete(job_map_key)
            await pipe.execute()
    except Exception as err:
        logger.warning(f"Failed to release active job slot '{job_id}' for user '{user_id}': {err}")


async def release_active_job_by_id(
    redis_client: aioredis.Redis,
    job_id: str,
) -> None:
    """
    Releases active-job slot by looking up user identity from reverse index.
    Invoked when a job is cancelled or completes.
    """
    job_map_key = f"spend_guard:job_user:{job_id}"
    try:
        user_id = await redis_client.get(job_map_key)
        if user_id:
            await release_active_job_slot(redis_client, user_id, job_id)
    except Exception as err:
        logger.warning(f"Failed to release active job slot for job '{job_id}' by id: {err}")