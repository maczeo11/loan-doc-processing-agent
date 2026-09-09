"""
FinScan AI: Deterministic Synthetic Loan Dossier & Discrepancy Generator
HUMAN-ONLY ZONE: Owned by Member 4 (Sravanthi).

Generates realistic multi-document PDF retail loan dossiers with controlled anomalies
for testing, model evaluation, and live hackathon demonstrations.
Uses a deterministic synthetic schema inspired by retail banking loan appraisal domains
(no external Kaggle CSV required).

Invariants:
  1. Deterministic generation: Same seed always generates identical dossier values.
  2. Every PDF page bears the prominent watermark: 'SYNTHETIC DEMO — NOT VALID'.
  3. All monetary and textual facts match Member 3's extraction regexes.
  4. Internal arithmetic consistency: opening + credits - debits = closing balance; gross - deductions = net.
  5. Ground truth manifest contains expected outcomes and details for all 4 deterministic rules:
     RULE-COMP-01, RULE-INC-01, RULE-TAX-01, RULE-ID-01.
"""

import argparse
import json
import os
from typing import Any, Dict, List, Optional, Tuple

import pymupdf

WATERMARK_TEXT = "SYNTHETIC DEMO \u2014 NOT VALID"

APPLICANT_NAMES = [
    "Aarav Sharma",
    "Priya Patel",
    "Vikram Malhotra",
    "Sneha Kulkarni",
    "Rajesh Nair",
    "Ananya Rao",
    "Kavita Iyer",
    "Rohan Verma",
]

COMPANIES = [
    "Tata Consultancy Services Ltd",
    "Infosys Technologies Ltd",
    "Wipro Enterprises Ltd",
    "Tech Mahindra Ltd",
    "HCL Technologies Ltd",
]

BANKS = [
    "HDFC Bank",
    "State Bank of India",
    "ICICI Bank",
    "Axis Bank",
]

SUPPORTED_SCENARIOS = [
    "clean",
    "missing_payslip",
    "salary_mismatch",
    "bank_mismatch",
    "tax_mismatch",
    "missing_itr",
    "identity_mismatch",
    "multiple_inconsistencies",
]


