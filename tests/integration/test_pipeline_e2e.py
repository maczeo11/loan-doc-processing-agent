"""
End-to-End Pipeline Integration Tests for FinScan AI.
Owned by Member 2 (Bhanu Teja).

Validates the full lifecycle across:
1. Job publication to QueuePort
2. ApplicationWorker atomic processing & LeaseHeartbeat
3. StateGraph sequential execution (Nodes 1-7)
4. Human-in-the-loop interrupt checkpoint (READY_FOR_REVIEW)
5. Acknowledge-last message confirmation
6. Durable SQLite checkpointer persistence
7. Human review resumption to final disposition (REVIEWED / NEEDS_INFORMATION)
"""

from typing import List, Tuple
from adapters.queue.base import QueuePort, Delivery
from core.contracts.jobs import JobRef
from core.contracts.evidence import EvidenceRef, BoundingBox
from core.contracts.facts import PayslipFacts, BankStatementFacts, TaxReturnFacts, ApplicantFact, MoneyFact
from core.graph.checkpoint import SqliteSaver
from core.graph.workflow import build_application_graph, resume_application_review
from worker.consumer import ApplicationWorker


class IntegrationQueueAdapter(QueuePort):
    """Test queue adapter supporting atomic delivery and audit logging."""

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


def create_e2e_dossier_job(app_id: str = "APP-E2E-2026") -> JobRef:
    """Constructs a coherent multi-document retail loan dossier payload."""
    bbox = BoundingBox(x0=0.05, y0=0.10, x1=0.95, y1=0.90)

    ev_payslip = EvidenceRef(
        document_id=f"{app_id}-payslip",
        document_type="payslip",
        page_number=1,
        quoted_span="Monthly Net Salary: INR 85,000",
        bounding_box=bbox,
    )
    ev_bank = EvidenceRef(
        document_id=f"{app_id}-bank",
        document_type="bank_statement",
        page_number=1,
        quoted_span="SALARY CREDIT: INR 85,000",
        bounding_box=bbox,
    )
    ev_tax = EvidenceRef(
        document_id=f"{app_id}-tax",
        document_type="tax_acknowledgement",
        page_number=1,
        quoted_span="Gross Total Income: INR 1,200,000",
        bounding_box=bbox,
    )
    ev_id = EvidenceRef(
        document_id=f"{app_id}-pan",
        document_type="id_card",
        page_number=1,
        quoted_span="Permanent Account Number: ABCDE1234F",
        bounding_box=bbox,
    )

    payslip = PayslipFacts(
        employee_name="Bhanu Teja",
        employer_name="TechCorp India Ltd",
        gross_salary=MoneyFact(amount=100000, currency="INR", source=ev_payslip),
        net_salary=MoneyFact(amount=85000, currency="INR", source=ev_payslip),
    )

    bank = BankStatementFacts(
        account_holder="Bhanu Teja",
        bank_name="State Bank of India",
        account_number_masked="XXXXXX9876",
        salary_credits=[MoneyFact(amount=85000, currency="INR", source=ev_bank)],
        average_salary_credit=MoneyFact(amount=85000, currency="INR", source=ev_bank),
        closing_balance=MoneyFact(amount=150000, currency="INR", source=ev_bank),
        bounced_transactions=0,
    )

    tax = TaxReturnFacts(
        assessee_name="Bhanu Teja",
        pan_number="ABCDE1234F",
        assessment_year="2025-26",
        gross_total_income=MoneyFact(amount=1200000, currency="INR", source=ev_tax),
        total_tax_paid=MoneyFact(amount=110000, currency="INR", source=ev_tax),
    )

    applicant = ApplicantFact(
        full_name="Bhanu Teja",
        source_name=ev_id,
        pan_number="ABCDE1234F",
        source_pan=ev_id,
    )

    metadata = {
        "document_ids": [
            f"{app_id}-appform",
            f"{app_id}-payslip",
            f"{app_id}-bank",
            f"{app_id}-tax",
            f"{app_id}-pan",
        ],
        "document_manifest": {
            f"{app_id}-appform": f"storage://{app_id}/application_form.pdf",
            f"{app_id}-payslip": f"storage://{app_id}/payslip.pdf",
            f"{app_id}-bank": f"storage://{app_id}/bank_statement.pdf",
            f"{app_id}-tax": f"storage://{app_id}/tax_return.pdf",
            f"{app_id}-pan": f"storage://{app_id}/pan_card.pdf",
        },
        "classified_types": {
            f"{app_id}-appform": "application_form",
            f"{app_id}-payslip": "payslip",
            f"{app_id}-bank": "bank_statement",
            f"{app_id}-tax": "tax_acknowledgement",
            f"{app_id}-pan": "id_card",
        },
        "applicant": applicant.model_dump(),
        "payslip": payslip.model_dump(),
        "bank_statement": bank.model_dump(),
        "tax_return": tax.model_dump(),
    }

    return JobRef(
        job_id=f"JOB-{app_id}",
        application_id=app_id,
        attempt_count=1,
        created_at="2026-09-08T22:00:00Z",
        priority=5,
        metadata=metadata,
    )


