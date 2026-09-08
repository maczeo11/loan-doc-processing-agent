"""
Unit tests for the ApplicationWorker consumer engine and LeaseHeartbeat.
Owned by Member 2 (Bhanu Teja).

Verifies AGENTS.md rules:
- Delivery is at-least-once.
- Idempotent execution.
- Bounded retries: attempt_count > 3 routes to DLQ (fail retryable=False).
- Acknowledge-Last: Results commit BEFORE ack is called. On failure, fail(retryable=True) is called, ack is NEVER called.
- LeaseHeartbeat extends lease periodically during processing.
"""

import time
import threading
from typing import List, Tuple
from adapters.queue.base import QueuePort, Delivery
from core.contracts.jobs import JobRef
from core.contracts.evidence import EvidenceRef, BoundingBox
from core.contracts.facts import PayslipFacts, BankStatementFacts, TaxReturnFacts, ApplicantFact, MoneyFact
from worker.consumer import ApplicationWorker, LeaseHeartbeat


class InMemoryQueueAdapter(QueuePort):
    """In-memory QueuePort adapter for testing worker consumer behaviors."""

    def __init__(self):
        self.published: List[JobRef] = []
        self.deliveries: List[Delivery] = []
        self.acked: List[str] = []
        self.failed: List[Tuple[str, bool]] = []
        self.extended: List[Tuple[str, int]] = []

    def publish(self, job_ref: JobRef) -> None:
        self.published.append(job_ref)
        delivery = Delivery(lease_handle=f"lease-{job_ref.job_id}", job_ref=job_ref)
        self.deliveries.append(delivery)

    def receive(self, max_n: int = 1) -> List[Delivery]:
        items = self.deliveries[:max_n]
        self.deliveries = self.deliveries[max_n:]
        return items

    def extend_lease(self, handle: str, seconds: int) -> None:
        self.extended.append((handle, seconds))

    def ack(self, handle: str) -> None:
        self.acked.append(handle)

    def fail(self, handle: str, retryable: bool) -> None:
        self.failed.append((handle, retryable))


def create_sample_job(app_id: str = "APP-TEST-WORKER", attempt_count: int = 1) -> JobRef:
    bbox = BoundingBox(x0=0.0, y0=0.0, x1=1.0, y1=1.0)
    ev = EvidenceRef(
        document_id=f"{app_id}-doc1",
        document_type="payslip",
        page_number=1,
        quoted_span="Net Pay: INR 50,000",
        bounding_box=bbox,
    )

    payslip = PayslipFacts(
        employee_name="Jane Doe",
        employer_name="FinScan Corp",
        gross_salary=MoneyFact(amount=60000, currency="INR", source=ev),
        net_salary=MoneyFact(amount=50000, currency="INR", source=ev),
    )

    bank = BankStatementFacts(
        account_holder="Jane Doe",
        bank_name="ICICI Bank",
        account_number_masked="XXXXXX9876",
        salary_credits=[MoneyFact(amount=50000, currency="INR", source=ev)],
        average_salary_credit=MoneyFact(amount=50000, currency="INR", source=ev),
        closing_balance=MoneyFact(amount=45000, currency="INR", source=ev),
        bounced_transactions=0,
    )

    tax = TaxReturnFacts(
        assessee_name="Jane Doe",
        pan_number="ABCDE9876F",
        assessment_year="2025-26",
        gross_total_income=MoneyFact(amount=720000, currency="INR", source=ev),
        total_tax_paid=MoneyFact(amount=20000, currency="INR", source=ev),
    )

    applicant = ApplicantFact(
        full_name="Jane Doe",
        source_name=ev,
        pan_number="ABCDE9876F",
        source_pan=ev,
    )

    return JobRef(
        job_id=f"JOB-{app_id}",
        application_id=app_id,
        attempt_count=attempt_count,
        created_at="2026-09-08T12:00:00Z",
        priority=0,
        metadata={
            "document_ids": [f"{app_id}-doc1", f"{app_id}-doc2", f"{app_id}-doc3", f"{app_id}-doc4", f"{app_id}-doc5"],
            "document_manifest": {
                f"{app_id}-doc1": "s3://bucket/payslip.pdf",
                f"{app_id}-doc2": "s3://bucket/bank.pdf",
                f"{app_id}-doc3": "s3://bucket/tax.pdf",
                f"{app_id}-doc4": "s3://bucket/pan_id.pdf",
                f"{app_id}-doc5": "s3://bucket/application_form.pdf",
            },
            "classified_types": {
                f"{app_id}-doc1": "payslip",
                f"{app_id}-doc2": "bank_statement",
                f"{app_id}-doc3": "tax_acknowledgement",
                f"{app_id}-doc4": "id_card",
                f"{app_id}-doc5": "application_form",
            },
            "applicant": applicant,
            "payslip": payslip,
            "bank_statement": bank,
            "tax_return": tax,
        },
    )


