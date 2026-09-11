"""
Unit tests for deterministic synthetic loan dossier generator.
Owned by Member 4 (Sravanthi).

Validates:
- Deterministic reproducibility with same seed
- Presence of all required dossier documents
- Presence of exact mandatory watermark 'SYNTHETIC DEMO — NOT VALID'
- Ground truth manifest completeness and rule outcome expectations
- Internal financial arithmetic consistency
- Controlled discrepancy injection across all scenarios
- Complete compatibility with Member 3's extractor regexes
"""

import json
import os
import subprocess
import sys
import pymupdf

from scripts.generate_dossiers import (
    generate_dossier,
    WATERMARK_TEXT,
    SUPPORTED_SCENARIOS,
)
from core.extraction.native_parser import extract_all_pages_content
from core.extraction.extractors.payslip import PayslipExtractor
from core.extraction.extractors.bank_statement import BankStatementExtractor
from core.extraction.extractors.tax_return import TaxReturnExtractor
from core.extraction.extractors.id_card import IdCardExtractor


def test_supported_scenarios_list():
    assert "clean" in SUPPORTED_SCENARIOS
    assert "missing_payslip" in SUPPORTED_SCENARIOS
    assert "salary_mismatch" in SUPPORTED_SCENARIOS
    assert "bank_mismatch" in SUPPORTED_SCENARIOS
    assert "tax_mismatch" in SUPPORTED_SCENARIOS
    assert "missing_itr" in SUPPORTED_SCENARIOS
    assert "identity_mismatch" in SUPPORTED_SCENARIOS
    assert "multiple_inconsistencies" in SUPPORTED_SCENARIOS


def test_deterministic_output_with_same_seed(tmp_path):
    dir1 = str(tmp_path / "run1")
    dir2 = str(tmp_path / "run2")

    m1 = generate_dossier(seed=101, scenario="clean", output_dir=dir1)
    m2 = generate_dossier(seed=101, scenario="clean", output_dir=dir2)

    assert m1["application_id"] == m2["application_id"]
    assert m1["applicant_facts"] == m2["applicant_facts"]
    assert m1["financial_ground_truth"] == m2["financial_ground_truth"]
    assert m1["expected_rule_outcomes"] == m2["expected_rule_outcomes"]
    assert m1["generated_document_names"] == m2["generated_document_names"]


def test_required_files_exist_for_clean_dossier(tmp_path):
    out_dir = str(tmp_path)
    manifest = generate_dossier(seed=102, scenario="clean", output_dir=out_dir)
    app_folder = os.path.join(out_dir, manifest["application_id"])

    expected_files = [
        "application.pdf",
        "payslip_1.pdf",
        "payslip_2.pdf",
        "payslip_3.pdf",
        "bank_statement.pdf",
        "itr.pdf",
        "kyc.pdf",
        "dossier_manifest.json",
    ]

    for fname in expected_files:
        p = os.path.join(app_folder, fname)
        assert os.path.exists(p), f"Missing required file: {fname}"
        assert os.path.getsize(p) > 0, f"File is empty: {fname}"


def test_watermark_exists_on_generated_pdfs(tmp_path):
    out_dir = str(tmp_path)
    manifest = generate_dossier(seed=103, scenario="clean", output_dir=out_dir)
    app_folder = os.path.join(out_dir, manifest["application_id"])

    pdf_files = [f for f in manifest["generated_document_names"] if f.endswith(".pdf")]
    assert len(pdf_files) == 7

    for pdf_name in pdf_files:
        pdf_path = os.path.join(app_folder, pdf_name)
        doc = pymupdf.open(pdf_path)
        assert len(doc) >= 1
        for page in doc:
            page_text = page.get_text()
            assert WATERMARK_TEXT in page_text, f"Watermark missing in {pdf_name}"
        doc.close()


