"""
Facts: Structured entities extracted from dossier documents.
Every numerical or monetary fact carries an EvidenceRef.
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from core.contracts.evidence import EvidenceRef


class MoneyFact(BaseModel):
    amount: float = Field(..., description="Monetary value")
    currency: str = Field("INR", description="Currency code (INR, USD, etc.)")
    period: Literal["monthly", "annual", "one_time"] = Field("monthly", description="Payment period")
    basis: Literal["gross", "net", "deduction", "balance"] = Field("gross", description="Accounting basis")
    source: EvidenceRef = Field(..., description="Traceable receipt back to document page and span")


class ApplicantFact(BaseModel):
    full_name: str
    source_name: EvidenceRef
    dob: Optional[str] = None
    source_dob: Optional[EvidenceRef] = None
    pan_number: Optional[str] = None
    source_pan: Optional[EvidenceRef] = None
    aadhaar_masked: Optional[str] = None
    source_aadhaar: Optional[EvidenceRef] = None


class PayslipFacts(BaseModel):
    employee_name: str
    employer_name: str
    # Provenance for the compared name: RULE-ID-01 must cite the payslip page
    # itself, not just the KYC side (else cross-doc evidence shows one doc).
    employee_name_evidence: Optional[EvidenceRef] = None
    gross_salary: MoneyFact
    net_salary: MoneyFact
    deductions_total: Optional[MoneyFact] = None
    pay_period_str: Optional[str] = None


class BankStatementFacts(BaseModel):
    account_holder: str
    # Provenance for the compared holder name (see PayslipFacts above).
    account_holder_evidence: Optional[EvidenceRef] = None
    bank_name: str
    account_number_masked: str
    salary_credits: List[MoneyFact] = Field(default_factory=list)
    average_salary_credit: Optional[MoneyFact] = None
    opening_balance: Optional[MoneyFact] = None
    closing_balance: Optional[MoneyFact] = None
    total_credits: Optional[MoneyFact] = None
    total_debits: Optional[MoneyFact] = None
    bounced_transactions: int = 0


class TaxReturnFacts(BaseModel):
    assessee_name: str
    # Provenance for the compared assessee name and PAN (see above).
    assessee_name_evidence: Optional[EvidenceRef] = None
    pan_number: str
    pan_evidence: Optional[EvidenceRef] = None
    assessment_year: str
    gross_total_income: MoneyFact
    total_tax_paid: Optional[MoneyFact] = None
