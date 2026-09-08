"""
Integration tests for Transactional Outbox Dispatcher (apps/api/db/outbox.py & outbox_dispatcher.py).
"""

import asyncio
import pytest
import pytest_asyncio
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from apps.api.db.models import Base, OutboxEventModel
from apps.api.db.outbox import create_outbox_event, dispatch_pending_outbox_events, JobRef
from adapters.queue.base import QueuePort


class InMemoryMockQueue(QueuePort):
    """
    Mock QueuePort capturing publications and enforcing typed JobRef contract.
    """

    def __init__(self, fail_count: int = 0):
        self.published_jobs: List[JobRef] = []
        self.fail_count = fail_count
        self.attempts = 0

    def publish(self, job_ref: Any) -> None:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise RuntimeError(f"Simulated SQS/Postgres transport error (attempt {self.attempts})")
        
        # Inviolable contract: Queue publishing must receive a typed JobRef
        assert isinstance(job_ref, JobRef), f"Expected typed JobRef instance, got {type(job_ref)}"
        assert job_ref.attempt_count >= 1, f"attempt_count must be >= 1, got {job_ref.attempt_count}"
        self.published_jobs.append(job_ref)

    def receive(self, max_n: int = 1) -> List[Any]:
        return []

    def extend_lease(self, handle: str, seconds: int) -> None:
        pass

    def ack(self, handle: str) -> None:
        pass

    def fail(self, handle: str, retryable: bool) -> None:
        pass


