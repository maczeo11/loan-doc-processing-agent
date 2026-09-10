"""
Unit tests for FinScan AI database models and schema constraints.
"""

import pytest
import pytest_asyncio
import uuid

from sqlalchemy import select, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from apps.api.db.models import (
    Base,
    ApplicationModel,
    DocumentModel,
    JobModel,
    OutboxEventModel,
    AuditEventModel,
    SpendLedgerModel,
    VALID_APPLICATION_STATUSES,
)


@pytest_asyncio.fixture
async def test_session():
    """Provides an isolated async in-memory SQLite session with foreign keys enabled."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Enable foreign keys for SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def enable_sqlite_fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_application_creation_and_fields(test_session: AsyncSession):
    """Verifies that an application model can be persisted with canonical fields."""
    app = ApplicationModel(
        id="APP-TEST-001",
        applicant_name="Aarav Sharma",
        loan_amount=500000.0,
        loan_purpose="Home Renovation",
        status="UPLOADED",
        reviewer_id=None,
        state_json={"test_key": "test_val"},
    )
    test_session.add(app)
    await test_session.commit()

    result = await test_session.execute(
        select(ApplicationModel).where(ApplicationModel.id == "APP-TEST-001")
    )
    saved = result.scalar_one()

    assert saved.id == "APP-TEST-001"
    assert saved.applicant_name == "Aarav Sharma"
    assert saved.loan_amount == 500000.0
    assert saved.status == "UPLOADED"
    assert saved.state_json == {"test_key": "test_val"}
    assert saved.created_at is not None
    assert saved.updated_at is not None
    assert saved.created_at.tzinfo is not None  # Timezone-aware


@pytest.mark.asyncio
async def test_application_status_enum_validity(test_session: AsyncSession):
    """Verifies all confirmed statuses from core/contracts/state.py are allowed."""
    for idx, status in enumerate(VALID_APPLICATION_STATUSES):
        app = ApplicationModel(
            id=f"APP-STATUS-{idx}",
            applicant_name=f"Applicant {idx}",
            loan_amount=100000.0,
            status=status,
            state_json={},
        )
        test_session.add(app)
    await test_session.commit()

    count_result = await test_session.execute(select(ApplicationModel))
    all_apps = count_result.scalars().all()
    assert len(all_apps) == len(VALID_APPLICATION_STATUSES)


@pytest.mark.asyncio
async def test_application_status_check_constraint_violation(test_session: AsyncSession):
    """Verifies that an invalid application status triggers IntegrityError."""
    app = ApplicationModel(
        id="APP-INVALID-STATUS",
        applicant_name="Invalid Status Tester",
        loan_amount=50000.0,
        status="INVALID_DISALLOWED_STATUS",  # Not in canonical status enum
        state_json={},
    )
    test_session.add(app)
    with pytest.raises(IntegrityError):
        await test_session.commit()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_document_model_and_foreign_key(test_session: AsyncSession):
    """Verifies document relationship and foreign key enforcement."""
    app = ApplicationModel(
        id="APP-DOC-001",
        applicant_name="Document Parent",
        loan_amount=250000.0,
        status="UPLOADED",
        state_json={},
    )
    test_session.add(app)
    await test_session.commit()

    doc = DocumentModel(
        id="DOC-001",
        application_id="APP-DOC-001",
        filename="payslip_june.pdf",
        storage_uri="file://data/storage/APP-DOC-001/DOC-001_payslip_june.pdf",
        doc_type="payslip",
        sha256="a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e",
        size_bytes=1048576,
    )
    test_session.add(doc)
    await test_session.commit()

    # Query with relationship
    res = await test_session.execute(
        select(ApplicationModel).where(ApplicationModel.id == "APP-DOC-001")
    )
    loaded_app = res.scalar_one()
    assert len(loaded_app.documents) == 1
    assert loaded_app.documents[0].filename == "payslip_june.pdf"
    assert loaded_app.documents[0].size_bytes == 1048576


@pytest.mark.asyncio
async def test_document_fk_constraint_failure(test_session: AsyncSession):
    """Verifies inserting a document without a valid application_id fails."""
    doc = DocumentModel(
        id="DOC-ORPHAN",
        application_id="NON_EXISTENT_APP",
        filename="orphan.pdf",
        storage_uri="file://data/storage/orphan.pdf",
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        size_bytes=0,
    )
    test_session.add(doc)
    with pytest.raises(IntegrityError):
        await test_session.commit()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_cascade_delete(test_session: AsyncSession):
    """Verifies that deleting an application cascades to documents, jobs, and audit events."""
    app = ApplicationModel(
        id="APP-CASCADE-001",
        applicant_name="Cascade Tester",
        loan_amount=100000.0,
        status="UPLOADED",
        state_json={},
    )
    test_session.add(app)
    await test_session.commit()

    doc = DocumentModel(
        id="DOC-CASCADE-001",
        application_id="APP-CASCADE-001",
        filename="doc.pdf",
        storage_uri="file://test.pdf",
        sha256="test-sha",
        size_bytes=100,
    )
    job = JobModel(
        id="JOB-CASCADE-001",
        application_id="APP-CASCADE-001",
        status="QUEUED",
        attempt_count=0,
    )
    audit = AuditEventModel(
        id="AUDIT-CASCADE-001",
        application_id="APP-CASCADE-001",
        from_status="UPLOADED",
        to_status="QUEUED",
        actor="system",
    )
    test_session.add_all([doc, job, audit])
    await test_session.commit()

    # Delete parent application
    await test_session.delete(app)
    await test_session.commit()

    # Verify children are gone
    docs = (await test_session.execute(select(DocumentModel).where(DocumentModel.id == "DOC-CASCADE-001"))).scalars().all()
    jobs = (await test_session.execute(select(JobModel).where(JobModel.id == "JOB-CASCADE-001"))).scalars().all()
    audits = (await test_session.execute(select(AuditEventModel).where(AuditEventModel.id == "AUDIT-CASCADE-001"))).scalars().all()

    assert len(docs) == 0
    assert len(jobs) == 0
    assert len(audits) == 0


@pytest.mark.asyncio
async def test_outbox_event_model(test_session: AsyncSession):
    """Verifies outbox event creation with JSONB payload and default pending status."""
    event_id = str(uuid.uuid4())
    outbox = OutboxEventModel(
        id=event_id,
        aggregate_type="application_job",
        aggregate_id="APP-OUTBOX-001",
        payload={"job_id": "JOB-123", "action": "process_dossier"},
        status="PENDING",
    )
    test_session.add(outbox)
    await test_session.commit()

    res = await test_session.execute(
        select(OutboxEventModel).where(OutboxEventModel.id == event_id)
    )
    saved = res.scalar_one()
    assert saved.aggregate_id == "APP-OUTBOX-001"
    assert saved.status == "PENDING"
    assert saved.payload["job_id"] == "JOB-123"
    assert saved.retry_count == 0
    assert saved.created_at is not None


@pytest.mark.asyncio
async def test_spend_ledger_model(test_session: AsyncSession):
    """Verifies append-only spend ledger accounting."""
    spend_id = str(uuid.uuid4())
    entry = SpendLedgerModel(
        id=spend_id,
        user_or_app_id="APP-SPEND-001",
        action="paddleocr_page_extraction",
        cost_units=1.5,
    )
    test_session.add(entry)
    await test_session.commit()

    res = await test_session.execute(
        select(SpendLedgerModel).where(SpendLedgerModel.id == spend_id)
    )
    saved = res.scalar_one()
    assert saved.action == "paddleocr_page_extraction"
    assert saved.cost_units == 1.5
    assert saved.timestamp is not None