def test_end_to_end_pipeline_approval_flow(tmp_path):
    """
    Verifies complete happy path:
    Publish -> Worker claim -> Halt at READY_FOR_REVIEW -> Underwriter APPROVE -> Final REVIEWED.
    """
    db_path = str(tmp_path / "e2e_checkpoints.sqlite3")
    checkpointer = SqliteSaver(db_path=db_path)
    queue = IntegrationQueueAdapter()

    # Step 1: Create application graph & worker
    worker_graph = build_application_graph(checkpointer=checkpointer, enable_interrupt=True)
    worker = ApplicationWorker(queue_adapter=queue, checkpointer=checkpointer, graph=worker_graph)

    # Step 2: Publish dossier job
    app_id = "APP-E2E-APPROVED"
    job = create_e2e_dossier_job(app_id=app_id)
    queue.publish(job)
    assert len(queue.deliveries) == 1

    # Step 3: Worker processes delivery
    delivery = queue.receive(max_n=1)[0]
    paused_state = worker.process_delivery(delivery)

    # Invariants Check:
    # A. Halts at READY_FOR_REVIEW
    assert paused_state is not None
    assert paused_state["status"] == "READY_FOR_REVIEW"
    assert paused_state["review_paused"] is True

    # B. Deterministic rules executed and verified
    findings = paused_state["findings"]
    assert len(findings) == 4
    rule_verdicts = {f.rule_id: f.verdict for f in findings}
    assert rule_verdicts["RULE-COMP-01"] == "pass"
    assert rule_verdicts["RULE-INC-01"] == "pass"
    assert rule_verdicts["RULE-TAX-01"] == "pass"
    assert rule_verdicts["RULE-ID-01"] == "pass"

    # C. CAM memo synthesized & grounding verified
    assert "Credit Appraisal Memo" in paused_state["summary_markdown"]
    assert paused_state["summary_grounded"] is True

    # D. Acknowledge-last guarantee: Worker acknowledged message upon pause commit
    assert f"lease-JOB-{app_id}" in queue.acked

    # Step 4: Separate process/API resumes graph from durable SQLite checkpointer
    api_checkpointer = SqliteSaver(db_path=db_path)
    final_state = resume_application_review(
        thread_id=app_id,
        decision="APPROVED",
        notes="All 4 deterministic rules verified and payroll deposits match payslip.",
        checkpointer=api_checkpointer,
    )

    # Final Invariants Check:
    assert final_state["status"] == "REVIEWED"
    assert final_state["review_paused"] is False
    assert final_state["reviewer_decision"] == "APPROVED"

    # Audit Trail Check
    history = final_state["status_history"]
    transitions = [h["to_status"] for h in history]
    assert "PROCESSING" in transitions
    assert "READY_FOR_REVIEW" in transitions
    assert transitions[-1] == "REVIEWED"


def test_end_to_end_pipeline_needs_info_flow(tmp_path):
    """
    Verifies human reviewer requesting additional info transitions to NEEDS_INFORMATION.
    """
    db_path = str(tmp_path / "e2e_needs_info.sqlite3")
    checkpointer = SqliteSaver(db_path=db_path)
    queue = IntegrationQueueAdapter()

    worker_graph = build_application_graph(checkpointer=checkpointer, enable_interrupt=True)
    worker = ApplicationWorker(queue_adapter=queue, checkpointer=checkpointer, graph=worker_graph)

    app_id = "APP-E2E-NEEDS-INFO"
    job = create_e2e_dossier_job(app_id=app_id)
    queue.publish(job)

    delivery = queue.receive(max_n=1)[0]
    worker.process_delivery(delivery)

    # Underwriter requests more info
    final_state = resume_application_review(
        thread_id=app_id,
        decision="NEEDS_INFO",
        notes="Bank statement page 2 has unreadable stamp. Please re-upload.",
        checkpointer=checkpointer,
    )

    assert final_state["status"] == "NEEDS_INFORMATION"
    assert final_state["review_paused"] is False
    assert final_state["reviewer_decision"] == "NEEDS_INFO"
