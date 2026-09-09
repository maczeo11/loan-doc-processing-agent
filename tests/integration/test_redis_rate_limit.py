"""
Integration tests for Redis sliding-window rate limiting, active-job spend guards,
idempotency, cancellation release, and fail-closed outage handling.
"""

import io
import os
import pytest
import pytest_asyncio
import fakeredis.aioredis
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from unittest.mock import AsyncMock

from apps.api.main import app
from apps.api.config import settings
from apps.api.db.models import Base
from apps.api.db.session import get_db
from apps.api.middleware.rate_limit import get_redis_client


@pytest_asyncio.fixture
async def rate_limit_env():
    """Sets up an isolated SQLite in-memory database and FakeRedis client."""
    db_url = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = lambda: fake_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield session_factory, client, fake_redis

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_upload_rate_limit_enforced(rate_limit_env):
    """
    Verifies upload allows up to MAX_SUBMISSIONS_PER_MIN requests
    and rejects the next request with 429 Too Many Requests and Retry-After header.
    """
    _, client, _ = rate_limit_env

    # 1. Create an application
    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Upload Rate Limit User", "loan_amount": 100000.0},
    )
    app_id = create_res.json()["application_id"]

    headers = {"X-User-Id": "upload-client-1"}
    pdf_bytes = b"%PDF-1.4 dummy valid payload"

    # Send MAX_SUBMISSIONS_PER_MIN uploads
    limit = settings.MAX_SUBMISSIONS_PER_MIN
    for i in range(limit):
        files = {"file": (f"doc_{i}.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        res = await client.post(f"/applications/{app_id}/documents", files=files, headers=headers)
        assert res.status_code == 201, f"Expected 201 for upload {i+1}, got {res.status_code}"

    # (limit + 1)-th upload must return 429
    files = {"file": ("doc_overflow.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    res_overflow = await client.post(f"/applications/{app_id}/documents", files=files, headers=headers)
    assert res_overflow.status_code == 429
    assert "Retry-After" in res_overflow.headers
    assert int(res_overflow.headers["Retry-After"]) > 0
    assert "rate limit exceeded" in res_overflow.json()["detail"].lower()


@pytest.mark.asyncio
async def test_polling_rate_limit_enforced(rate_limit_env):
    """
    Verifies GET /jobs/{id} allows up to MAX_STATUS_POLLS_PER_MIN requests
    and rejects the next request with 429 and Retry-After header.
    """
    _, client, _ = rate_limit_env
    headers = {"X-User-Id": "poll-client-1"}

    # Seed job via application creation and process
    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Poll Tester", "loan_amount": 50000.0},
    )
    app_id = create_res.json()["application_id"]
    await client.post(
        f"/applications/{app_id}/documents",
        files={"file": ("payslip.pdf", io.BytesIO(b"%PDF-1.4 content"), "application/pdf")},
    )
    proc_res = await client.post(f"/applications/{app_id}/process")
    job_id = proc_res.json()["job_id"]

    limit = settings.MAX_STATUS_POLLS_PER_MIN
    for i in range(limit):
        res = await client.get(f"/jobs/{job_id}", headers=headers)
        assert res.status_code == 200, f"Expected 200 on poll {i+1}, got {res.status_code}"

    # (limit + 1)-th poll must be rejected with 429
    res_overflow = await client.get(f"/jobs/{job_id}", headers=headers)
    assert res_overflow.status_code == 429
    assert "Retry-After" in res_overflow.headers
    assert "polling rate limit exceeded" in res_overflow.json()["detail"].lower()


@pytest.mark.asyncio
async def test_rate_limit_isolates_different_users(rate_limit_env):
    """
    Verifies rate limits isolate distinct user identities.
    User A hitting the limit does not affect User B.
    """
    _, client, _ = rate_limit_env

    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Isolation User", "loan_amount": 50000.0},
    )
    app_id = create_res.json()["application_id"]

    headers_user_a = {"X-User-Id": "user-AAA"}
    headers_user_b = {"X-User-Id": "user-BBB"}
    pdf_bytes = b"%PDF-1.4 content"

    # Exhaust user A
    for i in range(settings.MAX_SUBMISSIONS_PER_MIN):
        files = {"file": (f"doc_{i}.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        await client.post(f"/applications/{app_id}/documents", files=files, headers=headers_user_a)

    # User A is now blocked
    files = {"file": ("overflow.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    res_a = await client.post(f"/applications/{app_id}/documents", files=files, headers=headers_user_a)
    assert res_a.status_code == 429

    # User B should still succeed
    files_b = {"file": ("user_b_doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    res_b = await client.post(f"/applications/{app_id}/documents", files=files_b, headers=headers_user_b)
    assert res_b.status_code == 201


@pytest.mark.asyncio
async def test_spend_guard_active_job_limit_and_user_isolation(rate_limit_env):
    """
    Verifies MAX_ACTIVE_JOBS_PER_USER prevents creating more than configured concurrent jobs
    for a user, while another user remains unaffected.
    """
    _, client, _ = rate_limit_env
    user_a = {"X-User-Id": "heavy-user"}
    user_b = {"X-User-Id": "fresh-user"}

    # Create and queue 2 applications for user_a (reaching MAX_ACTIVE_JOBS_PER_USER = 2)
    for i in range(2):
        app_res = await client.post(
            "/applications",
            json={"applicant_name": f"User A App {i}", "loan_amount": 100000.0},
        )
        a_id = app_res.json()["application_id"]
        await client.post(
            f"/applications/{a_id}/documents",
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4 payload"), "application/pdf")},
        )
        proc_res = await client.post(f"/applications/{a_id}/process", headers=user_a)
        assert proc_res.status_code == 202

    # Attempt 3rd application process for user_a -> must return 429 (active job limit)
    app3_res = await client.post(
        "/applications",
        json={"applicant_name": "User A App 3", "loan_amount": 100000.0},
    )
    a3_id = app3_res.json()["application_id"]
    await client.post(
        f"/applications/{a3_id}/documents",
        files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4 payload"), "application/pdf")},
    )
    proc3_res = await client.post(f"/applications/{a3_id}/process", headers=user_a)
    assert proc3_res.status_code == 429
    assert "active job limit exceeded" in proc3_res.json()["detail"].lower()

    # User B should be able to process their own application without restriction
    b_res = await client.post(
        "/applications",
        json={"applicant_name": "User B App", "loan_amount": 80000.0},
    )
    b_id = b_res.json()["application_id"]
    await client.post(
        f"/applications/{b_id}/documents",
        files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4 payload"), "application/pdf")},
    )
    proc_b_res = await client.post(f"/applications/{b_id}/process", headers=user_b)
    assert proc_b_res.status_code == 202


@pytest.mark.asyncio
async def test_idempotent_processing_does_not_consume_active_job_slots(rate_limit_env):
    """
    Verifies calling /process repeatedly on an already QUEUED application returns
    the existing active job and does NOT consume an additional active-job slot.
    """
    _, client, _ = rate_limit_env
    user_headers = {"X-User-Id": "idempotency-tester"}

    # 1. Create first application and process
    app1_res = await client.post("/applications", json={"applicant_name": "App 1", "loan_amount": 50000.0})
    app1_id = app1_res.json()["application_id"]
    await client.post(f"/applications/{app1_id}/documents", files={"file": ("d.pdf", io.BytesIO(b"%PDF-1.4 x"), "application/pdf")})
    res1 = await client.post(f"/applications/{app1_id}/process", headers=user_headers)
    assert res1.status_code == 202
    job1_id = res1.json()["job_id"]

    # 2. Call process again on App 1 (idempotent request)
    res1_again = await client.post(f"/applications/{app1_id}/process", headers=user_headers)
    assert res1_again.status_code == 202
    assert res1_again.json()["job_id"] == job1_id

    # 3. User should still have capacity for 2nd distinct application (MAX_ACTIVE_JOBS_PER_USER = 2)
    app2_res = await client.post("/applications", json={"applicant_name": "App 2", "loan_amount": 60000.0})
    app2_id = app2_res.json()["application_id"]
    await client.post(f"/applications/{app2_id}/documents", files={"file": ("d.pdf", io.BytesIO(b"%PDF-1.4 x"), "application/pdf")})
    res2 = await client.post(f"/applications/{app2_id}/process", headers=user_headers)
    assert res2.status_code == 202


@pytest.mark.asyncio
async def test_failed_database_processing_releases_spend_guard_slot(rate_limit_env, monkeypatch):
    """
    Verifies that if database commit fails during /process, the reserved active-job slot
    in Redis is cleanly released.
    """
    session_factory, client, fake_redis = rate_limit_env
    user_headers = {"X-User-Id": "tx-fail-user"}

    app_res = await client.post("/applications", json={"applicant_name": "Tx Fail App", "loan_amount": 70000.0})
    app_id = app_res.json()["application_id"]
    await client.post(f"/applications/{app_id}/documents", files={"file": ("d.pdf", io.BytesIO(b"%PDF-1.4 x"), "application/pdf")})

    # Simulate DB commit failure
    async def failing_commit(*args, **kwargs):
        raise RuntimeError("Simulated database failure during job creation")

    monkeypatch.setattr(AsyncSession, "commit", failing_commit)

    with pytest.raises(RuntimeError):
        await client.post(f"/applications/{app_id}/process", headers=user_headers)

    # Verify Redis reservation is empty
    from apps.api.middleware.rate_limit import resolve_user_identity
    from starlette.requests import Request
    identity = resolve_user_identity(Request({"type": "http", "headers": [(b"x-user-id", b"tx-fail-user")]}))
    active_key = f"spend_guard:active:{identity}"
    active_count = await fake_redis.zcard(active_key)
    assert active_count == 0


@pytest.mark.asyncio
async def test_job_cancellation_releases_spend_guard_slot(rate_limit_env):
    """
    Verifies that cancelling an active job releases its spend guard slot,
    allowing the user to queue a subsequent application.
    """
    _, client, _ = rate_limit_env
    user_headers = {"X-User-Id": "cancel-user"}

    # Start 2 jobs for user (reaches MAX_ACTIVE_JOBS_PER_USER = 2)
    job_ids = []
    for i in range(2):
        app_res = await client.post("/applications", json={"applicant_name": f"App {i}", "loan_amount": 50000.0})
        a_id = app_res.json()["application_id"]
        await client.post(f"/applications/{a_id}/documents", files={"file": ("d.pdf", io.BytesIO(b"%PDF-1.4 x"), "application/pdf")})
        proc_res = await client.post(f"/applications/{a_id}/process", headers=user_headers)
        job_ids.append(proc_res.json()["job_id"])

    # 3rd job is blocked
    app3_res = await client.post("/applications", json={"applicant_name": "App 3", "loan_amount": 50000.0})
    a3_id = app3_res.json()["application_id"]
    await client.post(f"/applications/{a3_id}/documents", files={"file": ("d.pdf", io.BytesIO(b"%PDF-1.4 x"), "application/pdf")})
    assert (await client.post(f"/applications/{a3_id}/process", headers=user_headers)).status_code == 429

    # Cancel job 0
    cancel_res = await client.post(f"/jobs/{job_ids[0]}/cancel")
    assert cancel_res.status_code == 200

    # Now 3rd job should succeed!
    proc3_retry = await client.post(f"/applications/{a3_id}/process", headers=user_headers)
    assert proc3_retry.status_code == 202


@pytest.mark.asyncio
async def test_redis_outage_fails_closed_with_503(rate_limit_env):
    """
    Verifies that when Redis is unreachable, upload, process, and polling fail closed
    with HTTP 503 Service Unavailable.
    """
    _, client, fake_redis = rate_limit_env

    # Mock Redis client to simulate an outage
    broken_redis = AsyncMock()
    broken_redis.pipeline.side_effect = ConnectionError("Simulated Redis connection failure")
    broken_redis.zrangebyscore.side_effect = ConnectionError("Simulated Redis connection failure")
    app.dependency_overrides[get_redis_client] = lambda: broken_redis

    # 1. Upload returns 503
    files = {"file": ("d.pdf", io.BytesIO(b"%PDF-1.4 x"), "application/pdf")}
    res_upload = await client.post("/applications/APP-TEST/documents", files=files)
    assert res_upload.status_code == 503
    assert "temporarily unavailable" in res_upload.json()["detail"].lower()

    # 2. Process returns 503 (need an existing application with document)
    app.dependency_overrides[get_redis_client] = lambda: fake_redis
    app_res = await client.post("/applications", json={"applicant_name": "Outage App", "loan_amount": 50000.0})
    app_id = app_res.json()["application_id"]
    await client.post(f"/applications/{app_id}/documents", files=files)

    # Break redis again
    app.dependency_overrides[get_redis_client] = lambda: broken_redis
    res_proc = await client.post(f"/applications/{app_id}/process")
    assert res_proc.status_code == 503

    # 3. Polling returns 503
    res_poll = await client.get("/jobs/JOB-TEST")
    assert res_poll.status_code == 503


@pytest.mark.asyncio
async def test_health_check_not_rate_limited(rate_limit_env):
    """Verifies /health endpoint is exempt from rate limiting."""
    _, client, _ = rate_limit_env
    for _ in range(50):
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_production_request_with_user_id_succeeds(rate_limit_env, monkeypatch):
    """
    Verifies that in production mode, requests supplying a valid X-User-Id header succeed.
    """
    _, client, _ = rate_limit_env
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    headers = {"X-User-Id": "prod-verified-user"}

    # 1. Create application & upload document
    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Prod App", "loan_amount": 120000.0},
    )
    app_id = create_res.json()["application_id"]

    files = {"file": ("salary.pdf", io.BytesIO(b"%PDF-1.4 sample payload"), "application/pdf")}
    upload_res = await client.post(f"/applications/{app_id}/documents", files=files, headers=headers)
    assert upload_res.status_code == 201

    # 2. Trigger process
    proc_res = await client.post(f"/applications/{app_id}/process", headers=headers)
    assert proc_res.status_code == 202
    job_id = proc_res.json()["job_id"]

    # 3. Poll job status
    poll_res = await client.get(f"/jobs/{job_id}", headers=headers)
    assert poll_res.status_code == 200


@pytest.mark.asyncio
async def test_production_request_without_user_id_returns_400(rate_limit_env, monkeypatch):
    """
    Verifies that in production mode, requests without X-User-Id header are rejected
    with 400 Bad Request explaining the temporary demo requirement.
    """
    _, client, _ = rate_limit_env
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    # Create an application and upload a document with valid identity first
    headers_valid = {"X-User-Id": "prod-creator"}
    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Prod Header Tester", "loan_amount": 100000.0},
    )
    app_id = create_res.json()["application_id"]

    files = {"file": ("salary.pdf", io.BytesIO(b"%PDF-1.4 sample payload"), "application/pdf")}
    await client.post(f"/applications/{app_id}/documents", files=files, headers=headers_valid)

    # 1. Upload without X-User-Id returns 400
    upload_res = await client.post(f"/applications/{app_id}/documents", files=files)
    assert upload_res.status_code == 400
    assert "Missing required 'X-User-Id' header" in upload_res.json()["detail"]
    assert "JWT/OIDC integration" in upload_res.json()["detail"]

    # 2. Polling without X-User-Id returns 400
    poll_res = await client.get("/jobs/JOB-TEST")
    assert poll_res.status_code == 400
    assert "Missing required 'X-User-Id' header" in poll_res.json()["detail"]

    # 3. Process without X-User-Id returns 400
    proc_res = await client.post(f"/applications/{app_id}/process")
    assert proc_res.status_code == 400
    assert "Missing required 'X-User-Id' header" in proc_res.json()["detail"]


@pytest.mark.asyncio
async def test_local_fallback_identity_remains_functional(rate_limit_env, monkeypatch):
    """
    Verifies that in local/development mode, requests without X-User-Id header
    fall back to client IP and continue to work.
    """
    _, client, _ = rate_limit_env
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")

    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Local Dev Fallback App", "loan_amount": 90000.0},
    )
    app_id = create_res.json()["application_id"]

    # Upload without X-User-Id header succeeds via IP fallback
    files = {"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4 dummy payload"), "application/pdf")}
    upload_res = await client.post(f"/applications/{app_id}/documents", files=files)
    assert upload_res.status_code == 201

    # Process without X-User-Id header succeeds via IP fallback
    proc_res = await client.post(f"/applications/{app_id}/process")
    assert proc_res.status_code == 202

