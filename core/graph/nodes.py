"""
LangGraph Nodes: Step functions executed in the StateGraph.
Owned by Member 2 (Bhanu Teja).

Rules from AGENTS.md:
- Deterministic code decides. AI explains. A human approves.
- No total, disposition, pass/flag verdict or monetary value originates from an LLM.
- State transitions are recorded in status_history, not overwritten.
- All facts carry EvidenceRef provenance.
"""

import datetime
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Union

from core.contracts.state import LoanApplicationState, StatusTransition, ApplicationStatus
from core.contracts.findings import Finding
from core.contracts.facts import MoneyFact, PayslipFacts, BankStatementFacts, TaxReturnFacts, ApplicantFact
from core.rules.completeness import evaluate_completeness
from core.rules.salary_audit import audit_salary_vs_bank
from core.rules.tax_audit import audit_tax_vs_income
from core.rules.identity import audit_identity_consistency
from core.extraction.native_parser import extract_all_pages_content
from core.extraction.extractors.payslip import PayslipExtractor
from core.extraction.extractors.bank_statement import BankStatementExtractor
from core.extraction.extractors.tax_return import TaxReturnExtractor
from core.extraction.extractors.id_card import IdCardExtractor
from core.reporting.memo_builder import build_appraisal_memo
from core.rag.grounding import (
    detect_prompt_injection,
    filter_grounded_claims,
    sanitize_document_text,
    sanitize_summary_text,
    validate_citations,
)
from adapters.storage.local_fs import LocalFileSystemStorage

logger = logging.getLogger("finscan.graph.nodes")


def _get_utc_timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def triage_node(state: LoanApplicationState) -> Dict[str, Any]:
    """
    Node 1: Validates incoming application dossier manifest and initializes state.
    Transitions: QUEUED -> PROCESSING (or FAILED if no documents provided).
    """
    history: List[StatusTransition] = list(state.get("status_history", []))
    doc_ids = state.get("document_ids", [])
    doc_manifest = state.get("document_manifest", {})

    if not doc_ids and not doc_manifest:
        transition: StatusTransition = {
            "from_status": state.get("status", "QUEUED"),
            "to_status": "FAILED",
            "timestamp": _get_utc_timestamp(),
            "reason": "Dossier rejected: No documents submitted in application manifest.",
        }
        history.append(transition)
        return {
            "status": "FAILED",
            "status_history": history,
            "missing_documents": ["application_form", "payslip", "bank_statement", "tax_acknowledgement", "id_card"],
        }

    transition: StatusTransition = {
        "from_status": state.get("status", "QUEUED"),
        "to_status": "PROCESSING",
        "timestamp": _get_utc_timestamp(),
        "reason": "Dossier validated. Ingestion and triage complete.",
    }
    history.append(transition)

    return {
        "status": "PROCESSING",
        "status_history": history,
        "findings": state.get("findings", []),
        "missing_documents": state.get("missing_documents", []),
        "corrections_applied": state.get("corrections_applied", []),
    }


