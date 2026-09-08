"""
Unit tests for domain fact extractors:
- PayslipExtractor
- BankStatementExtractor
- TaxReturnExtractor
- IdCardExtractor
"""

import pytest
from core.contracts.facts import PayslipFacts, BankStatementFacts, TaxReturnFacts, ApplicantFact
from core.extraction.extractors.payslip import PayslipExtractor
from core.extraction.extractors.bank_statement import BankStatementExtractor
from core.extraction.extractors.tax_return import TaxReturnExtractor
from core.extraction.extractors.id_card import IdCardExtractor


def test_payslip_extractor_standard():
    pages = [
        {
            "page_number": 1,
            "text": (
                "TechCorp Solutions Pvt Ltd\n"
                "Employer: TechCorp Solutions Pvt Ltd\n"
                "Employee Name: Rajesh Sharma\n"
                "Pay Period: August 2024\n"
                "Gross Salary: ₹95,000.00\n"
                "Total Deductions: ₹10,000.00\n"
                "Net Salary: ₹85,000.00\n"
            ),
            "page_width": 600.0,
            "page_height": 800.0,
        }
    ]

    extractor = PayslipExtractor()
    facts: PayslipFacts = extractor.extract(doc_id="DOC-PAY-01", pages=pages)

    assert facts.employee_name == "Rajesh Sharma"
    assert facts.employer_name == "TechCorp Solutions Pvt Ltd"
    assert facts.gross_salary.amount == 95000.0
    assert facts.gross_salary.source.document_id == "DOC-PAY-01"
    assert facts.gross_salary.basis == "gross"
    assert facts.net_salary.amount == 85000.0
    assert facts.net_salary.basis == "net"
    assert facts.deductions_total is not None
    assert facts.deductions_total.amount == 10000.0
    assert facts.pay_period_str == "August 2024"


def test_payslip_extractor_missing_fallback():
    pages = [{"page_number": 1, "text": "", "page_width": 600.0, "page_height": 800.0}]

    extractor = PayslipExtractor()
    facts = extractor.extract(doc_id="DOC-EMPTY", pages=pages)

    assert facts.employee_name == "UNKNOWN"
    assert facts.gross_salary.amount == 0.0
    assert facts.gross_salary.source.confidence == 0.0
    assert facts.net_salary.amount == 0.0
    assert facts.net_salary.source.confidence == 0.0


def test_bank_statement_extractor():
    pages = [
        {
            "page_number": 1,
            "text": (
                "HDFC Bank Ltd\n"
                "Account Holder: Rajesh Sharma\n"
                "Account Number: 50100987654321\n"
                "Closing Balance: ₹ 42,150.75\n"
                "01-JUN-2024 NEFT TECHCORP SALARY CREDIT INR 85,000.00\n"
                "01-JUL-2024 NEFT TECHCORP SALARY CREDIT INR 85,000.00\n"
                "01-AUG-2024 NEFT TECHCORP SALARY CREDIT INR 85,000.00\n"
            ),
            "page_width": 600.0,
            "page_height": 800.0,
        }
    ]

    extractor = BankStatementExtractor()
    facts: BankStatementFacts = extractor.extract(doc_id="DOC-BANK-01", pages=pages)

    assert facts.account_holder == "Rajesh Sharma"
    assert "HDFC Bank" in facts.bank_name
    assert facts.account_number_masked == "XXXXXX4321"
    assert len(facts.salary_credits) == 3
    assert all(c.amount == 85000.0 for c in facts.salary_credits)
    assert facts.average_salary_credit is not None
    assert facts.average_salary_credit.amount == 85000.0
    assert facts.closing_balance is not None
    assert facts.closing_balance.amount == 42150.75
    assert facts.bounced_transactions == 0


def test_bank_statement_with_bounces():
    pages = [
        {
            "page_number": 1,
            "text": (
                "State Bank of India\n"
                "Customer Name: Vikram Malhotra\n"
                "Account No: 123456789012\n"
                "15-JUL-2024 ECS RETURN INSUFFICIENT FUNDS INR 500\n"
                "20-JUL-2024 CHEQUE BOUNCE CHARGES INR 250\n"
            ),
            "page_width": 600.0,
            "page_height": 800.0,
        }
    ]

    extractor = BankStatementExtractor()
    facts = extractor.extract(doc_id="DOC-BANK-02", pages=pages)

    assert facts.bounced_transactions == 2
    assert facts.salary_credits == []
    assert facts.average_salary_credit is None


def test_tax_return_extractor():
    pages = [
        {
            "page_number": 1,
            "text": (
                "INCOME TAX DEPARTMENT - ITR-V ACKNOWLEDGEMENT\n"
                "Name of Assessee: Rajesh Sharma\n"
                "PAN: ABCDE1234F\n"
                "Assessment Year: 2024-25\n"
                "Gross Total Income: ₹ 11,40,000.00\n"
                "Total Tax Paid: ₹ 1,20,000.00\n"
            ),
            "page_width": 600.0,
            "page_height": 800.0,
        }
    ]

    extractor = TaxReturnExtractor()
    facts: TaxReturnFacts = extractor.extract(doc_id="DOC-ITR-01", pages=pages)

    assert facts.assessee_name == "Rajesh Sharma"
    assert facts.pan_number == "ABCDE1234F"
    assert facts.assessment_year == "2024-25"
    assert facts.gross_total_income.amount == 1140000.0
    assert facts.gross_total_income.period == "annual"
    assert facts.total_tax_paid is not None
    assert facts.total_tax_paid.amount == 120000.0


def test_id_card_extractor():
    pages = [
        {
            "page_number": 1,
            "text": (
                "INCOME TAX DEPARTMENT\n"
                "GOVERNMENT OF INDIA\n"
                "Full Name: Rajesh Sharma\n"
                "Date of Birth: 1992-05-14\n"
                "Permanent Account Number (PAN): ABCDE1234F\n"
                "Aadhaar No: 9988 7766 5544\n"
            ),
            "page_width": 600.0,
            "page_height": 800.0,
        }
    ]

    extractor = IdCardExtractor()
    facts: ApplicantFact = extractor.extract(doc_id="DOC-KYC-01", pages=pages)

    assert facts.full_name == "Rajesh Sharma"
    assert facts.source_name.document_id == "DOC-KYC-01"
    assert facts.pan_number == "ABCDE1234F"
    assert facts.dob == "1992-05-14"
    assert facts.aadhaar_masked == "XXXX-XXXX-5544"