@pytest_asyncio.fixture
async def test_session_factory():
    """Provides an isolated async SQLite engine and session factory."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    yield session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_successful_outbox_dispatch_publishes_typed_jobref(test_session_factory):
    """
    Verifies that pending outbox events are validated against frozen JobRef,
    passed as typed JobRef instances to queue.publish(), and marked PUBLISHED.
    """
    queue = InMemoryMockQueue()

    # 1. Seed two pending events with default attempt_count=1
    async with test_session_factory() as session:
        create_outbox_event(
            session,
            aggregate_type="application_job",
            aggregate_id="APP-D-01",
            payload=JobRef(job_id="JOB-D-01", application_id="APP-D-01"),
        )
        create_outbox_event(
            session,
            aggregate_type="application_job",
            aggregate_id="APP-D-02",
            payload={"job_id": "JOB-D-02", "application_id": "APP-D-02"},  # defaults attempt_count to 1
        )
        await session.commit()

    # 2. Run dispatcher
    async with test_session_factory() as dispatch_session:
        stats = await dispatch_pending_outbox_events(
            session=dispatch_session,
            queue=queue,
            batch_size=10,
            max_retries=3,
        )

    assert stats["claimed"] == 2
    assert stats["published"] == 2
    assert stats["failed"] == 0
    assert len(queue.published_jobs) == 2

    # Verify typed JobRef properties on published items
    job1 = queue.published_jobs[0]
    assert isinstance(job1, JobRef)
    assert job1.job_id == "JOB-D-01"
    assert job1.attempt_count == 1

    job2 = queue.published_jobs[1]
    assert isinstance(job2, JobRef)
    assert job2.job_id == "JOB-D-02"
    assert job2.attempt_count == 1

    # 3. Verify database state
    async with test_session_factory() as verify_session:
        events = (await verify_session.execute(select(OutboxEventModel))).scalars().all()
        for ev in events:
            assert ev.status == "PUBLISHED"
            assert ev.published_at is not None
            assert ev.last_error is None


@pytest.mark.asyncio
async def test_dispatch_publish_failure_and_retry(test_session_factory):
    """
    Verifies that a transport failure increments retry_count, records last_error,
    and leaves the event PENDING for subsequent retry until max_retries.
    """
    # Fails 2 times, then succeeds
    queue = InMemoryMockQueue(fail_count=2)

    # 1. Seed 1 pending event
    async with test_session_factory() as session:
        create_outbox_event(
            session,
            aggregate_type="application_job",
            aggregate_id="APP-RETRY-01",
            payload=JobRef(job_id="JOB-RETRY-01", application_id="APP-RETRY-01", attempt_count=1),
        )
        await session.commit()

    # 2. First dispatch attempt -> fails
    async with test_session_factory() as s1:
        stats1 = await dispatch_pending_outbox_events(s1, queue, batch_size=10, max_retries=3)
    assert stats1["claimed"] == 1
    assert stats1["published"] == 0
    assert stats1["retried"] == 1

    async with test_session_factory() as v1:
        ev1 = (await v1.execute(select(OutboxEventModel))).scalar_one()
        assert ev1.status == "PENDING"
        assert ev1.retry_count == 1
        assert "Simulated SQS/Postgres transport error" in ev1.last_error

    # 3. Second dispatch attempt -> fails again
    async with test_session_factory() as s2:
        stats2 = await dispatch_pending_outbox_events(s2, queue, batch_size=10, max_retries=3)
    assert stats2["retried"] == 1

    async with test_session_factory() as v2:
        ev2 = (await v2.execute(select(OutboxEventModel))).scalar_one()
        assert ev2.status == "PENDING"
        assert ev2.retry_count == 2

    # 4. Third dispatch attempt -> succeeds!
    async with test_session_factory() as s3:
        stats3 = await dispatch_pending_outbox_events(s3, queue, batch_size=10, max_retries=3)
    assert stats3["published"] == 1

    async with test_session_factory() as v3:
        ev3 = (await v3.execute(select(OutboxEventModel))).scalar_one()
        assert ev3.status == "PUBLISHED"
        assert ev3.published_at is not None
        assert ev3.last_error is None


@pytest.mark.asyncio
async def test_dispatch_exceeding_max_retries_marks_failed(test_session_factory):
    """Verifies that an event exceeding max_retries transitions to FAILED."""
    queue = InMemoryMockQueue(fail_count=999)  # Always fails

    async with test_session_factory() as session:
        create_outbox_event(
            session,
            aggregate_type="application_job",
            aggregate_id="APP-FAIL-01",
            payload=JobRef(job_id="JOB-FAIL-01", application_id="APP-FAIL-01", attempt_count=1),
        )
        await session.commit()

    # Retry 3 times with max_retries=3
    for _ in range(3):
        async with test_session_factory() as dispatch_session:
            await dispatch_pending_outbox_events(dispatch_session, queue, batch_size=10, max_retries=3)

    async with test_session_factory() as v:
        ev = (await v.execute(select(OutboxEventModel))).scalar_one()
        assert ev.status == "FAILED"
        assert ev.retry_count == 3
        assert ev.published_at is None
        assert "transport error" in ev.last_error


@pytest.mark.asyncio
async def test_invalid_payload_does_not_crash_batch(test_session_factory):
    """
    Verifies that a malformed payload is recorded as an error on that specific event,
    and valid events in the same batch are still processed cleanly.
    """
    queue = InMemoryMockQueue()

    async with test_session_factory() as session:
        # Event 1: Valid
        create_outbox_event(
            session,
            aggregate_type="application_job",
            aggregate_id="APP-GOOD",
            payload=JobRef(job_id="JOB-GOOD", application_id="APP-GOOD", attempt_count=1),
        )
        # Event 2: Corrupted payload manually inserted (attempt_count=0 violates contract)
        corrupted = OutboxEventModel(
            id="CORRUPTED-EV-01",
            aggregate_type="application_job",
            aggregate_id="APP-BAD",
            payload={"job_id": "JOB-BAD", "application_id": "APP-BAD", "attempt_count": 0},
            status="PENDING",
        )
        session.add(corrupted)
        await session.commit()

    async with test_session_factory() as dispatch_session:
        stats = await dispatch_pending_outbox_events(
            session=dispatch_session,
            queue=queue,
            batch_size=10,
            max_retries=2,
        )

    assert stats["claimed"] == 2
    assert stats["published"] == 1  # Good event published
    assert stats["retried"] == 1    # Bad event flagged validation error

    assert len(queue.published_jobs) == 1
    assert queue.published_jobs[0].job_id == "JOB-GOOD"

    async with test_session_factory() as v:
        bad_ev = (await v.execute(select(OutboxEventModel).where(OutboxEventModel.id == "CORRUPTED-EV-01"))).scalar_one()
        assert "validation error" in bad_ev.last_error.lower()
        assert bad_ev.status == "PENDING"