def ocr_and_classify_node(state: LoanApplicationState) -> Dict[str, Any]:
    """
    Node 2: Determines document types for each uploaded file (router -> classifier).
    Single parse per doc; page texts cached in `document_texts` so Node 3 reuses
    them instead of re-running OCR (fixes 2x Tesseract cost / 20-min stall).
    Calls classifier_adapter with keyword-heuristic fallback on UNKNOWN or exception.
    """
    classified = dict(state.get("classified_types", {}) or {})
    manifest = state.get("document_manifest", {}) or {}
    doc_ids = state.get("document_ids", []) or list(manifest.keys())
    doc_bytes_map = state.get("document_bytes", {}) or {}
    doc_texts_map = dict(state.get("document_texts", {}) or {})

    storage = LocalFileSystemStorage()
    all_ids = list(set(doc_ids + list(manifest.keys())))

    for doc_id in all_ids:
        if doc_id in classified and classified[doc_id] not in ("unknown", "UNKNOWN", None):
            continue

        page_texts: List[str] = []

        # 1. Check if document texts provided directly in state (cache from prior run)
        if doc_id in doc_texts_map:
            val = doc_texts_map[doc_id]
            if isinstance(val, list):
                page_texts = [str(p) for p in val if str(p).strip()]
            elif isinstance(val, str) and val.strip():
                page_texts = [val.strip()]

        # 2. If no text yet, extract from PDF bytes or storage/manifest
        # Per-doc page cap: truncate beyond 30 pages (dossier cap enforced at API).
        if not page_texts:
            pdf_input: Optional[Union[str, bytes]] = None
            if doc_id in doc_bytes_map:
                pdf_input = doc_bytes_map[doc_id]
            elif doc_id in manifest:
                storage_key = manifest[doc_id]
                try:
                    pdf_input = storage.get(storage_key)
                except Exception:
                    if os.path.exists(storage_key):
                        pdf_input = storage_key

            if pdf_input:
                try:
                    import time as _t
                    _t0 = _t.monotonic()
                    pages = extract_all_pages_content(pdf_input)
                    if len(pages) > 30:
                        logger.warning(f"Truncating {doc_id} from {len(pages)} to 30 pages (dossier cap)")
                        pages = pages[:30]
                    page_texts = [p.get("text", "") for p in pages if p.get("text", "").strip()]
                    # Cache for Node 3 reuse (avoids second OCR pass).
                    doc_texts_map[doc_id] = page_texts
                    logger.info(f"Parsed {doc_id}: {len(page_texts)} text pages in {int((_t.monotonic() - _t0) * 1000)}ms")
                except Exception as err:
                    logger.debug(f"Failed to parse pages for {doc_id} in ocr_and_classify_node: {err}")

        # 3. Call classifier adapter if text is available
        predicted = "UNKNOWN"
        if page_texts:
            try:
                from core.extraction.classifier_adapter import classify_document
                res = classify_document(page_texts)
                predicted = res.get("document_class", "UNKNOWN")
            except Exception as ex:
                logger.warning(f"Classifier adapter exception for doc_id {doc_id}: {ex}")
                predicted = "UNKNOWN"

        # 4. Keyword-heuristic fallback on UNKNOWN or exception
        if predicted in ("UNKNOWN", "unknown"):
            doc_lower = doc_id.lower()
            uri_lower = manifest.get(doc_id, "").lower()
            text_snippet = " ".join(page_texts).lower() if page_texts else ""
            combo = f"{doc_lower} {uri_lower} {text_snippet}"

            if "payslip" in combo or "salary" in combo:
                predicted = "payslip"
            elif "bank" in combo or "statement" in combo:
                predicted = "bank_statement"
            elif "tax" in combo or "itr" in combo or "form16" in combo:
                predicted = "tax_acknowledgement"
            elif "pan" in combo or "aadhaar" in combo or "kyc" in combo or "id" in combo:
                predicted = "id_card"
            elif "form" in combo or "app" in combo:
                predicted = "application_form"
            else:
                predicted = "unknown"

        classified[doc_id] = predicted

    return {"classified_types": classified, "document_texts": doc_texts_map}


