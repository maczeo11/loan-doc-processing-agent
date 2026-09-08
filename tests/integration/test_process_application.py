"""
Integration tests for atomic application processing enqueue (POST /applications/{id}/process).
"""

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from apps.api.main import app
from apps.api.db.models import Base, ApplicationModel, JobModel, OutboxEventModel
from apps.api.db.session import get_db
from apps.api.db.outbox import JobRef


@pytest_asyncio.fixture
async def test_env():
    """
    Sets up an isolated test database and an AsyncClient with get_db override.
    """
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

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield session_factory, client

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_process_application_atomically_creates_job_and_outbox(test_env):
    """
    Verifies POST /applications/{id}/process atomically sets status to QUEUED,
    creates exactly one JobModel, and inserts one OutboxEventModel with valid JobRef.
    """
    session_factory, client = test_env

    # 1. Create initial application
    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Priya Nair", "loan_amount": 900000.0},
    )
    assert create_res.status_code == 201
    app_id = create_res.json()["application_id"]

    # 2. Trigger processing
    proc_res = await client.post(f"/applications/{app_id}/process")
    assert proc_res.status_code == 202
    data = proc_res.json()
    assert data["application_id"] == app_id
    assert data["status"] == "QUEUED"
    job_id = data["job_id"]
    assert job_id.startswith("JOB-")

    # 3. Verify PostgreSQL authoritative state
    async with session_factory() as session:
        app_model = (await session.execute(
            select(ApplicationModel).where(ApplicationModel.id == app_id)
        )).scalar_one()

        assert app_model.status == "QUEUED"
        history = app_model.state_json["status_history"]
        assert len(history) == 2
        assert history[-1]["from_status"] == "UPLOADED"
        assert history[-1]["to_status"] == "QUEUED"

        # Exactly one JobModel exists
        jobs = (await session.execute(
            select(JobModel).where(JobModel.application_id == app_id)
        )).scalars().all()
        assert len(jobs) == 1
        assert jobs[0].id == job_id
        assert jobs[0].status == "QUEUED"
        assert jobs[0].attempt_count == 1

        # Exactly one OutboxEventModel exists
        outbox_events = (await session.execute(
            select(OutboxEventModel).where(OutboxEventModel.aggregate_id == app_id)
        )).scalars().all()
        assert len(outbox_events) == 1
        outbox_ev = outbox_events[0]
        assert outbox_ev.status == "PENDING"
        assert outbox_ev.aggregate_type == "application_job"

        # Stored payload validates against exact JobRef contract
        validated_job = JobRef.model_validate(outbox_ev.payload)
        assert validated_job.job_id == job_id
        assert validated_job.application_id == app_id
        assert validated_job.attempt_count == 1


@pytest.mark.asyncio
async def test_process_unknown_application_returns_404(test_env):
    """Verifies process request returns 404 for nonexistent application."""
    _, client = test_env
    res = await client.post("/applications/APP-NONEXISTENT/process")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_process_idempotency_returns_existing_active_job(test_env):
    """
    Verifies that calling /process repeatedly on an already QUEUED application
    does not create duplicate jobs or outbox events, but returns the existing active job.
    """
    session_factory, client = test_env

    # 1. Create and process application
    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Idempotent Applicant", "loan_amount": 500000.0},
    )
    app_id = create_res.json()["application_id"]

    res1 = await client.post(f"/applications/{app_id}/process")
    assert res1.status_code == 202
    job_id_1 = res1.json()["job_id"]

    # 2. Call /process second time
    res2 = await client.post(f"/applications/{app_id}/process")
    assert res2.status_code == 202
    job_id_2 = res2.json()["job_id"]
    assert job_id_1 == job_id_2  # Same active job returned

    # 3. Confirm count in database is still exactly 1 job and 1 outbox event
    async with session_factory() as session:
        jobs = (await session.execute(
            select(JobModel).where(JobModel.application_id == app_id)
        )).scalars().all()
        assert len(jobs) == 1

        outbox_events = (await session.execute(
            select(OutboxEventModel).where(OutboxEventModel.aggregate_id == app_id)
        )).scalars().all()
        assert len(outbox_events) == 1


@pytest.mark.asyncio
async def test_invalid_state_transition_rejected_with_conflict(test_env):
    """
    Verifies that applications in terminal or review states (e.g. READY_FOR_REVIEW)
    cannot be queued for processing and return 409 Conflict.
    """
    session_factory, client = test_env

    # 1. Seed application already in READY_FOR_REVIEW status
    app_id = "APP-TERMINAL-01"
    async with session_factory() as session:
        app = ApplicationModel(
            id=app_id,
            applicant_name="Review Ready User",
            loan_amount=400000.0,
            status="READY_FOR_REVIEW",
            state_json={"status": "READY_FOR_REVIEW", "status_history": []},
        )
        session.add(app)
        await session.commit()

    # 2. Attempt to trigger processing -> 409 Conflict
    res = await client.post(f"/applications/{app_id}/process")
    assert res.status_code == 409
    data = res.json()
    assert "cannot be transitioned to queued" in data["detail"].lower()


@pytest.mark.asyncio
async def test_forced_transaction_failure_leaves_no_partial_data(test_env, monkeypatch):
    """
    Verifies that if an error occurs during processing enqueue before commit,
    the application status is not modified and no orphan job or outbox event is persisted.
    """
    session_factory, client = test_env

    # 1. Create application
    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Failure Tester", "loan_amount": 350000.0},
    )
    app_id = create_res.json()["application_id"]

    # 2. Monkeypatch create_outbox_event to raise an exception simulating error
    import apps.api.routes.applications as apps_route
    original_create_outbox = apps_route.create_outbox_event

    def failing_create_outbox(*args, **kwargs):
        raise RuntimeError("Simulated failure during outbox event creation")

    monkeypatch.setattr(apps_route, "create_outbox_event", failing_create_outbox)

    # 3. Call process -> must fail with internal error / exception
    with pytest.raises(RuntimeError):
        await client.post(f"/applications/{app_id}/process")

    # 4. Verify PostgreSQL: Application status remains UPLOADED, 0 jobs, 0 outbox events
    async with session_factory() as session:
        app_model = (await session.execute(
            select(ApplicationModel).where(ApplicationModel.id == app_id)
        )).scalar_one()
        assert app_model.status == "UPLOADED"

        jobs = (await session.execute(
            select(JobModel).where(JobModel.application_id == app_id)
        )).scalars().all()
        assert len(jobs) == 0

        outbox_events = (await session.execute(
            select(OutboxEventModel).where(OutboxEventModel.aggregate_id == app_id)
        )).scalars().all()
        assert len(outbox_events) == 0
