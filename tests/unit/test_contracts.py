"""
Unit tests for core contracts and domain invariants.
"""

import pytest
from pydantic import ValidationError
from core.contracts.evidence import EvidenceRef, BoundingBox
from core.contracts.facts import MoneyFact
from core.contracts.findings import Finding
from core.contracts.jobs import JobRef
from adapters.queue.base import Delivery


def test_job_ref_and_delivery():
    job = JobRef(
        job_id="JOB-123",
        application_id="APP-456",
        attempt_count=1,
        created_at="2026-09-08T12:00:00Z",
        priority=0,
        metadata={"user_id": "reviewer-1"}
    )
    assert job.job_id == "JOB-123"
    assert job.attempt_count == 1

    delivery = Delivery(lease_handle="lease-xyz", job_ref=job)
    assert delivery.lease_handle == "lease-xyz"
    assert delivery.handle == "lease-xyz"
    assert delivery.job_ref.application_id == "APP-456"



def test_evidence_ref_valid():
    bbox = BoundingBox(x0=0.1, y0=0.2, x1=0.5, y1=0.4)
    ref = EvidenceRef(
        document_id="DOC-123",
        document_type="payslip",
        page_number=1,
        quoted_span="Monthly Gross Salary: INR 50,000",
        bounding_box=bbox,
        confidence=0.98,
    )
    assert ref.document_id == "DOC-123"
    assert ref.page_number == 1
    assert ref.quoted_span == "Monthly Gross Salary: INR 50,000"


def test_money_fact_requires_evidence():
    bbox = BoundingBox(x0=0.0, y0=0.0, x1=1.0, y1=1.0)
    ref = EvidenceRef(
        document_id="DOC-123",
        document_type="payslip",
        page_number=1,
        quoted_span="50000",
        bounding_box=bbox,
    )
    fact = MoneyFact(amount=50000.0, currency="INR", source=ref)
    assert fact.amount == 50000.0
    assert fact.source.document_id == "DOC-123"

    # Verifying MoneyFact cannot be instantiated without source evidence
    with pytest.raises(ValidationError):
        MoneyFact(amount=50000.0, currency="INR")  # type: ignore


def test_finding_verdict_values():
    bbox = BoundingBox(x0=0.0, y0=0.0, x1=1.0, y1=1.0)
    ref = EvidenceRef(
        document_id="DOC-1",
        document_type="payslip",
        page_number=1,
        quoted_span="sample",
        bounding_box=bbox
    )

    f_pass = Finding(rule_id="RULE-01", rule_name="Rule 1", verdict="pass", reason="Matched", supporting_evidence=[ref])
    assert f_pass.verdict == "pass"

    f_flag = Finding(rule_id="RULE-02", rule_name="Rule 2", verdict="flag", reason="Mismatch", supporting_evidence=[ref])
    assert f_flag.verdict == "flag"

    f_unknown = Finding(rule_id="RULE-03", rule_name="Rule 3", verdict="unknown", reason="Cannot compare", supporting_evidence=[])
    assert f_unknown.verdict == "unknown"

    with pytest.raises(ValidationError):
        Finding(rule_id="RULE-04", rule_name="Rule 4", verdict="invalid_status", reason="Bad", supporting_evidence=[])  # type: ignore
