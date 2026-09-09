"""
Shared integration-test fixtures for the FastAPI suite.
Owned by Member 1 (Manjunath); rate-isolation helper added for Balaji's API tests.

Every integration test gets a private in-memory FakeRedis for rate limiting, so
sliding-window counters can never leak across tests — whether the machine runs a
real Redis (local dev with docker) or none at all (CI runners).
"""

import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def _isolated_rate_limit_redis():
    """Overrides the rate-limiter Redis dependency with a per-test FakeRedis."""
    import fakeredis.aioredis

    from apps.api.main import app
    from apps.api.middleware.rate_limit import close_redis_client, get_redis_client

    await close_redis_client()
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    app.dependency_overrides[get_redis_client] = lambda: fake
    yield
    app.dependency_overrides.pop(get_redis_client, None)
    await close_redis_client()
