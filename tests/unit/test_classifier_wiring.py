"""
Unit tests for LangGraph ocr_and_classify_node integration with ClassifierAdapter.
Owned by Member 5 (Karthik).

Verifies:
1. ocr_and_classify_node routes document pages through classifier_adapter.
2. Keyword-heuristic fallback activates when classifier returns UNKNOWN.
3. Node gracefully falls back to keyword heuristic if classifier raises an exception.
"""

from unittest.mock import patch
from core.graph.nodes import ocr_and_classify_node


def test_ocr_and_classify_node_ml_classification():
    """Verifies that ocr_and_classify_node invokes classifier_adapter and assigns predicted types."""
    state = {
        "document_ids": ["DOC-001", "DOC-002", "DOC-003"],
        "document_texts": {
            "DOC-001": [
                "INFOSYS TECHNOLOGIES LTD MONTHLY PAYSLIP FOR AUGUST 2025. "
                "Employee: Rahul Sharma. Basic Pay: INR 60,000. Net Salary: INR 52,000."
            ],
            "DOC-002": [
                "HDFC BANK LIMITED ACCOUNT STATEMENT FOR SAVINGS ACCOUNT 50100291823. "
                "Transactions ledger credits debits closing balance INR 1,45,000."
            ],
            "DOC-003": [
                "FORM NO. 16 INCOME TAX DEPARTMENT CERTIFICATE UNDER SECTION 203. "
                "Assessment Year 2024-25. Total Tax Deducted: INR 45,000."
            ],
        },
        "document_manifest": {
            "DOC-001": "storage/docs/doc1.pdf",
            "DOC-002": "storage/docs/doc2.pdf",
            "DOC-003": "storage/docs/doc3.pdf",
        },
        "classified_types": {},
    }

    result = ocr_and_classify_node(state)
    classified = result["classified_types"]

    assert classified["DOC-001"] == "payslip"
    assert classified["DOC-002"] == "bank_statement"
    assert classified["DOC-003"] == "tax_acknowledgement"


def test_ocr_and_classify_node_keyword_fallback_on_unknown():
    """Verifies that keyword heuristic acts as fallback when classifier returns UNKNOWN or text is unreadable."""
    state = {
        "document_ids": ["DOC-UNKNOWN-SALARY"],
        "document_texts": {
            "DOC-UNKNOWN-SALARY": ["Unreadable low confidence scanned blurry text xyz123"],
        },
        "document_manifest": {
            "DOC-UNKNOWN-SALARY": "storage/docs/salary_slip_unreadable.pdf",
        },
        "classified_types": {},
    }

    result = ocr_and_classify_node(state)
    classified = result["classified_types"]

    # Even if classifier returns UNKNOWN on blurry text, keyword "salary" in combo triggers payslip
    assert classified["DOC-UNKNOWN-SALARY"] == "payslip"


def test_ocr_and_classify_node_fallback_on_exception():
    """Verifies that an exception inside classifier_adapter is safely caught and falls back to keywords."""
    state = {
        "document_ids": ["DOC-BANK-CORRUPT"],
        "document_texts": {
            "DOC-BANK-CORRUPT": ["Some text"],
        },
        "document_manifest": {
            "DOC-BANK-CORRUPT": "storage/docs/bank_statement.pdf",
        },
        "classified_types": {},
    }

    with patch("core.extraction.classifier_adapter.classify_document", side_effect=RuntimeError("Simulated OCR/model error")):
        result = ocr_and_classify_node(state)

    classified = result["classified_types"]
    assert classified["DOC-BANK-CORRUPT"] == "bank_statement"
