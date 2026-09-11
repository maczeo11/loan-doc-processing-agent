"""
Regression tests for worker failure write-back.

A pipeline exception or a DLQ-routed poison message used to leave the
application pinned at QUEUED forever: the worker called queue.fail() but never
wrote a status back, so the reviewer UI polled a spinner with no error, no
terminal state, and no way out.
"""

import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from apps.api.db.models import ApplicationModel, Base, JobModel, utc_now
from core.contracts.jobs import JobRef
from worker.consumer import ApplicationWorker
from worker.persistence import persist_job_failure


@pytest.fixture
def sync_db(tmp_path):
    """File-backed SQLite so the worker's own sync engine sees the same data."""
    db_path = tmp_path / "worker.sqlite3"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield url, factory
    engine.dispose()


def _seed(factory, status="QUEUED"):
    app_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
    job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"
    with factory() as session:
        session.add(
            ApplicationModel(
                id=app_id,
                applicant_name="Failure Path",
                loan_amount=100000.0,
                status=status,
                state_json={"status": status, "status_history": []},
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        )
        session.add(
            JobModel(
                id=job_id,
                application_id=app_id,
                status=status,
                attempt_count=1,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        )
        session.commit()
    return app_id, job_id


def test_terminal_failure_marks_application_failed(sync_db):
    url, factory = sync_db
    app_id, job_id = _seed(factory)

    persist_job_failure(
        db_url=url,
        job_id=job_id,
        application_id=app_id,
        error_message="OCR engine crashed",
        terminal=True,
    )

    with factory() as session:
        app_model = session.execute(
            select(ApplicationModel).where(ApplicationModel.id == app_id)
        ).scalar_one()
        job = session.execute(select(JobModel).where(JobModel.id == job_id)).scalar_one()

    assert app_model.status == "FAILED"
    assert app_model.state_json["status"] == "FAILED"
    assert job.status == "FAILED"
    assert "OCR engine crashed" in job.error_message
    # The transition is recorded so the reviewer can see when and why it stopped.
    history = app_model.state_json["status_history"]
    assert history[-1]["to_status"] == "FAILED"
    assert "OCR engine crashed" in history[-1]["reason"]


def test_retryable_failure_keeps_application_queued(sync_db):
    """A redelivery is still expected, so only the job records the error."""
    url, factory = sync_db
    app_id, job_id = _seed(factory)

    persist_job_failure(
        db_url=url,
        job_id=job_id,
        application_id=app_id,
        error_message="transient storage timeout",
        terminal=False,
    )

    with factory() as session:
        app_model = session.execute(
            select(ApplicationModel).where(ApplicationModel.id == app_id)
        ).scalar_one()
        job = session.execute(select(JobModel).where(JobModel.id == job_id)).scalar_one()

    assert app_model.status == "QUEUED"
    assert job.status == "QUEUED"
    assert "transient storage timeout" in job.error_message


class _ExplodingGraph:
    def invoke(self, state, config=None):
        raise RuntimeError("extractor blew up")


class _FakeQueue:
    def __init__(self):
        self.failed = []

    def receive(self, max_n=1):
        return []

    def ack(self, handle):
        raise AssertionError("must not ack a failed job")

    def fail(self, handle, retryable):
        self.failed.append(retryable)

    def extend_lease(self, handle, seconds):
        pass


class _Delivery:
    def __init__(self, job_ref):
        self.job_ref = job_ref
        self.lease_handle = "handle-1"


def test_worker_marks_failed_on_last_attempt(sync_db):
    """On the final delivery attempt the dossier reaches a terminal state
    instead of spinning at QUEUED indefinitely."""
    url, factory = sync_db
    app_id, job_id = _seed(factory)

    queue = _FakeQueue()
    worker = ApplicationWorker(
        queue_adapter=queue,
        graph=_ExplodingGraph(),
        db_url=url,
        max_delivery_attempts=3,
    )
    job_ref = JobRef(
        job_id=job_id,
        application_id=app_id,
        attempt_count=3,  # final attempt
        created_at=utc_now().isoformat(),
        metadata={"document_ids": [], "document_manifest": {}},
    )

    worker.process_delivery(_Delivery(job_ref))

    assert queue.failed == [True]
    with factory() as session:
        app_model = session.execute(
            select(ApplicationModel).where(ApplicationModel.id == app_id)
        ).scalar_one()
    assert app_model.status == "FAILED"


def test_worker_keeps_queued_on_early_attempt(sync_db):
    """An early failure stays retryable; the dossier must not be marked FAILED
    while a redelivery is still coming."""
    url, factory = sync_db
    app_id, job_id = _seed(factory)

    queue = _FakeQueue()
    worker = ApplicationWorker(
        queue_adapter=queue,
        graph=_ExplodingGraph(),
        db_url=url,
        max_delivery_attempts=3,
    )
    job_ref = JobRef(
        job_id=job_id,
        application_id=app_id,
        attempt_count=1,
        created_at=utc_now().isoformat(),
        metadata={"document_ids": [], "document_manifest": {}},
    )

    worker.process_delivery(_Delivery(job_ref))

    assert queue.failed == [True]
    with factory() as session:
        app_model = session.execute(
            select(ApplicationModel).where(ApplicationModel.id == app_id)
        ).scalar_one()
    assert app_model.status == "QUEUED"


def test_dlq_routing_marks_application_failed(sync_db):
    """Exceeding the attempt ceiling routes to DLQ and records a terminal state."""
    url, factory = sync_db
    app_id, job_id = _seed(factory)

    queue = _FakeQueue()
    worker = ApplicationWorker(
        queue_adapter=queue,
        graph=_ExplodingGraph(),
        db_url=url,
        max_delivery_attempts=3,
    )
    job_ref = JobRef(
        job_id=job_id,
        application_id=app_id,
        attempt_count=4,  # over the ceiling
        created_at=utc_now().isoformat(),
        metadata={"document_ids": [], "document_manifest": {}},
    )

    worker.process_delivery(_Delivery(job_ref))

    assert queue.failed == [False]  # non-retryable -> DLQ
    with factory() as session:
        app_model = session.execute(
            select(ApplicationModel).where(ApplicationModel.id == app_id)
        ).scalar_one()
    assert app_model.status == "FAILED"
