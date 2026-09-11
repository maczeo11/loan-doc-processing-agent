"""
Regression tests for spend-guard slot reclamation.

Only explicit cancellation ever released an active-job slot. A job that
SUCCEEDED kept its reservation for the full TTL, so after two completed
dossiers the next /process returned 429 "wait for ongoing processing to
complete" for 15 minutes while nothing was running.
"""

import fakeredis.aioredis
import pytest

from apps.api.middleware.spend_guard import (
    release_active_job_by_id,
    reserve_active_job_slot,
)


@pytest.fixture
def redis_client():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.mark.asyncio
async def test_finished_jobs_free_their_slots(redis_client):
    finished = {"JOB-A", "JOB-B"}

    async def resolve_finished(ids):
        return {i for i in ids if i in finished}

    assert await reserve_active_job_slot(redis_client, "user-1", "JOB-A", max_active=2)
    assert await reserve_active_job_slot(redis_client, "user-1", "JOB-B", max_active=2)

    # Without the resolver the third request is refused: both slots look busy.
    assert not await reserve_active_job_slot(redis_client, "user-1", "JOB-C", max_active=2)

    # With it, the two completed jobs give their slots back.
    assert await reserve_active_job_slot(
        redis_client, "user-1", "JOB-C", max_active=2,
        resolve_finished_job_ids=resolve_finished,
    )


@pytest.mark.asyncio
async def test_running_jobs_keep_their_slots(redis_client):
    """The guard must still bite while work is genuinely in flight."""

    async def resolve_finished(ids):
        return set()  # everything still running

    assert await reserve_active_job_slot(redis_client, "user-2", "JOB-A", max_active=2)
    assert await reserve_active_job_slot(redis_client, "user-2", "JOB-B", max_active=2)
    assert not await reserve_active_job_slot(
        redis_client, "user-2", "JOB-C", max_active=2,
        resolve_finished_job_ids=resolve_finished,
    )


@pytest.mark.asyncio
async def test_partial_reclaim_frees_only_finished_slots(redis_client):
    async def resolve_finished(ids):
        return {i for i in ids if i == "JOB-A"}

    assert await reserve_active_job_slot(redis_client, "user-3", "JOB-A", max_active=2)
    assert await reserve_active_job_slot(redis_client, "user-3", "JOB-B", max_active=2)

    # JOB-A's slot is reclaimed, so JOB-C fits...
    assert await reserve_active_job_slot(
        redis_client, "user-3", "JOB-C", max_active=2,
        resolve_finished_job_ids=resolve_finished,
    )
    # ...but JOB-B still holds the other, so JOB-D does not.
    assert not await reserve_active_job_slot(
        redis_client, "user-3", "JOB-D", max_active=2,
        resolve_finished_job_ids=resolve_finished,
    )


@pytest.mark.asyncio
async def test_unknown_reservation_is_treated_as_stale(redis_client):
    """A job id Redis holds but the database has never seen cannot be running."""

    async def resolve_finished(ids):
        known_running = {"JOB-B"}
        return {i for i in ids if i not in known_running}

    assert await reserve_active_job_slot(redis_client, "user-4", "JOB-GHOST", max_active=2)
    assert await reserve_active_job_slot(redis_client, "user-4", "JOB-B", max_active=2)
    assert await reserve_active_job_slot(
        redis_client, "user-4", "JOB-C", max_active=2,
        resolve_finished_job_ids=resolve_finished,
    )


@pytest.mark.asyncio
async def test_explicit_release_still_works(redis_client):
    """Cancellation keeps its direct path; reclamation is an addition, not a
    replacement."""
    assert await reserve_active_job_slot(redis_client, "user-5", "JOB-A", max_active=1)
    assert not await reserve_active_job_slot(redis_client, "user-5", "JOB-B", max_active=1)

    await release_active_job_by_id(redis_client, "JOB-A")
    assert await reserve_active_job_slot(redis_client, "user-5", "JOB-B", max_active=1)


@pytest.mark.asyncio
async def test_resolver_failure_falls_back_to_ttl_behaviour(redis_client):
    """A broken resolver must not crash /process; the guard just stays strict."""

    async def broken(ids):
        raise RuntimeError("database unavailable")

    assert await reserve_active_job_slot(redis_client, "user-6", "JOB-A", max_active=1)
    assert not await reserve_active_job_slot(
        redis_client, "user-6", "JOB-B", max_active=1, resolve_finished_job_ids=broken
    )
