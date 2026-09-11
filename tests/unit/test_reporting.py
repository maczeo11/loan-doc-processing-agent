"""
Unit tests for Credit Appraisal Memo assembly and reviewed-dossier export.
"""

import pytest

from core.contracts.evidence import BoundingBox, EvidenceRef
from core.contracts.facts import ApplicantFact
from core.contracts.findings import Finding
from core.reporting.exporter import export_reviewed_dossier_json, export_reviewed_dossier_pdf
from core.reporting.memo_builder import build_appraisal_memo


def make_evidence(doc_id: str, text: str) -> EvidenceRef:
    return EvidenceRef(
        document_id=doc_id,
        document_type="payslip",
        page_number=1,
        quoted_span=text,
        bounding_box=BoundingBox(x0=0.0, y0=0.0, x1=1.0, y1=1.0),
    )


def make_state(**overrides) -> dict:
    state = {
        "application_id": "APP-25195",
        "status": "READY_FOR_REVIEW",
        "applicant": ApplicantFact(full_name="Rajesh Kumar Sharma", source_name=make_evidence("DOC-KYC", "Rajesh")),
        "findings": [
            Finding(
                rule_id="RULE-INC-01",
                rule_name="Salary vs. Bank Credit Reconciliation",
                verdict="pass",
                reason="Salary verified within tolerance.",
            ),
            Finding(
                rule_id="RULE-TAX-01",
                rule_name="ITR Gross Income Reconciliation",
                verdict="flag",
                reason="Income discrepancy detected.",
            ),
        ],
        "retrieved_chunk_ids": ["credit_policy_v1_p2", "kyc_guidelines_v1_p1"],
        "missing_documents": [],
    }
    state.update(overrides)
    return state


# ── Memo builder ──────────────────────────────────────────────────────────────


def test_memo_includes_application_and_applicant():
    memo = build_appraisal_memo(make_state())
    assert "APP-25195" in memo
    assert "Rajesh Kumar Sharma" in memo


def test_memo_renders_every_finding_with_its_verdict_badge():
    memo = build_appraisal_memo(make_state())
    assert "RULE-INC-01" in memo and "✅ PASS" in memo
    assert "RULE-TAX-01" in memo and "⚠️ FLAG" in memo


def test_memo_emits_bracketed_citations_for_the_grounding_gate():
    # validate_grounding_node parses these back out; the bracket format is load-bearing.
    memo = build_appraisal_memo(make_state())
    assert "[credit_policy_v1_p2]" in memo
    assert "[kyc_guidelines_v1_p1]" in memo


def test_memo_reports_no_citations_when_retrieval_empty():
    memo = build_appraisal_memo(make_state(retrieved_chunk_ids=[]))
    assert "Referenced guidelines: None" in memo


def test_memo_lists_missing_documents():
    memo = build_appraisal_memo(make_state(missing_documents=["tax_acknowledgement", "id_card"]))
    assert "Missing Mandatory Documents" in memo
    assert "tax_acknowledgement" in memo


def test_memo_accepts_serialized_dict_findings():
    # Findings arrive as dicts when rehydrated from job metadata or state_json.
    state = make_state(findings=[{"rule_id": "RULE-ID-01", "rule_name": "Identity", "verdict": "flag", "reason": "Name mismatch."}])
    memo = build_appraisal_memo(state)
    assert "RULE-ID-01" in memo
    assert "⚠️ FLAG" in memo


def test_memo_handles_absent_applicant():
    memo = build_appraisal_memo(make_state(applicant=None))
    assert "Unknown Applicant" in memo


# ── Exporters ─────────────────────────────────────────────────────────────────


def test_json_export_returns_full_state():
    exported = export_reviewed_dossier_json(make_state())
    assert exported["application_id"] == "APP-25195"
    assert len(exported["findings"]) == 2


def test_pdf_export_writes_a_real_pdf(tmp_path):
    pytest.importorskip("reportlab")
    out = tmp_path / "APP-25195.pdf"
    state = make_state(summary_markdown=build_appraisal_memo(make_state()))

    returned = export_reviewed_dossier_pdf(state, str(out))

    assert returned == str(out)
    assert out.exists()
    assert out.read_bytes().startswith(b"%PDF-")


def test_pdf_export_creates_missing_parent_directory(tmp_path):
    pytest.importorskip("reportlab")
    out = tmp_path / "nested" / "dir" / "APP-25195.pdf"
    export_reviewed_dossier_pdf(make_state(), str(out))
    assert out.exists()


def test_pdf_export_paginates_long_memos_without_crashing(tmp_path):
    pytest.importorskip("reportlab")
    out = tmp_path / "long.pdf"
    long_memo = "\n".join(f"Policy clause line {i} " + ("x" * 200) for i in range(300))
    export_reviewed_dossier_pdf(make_state(summary_markdown=long_memo), str(out))
    assert out.exists()
    assert out.stat().st_size > 0