def render_synthetic_pdf(
    filepath: str,
    title: str,
    key_values: List[Tuple[str, str]],
    extra_lines: Optional[List[str]] = None,
) -> str:
    """
    Renders an A4 PDF using PyMuPDF containing the mandatory bold watermark
    and extractor-compatible key-value pairs.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)

    # Insert CJK font buffer to support the unicode em-dash without replacement
    page.insert_font(fontname="cjk", fontbuffer=pymupdf.Font("cjk").buffer)

    # Watermark 1: Top header warning (Bold red)
    page.insert_text(
        pymupdf.Point(60, 32),
        WATERMARK_TEXT,
        fontname="cjk",
        fontsize=13,
        color=(0.85, 0.1, 0.1),
    )

    # Watermark 2: Subtle background watermark across center of page
    page.insert_text(
        pymupdf.Point(80, 420),
        WATERMARK_TEXT,
        fontname="cjk",
        fontsize=24,
        color=(0.78, 0.78, 0.78),
    )

    # Watermark 3: Bottom footer warning
    page.insert_text(
        pymupdf.Point(60, 818),
        WATERMARK_TEXT,
        fontname="cjk",
        fontsize=11,
        color=(0.85, 0.1, 0.1),
    )

    # Document Title & Border line
    page.insert_text(
        pymupdf.Point(50, 70),
        title,
        fontname="helv",
        fontsize=14,
        color=(0.1, 0.2, 0.4),
    )
    page.draw_line(pymupdf.Point(50, 80), pymupdf.Point(545, 80), color=(0.1, 0.2, 0.4), width=1.5)

    y = 110
    for label, val in key_values:
        line_str = f"{label}: {val}" if val else label
        page.insert_text(pymupdf.Point(50, y), line_str, fontname="helv", fontsize=11, color=(0.15, 0.15, 0.15))
        y += 24

    if extra_lines:
        y += 10
        page.draw_line(pymupdf.Point(50, y), pymupdf.Point(545, y), color=(0.7, 0.7, 0.7), width=0.75)
        y += 18
        for line in extra_lines:
            page.insert_text(pymupdf.Point(50, y), line, fontname="helv", fontsize=10, color=(0.25, 0.25, 0.25))
            y += 18

    try:
        doc.subset_fonts()
    except Exception:
        pass

    doc.save(filepath, garbage=4, deflate=True)
    doc.close()
    return filepath


def generate_dossier(
    seed: int = 42,
    scenario: str = "clean",
    output_dir: Optional[str] = None,
    split: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generates a deterministic synthetic loan dossier with ground truth manifest and PDFs.

    Parameters:
      seed: Integer seed for 100% deterministic reproducibility.
      scenario: One of SUPPORTED_SCENARIOS.
      output_dir: Directory to output the dossier folder. Defaults to data/synthetic_dossiers.
      split: Optional dataset split name (e.g. 'dev', 'tuning', 'held-out', 'demo').
    """
    if scenario not in SUPPORTED_SCENARIOS:
        raise ValueError(f"Unknown scenario '{scenario}'. Supported: {SUPPORTED_SCENARIOS}")

    app_id = f"APP-{seed:05d}"
    if output_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "data", "synthetic_dossiers")
    folder = os.path.join(output_dir, app_id)
    os.makedirs(folder, exist_ok=True)

    # Deterministic Identity Data
    applicant_name = APPLICANT_NAMES[seed % len(APPLICANT_NAMES)]
    company_name = COMPANIES[seed % len(COMPANIES)]
    bank_name = BANKS[seed % len(BANKS)]
    pan_number = f"ABCDE{1000 + (seed * 37) % 9000}F"
    aadhaar_masked = f"XXXX-XXXX-{1000 + (seed * 53) % 9000}"
    account_number = f"50100{1000000 + (seed * 91) % 9000000}"
    dob = "1992-06-15"

    # Deterministic Financial Baseline
    monthly_gross = round(80000.0 + (seed % 10) * 10000.0, 2)
    epf_deduction = round(monthly_gross * 0.08, 2)
    tds_deduction = round(monthly_gross * 0.07, 2)
    deductions_total = round(epf_deduction + tds_deduction, 2)
    net_salary = round(monthly_gross - deductions_total, 2)
    annualized_gross = round(monthly_gross * 12.0, 2)
    total_tax_paid = round(annualized_gross * 0.10, 2)

    # Bank Balance Arithmetic Baseline
    opening_balance = 50000.0
    baseline_bank_salary_credit = net_salary
    baseline_annualized_gross = annualized_gross
    baseline_employee_name = applicant_name

    # Baseline records before any manipulation
    baseline_values: Dict[str, Any] = {
        "applicant": {
            "full_name": applicant_name,
            "dob": dob,
            "pan_number": pan_number,
            "aadhaar_masked": aadhaar_masked,
            "employer_name": company_name,
            "bank_name": bank_name,
            "account_number": account_number,
        },
        "financial": {
            "monthly_gross": monthly_gross,
            "epf_deduction": epf_deduction,
            "tds_deduction": tds_deduction,
            "deductions_total": deductions_total,
            "net_salary": net_salary,
            "annualized_gross": annualized_gross,
            "bank_salary_credit": baseline_bank_salary_credit,
            "opening_balance": opening_balance,
            "itr_gross_income": baseline_annualized_gross,
            "total_tax_paid": total_tax_paid,
        },
    }

    # Manipulated Values tracking (empty dict for clean scenario)
    manipulated_values: Dict[str, Any] = {}

    bank_salary_credit = baseline_bank_salary_credit
    payslip_employee_name = baseline_employee_name
    itr_gross_income = baseline_annualized_gross

    # Expected Rule Outcomes Initialization
    expected_rules = {
        "RULE-COMP-01": "pass",
        "RULE-INC-01": "pass",
        "RULE-TAX-01": "pass",
        "RULE-ID-01": "pass",
    }

    # Inject Controlled Scenarios
    if scenario == "missing_payslip":
        expected_rules["RULE-COMP-01"] = "flag"
        expected_rules["RULE-INC-01"] = "unknown"
        expected_rules["RULE-TAX-01"] = "unknown"
        manipulated_values["omitted_documents"] = ["payslip_1.pdf", "payslip_2.pdf", "payslip_3.pdf"]
        manipulated_values["reason"] = "All 3 monthly payslips omitted from dossier"
    elif scenario in ("salary_mismatch", "bank_mismatch"):
        bank_salary_credit = round(net_salary * 0.45, 2)  # Discrepancy > 5% tolerance
        expected_rules["RULE-INC-01"] = "flag"
        variance_ratio = round(abs(net_salary - bank_salary_credit) / net_salary, 4)
        manipulated_values["salary_reconciliation"] = {
            "field": "bank_salary_credit",
            "stated_net_salary": net_salary,
            "actual_bank_credit": bank_salary_credit,
            "variance_ratio": variance_ratio,
            "variance_pct": round(variance_ratio * 100.0, 2),
            "configured_tolerance": 0.05,
            "exceeds_tolerance": True,
        }
    elif scenario == "tax_mismatch":
        itr_gross_income = round(annualized_gross * 0.55, 2)  # Discrepancy > 5% tolerance
        expected_rules["RULE-TAX-01"] = "flag"
        variance_ratio = round(abs(annualized_gross - itr_gross_income) / annualized_gross, 4)
        manipulated_values["tax_reconciliation"] = {
            "field": "itr_gross_total_income",
            "annualized_stated_gross": annualized_gross,
            "actual_itr_gross": itr_gross_income,
            "variance_ratio": variance_ratio,
            "variance_pct": round(variance_ratio * 100.0, 2),
            "configured_tolerance": 0.05,
            "exceeds_tolerance": True,
        }
    elif scenario == "missing_itr":
        expected_rules["RULE-COMP-01"] = "flag"
        expected_rules["RULE-TAX-01"] = "unknown"
        manipulated_values["omitted_documents"] = ["itr.pdf"]
        manipulated_values["reason"] = "ITR-V acknowledgement omitted from dossier"
    elif scenario == "identity_mismatch":
        payslip_employee_name = "Vikram Joshi" if applicant_name != "Vikram Joshi" else "Sneha Kulkarni"
        expected_rules["RULE-ID-01"] = "flag"
        manipulated_values["identity_check"] = {
            "field": "payslip_employee_name",
            "applicant_name": applicant_name,
            "payslip_name": payslip_employee_name,
            "expected_verdict": "flag",
            "kyc_pass_threshold": 0.85,
            "kyc_flag_threshold": 0.70,
            "reason": "Name mismatch between KYC and payslip below 70% threshold",
        }
    elif scenario == "multiple_inconsistencies":
        bank_salary_credit = round(net_salary * 0.45, 2)
        itr_gross_income = round(annualized_gross * 0.55, 2)
        payslip_employee_name = "Vikram Joshi" if applicant_name != "Vikram Joshi" else "Sneha Kulkarni"
        expected_rules["RULE-INC-01"] = "flag"
        expected_rules["RULE-TAX-01"] = "flag"
        expected_rules["RULE-ID-01"] = "flag"

        salary_var = round(abs(net_salary - bank_salary_credit) / net_salary, 4)
        tax_var = round(abs(annualized_gross - itr_gross_income) / annualized_gross, 4)

        manipulated_values["salary_reconciliation"] = {
            "field": "bank_salary_credit",
            "stated_net_salary": net_salary,
            "actual_bank_credit": bank_salary_credit,
            "variance_ratio": salary_var,
            "variance_pct": round(salary_var * 100.0, 2),
            "configured_tolerance": 0.05,
            "exceeds_tolerance": True,
        }
        manipulated_values["tax_reconciliation"] = {
            "field": "itr_gross_total_income",
            "annualized_stated_gross": annualized_gross,
            "actual_itr_gross": itr_gross_income,
            "variance_ratio": tax_var,
            "variance_pct": round(tax_var * 100.0, 2),
            "configured_tolerance": 0.05,
            "exceeds_tolerance": True,
        }
        manipulated_values["identity_check"] = {
            "field": "payslip_employee_name",
            "applicant_name": applicant_name,
            "payslip_name": payslip_employee_name,
            "expected_verdict": "flag",
            "kyc_pass_threshold": 0.85,
            "kyc_flag_threshold": 0.70,
            "reason": "Name mismatch below 70% threshold",
        }

    # Strictly verify bank arithmetic: opening + credits - debits = closing
    salary_credits_total = round(bank_salary_credit * 3.0, 2)
    total_debits = round(salary_credits_total * 0.70, 2)
    closing_balance = round(opening_balance + salary_credits_total - total_debits, 2)

    # Document tracking
    expected_docs = [
        "application.pdf",
        "payslip_1.pdf",
        "payslip_2.pdf",
        "payslip_3.pdf",
        "bank_statement.pdf",
        "itr.pdf",
        "kyc.pdf",
    ]
    generated_docs: List[str] = []

    # 1. Application Form PDF
    app_pdf_path = os.path.join(folder, "application.pdf")
    render_synthetic_pdf(
        filepath=app_pdf_path,
        title="RETAIL LOAN APPLICATION FORM",
        key_values=[
            ("Application ID", app_id),
            ("Applicant Name", applicant_name),
            ("Date of Birth", dob),
            ("Permanent Account Number", pan_number),
            ("Employer Name", company_name),
            ("Stated Monthly Gross Income", f"INR {monthly_gross:,.2f}"),
            ("Stated Monthly Net Income", f"INR {net_salary:,.2f}"),
            ("Loan Amount Requested", "INR 3,500,000.00"),
            ("Loan Term (Years)", "15"),
            ("Purpose of Loan", "Personal / Home Improvement"),
            ("Declaration", "I hereby declare that all information provided is true and accurate."),
        ],
    )
    generated_docs.append("application.pdf")

    # 2. Payslips (3 months)
    if scenario != "missing_payslip":
        months = ["June 2026", "July 2026", "August 2026"]
        for idx, month in enumerate(months, 1):
            payslip_filename = f"payslip_{idx}.pdf"
            payslip_path = os.path.join(folder, payslip_filename)
            render_synthetic_pdf(
                filepath=payslip_path,
                title=f"SALARY PAYSLIP - {month.upper()}",
                key_values=[
                    ("Employee Name", payslip_employee_name),
                    ("Employer Name", company_name),
                    ("Pay Period", month),
                    ("Gross Salary", f"INR {monthly_gross:,.2f}"),
                    ("EPF Deduction", f"INR {epf_deduction:,.2f}"),
                    ("TDS Deduction", f"INR {tds_deduction:,.2f}"),
                    ("Total Deductions", f"INR {deductions_total:,.2f}"),
                    ("Net Salary", f"INR {net_salary:,.2f}"),
                ],
            )
            generated_docs.append(payslip_filename)

    # 3. Bank Statement PDF
    bank_pdf_path = os.path.join(folder, "bank_statement.pdf")
    render_synthetic_pdf(
        filepath=bank_pdf_path,
        title=f"{bank_name.upper()} - STATEMENT OF ACCOUNT",
        key_values=[
            ("Account Holder", applicant_name),
            ("Bank Name", bank_name),
            ("Account Number", account_number),
            ("Statement Window", "2026-06-01 to 2026-08-31"),
            ("Opening Balance", f"INR {opening_balance:,.2f}"),
            ("Closing Balance", f"INR {closing_balance:,.2f}"),
        ],
        extra_lines=[
            "TRANSACTION ACTIVITY:",
            f"2026-06-30 SALARY CREDIT: INR {bank_salary_credit:,.2f}",
            f"2026-07-31 SALARY CREDIT: INR {bank_salary_credit:,.2f}",
            f"2026-08-31 SALARY CREDIT: INR {bank_salary_credit:,.2f}",
            f"SUMMARY: Total Credits INR {salary_credits_total:,.2f} | Total Debits INR {total_debits:,.2f}",
            f"ARITHMETIC CHECK: {opening_balance:,.2f} + {salary_credits_total:,.2f} - {total_debits:,.2f} = {closing_balance:,.2f}",
        ],
    )
    generated_docs.append("bank_statement.pdf")

    # 4. Income Tax Return (ITR-V) PDF
    if scenario != "missing_itr":
        itr_pdf_path = os.path.join(folder, "itr.pdf")
        render_synthetic_pdf(
            filepath=itr_pdf_path,
            title="INCOME TAX DEPARTMENT - ITR-V ACKNOWLEDGEMENT",
            key_values=[
                ("Name of Assessee", applicant_name),
                ("Permanent Account Number", pan_number),
                ("Assessment Year", "2025-26"),
                ("Gross Total Income", f"INR {itr_gross_income:,.2f}"),
                ("Total Tax Paid", f"INR {total_tax_paid:,.2f}"),
                ("Filing Status", "e-Verified (Deterministic Track)"),
            ],
        )
        generated_docs.append("itr.pdf")

    # 5. Identity Verification (KYC) PDF
    kyc_pdf_path = os.path.join(folder, "kyc.pdf")
    render_synthetic_pdf(
        filepath=kyc_pdf_path,
        title="GOVERNMENT OF INDIA - IDENTITY PROOF (KYC)",
        key_values=[
            ("Full Name", applicant_name),
            ("Date of Birth", dob),
            ("Permanent Account Number", pan_number),
            ("Aadhaar No", aadhaar_masked),
        ],
    )
    generated_docs.append("kyc.pdf")

    # Detailed Expected Outcomes for Each Deterministic Rule
    expected_rule_details: Dict[str, Any] = {
        "RULE-COMP-01": {
            "rule_id": "RULE-COMP-01",
            "rule_name": "Dossier Completeness Check",
            "verdict": expected_rules["RULE-COMP-01"],
            "expected_documents": expected_docs,
            "omitted_documents": manipulated_values.get("omitted_documents", []),
        },
        "RULE-INC-01": {
            "rule_id": "RULE-INC-01",
            "rule_name": "Salary vs Bank Credit Reconciliation",
            "verdict": expected_rules["RULE-INC-01"],
            "stated_net_salary": net_salary if scenario != "missing_payslip" else None,
            "bank_monthly_salary_credit": bank_salary_credit,
            "configured_tolerance": 0.05,
        },
        "RULE-TAX-01": {
            "rule_id": "RULE-TAX-01",
            "rule_name": "Tax Return vs Stated Income Audit",
            "verdict": expected_rules["RULE-TAX-01"],
            "annualized_stated_gross": annualized_gross if scenario != "missing_payslip" else None,
            "itr_gross_total_income": itr_gross_income if scenario != "missing_itr" else None,
            "configured_tolerance": 0.05,
        },
        "RULE-ID-01": {
            "rule_id": "RULE-ID-01",
            "rule_name": "Cross-Document Identity Consistency",
            "verdict": expected_rules["RULE-ID-01"],
            "applicant_name": applicant_name,
            "payslip_name": payslip_employee_name,
            "kyc_pass_threshold": 0.85,
            "kyc_flag_threshold": 0.70,
        },
    }

    # Ground Truth Manifest
    manifest: Dict[str, Any] = {
        "application_id": app_id,
        "seed": seed,
        "scenario": scenario,
        "split": split,
        "expected_documents": expected_docs,
        "generated_document_names": generated_docs,
        "baseline_values": baseline_values,
        "manipulated_values": manipulated_values,
        "applicant_facts": {
            "full_name": applicant_name,
            "dob": dob,
            "pan_number": pan_number,
            "aadhaar_masked": aadhaar_masked,
            "employer_name": company_name,
        },
        "financial_ground_truth": {
            "gross_monthly_salary": monthly_gross,
            "net_monthly_salary": net_salary,
            "deductions_total": deductions_total,
            "annualized_gross_income": annualized_gross,
            "bank_monthly_salary_credit": bank_salary_credit,
            "bank_opening_balance": opening_balance,
            "bank_total_credits": salary_credits_total,
            "bank_total_debits": total_debits,
            "bank_closing_balance": closing_balance,
            "itr_gross_total_income": itr_gross_income,
            "total_tax_paid": total_tax_paid,
        },
        "expected_rule_outcomes": expected_rules,
        "expected_rule_details": expected_rule_details,
        # Legacy compatibility keys
        "applicant_name": applicant_name,
        "injected_anomaly": scenario if scenario != "clean" else None,
        "payslip": {
            "employee_name": payslip_employee_name,
            "employer_name": company_name,
            "gross_salary": monthly_gross,
            "net_salary": net_salary,
            "epf_deduction": epf_deduction,
            "tds_deduction": tds_deduction,
        },
        "bank_statement": {
            "account_holder": applicant_name,
            "bank_name": bank_name,
            "account_number": account_number,
            "monthly_salary_credits": [bank_salary_credit] * 3,
            "average_balance": round(closing_balance * 0.45, 2),
            "bounced_transactions": 0,
        },
        "tax_return": {
            "assessee_name": applicant_name,
            "pan_number": pan_number,
            "gross_total_income": itr_gross_income,
            "total_tax_paid": total_tax_paid,
        },
        "kyc": {
            "full_name": applicant_name,
            "pan_number": pan_number,
            "dob": dob,
            "aadhaar_masked": aadhaar_masked,
        },
    }

    manifest_path = os.path.join(folder, "dossier_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest


DATASET_SPLITS: Dict[str, int] = {
    "dev": 25,
    "tuning": 10,
    "held-out": 10,
    "demo": 5,
}

SPLIT_SCENARIOS: Dict[str, List[str]] = {
    "dev": [
        "clean", "missing_payslip", "salary_mismatch", "bank_mismatch",
        "tax_mismatch", "missing_itr", "identity_mismatch", "multiple_inconsistencies",
        "clean", "missing_payslip", "salary_mismatch", "bank_mismatch",
        "tax_mismatch", "missing_itr", "identity_mismatch", "multiple_inconsistencies",
        "clean", "missing_payslip", "salary_mismatch", "bank_mismatch",
        "tax_mismatch", "missing_itr", "identity_mismatch", "clean", "clean",
    ],
    "tuning": [
        "clean", "missing_payslip", "salary_mismatch", "bank_mismatch",
        "tax_mismatch", "missing_itr", "identity_mismatch", "multiple_inconsistencies",
        "clean", "multiple_inconsistencies",
    ],
    "held-out": [
        "clean", "missing_payslip", "salary_mismatch", "bank_mismatch",
        "tax_mismatch", "missing_itr", "identity_mismatch", "multiple_inconsistencies",
        "clean", "multiple_inconsistencies",
    ],
    "demo": [
        "clean", "salary_mismatch", "bank_mismatch", "tax_mismatch", "identity_mismatch",
    ],
}


def generate_dataset(
    output_dir: Optional[str] = None,
    base_seed: int = 1,
) -> Dict[str, Any]:
    """
    Generates the complete synthetic dataset of 50 dossiers across 4 splits:
      - 25 dev (seeds 1 to 25)
      - 10 tuning (seeds 26 to 35)
      - 10 held-out (seeds 36 to 45)
      - 5 demo (seeds 46 to 50)

    Saves each dossier in <output_dir>/APP-xxxxx/ and writes
    <output_dir>/dataset_splits.json as the authoritative master split manifest.
    """
    if output_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "data", "synthetic_dossiers")
    os.makedirs(output_dir, exist_ok=True)

    splits_manifest: Dict[str, List[str]] = {s: [] for s in DATASET_SPLITS}
    dossiers_summary: Dict[str, Dict[str, Any]] = {}
    current_seed = base_seed

    for split_name, count in DATASET_SPLITS.items():
        scenarios = SPLIT_SCENARIOS[split_name]
        if len(scenarios) != count:
            raise ValueError(f"Scenario count {len(scenarios)} does not match split count {count} for {split_name}")
        for scenario in scenarios:
            manifest = generate_dossier(
                seed=current_seed,
                scenario=scenario,
                output_dir=output_dir,
                split=split_name,
            )
            app_id = manifest["application_id"]
            splits_manifest[split_name].append(app_id)
            dossiers_summary[app_id] = {
                "seed": current_seed,
                "split": split_name,
                "scenario": scenario,
                "applicant_name": manifest["applicant_facts"]["full_name"],
                "generated_documents": manifest["generated_document_names"],
                "expected_rule_outcomes": manifest["expected_rule_outcomes"],
            }
            current_seed += 1

    dataset_manifest: Dict[str, Any] = {
        "total_dossiers": len(dossiers_summary),
        "split_counts": {s: len(ids) for s, ids in splits_manifest.items()},
        "splits": splits_manifest,
        "dossiers": dossiers_summary,
    }

    # Save master dataset splits manifest
    splits_path = os.path.join(output_dir, "dataset_splits.json")
    with open(splits_path, "w", encoding="utf-8") as f:
        json.dump(dataset_manifest, f, indent=2)

    # Also write to data/dataset_splits.json if output_dir is inside data/
    parent_data_dir = os.path.dirname(os.path.abspath(output_dir))
    if os.path.basename(parent_data_dir) == "data":
        alt_splits_path = os.path.join(parent_data_dir, "dataset_splits.json")
        try:
            with open(alt_splits_path, "w", encoding="utf-8") as f:
                json.dump(dataset_manifest, f, indent=2)
        except Exception:
            pass

    return dataset_manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="FinScan AI: Deterministic Synthetic Loan Dossier & Discrepancy Generator"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=1,
        help="Deterministic random seed (default: 1)",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        choices=SUPPORTED_SCENARIOS,
        default=None,
        help="Generate a single dossier for a specific scenario",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: data/synthetic_dossiers)",
    )
    parser.add_argument(
        "--dataset",
        action="store_true",
        help="Generate the full 50-dossier dataset across all 4 splits",
    )

    args = parser.parse_args()

    default_dir = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic_dossiers")
    target_dir = args.output_dir if args.output_dir is not None else default_dir
    os.makedirs(target_dir, exist_ok=True)

    if args.scenario:
        print(f"Generating single dossier for scenario '{args.scenario}' with seed {args.seed}...")
        single_manifest = generate_dossier(
            seed=args.seed,
            scenario=args.scenario,
            output_dir=target_dir,
        )
        print(f"Generated dossier: {single_manifest['application_id']} in {target_dir}")
        print(f"Expected rule outcomes: {single_manifest['expected_rule_outcomes']}")
    else:
        print(f"Generating Deterministic Synthetic Loan Dataset (50 dossiers) with base seed {args.seed}...")
        ds_manifest = generate_dataset(output_dir=target_dir, base_seed=args.seed)
        print(f"Complete dataset generated: {ds_manifest['total_dossiers']} dossiers.")
        print(f"Split distribution: {ds_manifest['split_counts']}")
