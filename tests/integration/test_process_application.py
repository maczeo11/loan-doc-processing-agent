"""
Integration tests for application processing enqueue:
- POST /applications/{id}/process
- GET  /jobs/{id}
- Atomicity: Status transition, JobModel creation, and Outbox event creation commit together
- Idempotency: Duplicate calls return existing active job without creating new jobs or outbox records
- Document presence validation: At least one document required before queueing
- JobRef metadata: Persisted document IDs and document manifest passed to worker
"""

import io
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from apps.api.main import app
from apps.api.db.models import Base, ApplicationModel, JobModel, OutboxEventModel, DocumentModel
from apps.api.db.session import get_db
from apps.api.routes.applications import JobRef


@pytest_asyncio.fixture
async def test_env():
    """Sets up an isolated in-memory test database and AsyncClient."""
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
async def test_process_application_without_documents_fails_with_409(test_env):
    """
    Verifies POST /applications/{id}/process without any uploaded documents
    returns 409 Conflict and creates 0 jobs or outbox events.
    """
    session_factory, client = test_env

    # 1. Create application without documents
    create_res = await client.post(
        "/applications",
        json={"applicant_name": "No Doc Applicant", "loan_amount": 300000.0},
    )
    assert create_res.status_code == 201
    app_id = create_res.json()["application_id"]

    # 2. Call process -> must fail with 409
    proc_res = await client.post(f"/applications/{app_id}/process")
    assert proc_res.status_code == 409
    assert "no uploaded documents" in proc_res.json()["detail"].lower()

    # 3. Confirm 0 jobs and 0 outbox events exist
    async with session_factory() as session:
        jobs = (await session.execute(
            select(JobModel).where(JobModel.application_id == app_id)
        )).scalars().all()
        assert len(jobs) == 0

        outbox = (await session.execute(
            select(OutboxEventModel).where(OutboxEventModel.aggregate_id == app_id)
        )).scalars().all()
        assert len(outbox) == 0


@pytest.mark.asyncio
async def test_process_application_atomically_creates_job_and_outbox(test_env):
    """
    Verifies POST /applications/{id}/process with an uploaded document atomically
    sets status to QUEUED, creates exactly one JobModel, and inserts one OutboxEventModel with valid JobRef.
    """
    session_factory, client = test_env

    # 1. Create initial application
    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Priya Nair", "loan_amount": 900000.0},
    )
    assert create_res.status_code == 201
    app_id = create_res.json()["application_id"]

    # 2. Upload required document
    files = {"file": ("payslip.pdf", io.BytesIO(b"%PDF-1.4 valid dummy pdf payload"), "application/pdf")}
    upload_res = await client.post(f"/applications/{app_id}/documents", files=files)
    assert upload_res.status_code == 201
    uploaded_doc_id = upload_res.json()["document_id"]

    # 3. Trigger processing
    proc_res = await client.post(f"/applications/{app_id}/process")
    assert proc_res.status_code == 202
    data = proc_res.json()
    assert data["application_id"] == app_id
    assert data["status"] == "QUEUED"
    job_id = data["job_id"]
    assert job_id.startswith("JOB-")

    # 4. Verify PostgreSQL authoritative state
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
        assert validated_job.priority == 0
        assert validated_job.created_at is not None
        assert validated_job.metadata["document_ids"] == [uploaded_doc_id]
        assert uploaded_doc_id in validated_job.metadata["document_manifest"]


@pytest.mark.asyncio
async def test_process_populates_multiple_documents_metadata(test_env):
    """
    Verifies that when multiple documents are uploaded, JobRef.metadata correctly
    reflects all persisted document IDs and their storage URIs.
    """
    session_factory, client = test_env

    # 1. Create application
    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Multi Doc Applicant", "loan_amount": 750000.0},
    )
    app_id = create_res.json()["application_id"]

    # 2. Upload two distinct documents
    doc1_res = await client.post(
        f"/applications/{app_id}/documents",
        files={"file": ("payslip.pdf", io.BytesIO(b"%PDF-1.4 payslip content"), "application/pdf")},
    )
    doc1_id = doc1_res.json()["document_id"]

    doc2_res = await client.post(
        f"/applications/{app_id}/documents",
        files={"file": ("bank_stmt.pdf", io.BytesIO(b"%PDF-1.4 bank stmt content"), "application/pdf")},
    )
    doc2_id = doc2_res.json()["document_id"]

    # 3. Process application
    proc_res = await client.post(f"/applications/{app_id}/process")
    assert proc_res.status_code == 202

    # 4. Verify JobRef metadata matches persisted document records
    async with session_factory() as session:
        outbox_ev = (await session.execute(
            select(OutboxEventModel).where(OutboxEventModel.aggregate_id == app_id)
        )).scalar_one()

        validated_job = JobRef.model_validate(outbox_ev.payload)
        assert set(validated_job.metadata["document_ids"]) == {doc1_id, doc2_id}

        manifest = validated_job.metadata["document_manifest"]
        assert doc1_id in manifest
        assert doc2_id in manifest

        # Confirm URIs match DocumentModel rows
        docs = (await session.execute(
            select(DocumentModel).where(DocumentModel.application_id == app_id)
        )).scalars().all()
        doc_uri_map = {d.id: d.storage_uri for d in docs}
        assert manifest == doc_uri_map


@pytest.mark.asyncio
async def test_get_job_status_success_and_404(test_env):
    """
    Verifies GET /jobs/{id} returns 404 for nonexistent job and returns
    authoritative JobModel data for a real job.
    """
    session_factory, client = test_env

    # 1. Non-existent job returns 404
    res_404 = await client.get("/jobs/JOB-NONEXISTENT")
    assert res_404.status_code == 404

    # 2. Create application, upload doc, process to create job
    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Job Status User", "loan_amount": 200000.0},
    )
    app_id = create_res.json()["application_id"]
    await client.post(
        f"/applications/{app_id}/documents",
        files={"file": ("tax_return.pdf", io.BytesIO(b"%PDF-1.4 tax doc"), "application/pdf")},
    )

    proc_res = await client.post(f"/applications/{app_id}/process")
    job_id = proc_res.json()["job_id"]

    # 3. Query GET /jobs/{job_id}
    job_res = await client.get(f"/jobs/{job_id}")
    assert job_res.status_code == 200
    job_data = job_res.json()
    assert job_data["job_id"] == job_id
    assert job_data["application_id"] == app_id
    assert job_data["status"] == "QUEUED"
    assert job_data["attempt_count"] == 1
    assert job_data["error_message"] is None


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

    # 1. Create application and upload document
    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Idempotent Applicant", "loan_amount": 500000.0},
    )
    app_id = create_res.json()["application_id"]
    files = {"file": ("bank_stmt.pdf", io.BytesIO(b"%PDF-1.4 dummy payload"), "application/pdf")}
    await client.post(f"/applications/{app_id}/documents", files=files)

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

    # 1. Create application and upload document
    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Failure Tester", "loan_amount": 350000.0},
    )
    app_id = create_res.json()["application_id"]
    files = {"file": ("id_proof.pdf", io.BytesIO(b"%PDF-1.4 dummy payload"), "application/pdf")}
    await client.post(f"/applications/{app_id}/documents", files=files)

    # 2. Monkeypatch create_outbox_event to raise an exception simulating failure
    import apps.api.routes.applications as apps_route

    def failing_create_outbox(*args, **kwargs):
        raise RuntimeError("Simulated failure during outbox event creation")

    monkeypatch.setattr(apps_route, "create_outbox_event", failing_create_outbox)

    # 3. Call process -> must fail with exception
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