def extract_facts_node(state: LoanApplicationState) -> Dict[str, Any]:
    """
    Node 3: Fact Extraction Node (aliased as extract_fields_node).
    Reuses `document_texts` cached by Node 2 when available (no second OCR pass);
    only re-parses PDFs for docs missing from cache. Pure native probe here —
    heavy OCR routing lives in router.route_page_extraction for scanned pages.
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
    payslip_extractor = PayslipExtractor()
    bank_extractor = BankStatementExtractor()
    tax_extractor = TaxReturnExtractor()
    id_extractor = IdCardExtractor()

    for doc_id in doc_ids:
        # Reuse Node 2 cache first: avoids second full OCR pass (major stall fix).
        cached_texts = (state.get("document_texts") or {}).get(doc_id)
        pages: List[Dict[str, Any]] = []
        if cached_texts:
            vals = cached_texts if isinstance(cached_texts, list) else [cached_texts]
            pages = [
                {"page_number": i + 1, "text": str(t)}
                for i, t in enumerate(vals)
                if str(t).strip()
            ][:30]

        if not pages:
            pdf_input: Optional[Union[str, bytes]] = None
            if doc_id in doc_bytes_map:
                pdf_input = doc_bytes_map[doc_id]
            elif doc_id in manifest:
                storage_key = manifest[doc_id]
                try:
                    pdf_input = storage.get(storage_key)
                except Exception as e:
                    logger.debug(f"Could not load bytes from storage key {storage_key}: {e}")
                    if os.path.exists(storage_key):
                        pdf_input = storage_key

            if pdf_input:
                try:
                    pages = extract_all_pages_content(pdf_input)[:30]
                except Exception as err:
                    logger.warning(f"Failed to parse pages for {doc_id}: {err}")

        # Fallback page structure for test environments without PDFs
        doc_type = classified_types.get(doc_id, "unknown")
        if not pages:
            pages = [{"page_number": 1, "text": f"Document content for {doc_id} of type {doc_type}"}]

        # Prompt-injection defense (Member 8): document text is untrusted external
        # input. Defuse adversarial spans BEFORE classification and extraction so
        # injected instructions can never reach LLM prompts or flip verdicts.
        # Facts (amounts, names, dates) are unaffected — only override phrases
        # and markdown breakouts are neutralized.
        defused_pages: List[Dict[str, Any]] = []
        for page in pages:
            raw_text = page.get("text", "")
            if raw_text:
                flagged, _ = detect_prompt_injection(raw_text)
                if flagged:
                    logger.warning(
                        f"Prompt-injection pattern defused in document {doc_id} page {page.get('page_number', '?')}"
                    )
                page = {**page, "text": sanitize_document_text(raw_text)}
            defused_pages.append(page)
        pages = defused_pages

        # Classify document type from text if unknown
        if not doc_type or doc_type == "unknown":
            combined_text = " ".join(p.get("text", "") for p in pages).lower()
            if any(k in combined_text for k in ["payslip", "gross salary", "net salary", "net take home"]):
                doc_type = "payslip"
            elif any(
                k in combined_text for k in ["bank", "account number", "closing balance", "salary credit", "neft"]
            ):
                doc_type = "bank_statement"
            elif any(k in combined_text for k in ["income tax", "itr-v", "assessee", "gross total income"]):
                doc_type = "tax_acknowledgement"
            elif any(k in combined_text for k in ["permanent account number", "aadhaar", "pan", "date of birth"]):
                doc_type = "id_card"
            else:
                doc_type = "unknown"
            classified_types[doc_id] = doc_type

        # Invoke domain extractors
        norm_type = doc_type.lower()
        if norm_type in ("payslip", "salary_slip") and payslip is None:
            logger.info(f"Extracting Payslip facts for {doc_id}")
            payslip = payslip_extractor.extract(doc_id=doc_id, pages=pages)
        elif norm_type in ("bank_statement", "bank") and bank_statement is None:
            logger.info(f"Extracting Bank Statement facts for {doc_id}")
            bank_statement = bank_extractor.extract(doc_id=doc_id, pages=pages)
        elif norm_type in ("tax_return", "itr", "tax_acknowledgement") and tax_return is None:
            logger.info(f"Extracting Tax Return facts for {doc_id}")
            tax_return = tax_extractor.extract(doc_id=doc_id, pages=pages)
        elif norm_type in ("id_card", "kyc", "identity_document", "pan", "aadhaar") and applicant is None:
            logger.info(f"Extracting Applicant/KYC facts for {doc_id}")
            applicant = id_extractor.extract(doc_id=doc_id, pages=pages)

    return {
        "applicant": applicant,
        "payslip": payslip,
        "bank_statement": bank_statement,
        "tax_return": tax_return,
        "classified_types": classified_types,
        # Drop bulk bytes after extraction so later checkpoints (RAG/synthesis/
        # grounding/human_review) stay small — fixes SQLite BLOB bloat on 10pp jobs.
        "document_bytes": {},
    }


# Friendly alias for Node 3
extract_fields_node = extract_facts_node


def evaluate_rules_node(state: LoanApplicationState) -> Dict[str, Any]:
    """
    Node 4: Executes deterministic financial arithmetic and consistency rules.
    HUMAN-ONLY ZONE: No LLM decides findings.
    """
    findings: List[Finding] = list(state.get("findings", []))
    classified = state.get("classified_types", {})
    uploaded_types = list(classified.values())
    required_types = ["application_form", "payslip", "bank_statement", "tax_acknowledgement", "id_card"]

    # 1. Completeness Rule
    comp_finding = evaluate_completeness(uploaded_types, required_types)
    findings.append(comp_finding)
    missing = [doc for doc in required_types if doc not in uploaded_types]

    # 2. Salary vs Bank Credit Reconciliation
    payslip = state.get("payslip")
    if isinstance(payslip, dict):
        try:
            payslip = PayslipFacts.model_validate(payslip)
        except Exception:
            pass

    bank = state.get("bank_statement")
    if isinstance(bank, dict):
        try:
            bank = BankStatementFacts.model_validate(bank)
        except Exception:
            pass

    tax_return = state.get("tax_return")
    if isinstance(tax_return, dict):
        try:
            tax_return = TaxReturnFacts.model_validate(tax_return)
        except Exception:
            pass

    applicant = state.get("applicant")
    if isinstance(applicant, dict):
        try:
            applicant = ApplicantFact.model_validate(applicant)
        except Exception:
            pass

    payslip_net = payslip.net_salary if payslip else None
    bank_credit = None
    if bank:
        if bank.salary_credits:
            bank_credit = bank.salary_credits[0]
        elif bank.average_salary_credit:
            bank_credit = bank.average_salary_credit
        elif bank.closing_balance:
            bank_credit = bank.closing_balance

    salary_finding = audit_salary_vs_bank(payslip_net, bank_credit, tolerance=0.05)
    findings.append(salary_finding)

    # 3. Tax Return vs Stated Earnings
    itr_gross = tax_return.gross_total_income if tax_return else None
    annual_gross = (
        MoneyFact(
            amount=payslip.gross_salary.amount * 12,
            currency=payslip.gross_salary.currency,
            period="annual",
            basis="gross",
            source=payslip.gross_salary.source,
        )
        if payslip and payslip.gross_salary
        else None
    )
    tax_finding = audit_tax_vs_income(annual_gross, itr_gross)
    findings.append(tax_finding)

    # 4. Identity & KYC Consistency
    payslip_emp_name = payslip.employee_name if payslip else None
    bank_holder_name = bank.account_holder if bank else None
    itr_pan = tax_return.pan_number if tax_return else None
    id_finding = audit_identity_consistency(applicant, payslip_emp_name, bank_holder_name, tax_pan=itr_pan)
    findings.append(id_finding)
    logger.info(f"Rules evaluation completed: generated {len(findings)} findings.")

    return {
        "findings": findings,
        "missing_documents": missing,
    }


def _finding_field(finding: Any, name: str, default: Any = None) -> Any:
    """Reads a Finding field whether the state carries a model or a plain dict (post-checkpoint serde)."""
    if isinstance(finding, dict):
        return finding.get(name, default)
    return getattr(finding, name, default)


def _resolve_policy_dir() -> str:
    """Locates the policy corpus: env override, else repo-root policies/, else cwd policies/."""
    env_dir = os.getenv("FINSCAN_POLICY_DIR")
    if env_dir and os.path.isdir(env_dir):
        return env_dir
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    repo_policies = os.path.join(repo_root, "policies")
    if os.path.isdir(repo_policies):
        return repo_policies
    return "policies"


def retrieve_policy_node(state: LoanApplicationState) -> Dict[str, Any]:
    """
    Node 5: Hybrid RAG retrieval (BM25 + BGE dense, RRF fused) over the policy corpus.
    Hard tenant isolation: Only retrieves policy corpus passages, never applicant dossiers.

    Finding-aware queries drive retrieval; the deterministic canonical backstop
    below guarantees the mandatory clauses are always cited even if retrieval
    returns nothing (e.g. missing policy dir in a minimal test env).
    """
    retrieved_chunk_ids: List[str] = list(state.get("retrieved_chunk_ids", []))
    findings = state.get("findings", [])

    has_salary_flag = any(
        _finding_field(f, "rule_id") == "RULE-INC-01" and _finding_field(f, "verdict") == "flag" for f in findings
    )
    has_comp_flag = any(
        _finding_field(f, "rule_id") == "RULE-COMP-01" and _finding_field(f, "verdict") == "flag" for f in findings
    )

    # 1. Live hybrid retrieval over the isolated policy index (best effort)
    queries = [
        "retail credit underwriting policy debt-to-income DTI salary tolerance",
        "mandatory documents checklist payslip bank statement ITR KYC",
    ]
    if has_salary_flag:
        queries.append("payslip net salary bank statement salary credit reconciliation tolerance percent")
    if has_comp_flag:
        queries.append("mandatory documentation checklist application form consecutive payslips")
    try:
        from core.rag.indexer import IndexManager
        from core.rag.retriever import HybridRetriever

        manager = IndexManager()
        manager.load_policy_corpus(policy_dir=_resolve_policy_dir())
        retriever = HybridRetriever(index_manager=manager, policy_dir=_resolve_policy_dir())
        for query in queries:
            for hit in retriever.retrieve_policy(query, top_k=3):
                chunk_id = hit["chunk_id"]
                if chunk_id not in retrieved_chunk_ids:
                    retrieved_chunk_ids.append(chunk_id)
    except Exception as e:
        logger.warning(f"Policy hybrid retrieval unavailable, using canonical backstop: {e}")

    # 2. Deterministic canonical backstop — mandatory clauses always cited
    if has_salary_flag and "credit_policy_v1_p1" not in retrieved_chunk_ids:
        retrieved_chunk_ids.append("credit_policy_v1_p1")
    if has_comp_flag and "credit_policy_v1_p2" not in retrieved_chunk_ids:
        retrieved_chunk_ids.append("credit_policy_v1_p2")
    if "kyc_guidelines_v1_p1" not in retrieved_chunk_ids:
        retrieved_chunk_ids.append("kyc_guidelines_v1_p1")

    for chunk in ["CHUNK-POLICY-REQ-01", "CHUNK-POLICY-SAL-02", "CHUNK-POLICY-TAX-03"]:
        if chunk not in retrieved_chunk_ids:
            retrieved_chunk_ids.append(chunk)

    return {"retrieved_chunk_ids": retrieved_chunk_ids}


def synthesize_summary_node(state: LoanApplicationState) -> Dict[str, Any]:
    """
    Node 6: Synthesizes Credit Appraisal Memo (CAM) narrative with citations.
    Zero hallucinated numbers: Narrative only reflects deterministic findings.
    """
    # CAM assembly lives in core/reporting/memo_builder.py so the narrative format
    # is owned in one place (AGENTS.md §9 P2 #4). Bracketed policy IDs it emits are
    # parsed back out by validate_grounding_node below.
    return {
        "summary_markdown": build_appraisal_memo(state),
    }


# Bracket citations parsed from memo markdown. Status badges ([PASS]/[FLAG]/...)
# and abstention markers are NOT citations and are excluded.
_CITATION_RE = re.compile(r"\[([A-Za-z0-9_\-]+)\]")
_NON_CITATION_PREFIXES = ("PASS", "FLAG", "UNKNOWN", "ABSTENTION", "DOC", "APP")


def _parse_memo_citations(summary_markdown: str, known_doc_ids: Optional[Set[str]] = None) -> List[str]:
    """Extracts machine-verifiable [chunk_id] citations from the memo."""
    if not summary_markdown:
        return []
    doc_set = {d.upper() for d in (known_doc_ids or set())}
    return [
        c for c in _CITATION_RE.findall(summary_markdown)
        if not c.upper().startswith(_NON_CITATION_PREFIXES)
        and c.upper() not in doc_set
    ]


def validate_grounding_node(state: LoanApplicationState) -> Dict[str, Any]:
    """
    Node 7: Deterministic citation validation gate. Drops ungrounded claims.
    Parses actual [chunk_id] citations from the memo (never trusts the
    retrieved list as its own proof), strips unauthorized lines, and appends
    an explicit abstention when evidence is missing or unverified.
    Transitions: PROCESSING -> READY_FOR_REVIEW
    """
    summary = state.get("summary_markdown", "") or ""
    retrieved_chunks = list(state.get("retrieved_chunk_ids", []) or [])
    doc_ids = set(state.get("document_ids", []) or [])

    parsed_citations = _parse_memo_citations(summary, known_doc_ids=doc_ids)
    claims = [{"text": summary, "citations": parsed_citations}]
    is_grounded = validate_citations(claims, retrieved_chunks)

    sanitized_summary = sanitize_summary_text(summary, retrieved_chunks, known_doc_ids=doc_ids)
    _, dropped = filter_grounded_claims(claims, retrieved_chunks)
    if dropped:
        logger.warning(
            f"Grounding gate dropped {len(dropped)} ungrounded claim block(s); "
            f"parsed={parsed_citations} authorized={retrieved_chunks}"
        )

    history: List[StatusTransition] = list(state.get("status_history", []))
    transition: StatusTransition = {
        "from_status": state.get("status", "PROCESSING"),
        "to_status": "READY_FOR_REVIEW",
        "timestamp": _get_utc_timestamp(),
        "reason": (
            "Pipeline execution and grounding check complete. "
            f"Citations grounded: {is_grounded}. Ready for human underwriter review."
        ),
    }
    history.append(transition)

    return {
        "status": "READY_FOR_REVIEW",
        "status_history": history,
        "summary_markdown": sanitized_summary,
        "summary_grounded": is_grounded,
        "review_paused": True,
    }


def human_review_node(state: LoanApplicationState) -> Dict[str, Any]:
    """
    Node 8: The LangGraph interrupt() checkpoint.
    Halts for human underwriter sign-off.
    Upon resume, records reviewer decision and transitions state to REVIEWED or NEEDS_INFORMATION.
    """
    history: List[StatusTransition] = list(state.get("status_history", []))
    decision = state.get("reviewer_decision")

    # If entering human review node without underwriter decision, remain paused
    if decision is None:
        return {
            "status": "READY_FOR_REVIEW",
            "review_paused": True,
        }

    # Underwriter resumed execution with decision
    target_status: ApplicationStatus = "REVIEWED" if decision in ["APPROVED", "REJECTED"] else "NEEDS_INFORMATION"
    transition: StatusTransition = {
        "from_status": "READY_FOR_REVIEW",
        "to_status": target_status,
        "timestamp": _get_utc_timestamp(),
        "reason": f"Underwriter sign-off submitted: {decision}. Notes: {state.get('reviewer_notes', 'None')}",
    }
    history.append(transition)

    return {
        "status": target_status,
        "status_history": history,
        "review_paused": False,
    }
