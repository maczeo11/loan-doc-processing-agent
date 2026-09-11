"""
Unit & Integration tests for LangGraph Node 2 Fact Extraction Wiring,
Worker Storage Retrieval via StoragePort.get(key), and Rules Engine integration.
"""

import io
import fitz
import pytest
from core.contracts.jobs import JobRef
from core.graph.nodes import (
    extract_fields_node,
    extract_facts_node,
    evaluate_rules_node,
)
from adapters.storage.local_fs import LocalFileSystemStorage
from adapters.queue.base import QueuePort, Delivery
from worker.consumer import ApplicationWorker


def _create_sample_pdf(text: str) -> bytes:
    """Helper: Creates a minimal single-page PDF with native text using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page(width=595.0, height=842.0)
    # Insert text lines
    y = 50.0
    for line in text.split("\n"):
        if line.strip():
            page.insert_text(fitz.Point(50, y), line.strip(), fontsize=11)
            y += 20.0
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def sample_dossier_pdfs():
    """Generates synthetic PDF byte buffers for a complete loan dossier."""
    payslip_text = (
        "EMPLOYER: Infosys Technologies Ltd\n"
        "Employee Name: Priya Patel\n"
        "Pay Period: August 2024\n"
        "Gross Salary: INR 80,000.00\n"
        "Total Deductions: INR 10,000.00\n"
        "Net Salary: INR 70,000.00\n"
    )
    bank_text = (
        "HDFC Bank Ltd\n"
        "Account Holder: Priya Patel\n"
        "Account Number: 5010022334455\n"
        "Closing Balance: ₹ 55,000.00\n"
        "01-JUN-2024 NEFT INFOSYS SALARY CREDIT INR 70,000.00\n"
        "01-JUL-2024 NEFT INFOSYS SALARY CREDIT INR 70,000.00\n"
        "01-AUG-2024 NEFT INFOSYS SALARY CREDIT INR 70,000.00\n"
    )
    tax_text = (
        "INCOME TAX DEPARTMENT - ITR-V ACKNOWLEDGEMENT\n"
        "Name of Assessee: Priya Patel\n"
        "PAN: ABCDE9988F\n"
        "Assessment Year: 2024-25\n"
        "Gross Total Income: INR 9,60,000.00\n"
        "Total Tax Paid: INR 96,000.00\n"
    )
    kyc_text = (
        "INCOME TAX DEPARTMENT - GOVERNMENT OF INDIA\n"
        "Full Name: Priya Patel\n"
        "Date of Birth: 1995-04-20\n"
        "Permanent Account Number: ABCDE9988F\n"
        "Aadhaar No: 1234 5678 9012\n"
    )

    return {
        "DOC-PAY-01": _create_sample_pdf(payslip_text),
        "DOC-BANK-01": _create_sample_pdf(bank_text),
        "DOC-TAX-01": _create_sample_pdf(tax_text),
        "DOC-KYC-01": _create_sample_pdf(kyc_text),
    }


def test_local_storage_put_and_get(tmp_path):
    storage = LocalFileSystemStorage(base_dir=str(tmp_path))
    content = b"%PDF-1.4 test document content"
    key = "dossiers/APP-100/test.pdf"

    uri = storage.put(key, io.BytesIO(content))
    assert uri.startswith("file://")

    retrieved = storage.get(key)
    assert retrieved == content

    # Test file:// retrieval
    retrieved_via_uri = storage.get(uri)
    assert retrieved_via_uri == content


def test_node2_fact_extraction_wiring(sample_dossier_pdfs):
    """Verifies that Node 2 (extract_fields_node / extract_facts_node) populates all 4 domain fact contracts."""
    state = {
        "application_id": "APP-TEST-01",
        "status": "PROCESSING",
        "status_history": [],
        "document_ids": list(sample_dossier_pdfs.keys()),
        "document_manifest": {k: f"mock/{k}.pdf" for k in sample_dossier_pdfs},
        "document_bytes": sample_dossier_pdfs,
        "classified_types": {
            "DOC-PAY-01": "payslip",
            "DOC-BANK-01": "bank_statement",
            "DOC-TAX-01": "tax_return",
            "DOC-KYC-01": "id_card",
        },
        "applicant": None,
        "payslip": None,
        "bank_statement": None,
        "tax_return": None,
        "findings": [],
        "missing_documents": [],
        "retrieved_chunk_ids": [],
        "summary_markdown": None,
        "summary_grounded": False,
        "review_paused": False,
        "reviewer_decision": None,
        "reviewer_notes": None,
        "corrections_applied": [],
    }

    # Test extract_facts_node alias
    output = extract_facts_node(state)

    assert output["payslip"] is not None
    assert output["payslip"].employee_name == "Priya Patel"
    assert output["payslip"].gross_salary.amount == 80000.0
    assert output["payslip"].net_salary.amount == 70000.0

    assert output["bank_statement"] is not None
    assert output["bank_statement"].account_holder == "Priya Patel"
    assert output["bank_statement"].average_salary_credit.amount == 70000.0

    assert output["tax_return"] is not None
    assert output["tax_return"].assessee_name == "Priya Patel"
    assert output["tax_return"].gross_total_income.amount == 960000.0

    assert output["applicant"] is not None
    assert output["applicant"].full_name == "Priya Patel"
    assert output["applicant"].pan_number == "ABCDE9988F"


def test_node3_rules_evaluation_with_extracted_facts(sample_dossier_pdfs):
    """Verifies that Node 3 (evaluate_rules_node) consumes extracted facts and computes findings."""
    state = {
        "application_id": "APP-TEST-01",
        "status": "PROCESSING",
        "status_history": [],
        "document_ids": list(sample_dossier_pdfs.keys()),
        "document_manifest": {},
        "document_bytes": sample_dossier_pdfs,
        "classified_types": {
            "DOC-PAY-01": "payslip",
            "DOC-BANK-01": "bank_statement",
            "DOC-TAX-01": "tax_return",
            "DOC-KYC-01": "id_card",
        },
        "applicant": None,
        "payslip": None,
        "bank_statement": None,
        "tax_return": None,
        "findings": [],
        "missing_documents": [],
        "retrieved_chunk_ids": [],
        "summary_markdown": None,
        "summary_grounded": False,
        "review_paused": False,
        "reviewer_decision": None,
        "reviewer_notes": None,
        "corrections_applied": [],
    }

    # 1. Run Extraction
    extracted = extract_fields_node(state)
    state.update(extracted)

    # 2. Run Rules
    rules_output = evaluate_rules_node(state)

    findings = rules_output["findings"]
    assert len(findings) == 5

    rule_ids = {f.rule_id for f in findings}
    assert "RULE-COMP-01" in rule_ids
    assert "RULE-INC-01" in rule_ids
    assert "RULE-TAX-01" in rule_ids
    assert "RULE-ID-01" in rule_ids
    assert "RULE-BANK-01" in rule_ids

    # Salary matches (70k net vs 70k credits) -> pass
    salary_finding = next(f for f in findings if f.rule_id == "RULE-INC-01")
    assert salary_finding.verdict == "pass"

    # Identity matches ("Priya Patel" across all docs) -> pass
    id_finding = next(f for f in findings if f.rule_id == "RULE-ID-01")
    assert id_finding.verdict == "pass"


class MockQueue(QueuePort):
    def __init__(self, deliveries=None):
        self.deliveries = deliveries or []
        self.acked = []
        self.failed = []

    def publish(self, job_ref: JobRef) -> None:
        pass

    def receive(self, max_n: int = 1):
        if self.deliveries:
            return [self.deliveries.pop(0)]
        return []

    def extend_lease(self, handle: str, seconds: int) -> None:
        pass

    def ack(self, handle: str) -> None:
        self.acked.append(handle)

    def fail(self, handle: str, retryable: bool) -> None:
        self.failed.append((handle, retryable))


def test_worker_storage_retrieval_and_graph_execution(tmp_path, sample_dossier_pdfs):
    """
    Verifies that ApplicationWorker:
    1. Retrieves raw document bytes via StoragePort.get(key)
    2. Runs LangGraph through extraction, rules, and synthesis
    3. Commits results and calls queue.ack()
    """
    storage = LocalFileSystemStorage(base_dir=str(tmp_path))

    manifest = {}
    for doc_id, pdf_bytes in sample_dossier_pdfs.items():
        key = f"dossiers/APP-25195/{doc_id}.pdf"
        storage.put(key, io.BytesIO(pdf_bytes))
        manifest[doc_id] = key

    job_ref = JobRef(
        job_id="JOB-TEST-12345",
        application_id="APP-25195",
        attempt_count=1,
        created_at="2026-09-08T22:00:00Z",
        metadata={
            "document_manifest": manifest,
            "classified_types": {
                "DOC-PAY-01": "payslip",
                "DOC-BANK-01": "bank_statement",
                "DOC-TAX-01": "tax_return",
                "DOC-KYC-01": "id_card",
            },
        },
    )

    delivery = Delivery(
        job_ref=job_ref,
        lease_handle="LEASE-TEST-HANDLE-01",
        approximate_receive_count=1,
    )

    queue = MockQueue(deliveries=[delivery])
    worker = ApplicationWorker(queue_adapter=queue, storage_adapter=storage)

    # Process delivery
    worker.process_delivery(delivery)

    # Should have acked after successful run
    assert "LEASE-TEST-HANDLE-01" in queue.acked
    assert len(queue.failed) == 0


def test_worker_delivery_ceiling_exceeded():
    """Verifies that attempts > 3 trigger dead-letter failure without executing graph."""
    job_ref = JobRef(
        job_id="JOB-FAIL-CEILING",
        application_id="APP-CEILING",
        attempt_count=4,
        created_at="2026-09-08T22:00:00Z",
    )
    delivery = Delivery(
        job_ref=job_ref,
        lease_handle="LEASE-FAIL-HANDLE",
        approximate_receive_count=4,
    )
    queue = MockQueue(deliveries=[delivery])
    worker = ApplicationWorker(queue_adapter=queue)

    worker.process_delivery(delivery)

    assert len(queue.acked) == 0
    assert len(queue.failed) == 1
    assert queue.failed[0] == ("LEASE-FAIL-HANDLE", False)