def test_worker_process_delivery_success():
    """Happy path: Delivery completes LangGraph pipeline and calls ack-last."""
    queue = InMemoryQueueAdapter()
    job = create_sample_job("APP-SUCCESS-001")
    queue.publish(job)

    deliveries = queue.receive(max_n=1)
    assert len(deliveries) == 1
    delivery = deliveries[0]

    worker = ApplicationWorker(queue_adapter=queue)
    result = worker.process_delivery(delivery)

    assert result is not None
    assert result["status"] == "READY_FOR_REVIEW"
    assert result["review_paused"] is True
    assert len(result["findings"]) >= 4

    # Acknowledge-last guarantee: message acked, not failed
    assert delivery.lease_handle in queue.acked
    assert queue.failed == []


def test_worker_attempt_ceiling_routes_to_dlq():
    """Bounded retry ceiling: attempt_count > 3 triggers non-retryable fail (DLQ) without running pipeline."""
    queue = InMemoryQueueAdapter()
    job = create_sample_job("APP-POISON-001", attempt_count=4)
    queue.publish(job)

    deliveries = queue.receive(max_n=1)
    delivery = deliveries[0]

    worker = ApplicationWorker(queue_adapter=queue, max_delivery_attempts=3)
    result = worker.process_delivery(delivery)

    # Must NOT run pipeline or ack
    assert result is None
    assert delivery.lease_handle not in queue.acked

    # Must route to DLQ: fail(handle, retryable=False)
    assert (delivery.lease_handle, False) in queue.failed


def test_worker_failure_triggers_retryable_fail():
    """Acknowledge-Last: When graph execution crashes, fail(retryable=True) is called and ack is NEVER called."""
    queue = InMemoryQueueAdapter()
    job = create_sample_job("APP-FAIL-001", attempt_count=1)
    queue.publish(job)

    deliveries = queue.receive(max_n=1)
    delivery = deliveries[0]

    class FailingGraph:
        def invoke(self, *args, **kwargs):
            raise RuntimeError("Database connection timed out during execution")

    worker = ApplicationWorker(queue_adapter=queue, graph=FailingGraph())
    result = worker.process_delivery(delivery)

    # Must return None and NOT acknowledge the message
    assert result is None
    assert delivery.lease_handle not in queue.acked

    # Must fail retryably so queue can redeliver
    assert (delivery.lease_handle, True) in queue.failed


def test_lease_heartbeat_extends_lease():
    """LeaseHeartbeat periodically invokes queue.extend_lease in background thread."""
    queue = InMemoryQueueAdapter()
    handle = "lease-heartbeat-test"

    with LeaseHeartbeat(queue, handle, interval_seconds=0.05, extension_seconds=15):
        time.sleep(0.18)

    # Heartbeat thread should have extended the lease at least 2-3 times
    assert len(queue.extended) >= 2
    for item in queue.extended:
        assert item == (handle, 15)


def test_worker_consumer_loop_start_and_graceful_stop():
    """ApplicationWorker consumer polling loop receives and processes queued deliveries."""
    queue = InMemoryQueueAdapter()
    job1 = create_sample_job("APP-LOOP-001")
    job2 = create_sample_job("APP-LOOP-002")
    queue.publish(job1)
    queue.publish(job2)

    worker = ApplicationWorker(queue_adapter=queue)

    # Run worker in a separate thread and stop it after a short delay
    worker_thread = threading.Thread(target=lambda: worker.start(poll_interval_seconds=0.05), daemon=True)
    worker_thread.start()

    # Wait for deliveries to be processed
    time.sleep(0.4)
    worker.stop()
    worker_thread.join(timeout=1.0)

    # Both jobs should be processed and acked
    assert len(queue.acked) == 2
    assert f"lease-{job1.job_id}" in queue.acked
    assert f"lease-{job2.job_id}" in queue.acked
