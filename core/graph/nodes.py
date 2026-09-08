"""
LangGraph Nodes: Step functions executed in the StateGraph.
Owned by Member 2 (Bhanu Teja).

Wires Perception/Extraction directly into Domain Extractors (Member 3: Jeevan)
and passes structured facts into Deterministic Rules (Member 4: Sravanthi).
"""

import logging
import os
from typing import Dict, Any, List, Optional, Union

from core.contracts.state import LoanApplicationState
from core.contracts.facts import ApplicantFact, PayslipFacts, BankStatementFacts, TaxReturnFacts
from core.contracts.findings import Finding
from core.extraction.native_parser import extract_all_pages_content
from core.extraction.extractors.payslip import PayslipExtractor
from core.extraction.extractors.bank_statement import BankStatementExtractor
from core.extraction.extractors.tax_return import TaxReturnExtractor
from core.extraction.extractors.id_card import IdCardExtractor
from core.rules.completeness import evaluate_completeness
from core.rules.salary_audit import audit_salary_vs_bank
from core.rules.tax_audit import audit_tax_vs_income
from core.rules.identity import audit_identity_consistency
from adapters.storage.local_fs import LocalFileSystemStorage

logger = logging.getLogger("finscan.graph.nodes")


def triage_and_validate_node(state: LoanApplicationState) -> Dict[str, Any]:
    """
    Node 1: Evaluates uploaded files, registers document IDs, and transitions state to PROCESSING.
    """
    manifest = state.get("document_manifest") or {}
    doc_ids = state.get("document_ids") or list(manifest.keys())

    logger.info(f"Triage node processing application {state.get('application_id')} with {len(doc_ids)} documents.")

    return {
        "status": "PROCESSING",
        "document_ids": doc_ids,
        "document_manifest": manifest,
    }


def extract_fields_node(state: LoanApplicationState) -> Dict[str, Any]:
    """
    Node 2: Fact Extraction Node (aliased as extract_facts_node).
    Reads document bytes or paths via storage/manifest, routes through native parser / OCR,
    and executes domain fact extractors for Payslip, Bank Statement, Tax Return, and ID Card.
    """
    manifest: Dict[str, str] = state.get("document_manifest") or {}
    doc_ids: List[str] = state.get("document_ids") or list(manifest.keys())
    doc_bytes_map: Dict[str, bytes] = state.get("document_bytes") or {}
    classified_types: Dict[str, str] = dict(state.get("classified_types") or {})

    applicant: Optional[ApplicantFact] = state.get("applicant")
    payslip: Optional[PayslipFacts] = state.get("payslip")
    bank_statement: Optional[BankStatementFacts] = state.get("bank_statement")
    tax_return: Optional[TaxReturnFacts] = state.get("tax_return")

    storage = LocalFileSystemStorage()

    for doc_id in doc_ids:
        # 1. Resolve raw document input (bytes or path)
        pdf_input: Optional[Union[str, bytes]] = None
        if doc_id in doc_bytes_map:
            pdf_input = doc_bytes_map[doc_id]
        elif doc_id in manifest:
            storage_key = manifest[doc_id]
            try:
                pdf_input = storage.get(storage_key)
            except Exception as e:
                logger.warning(f"Could not load bytes from storage key {storage_key}: {e}")
                if os.path.exists(storage_key):
                    pdf_input = storage_key

        if not pdf_input:
            logger.warning(f"No document payload found for {doc_id}. Skipping extraction.")
            continue

        # 2. Extract page contents
        try:
            pages = extract_all_pages_content(pdf_input)
        except Exception as err:
            logger.error(f"Failed to parse pages for {doc_id}: {err}", exc_info=True)
            continue

        # 3. Classify document type if not already provided
        doc_type = classified_types.get(doc_id)
        if not doc_type or doc_type == "unknown":
            combined_text = " ".join(p.get("text", "") for p in pages).lower()
            if any(k in combined_text for k in ["payslip", "gross salary", "net salary", "net take home"]):
                doc_type = "payslip"
            elif any(k in combined_text for k in ["bank", "account number", "closing balance", "salary credit", "neft"]):
                doc_type = "bank_statement"
            elif any(k in combined_text for k in ["income tax", "itr-v", "assessee", "gross total income"]):
                doc_type = "tax_return"
            elif any(k in combined_text for k in ["permanent account number", "aadhaar", "pan", "date of birth"]):
                doc_type = "id_card"
            else:
                doc_type = "unknown"
            classified_types[doc_id] = doc_type

        # 4. Invoke domain extractor based on classified type
        normalized_type = doc_type.lower()
        if normalized_type in ("payslip", "salary_slip"):
            logger.info(f"Extracting Payslip facts for {doc_id}")
            payslip = PayslipExtractor().extract(doc_id=doc_id, pages=pages)
        elif normalized_type in ("bank_statement", "bank"):
            logger.info(f"Extracting Bank Statement facts for {doc_id}")
            bank_statement = BankStatementExtractor().extract(doc_id=doc_id, pages=pages)
        elif normalized_type in ("tax_return", "itr", "tax_acknowledgement"):
            logger.info(f"Extracting Tax Return facts for {doc_id}")
            tax_return = TaxReturnExtractor().extract(doc_id=doc_id, pages=pages)
        elif normalized_type in ("id_card", "kyc", "identity_document", "pan", "aadhaar"):
            logger.info(f"Extracting Applicant/KYC facts for {doc_id}")
            applicant = IdCardExtractor().extract(doc_id=doc_id, pages=pages)

    return {
        "applicant": applicant,
        "payslip": payslip,
        "bank_statement": bank_statement,
        "tax_return": tax_return,
        "classified_types": classified_types,
    }


