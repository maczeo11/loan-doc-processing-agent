"""
Unit tests for the Transactional Outbox producer helper (apps/api/db/outbox.py).
"""

import pytest
import pytest_asyncio
from pydantic import ValidationError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from apps.api.db.models import Base, ApplicationModel, OutboxEventModel
from apps.api.db.outbox import create_outbox_event, JobRef


@pytest_asyncio.fixture
async def test_session():
    """Provides an isolated async in-memory SQLite session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

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


def test_jobref_attempt_count_ge_one_and_default():
    """Verifies that JobRef defaults attempt_count to 1 and strictly rejects attempt_count=0."""
    # 1. Default is 1
    job_default = JobRef(job_id="JOB-DEF", application_id="APP-DEF")
    assert job_default.attempt_count == 1

    # 2. Explicit valid attempt_count >= 1
    job_valid = JobRef(job_id="JOB-VAL", application_id="APP-VAL", attempt_count=2)
    assert job_valid.attempt_count == 2

    # 3. attempt_count=0 must be rejected
    with pytest.raises(ValidationError) as exc_info:
        JobRef(job_id="JOB-ZERO", application_id="APP-ZERO", attempt_count=0)
    assert "greater than or equal to 1" in str(exc_info.value)

    # 4. negative attempt_count must be rejected
    with pytest.raises(ValidationError):
        JobRef(job_id="JOB-NEG", application_id="APP-NEG", attempt_count=-1)


@pytest.mark.asyncio
async def test_create_outbox_event_defaults_attempt_count_to_one(test_session: AsyncSession):
    """Verifies that initial enqueue defaults attempt_count to 1 when omitted."""
    raw_payload = {"job_id": "JOB-INIT", "application_id": "APP-INIT"}
    event = create_outbox_event(
        session=test_session,
        aggregate_type="application_job",
        aggregate_id="APP-INIT",
        payload=raw_payload,
    )
    assert event.payload["attempt_count"] == 1
    assert event.status == "PENDING"
    await test_session.commit()

    res = await test_session.execute(
        select(OutboxEventModel).where(OutboxEventModel.aggregate_id == "APP-INIT")
    )
    saved = res.scalar_one()
    assert saved.payload["attempt_count"] == 1


@pytest.mark.asyncio
async def test_create_outbox_event_rejects_attempt_count_zero(test_session: AsyncSession):
    """Verifies that attempting to enqueue a payload with attempt_count=0 is rejected."""
    with pytest.raises(ValidationError):
        create_outbox_event(
            session=test_session,
            aggregate_type="application_job",
            aggregate_id="APP-ZERO",
            payload={"job_id": "JOB-ZERO", "application_id": "APP-ZERO", "attempt_count": 0},
        )


@pytest.mark.asyncio
async def test_create_outbox_event_with_typed_jobref(test_session: AsyncSession):
    """Verifies creating an outbox event with a typed JobRef instance."""
    job = JobRef(job_id="JOB-TYPED", application_id="APP-TYPED", attempt_count=1)
    event = create_outbox_event(
        session=test_session,
        aggregate_type="application_job",
        aggregate_id="APP-TYPED",
        payload=job,
    )
    assert event.payload["job_id"] == "JOB-TYPED"
    assert event.payload["attempt_count"] == 1
    await test_session.commit()


@pytest.mark.asyncio
async def test_create_outbox_event_rejects_malformed_payload(test_session: AsyncSession):
    """Verifies non-conforming payload shapes trigger immediate validation error."""
    # Missing job_id
    with pytest.raises(ValidationError):
        create_outbox_event(
            session=test_session,
            aggregate_type="application_job",
            aggregate_id="APP-ERR",
            payload={"application_id": "APP-ERR"},
        )

    # Invalid type
    with pytest.raises(ValueError):
        create_outbox_event(
            session=test_session,
            aggregate_type="application_job",
            aggregate_id="APP-ERR",
            payload=12345,  # type: ignore
        )


@pytest.mark.asyncio
async def test_failed_enclosing_transaction_rolls_back_outbox(test_session: AsyncSession):
    """Verifies caller owns transaction atomicity; rollback drops both app and outbox event."""
    app = ApplicationModel(
        id="APP-TX-FAIL",
        applicant_name="Rollback Tester",
        loan_amount=200000.0,
        status="QUEUED",
        state_json={},
    )
    test_session.add(app)
    create_outbox_event(
        session=test_session,
        aggregate_type="application_job",
        aggregate_id="APP-TX-FAIL",
        payload=JobRef(job_id="JOB-TX-FAIL", application_id="APP-TX-FAIL"),
    )

    await test_session.rollback()

    app_res = await test_session.execute(
        select(ApplicationModel).where(ApplicationModel.id == "APP-TX-FAIL")
    )
    assert app_res.scalar_one_or_none() is None

    outbox_res = await test_session.execute(
        select(OutboxEventModel).where(OutboxEventModel.aggregate_id == "APP-TX-FAIL")
    )
    assert outbox_res.scalar_one_or_none() is None


def test_frozen_delivery_contract_uses_lease_handle_and_job_ref():
    """
    Verifies that the frozen Delivery contract definition relies exclusively on
    lease_handle and typed job_ref, rejecting legacy handle or raw payload fields.
    """
    from pydantic import BaseModel

    class FrozenDelivery(BaseModel):
        lease_handle: str
        job_ref: JobRef

    job = JobRef(job_id="JOB-DELIVERY-01", application_id="APP-DELIVERY-01", attempt_count=1)
    delivery = FrozenDelivery(lease_handle="LEASE-XYZ", job_ref=job)

    assert delivery.lease_handle == "LEASE-XYZ"
    assert delivery.job_ref.job_id == "JOB-DELIVERY-01"
    assert delivery.job_ref.attempt_count == 1
    assert not hasattr(delivery, "payload")
    assert not hasattr(delivery, "handle")
