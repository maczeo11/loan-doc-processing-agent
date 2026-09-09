"""
Unit tests for Redis sliding-window rate limiter, client identity resolution,
and active-job spend guard primitives.
"""

import time
import pytest
import fakeredis.aioredis
from starlette.requests import Request

from apps.api.config import settings
from apps.api.middleware.rate_limit import (
    resolve_user_identity,
    check_sliding_window_rate_limit,
)
from apps.api.middleware.spend_guard import (
    reserve_active_job_slot,
    release_active_job_slot,
    release_active_job_by_id,
)


def make_mock_request(headers: dict = None, client_host: str = "192.168.1.100") -> Request:
    """Constructs a minimal Starlette request mock for identity testing."""
    raw_headers = []
    if headers:
        for k, v in headers.items():
            raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": raw_headers,
        "client": (client_host, 12345),
    }
    return Request(scope)


def test_resolve_user_identity_with_header():
    """Verifies X-User-Id header takes precedence and produces consistent sha256 hash."""
    req1 = make_mock_request(headers={"X-User-Id": "user-alpha"}, client_host="10.0.0.1")
    req2 = make_mock_request(headers={"X-User-Id": "user-alpha"}, client_host="10.0.0.2")
    req3 = make_mock_request(headers={"X-User-Id": "user-beta"}, client_host="10.0.0.1")

    id1 = resolve_user_identity(req1)
    id2 = resolve_user_identity(req2)
    id3 = resolve_user_identity(req3)

    assert id1 == id2
    assert id1 != id3
    assert len(id1) == 16


def test_resolve_user_identity_fallback_dev(monkeypatch):
    """Verifies development mode falls back to client IP address when header is absent."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")

    req_ip1 = make_mock_request(headers={}, client_host="192.168.1.50")
    req_ip2 = make_mock_request(headers={}, client_host="192.168.1.51")

    hash1 = resolve_user_identity(req_ip1)
    hash2 = resolve_user_identity(req_ip2)

    assert hash1 != hash2
    assert len(hash1) == 16


def test_resolve_user_identity_production_requires_header(monkeypatch):
    """Verifies production mode strictly requires X-User-Id and rejects absent/empty header with 400."""
    from fastapi import HTTPException
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    # 1. Completely absent header
    req_absent = make_mock_request(headers={}, client_host="192.168.1.50")
    with pytest.raises(HTTPException) as exc_info:
        resolve_user_identity(req_absent)
    assert exc_info.value.status_code == 400
    assert "Missing required 'X-User-Id' header" in exc_info.value.detail
    assert "JWT/OIDC integration" in exc_info.value.detail

    # 2. Empty or whitespace-only header
    req_empty = make_mock_request(headers={"X-User-Id": "   "}, client_host="192.168.1.50")
    with pytest.raises(HTTPException) as exc_info2:
        resolve_user_identity(req_empty)
    assert exc_info2.value.status_code == 400


def test_resolve_user_identity_production_with_valid_header(monkeypatch):
    """Verifies production mode succeeds and hashes identity when X-User-Id is provided."""
    import hashlib
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    req = make_mock_request(headers={"X-User-Id": "prod-user-99"}, client_host="192.168.1.50")
    user_hash = resolve_user_identity(req)

    expected = hashlib.sha256(b"prod-user-99").hexdigest()[:16]
    assert user_hash == expected
    assert len(user_hash) == 16


@pytest.mark.asyncio
async def test_sliding_window_rate_limit_allows_and_rejects():
    """Verifies sliding-window allows requests up to limit and rejects subsequent requests."""
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    key = "rl:test:user1"
    limit = 3

    # First 3 requests must be allowed
    for i in range(limit):
        allowed, remaining, retry_after = await check_sliding_window_rate_limit(
            fake_redis, key=key, limit=limit, window_seconds=60.0
        )
        assert allowed is True
        assert remaining == (limit - 1 - i)
        assert retry_after == 0

    # 4th request must be rejected
    allowed, remaining, retry_after = await check_sliding_window_rate_limit(
        fake_redis, key=key, limit=limit, window_seconds=60.0
    )
    assert allowed is False
    assert remaining == 0
    assert retry_after > 0


@pytest.mark.asyncio
async def test_sliding_window_isolates_different_users():
    """Verifies that user A exhausting rate limit does not block user B."""
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    key_a = "rl:test:userA"
    key_b = "rl:test:userB"
    limit = 2

    # Exhaust user A
    for _ in range(limit):
        allowed, _, _ = await check_sliding_window_rate_limit(fake_redis, key=key_a, limit=limit)
        assert allowed is True

    allowed_a, _, _ = await check_sliding_window_rate_limit(fake_redis, key=key_a, limit=limit)
    assert allowed_a is False

    # User B should still be allowed
    allowed_b, remaining_b, _ = await check_sliding_window_rate_limit(fake_redis, key=key_b, limit=limit)
    assert allowed_b is True
    assert remaining_b == 1


@pytest.mark.asyncio
async def test_reserve_and_release_active_job_spend_guard():
    """Verifies MAX_ACTIVE_JOBS_PER_USER enforcement and release functionality."""
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    user_id = "user_guard_1"
    max_active = 2

    # Reserve 2 jobs (up to max_active)
    res1 = await reserve_active_job_slot(fake_redis, user_id=user_id, job_id="JOB-01", max_active=max_active)
    assert res1 is True

    res2 = await reserve_active_job_slot(fake_redis, user_id=user_id, job_id="JOB-02", max_active=max_active)
    assert res2 is True

    # 3rd reservation exceeds limit and must return False
    res3 = await reserve_active_job_slot(fake_redis, user_id=user_id, job_id="JOB-03", max_active=max_active)
    assert res3 is False

    # Release JOB-01 -> user should be able to reserve JOB-03
    await release_active_job_slot(fake_redis, user_id=user_id, job_id="JOB-01")

    res3_retry = await reserve_active_job_slot(fake_redis, user_id=user_id, job_id="JOB-03", max_active=max_active)
    assert res3_retry is True


@pytest.mark.asyncio
async def test_release_active_job_by_id_reverse_index():
    """Verifies that release_active_job_by_id finds user via reverse index and clears slot."""
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    user_id = "user_guard_2"

    await reserve_active_job_slot(fake_redis, user_id=user_id, job_id="JOB-REV-1", max_active=1)

    # Limit reached
    assert await reserve_active_job_slot(fake_redis, user_id=user_id, job_id="JOB-REV-2", max_active=1) is False

    # Release by job_id only
    await release_active_job_by_id(fake_redis, job_id="JOB-REV-1")

    # Now can reserve JOB-REV-2
    assert await reserve_active_job_slot(fake_redis, user_id=user_id, job_id="JOB-REV-2", max_active=1) is True