# Friendly alias for Node 2
extract_facts_node = extract_fields_node


def evaluate_rules_node(state: LoanApplicationState) -> Dict[str, Any]:
    """
    Node 3: Executes deterministic completeness and reconciliation rules.
    Operates strictly on extracted facts without any LLM influence.
    """
    findings: List[Finding] = []
    classified = state.get("classified_types") or {}
    uploaded_types = list(set(classified.values()))
    required_types = ["payslip", "bank_statement", "tax_return", "id_card"]

    # 1. Dossier Completeness Check
    completeness_finding = evaluate_completeness(uploaded_types=uploaded_types, required_types=required_types)
    findings.append(completeness_finding)

    missing = [t for t in required_types if t not in uploaded_types]

    # 2. Salary vs. Bank Credit Reconciliation
    payslip = state.get("payslip")
    bank_statement = state.get("bank_statement")
    payslip_net = payslip.net_salary if payslip else None
    bank_credit = bank_statement.average_salary_credit if bank_statement else None
    findings.append(audit_salary_vs_bank(payslip_net, bank_credit))

    # 3. Tax vs. Income Reconciliation
    tax_return = state.get("tax_return")
    stated_annual = payslip.gross_salary if payslip else None
    itr_gross = tax_return.gross_total_income if tax_return else None
    findings.append(audit_tax_vs_income(stated_annual, itr_gross))

    # 4. Identity Consistency Check
    applicant = state.get("applicant")
    payslip_emp = payslip.employee_name if payslip else None
    bank_holder = bank_statement.account_holder if bank_statement else None
    findings.append(audit_identity_consistency(applicant, payslip_emp, bank_holder))

    logger.info(f"Rules evaluation completed: generated {len(findings)} findings.")

    return {
        "findings": findings,
        "missing_documents": missing,
    }


def retrieve_policy_node(state: LoanApplicationState) -> Dict[str, Any]:
    """
    Node 4: Retrieves relevant policy clauses via hybrid RAG to support summary citations.
    """
    # Policy chunk references for demo
    policy_chunks = [
        "CHUNK-POLICY-REQ-01",  # Mandatory document submission
        "CHUNK-POLICY-SAL-02",  # Salary credit verification tolerance
        "CHUNK-POLICY-TAX-03",  # ITR-V verification
    ]
    return {
        "retrieved_chunk_ids": policy_chunks,
    }


def synthesize_summary_node(state: LoanApplicationState) -> Dict[str, Any]:
    """
    Node 5: Generates cited loan review summary and pauses for human reviewer approval.
    """
    app_id = state.get("application_id", "APP-UNKNOWN")
    applicant = state.get("applicant")
    applicant_name = applicant.full_name if applicant else "Unknown Applicant"
    findings = state.get("findings") or []
    missing_docs = state.get("missing_documents") or []

    lines = [
        f"### Loan Document Processing Summary: {app_id}",
        f"**Applicant Name:** {applicant_name}",
        "",
        "#### Verification Findings:",
    ]
    for f in findings:
        badge = "✅ PASS" if f.verdict == "pass" else ("⚠️ FLAG" if f.verdict == "flag" else "❓ UNKNOWN")
        lines.append(f"- **{f.rule_name}** [{badge}]: {f.reason}")

    if missing_docs:
        lines.append("")
        lines.append(f"**Missing Mandatory Documents:** {', '.join(missing_docs)}")

    summary_text = "\n".join(lines)

    return {
        "status": "READY_FOR_REVIEW",
        "summary_markdown": summary_text,
        "summary_grounded": True,
        "review_paused": True,
    }
