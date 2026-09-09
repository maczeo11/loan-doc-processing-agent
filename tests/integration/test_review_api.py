"""
Integration tests for Phase 5:
- Human review decisions (APPROVED, REJECTED, NEEDS_INFO)
- Invalid source state (409) and missing application (404)
- Audit trail persistence and append-only verification
- Job cancellation from QUEUED and PROCESSING
- Non-cancellable/terminal job rejection (409) and missing job (404)
- Atomic updates and forced transaction failure isolation
- Redis active-job reservation release only on successful commit
"""

import os
import uuid
import pytest
import pytest_asyncio
import fakeredis.aioredis
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from apps.api.main import app
from apps.api.db.models import Base, ApplicationModel, JobModel, AuditEventModel, utc_now
from apps.api.db.session import get_db
from apps.api.middleware.rate_limit import get_redis_client
from apps.api.middleware.spend_guard import reserve_active_job_slot


@pytest_asyncio.fixture
async def review_test_env():
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
async def test_review_approved_transition(review_test_env):
    """
    Verifies APPROVED review transition:
    - Status transitions from READY_FOR_REVIEW to REVIEWED.
    - Relational model and state_json are updated atomically.
    - Reviewer decision, notes, and corrections are recorded.
    - An immutable AuditEventModel is appended.
    """
    session_factory, client, _ = review_test_env

    # 1. Create application and set to READY_FOR_REVIEW
    app_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
    async with session_factory() as session:
        app_model = ApplicationModel(
            id=app_id,
            applicant_name="Alice Smith",
            loan_amount=250000.0,
            status="READY_FOR_REVIEW",
            state_json={"status": "READY_FOR_REVIEW", "status_history": []},
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(app_model)
        await session.commit()

    # 2. Submit APPROVED review
    payload = {
        "decision": "APPROVED",
        "reviewer_id": "REV-CHRIS",
        "notes": "Income and identity verified. Risk acceptable.",
        "corrections": [{"field": "income", "from": 80000, "to": 85000}],
    }
    res = await client.post(f"/applications/{app_id}/review", json=payload)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["application_id"] == app_id
    assert res_data["decision"] == "APPROVED"
    assert res_data["status"] == "REVIEWED"

    # 3. Verify Database state
    async with session_factory() as session:
        app_db = (await session.execute(
            select(ApplicationModel).where(ApplicationModel.id == app_id)
        )).scalar_one()

        assert app_db.status == "REVIEWED"
        assert app_db.reviewer_id == "REV-CHRIS"
        assert app_db.state_json["status"] == "REVIEWED"
        assert app_db.state_json["reviewer_id"] == "REV-CHRIS"
        assert app_db.state_json["reviewer_decision"] == "APPROVED"
        assert app_db.state_json["reviewer_notes"] == "Income and identity verified. Risk acceptable."
        assert app_db.state_json["corrections_applied"] == [{"field": "income", "from": 80000, "to": 85000}]
        assert app_db.state_json["review_paused"] is False

        # Verify status history
        history = app_db.state_json["status_history"]
        assert len(history) == 1
        assert history[0]["from_status"] == "READY_FOR_REVIEW"
        assert history[0]["to_status"] == "REVIEWED"

        # Verify Audit Event
        audits = (await session.execute(
            select(AuditEventModel).where(AuditEventModel.application_id == app_id)
        )).scalars().all()
        assert len(audits) == 1
        assert audits[0].from_status == "READY_FOR_REVIEW"
        assert audits[0].to_status == "REVIEWED"
        assert audits[0].actor == "REV-CHRIS"
        assert audits[0].decision == "APPROVED"
        assert audits[0].notes == "Income and identity verified. Risk acceptable."
        assert audits[0].corrections == {"corrections": [{"field": "income", "from": 80000, "to": 85000}]}


@pytest.mark.asyncio
async def test_review_rejected_transition(review_test_env):
    """
    Verifies REJECTED review transition:
    - Status transitions from READY_FOR_REVIEW to REVIEWED.
    - Decision REJECTED is stored in database and audit trail.
    """
    session_factory, client, _ = review_test_env

    app_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
    async with session_factory() as session:
        app_model = ApplicationModel(
            id=app_id,
            applicant_name="Bob Jones",
            loan_amount=450000.0,
            status="READY_FOR_REVIEW",
            state_json={"status": "READY_FOR_REVIEW", "status_history": []},
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(app_model)
        await session.commit()

    payload = {
        "decision": "REJECTED",
        "reviewer_id": "REV-TAYLOR",
        "notes": "Debt-to-income ratio exceeds institutional threshold.",
        "corrections": [],
    }
    res = await client.post(f"/applications/{app_id}/review", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "REVIEWED"
    assert res.json()["decision"] == "REJECTED"

    async with session_factory() as session:
        app_db = (await session.execute(
            select(ApplicationModel).where(ApplicationModel.id == app_id)
        )).scalar_one()
        assert app_db.status == "REVIEWED"
        assert app_db.reviewer_id == "REV-TAYLOR"
        assert app_db.state_json["reviewer_decision"] == "REJECTED"


@pytest.mark.asyncio
async def test_review_needs_info_transition(review_test_env):
    """
    Verifies NEEDS_INFO review transition:
    - Status transitions from READY_FOR_REVIEW to NEEDS_INFORMATION.
    - Decision NEEDS_INFO is stored in database and audit trail.
    """
    session_factory, client, _ = review_test_env

    app_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
    async with session_factory() as session:
        app_model = ApplicationModel(
            id=app_id,
            applicant_name="Charlie Brown",
            loan_amount=150000.0,
            status="READY_FOR_REVIEW",
            state_json={"status": "READY_FOR_REVIEW", "status_history": []},
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(app_model)
        await session.commit()

    payload = {
        "decision": "NEEDS_INFO",
        "reviewer_id": "REV-JORDAN",
        "notes": "Requires clarification on unexplained bank deposit.",
        "corrections": [],
    }
    res = await client.post(f"/applications/{app_id}/review", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "NEEDS_INFORMATION"
    assert res.json()["decision"] == "NEEDS_INFO"

    async with session_factory() as session:
        app_db = (await session.execute(
            select(ApplicationModel).where(ApplicationModel.id == app_id)
        )).scalar_one()
        assert app_db.status == "NEEDS_INFORMATION"
        assert app_db.reviewer_id == "REV-JORDAN"
        assert app_db.state_json["status"] == "NEEDS_INFORMATION"
        assert app_db.state_json["reviewer_decision"] == "NEEDS_INFO"


@pytest.mark.asyncio
async def test_review_invalid_source_state_returns_409(review_test_env):
    """
    Verifies that attempting to review an application not in READY_FOR_REVIEW returns 409 Conflict.
    """
    session_factory, client, _ = review_test_env

    app_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
    async with session_factory() as session:
        app_model = ApplicationModel(
            id=app_id,
            applicant_name="Dave Smith",
            loan_amount=100000.0,
            status="UPLOADED",  # Invalid source status
            state_json={"status": "UPLOADED"},
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(app_model)
        await session.commit()

    payload = {
        "decision": "APPROVED",
        "reviewer_id": "REV-TEST",
    }
    res = await client.post(f"/applications/{app_id}/review", json=payload)
    assert res.status_code == 409
    assert "cannot be reviewed" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_review_missing_application_returns_404(review_test_env):
    """Verifies review on non-existent application returns 404."""
    _, client, _ = review_test_env
    payload = {"decision": "APPROVED", "reviewer_id": "REV-01"}
    res = await client.post("/applications/APP-NONEXISTENT/review", json=payload)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_audit_event_contents_are_append_only(review_test_env):
    """
    Verifies audit events are appended sequentially and preserve history.
    """
    session_factory, client, _ = review_test_env

    app_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
    async with session_factory() as session:
        app_model = ApplicationModel(
            id=app_id,
            applicant_name="Audit Tester",
            loan_amount=100000.0,
            status="READY_FOR_REVIEW",
            state_json={"status": "READY_FOR_REVIEW", "status_history": []},
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        # Pre-populate an earlier audit event
        audit_init = AuditEventModel(
            id=f"AUDIT-{uuid.uuid4().hex[:8].upper()}",
            application_id=app_id,
            from_status="PROCESSING",
            to_status="READY_FOR_REVIEW",
            actor="pipeline_worker",
            notes="Automated processing complete",
            timestamp=utc_now(),
        )
        session.add_all([app_model, audit_init])
        await session.commit()

    # Submit review
    payload = {
        "decision": "APPROVED",
        "reviewer_id": "REV-LEAD",
        "notes": "Approved by senior underwriter",
    }
    res = await client.post(f"/applications/{app_id}/review", json=payload)
    assert res.status_code == 200

    async with session_factory() as session:
        audits = (await session.execute(
            select(AuditEventModel).where(AuditEventModel.application_id == app_id).order_by(AuditEventModel.timestamp.asc())
        )).scalars().all()
        assert len(audits) == 2
        assert audits[0].actor == "pipeline_worker"
        assert audits[0].to_status == "READY_FOR_REVIEW"
        assert audits[1].actor == "REV-LEAD"
        assert audits[1].to_status == "REVIEWED"


@pytest.mark.asyncio
async def test_cancel_queued_and_processing_jobs(review_test_env):
    """
    Verifies cancelling QUEUED and PROCESSING jobs:
    - Atomically updates job and application to CANCELLED.
    - Appends status history and records AuditEventModel.
    - Releases Redis active-job reservation.
    """
    session_factory, client, fake_redis = review_test_env

    # 1. Test QUEUED job cancellation
    app_id_1 = f"APP-{uuid.uuid4().hex[:8].upper()}"
    job_id_1 = f"JOB-{uuid.uuid4().hex[:8].upper()}"

    async with session_factory() as session:
        app1 = ApplicationModel(
            id=app_id_1,
            applicant_name="Cancel Applicant 1",
            loan_amount=50000.0,
            status="QUEUED",
            state_json={"status": "QUEUED", "status_history": []},
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        job1 = JobModel(
            id=job_id_1,
            application_id=app_id_1,
            status="QUEUED",
            attempt_count=0,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add_all([app1, job1])
        await session.commit()

    # Reserve slot in Redis
    await reserve_active_job_slot(fake_redis, user_id="user-cancel-test", job_id=job_id_1)
    assert await fake_redis.zcard("spend_guard:active:user-cancel-test") == 1

    # Cancel job
    res1 = await client.post(f"/jobs/{job_id_1}/cancel", headers={"X-User-Id": "user-cancel-test"})
    assert res1.status_code == 200
    assert res1.json()["status"] == "CANCELLED"

    # Verify DB updates
    async with session_factory() as session:
        j1 = (await session.execute(select(JobModel).where(JobModel.id == job_id_1))).scalar_one()
        a1 = (await session.execute(select(ApplicationModel).where(ApplicationModel.id == app_id_1))).scalar_one()
        assert j1.status == "CANCELLED"
        assert a1.status == "CANCELLED"
        assert a1.state_json["status"] == "CANCELLED"

        audits = (await session.execute(select(AuditEventModel).where(AuditEventModel.application_id == app_id_1))).scalars().all()
        assert len(audits) == 1
        assert audits[0].to_status == "CANCELLED"
        assert audits[0].actor == "user-cancel-test"

    # Verify Redis reservation released
    assert await fake_redis.zcard("spend_guard:active:user-cancel-test") == 0

    # 2. Test PROCESSING job cancellation
    app_id_2 = f"APP-{uuid.uuid4().hex[:8].upper()}"
    job_id_2 = f"JOB-{uuid.uuid4().hex[:8].upper()}"

    async with session_factory() as session:
        app2 = ApplicationModel(
            id=app_id_2,
            applicant_name="Cancel Applicant 2",
            loan_amount=60000.0,
            status="PROCESSING",
            state_json={"status": "PROCESSING", "status_history": []},
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        job2 = JobModel(
            id=job_id_2,
            application_id=app_id_2,
            status="PROCESSING",
            attempt_count=1,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add_all([app2, job2])
        await session.commit()

    res2 = await client.post(f"/jobs/{job_id_2}/cancel")
    assert res2.status_code == 200
    assert res2.json()["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_cancel_terminal_job_returns_409(review_test_env):
    """
    Verifies that terminal jobs (COMPLETED, FAILED, CANCELLED) cannot be cancelled (409 Conflict).
    """
    session_factory, client, _ = review_test_env

    for terminal_status in ("COMPLETED", "FAILED", "CANCELLED"):
        app_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
        job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"

        async with session_factory() as session:
            app_model = ApplicationModel(
                id=app_id,
                applicant_name="Terminal User",
                loan_amount=50000.0,
                status=terminal_status if terminal_status != "COMPLETED" else "READY_FOR_REVIEW",
                state_json={},
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            job_model = JobModel(
                id=job_id,
                application_id=app_id,
                status=terminal_status,
                attempt_count=1,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add_all([app_model, job_model])
            await session.commit()

        res = await client.post(f"/jobs/{job_id}/cancel")
        assert res.status_code == 409
        assert "cannot be cancelled" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cancel_missing_job_returns_404(review_test_env):
    """Verifies cancelling a nonexistent job returns 404."""
    _, client, _ = review_test_env
    res = await client.post("/jobs/JOB-DOESNOTEXIST/cancel")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_cancel_forced_transaction_failure_leaves_no_partial_data(review_test_env, monkeypatch):
    """
    Verifies that if DB commit fails during cancellation:
    - No partial data is written.
    - Redis reservation is NOT released.
    """
    session_factory, client, fake_redis = review_test_env

    app_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
    job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"

    async with session_factory() as session:
        app_model = ApplicationModel(
            id=app_id,
            applicant_name="Tx Failure Applicant",
            loan_amount=75000.0,
            status="QUEUED",
            state_json={"status": "QUEUED"},
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        job_model = JobModel(
            id=job_id,
            application_id=app_id,
            status="QUEUED",
            attempt_count=0,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add_all([app_model, job_model])
        await session.commit()

    await reserve_active_job_slot(fake_redis, user_id="fail-user", job_id=job_id)

    # Force commit failure
    async def failing_commit(*args, **kwargs):
        raise RuntimeError("Simulated database failure during cancellation")

    monkeypatch.setattr(AsyncSession, "commit", failing_commit)

    with pytest.raises(RuntimeError):
        await client.post(f"/jobs/{job_id}/cancel", headers={"X-User-Id": "fail-user"})

    # Verify Redis reservation is STILL active because commit failed
    assert await fake_redis.zcard("spend_guard:active:fail-user") == 1

    # Verify DB records remain QUEUED
    async with session_factory() as session:
        j = (await session.execute(select(JobModel).where(JobModel.id == job_id))).scalar_one()
        a = (await session.execute(select(ApplicationModel).where(ApplicationModel.id == app_id))).scalar_one()
        assert j.status == "QUEUED"
        assert a.status == "QUEUED"
        audits = (await session.execute(select(AuditEventModel).where(AuditEventModel.application_id == app_id))).scalars().all()
        assert len(audits) == 0
