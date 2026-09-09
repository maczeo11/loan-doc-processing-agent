"""
FinScan AI: Deterministic Rules Engine Orchestrator.
HUMAN-ONLY ZONE: Owned by Member 4 (Sravanthi).

Orchestrates all 5 deterministic loan dossier evaluation rules:
  1. RULE-COMP-01: Dossier Completeness Check (completeness.py)
  2. RULE-INC-01: Salary vs. Bank Credit Reconciliation (salary_audit.py)
  3. RULE-TAX-01: Tax Return vs. Stated Income Audit (tax_audit.py)
  4. RULE-ID-01: Cross-Document Identity Consistency (identity.py)
  5. RULE-BANK-01: Bank Statement Arithmetic Validation (bank_arithmetic.py)

Invariants:
  1. Pure deterministic Python — zero LLM involvement in arithmetic or findings.
  2. Non-overwriting: Every rule produces a distinct, typed Finding with its own rule_id.
  3. Strict contract compliance: Returns typed Finding objects with EvidenceRef citations.
  4. Non-coercion: Missing data strictly yields 'unknown' or 'flag', never an unverified 'pass'.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Union

from core.contracts.evidence import BoundingBox, EvidenceRef
from core.contracts.facts import (
    ApplicantFact,
    BankStatementFacts,
    MoneyFact,
    PayslipFacts,
    TaxReturnFacts,
)
from core.contracts.findings import Finding
from core.rules.bank_arithmetic import validate_bank_statement_arithmetic
from core.rules.completeness import evaluate_completeness, normalize_doc_type
from core.rules.identity import audit_identity_consistency
from core.rules.salary_audit import audit_salary_vs_bank
from core.rules.tax_audit import audit_tax_vs_income


def findings_to_dict(findings: Sequence[Finding]) -> Dict[str, Finding]:
    """Indexes a sequence of Finding models by rule_id to ensure non-overwriting access."""
    return {f.rule_id: f for f in findings}


def evaluate_dossier_rules(
    uploaded_types: Optional[List[str]] = None,
    applicant: Optional[ApplicantFact] = None,
    payslip: Optional[PayslipFacts] = None,
    bank_statement: Optional[BankStatementFacts] = None,
    tax_return: Optional[TaxReturnFacts] = None,
    *,
    opening_balance: Optional[Union[MoneyFact, Decimal, float, int, dict]] = None,
    closing_balance: Optional[Union[MoneyFact, Decimal, float, int, dict]] = None,
    credits: Optional[Union[MoneyFact, Sequence[Any], Decimal, float, int, dict]] = None,
    debits: Optional[Union[MoneyFact, Sequence[Any], Decimal, float, int, dict]] = None,
    tolerance: Union[float, Decimal] = 0.05,
    required_types: Optional[List[str]] = None,
    evidence: Optional[List[EvidenceRef]] = None,
    dossier_manifest: Optional[Dict[str, Any]] = None,
) -> List[Finding]:
    """
    Executes all 5 deterministic loan underwriting rules against applicant facts or a dossier manifest.

    Parameters:
      uploaded_types: List of document category names uploaded for the application.
      applicant: Primary applicant KYC fact model.
      payslip: Extracted payslip facts model.
      bank_statement: Extracted bank statement facts model.
      tax_return: Extracted tax return facts model.
      opening_balance: Bank statement opening balance (MoneyFact, Decimal, or dict).
      closing_balance: Bank statement closing balance (MoneyFact, Decimal, or dict).
      credits: Credit transactions or total credits for bank statement arithmetic.
      debits: Debit transactions or total debits for bank statement arithmetic.
      tolerance: Relative/absolute numerical tolerance margin (defaults to 0.05).
      required_types: Optional explicit list of required document types.
      evidence: Optional list of EvidenceRefs grounding the documents.
      dossier_manifest: Optional synthetic or production dossier manifest dictionary.
                        If provided, missing parameters are parsed from the manifest.

    Returns:
      Ordered list of 5 typed Finding models:
      [RULE-COMP-01, RULE-INC-01, RULE-TAX-01, RULE-ID-01, RULE-BANK-01]
    """
    bbox = BoundingBox(x0=0.0, y0=0.0, x1=1.0, y1=1.0)

    # --------------------------------------------------------------------------
    # 1. Parse parameters from dossier_manifest if provided
    # --------------------------------------------------------------------------
    if dossier_manifest is not None:
        omitted = dossier_manifest.get("manipulated_values", {}).get("omitted_documents", [])

        # Uploaded document list
        if uploaded_types is None:
            uploaded_types = list(
                dossier_manifest.get("generated_document_names")
                or dossier_manifest.get("expected_documents")
                or []
            )

        # Grounding evidence for completeness verification
        if evidence is None and uploaded_types:
            evidence = [
                EvidenceRef(
                    document_id=doc,
                    document_type=normalize_doc_type(doc) or "unknown",
                    page_number=1,
                    quoted_span=doc,
                    bounding_box=bbox,
                )
                for doc in uploaded_types
            ]

        # Applicant KYC fact
        if applicant is None:
            app_dict = dossier_manifest.get("applicant_facts") or dossier_manifest.get("kyc") or {}
            full_name = app_dict.get("full_name") or dossier_manifest.get("applicant_name")
            if full_name:
                ev_name = EvidenceRef(
                    document_id="DOC-KYC",
                    document_type="id_card",
                    page_number=1,
                    quoted_span=full_name,
                    bounding_box=bbox,
                )
                pan_val = app_dict.get("pan_number")
                ev_pan = (
                    EvidenceRef(
                        document_id="DOC-KYC",
                        document_type="id_card",
                        page_number=1,
                        quoted_span=pan_val,
                        bounding_box=bbox,
                    )
                    if pan_val
                    else None
                )
                applicant = ApplicantFact(
                    full_name=full_name,
                    source_name=ev_name,
                    pan_number=pan_val,
                    source_pan=ev_pan,
                    dob=app_dict.get("dob"),
                    aadhaar_masked=app_dict.get("aadhaar_masked"),
                )

        # Payslip facts
        if payslip is None:
            has_payslip_doc = any("payslip" in doc for doc in (uploaded_types or []))
            if has_payslip_doc and "payslip_1.pdf" not in omitted:
                fgt = dossier_manifest.get("financial_ground_truth", {})
                ps_dict = dossier_manifest.get("payslip", {})
                gross_amt = fgt.get("gross_monthly_salary") or ps_dict.get("gross_salary")
                net_amt = fgt.get("net_monthly_salary") or ps_dict.get("net_salary")
                emp_name = (
                    ps_dict.get("employee_name")
                    or (applicant.full_name if applicant else "UNKNOWN")
                )
                employer = ps_dict.get("employer_name") or "Employer Ltd"

                if gross_amt is not None and net_amt is not None:
                    ev_gross = EvidenceRef(
                        document_id="DOC-PAY",
                        document_type="payslip",
                        page_number=1,
                        quoted_span=f"Gross {gross_amt}",
                        bounding_box=bbox,
                    )
                    ev_net = EvidenceRef(
                        document_id="DOC-PAY",
                        document_type="payslip",
                        page_number=1,
                        quoted_span=f"Net {net_amt}",
                        bounding_box=bbox,
                    )
                    payslip = PayslipFacts(
                        employee_name=emp_name,
                        employer_name=employer,
                        gross_salary=MoneyFact(
                            amount=gross_amt, currency="INR", basis="gross", source=ev_gross
                        ),
                        net_salary=MoneyFact(
                            amount=net_amt, currency="INR", basis="net", source=ev_net
                        ),
                    )

        # Bank statement facts
        if bank_statement is None:
            has_bank_doc = any("bank" in doc for doc in (uploaded_types or []))
            if has_bank_doc and "bank_statement.pdf" not in omitted:
                fgt = dossier_manifest.get("financial_ground_truth", {})
                bs_dict = dossier_manifest.get("bank_statement", {})
                holder = bs_dict.get("account_holder") or (
                    applicant.full_name if applicant else "UNKNOWN"
                )
                b_name = bs_dict.get("bank_name") or "Bank Ltd"
                sal_credit_amt = fgt.get("bank_monthly_salary_credit")
                ev_b = EvidenceRef(
                    document_id="DOC-BANK",
                    document_type="bank_statement",
                    page_number=1,
                    quoted_span=f"Salary credit {sal_credit_amt}",
                    bounding_box=bbox,
                )
                sal_credits = (
                    [
                        MoneyFact(
                            amount=sal_credit_amt,
                            currency="INR",
                            basis="net",
                            source=ev_b,
                        )
                    ]
                    * 3
                    if sal_credit_amt is not None
                    else []
                )
                close_amt = fgt.get("bank_closing_balance")
                ev_close = EvidenceRef(
                    document_id="DOC-BANK",
                    document_type="bank_statement",
                    page_number=1,
                    quoted_span=f"Closing {close_amt}",
                    bounding_box=bbox,
                )
                close_fact = (
                    MoneyFact(
                        amount=close_amt,
                        currency="INR",
                        basis="balance",
                        source=ev_close,
                    )
                    if close_amt is not None
                    else None
                )
                bank_statement = BankStatementFacts(
                    account_holder=holder,
                    bank_name=b_name,
                    account_number_masked=bs_dict.get("account_number", "XXXXXX1234"),
                    salary_credits=sal_credits,
                    closing_balance=close_fact,
                )

        # Tax return facts
        if tax_return is None:
            has_tax_doc = any("itr" in doc or "tax" in doc for doc in (uploaded_types or []))
            if has_tax_doc and "itr.pdf" not in omitted:
                fgt = dossier_manifest.get("financial_ground_truth", {})
                tr_dict = dossier_manifest.get("tax_return", {})
                assessee = tr_dict.get("assessee_name") or (
                    applicant.full_name if applicant else "UNKNOWN"
                )
                pan = tr_dict.get("pan_number") or (applicant.pan_number if applicant else "")
                ay = tr_dict.get("assessment_year", "2025-26")
                gross_tax = fgt.get("itr_gross_total_income") or tr_dict.get("gross_total_income")
                if gross_tax is not None:
                    ev_tax = EvidenceRef(
                        document_id="DOC-TAX",
                        document_type="tax_acknowledgement",
                        page_number=1,
                        quoted_span=f"ITR {gross_tax}",
                        bounding_box=bbox,
                    )
                    tax_return = TaxReturnFacts(
                        assessee_name=assessee,
                        pan_number=pan,
                        assessment_year=ay,
                        gross_total_income=MoneyFact(
                            amount=gross_tax,
                            currency="INR",
                            basis="gross",
                            source=ev_tax,
                        ),
                    )

        # Bank balance arithmetic parameters
        fgt = dossier_manifest.get("financial_ground_truth", {})
        has_bank_doc = any("bank" in doc for doc in (uploaded_types or []))
        if has_bank_doc and "bank_statement.pdf" not in omitted:
            ev_math = EvidenceRef(
                document_id="DOC-BANK",
                document_type="bank_statement",
                page_number=1,
                quoted_span="Balance activity",
                bounding_box=bbox,
            )
            if opening_balance is None and "bank_opening_balance" in fgt:
                opening_balance = MoneyFact(
                    amount=fgt["bank_opening_balance"],
                    currency="INR",
                    basis="balance",
                    source=ev_math,
                )
            if closing_balance is None and "bank_closing_balance" in fgt:
                closing_balance = MoneyFact(
                    amount=fgt["bank_closing_balance"],
                    currency="INR",
                    basis="balance",
                    source=ev_math,
                )
            if credits is None and "bank_total_credits" in fgt:
                credits = MoneyFact(
                    amount=fgt["bank_total_credits"],
                    currency="INR",
                    basis="net",
                    source=ev_math,
                )
            if debits is None and "bank_total_debits" in fgt:
                debits = MoneyFact(
                    amount=fgt["bank_total_debits"],
                    currency="INR",
                    basis="deduction",
                    source=ev_math,
                )

    # --------------------------------------------------------------------------
    # 2. Rule 1: RULE-COMP-01 (Dossier Completeness Check)
    # --------------------------------------------------------------------------
    finding_comp = evaluate_completeness(
        uploaded_types=uploaded_types,
        required_types=required_types,
        evidence=evidence,
    )

    # --------------------------------------------------------------------------
    # 3. Rule 2: RULE-INC-01 (Salary vs. Bank Credit Reconciliation)
    # --------------------------------------------------------------------------
    payslip_net = payslip.net_salary if payslip else None
    bank_credits = bank_statement.salary_credits if bank_statement else None
    finding_inc = audit_salary_vs_bank(
        payslip_net=payslip_net,
        bank_salary_credit=bank_credits,
        tolerance=tolerance,
    )

    # --------------------------------------------------------------------------
    # 4. Rule 3: RULE-TAX-01 (Tax Return vs. Stated Gross Income Audit)
    # --------------------------------------------------------------------------
    monthly_gross = payslip.gross_salary if payslip else None
    itr_gross = tax_return.gross_total_income if tax_return else None
    finding_tax = audit_tax_vs_income(
        monthly_gross=monthly_gross,
        itr_gross_income=itr_gross,
        tolerance=tolerance,
    )

    # --------------------------------------------------------------------------
    # 5. Rule 4: RULE-ID-01 (Cross-Document Identity Consistency)
    # --------------------------------------------------------------------------
    payslip_name = payslip.employee_name if payslip else None
    bank_holder_name = bank_statement.account_holder if bank_statement else None
    tax_name = tax_return.assessee_name if tax_return else None
    tax_pan = tax_return.pan_number if tax_return else None

    finding_id = audit_identity_consistency(
        applicant=applicant,
        payslip_name=payslip_name,
        bank_name=bank_holder_name,
        tax_name=tax_name,
        tax_pan=tax_pan,
    )

    # --------------------------------------------------------------------------
    # 6. Rule 5: RULE-BANK-01 (Bank Statement Arithmetic Validation)
    # --------------------------------------------------------------------------
    finding_bank = validate_bank_statement_arithmetic(
        opening_balance=opening_balance,
        closing_balance=closing_balance,
        credits=credits,
        debits=debits,
        tolerance=tolerance,
    )

    # Return ordered list of all 5 findings
    return [finding_comp, finding_inc, finding_tax, finding_id, finding_bank]