def test_manifest_exists_and_contains_ground_truth(tmp_path):
    out_dir = str(tmp_path)
    manifest = generate_dossier(seed=104, scenario="clean", output_dir=out_dir)
    app_folder = os.path.join(out_dir, manifest["application_id"])

    manifest_file = os.path.join(app_folder, "dossier_manifest.json")
    with open(manifest_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded["application_id"] == "APP-00104"
    assert loaded["seed"] == 104
    assert loaded["scenario"] == "clean"
    assert "applicant_facts" in loaded
    assert "financial_ground_truth" in loaded
    assert "expected_rule_outcomes" in loaded

    rules = loaded["expected_rule_outcomes"]
    assert rules["RULE-COMP-01"] == "pass"
    assert rules["RULE-INC-01"] == "pass"
    assert rules["RULE-TAX-01"] == "pass"
    assert rules["RULE-ID-01"] == "pass"


def test_clean_scenario_produces_internally_consistent_values(tmp_path):
    manifest = generate_dossier(seed=105, scenario="clean", output_dir=str(tmp_path))
    fgt = manifest["financial_ground_truth"]

    # Payslip internal consistency: gross - deductions = net
    gross = fgt["gross_monthly_salary"]
    deductions = fgt["deductions_total"]
    net = fgt["net_monthly_salary"]
    assert round(gross - deductions, 2) == round(net, 2)

    # Clean salary vs bank consistency: bank credit == net salary
    assert fgt["bank_monthly_salary_credit"] == net

    # Clean tax vs stated consistency: annualized gross == itr gross
    assert fgt["annualized_gross_income"] == round(gross * 12.0, 2)
    assert fgt["itr_gross_total_income"] == fgt["annualized_gross_income"]


def test_salary_mismatch_scenario_creates_intended_discrepancy(tmp_path):
    manifest = generate_dossier(seed=106, scenario="salary_mismatch", output_dir=str(tmp_path))
    fgt = manifest["financial_ground_truth"]

    net = fgt["net_monthly_salary"]
    bank_cr = fgt["bank_monthly_salary_credit"]
    variance_ratio = abs(net - bank_cr) / net
    assert variance_ratio > 0.05

    rules = manifest["expected_rule_outcomes"]
    assert rules["RULE-COMP-01"] == "pass"
    assert rules["RULE-INC-01"] == "flag"
    assert rules["RULE-TAX-01"] == "pass"
    assert rules["RULE-ID-01"] == "pass"


def test_tax_mismatch_scenario_creates_intended_discrepancy(tmp_path):
    manifest = generate_dossier(seed=107, scenario="tax_mismatch", output_dir=str(tmp_path))
    fgt = manifest["financial_ground_truth"]

    stated_annual = fgt["annualized_gross_income"]
    itr_gross = fgt["itr_gross_total_income"]
    variance_ratio = abs(stated_annual - itr_gross) / stated_annual
    assert variance_ratio > 0.05

    rules = manifest["expected_rule_outcomes"]
    assert rules["RULE-COMP-01"] == "pass"
    assert rules["RULE-INC-01"] == "pass"
    assert rules["RULE-TAX-01"] == "flag"
    assert rules["RULE-ID-01"] == "pass"


def test_identity_mismatch_scenario_creates_intended_discrepancy(tmp_path):
    manifest = generate_dossier(seed=108, scenario="identity_mismatch", output_dir=str(tmp_path))

    applicant_name = manifest["applicant_facts"]["full_name"]
    payslip_name = manifest["payslip"]["employee_name"]
    assert applicant_name != payslip_name

    rules = manifest["expected_rule_outcomes"]
    assert rules["RULE-COMP-01"] == "pass"
    assert rules["RULE-INC-01"] == "pass"
    assert rules["RULE-TAX-01"] == "pass"
    assert rules["RULE-ID-01"] == "flag"


def test_missing_document_scenarios_actually_omit_documents(tmp_path):
    # 1. Missing payslip scenario
    dir_no_payslip = str(tmp_path / "no_payslip")
    m_pay = generate_dossier(seed=109, scenario="missing_payslip", output_dir=dir_no_payslip)
    folder_pay = os.path.join(dir_no_payslip, m_pay["application_id"])

    assert not os.path.exists(os.path.join(folder_pay, "payslip_1.pdf"))
    assert not os.path.exists(os.path.join(folder_pay, "payslip_2.pdf"))
    assert not os.path.exists(os.path.join(folder_pay, "payslip_3.pdf"))
    assert os.path.exists(os.path.join(folder_pay, "bank_statement.pdf"))
    assert m_pay["expected_rule_outcomes"]["RULE-COMP-01"] == "flag"
    assert m_pay["expected_rule_outcomes"]["RULE-INC-01"] == "unknown"

    # 2. Missing ITR scenario
    dir_no_itr = str(tmp_path / "no_itr")
    m_itr = generate_dossier(seed=110, scenario="missing_itr", output_dir=dir_no_itr)
    folder_itr = os.path.join(dir_no_itr, m_itr["application_id"])

    assert not os.path.exists(os.path.join(folder_itr, "itr.pdf"))
    assert os.path.exists(os.path.join(folder_itr, "payslip_1.pdf"))
    assert m_itr["expected_rule_outcomes"]["RULE-COMP-01"] == "flag"
    assert m_itr["expected_rule_outcomes"]["RULE-TAX-01"] == "unknown"


def test_bank_arithmetic_is_correct(tmp_path):
    manifest = generate_dossier(seed=111, scenario="clean", output_dir=str(tmp_path))
    fgt = manifest["financial_ground_truth"]

    opening = fgt["bank_opening_balance"]
    credits = fgt["bank_total_credits"]
    debits = fgt["bank_total_debits"]
    closing = fgt["bank_closing_balance"]

    assert round(opening + credits - debits, 2) == round(closing, 2)


def test_no_real_customer_data_used(tmp_path):
    manifest = generate_dossier(seed=112, scenario="clean", output_dir=str(tmp_path))
    app_folder = os.path.join(str(tmp_path), manifest["application_id"])

    # Synthetic identifiers
    pan = manifest["applicant_facts"]["pan_number"]
    assert pan.startswith("ABCDE") and pan.endswith("F")

    aadhaar = manifest["applicant_facts"]["aadhaar_masked"]
    assert aadhaar.startswith("XXXX-XXXX-")

    # Watermark test on all rendered pages
    for f in manifest["generated_document_names"]:
        p = os.path.join(app_folder, f)
        doc = pymupdf.open(p)
        for page in doc:
            assert "SYNTHETIC DEMO — NOT VALID" in page.get_text()
        doc.close()


def test_generated_text_contains_extractor_compatible_labels(tmp_path):
    manifest = generate_dossier(seed=113, scenario="clean", output_dir=str(tmp_path))
    app_folder = os.path.join(str(tmp_path), manifest["application_id"])

    # 1. Test Payslip Extraction with Member 3's PayslipExtractor
    payslip_pages = extract_all_pages_content(os.path.join(app_folder, "payslip_1.pdf"))
    payslip_facts = PayslipExtractor().extract("DOC-PAY", payslip_pages)
    assert payslip_facts.employee_name != "UNKNOWN"
    assert payslip_facts.employer_name != "UNKNOWN"
    assert payslip_facts.gross_salary.amount > 0
    assert payslip_facts.net_salary.amount > 0
    assert "Net Salary:" in payslip_facts.net_salary.source.quoted_span

    # 2. Test Bank Statement Extraction with Member 3's BankStatementExtractor
    bank_pages = extract_all_pages_content(os.path.join(app_folder, "bank_statement.pdf"))
    bank_facts = BankStatementExtractor().extract("DOC-BANK", bank_pages)
    assert bank_facts.account_holder != "UNKNOWN"
    assert bank_facts.bank_name != "UNKNOWN"
    assert len(bank_facts.salary_credits) >= 3
    assert bank_facts.average_salary_credit is not None
    assert bank_facts.average_salary_credit.amount > 0
    assert bank_facts.closing_balance is not None
    assert bank_facts.closing_balance.amount > 0

    # 3. Test Tax Return Extraction with Member 3's TaxReturnExtractor
    tax_pages = extract_all_pages_content(os.path.join(app_folder, "itr.pdf"))
    tax_facts = TaxReturnExtractor().extract("DOC-TAX", tax_pages)
    assert tax_facts.assessee_name != "UNKNOWN"
    assert tax_facts.pan_number != "UNKNOWN"
    assert tax_facts.gross_total_income.amount > 0

    # 4. Test KYC Extraction with Member 3's IdCardExtractor
    kyc_pages = extract_all_pages_content(os.path.join(app_folder, "kyc.pdf"))
    id_facts = IdCardExtractor().extract("DOC-KYC", kyc_pages)
    assert id_facts.full_name != "UNKNOWN"
    assert id_facts.pan_number != "UNKNOWN"
    assert id_facts.aadhaar_masked is not None
    assert id_facts.aadhaar_masked.startswith("XXXX-XXXX-")


def test_baseline_and_manipulated_values_ground_truth(tmp_path):
    # 1. Clean scenario: manipulated_values must be empty dict {}
    clean_manifest = generate_dossier(seed=201, scenario="clean", output_dir=str(tmp_path / "clean"))
    assert "baseline_values" in clean_manifest
    assert "applicant" in clean_manifest["baseline_values"]
    assert "financial" in clean_manifest["baseline_values"]
    assert clean_manifest["manipulated_values"] == {}

    # 2. Salary mismatch scenario: manipulated_values records reconciliation details
    sal_manifest = generate_dossier(seed=202, scenario="salary_mismatch", output_dir=str(tmp_path / "sal"))
    assert "salary_reconciliation" in sal_manifest["manipulated_values"]
    sal_manip = sal_manifest["manipulated_values"]["salary_reconciliation"]
    assert sal_manip["configured_tolerance"] == 0.05
    assert sal_manip["exceeds_tolerance"] is True
    assert sal_manip["variance_ratio"] > 0.05

    # 3. Tax mismatch scenario
    tax_manifest = generate_dossier(seed=203, scenario="tax_mismatch", output_dir=str(tmp_path / "tax"))
    assert "tax_reconciliation" in tax_manifest["manipulated_values"]
    tax_manip = tax_manifest["manipulated_values"]["tax_reconciliation"]
    assert tax_manip["configured_tolerance"] == 0.05
    assert tax_manip["exceeds_tolerance"] is True
    assert tax_manip["variance_ratio"] > 0.05

    # 4. Identity mismatch scenario
    id_manifest = generate_dossier(seed=204, scenario="identity_mismatch", output_dir=str(tmp_path / "id"))
    assert "identity_check" in id_manifest["manipulated_values"]
    id_manip = id_manifest["manipulated_values"]["identity_check"]
    assert id_manip["kyc_pass_threshold"] == 0.85
    assert id_manip["kyc_flag_threshold"] == 0.70
    assert id_manip["expected_verdict"] == "flag"


def test_expected_rule_details_structure_and_thresholds(tmp_path):
    manifest = generate_dossier(seed=205, scenario="clean", output_dir=str(tmp_path))
    assert "expected_rule_details" in manifest
    details = manifest["expected_rule_details"]

    assert "RULE-COMP-01" in details
    assert details["RULE-COMP-01"]["rule_id"] == "RULE-COMP-01"
    assert details["RULE-COMP-01"]["verdict"] == "pass"
    assert len(details["RULE-COMP-01"]["expected_documents"]) == 7

    assert "RULE-INC-01" in details
    assert details["RULE-INC-01"]["configured_tolerance"] == 0.05
    assert details["RULE-INC-01"]["verdict"] == "pass"

    assert "RULE-TAX-01" in details
    assert details["RULE-TAX-01"]["configured_tolerance"] == 0.05
    assert details["RULE-TAX-01"]["verdict"] == "pass"

    assert "RULE-ID-01" in details
    assert details["RULE-ID-01"]["kyc_pass_threshold"] == 0.85
    assert details["RULE-ID-01"]["kyc_flag_threshold"] == 0.70
    assert details["RULE-ID-01"]["verdict"] == "pass"


def test_all_supported_scenarios_generate_valid_ground_truth(tmp_path):
    for idx, scenario in enumerate(SUPPORTED_SCENARIOS, 1):
        s_dir = str(tmp_path / f"scen_{scenario}")
        manifest = generate_dossier(seed=300 + idx, scenario=scenario, output_dir=s_dir)

        # Baseline values must be present and structured
        assert "baseline_values" in manifest
        assert manifest["baseline_values"]["applicant"]["full_name"] != ""
        assert manifest["baseline_values"]["financial"]["monthly_gross"] > 0

        # Expected rule outcomes must cover all 4 rules
        rules = manifest["expected_rule_outcomes"]
        for rule_id in ("RULE-COMP-01", "RULE-INC-01", "RULE-TAX-01", "RULE-ID-01"):
            assert rule_id in rules
            assert rules[rule_id] in ("pass", "flag", "unknown")
            assert manifest["expected_rule_details"][rule_id]["verdict"] == rules[rule_id]

        # Clean has empty manipulated_values, others have content
        if scenario == "clean":
            assert manifest["manipulated_values"] == {}
        else:
            assert len(manifest["manipulated_values"]) > 0


def test_cli_single_scenario_generation(tmp_path):
    out_dir = str(tmp_path / "cli_output")
    result = subprocess.run(
        [
            sys.executable,
            os.path.join("scripts", "generate_dossiers.py"),
            "--seed",
            "42",
            "--scenario",
            "salary_mismatch",
            "--output-dir",
            out_dir,
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Generated dossier: APP-00042" in result.stdout
    manifest_path = os.path.join(out_dir, "APP-00042", "dossier_manifest.json")
    assert os.path.exists(manifest_path)
    with open(manifest_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["scenario"] == "salary_mismatch"
    assert loaded["expected_rule_outcomes"]["RULE-INC-01"] == "flag"
    assert "baseline_values" in loaded
    assert "manipulated_values" in loaded
