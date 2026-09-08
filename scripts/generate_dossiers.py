"""
FinScan AI: Synthetic Loan Dossier & Controlled Discrepancy Generator
Generates realistic multi-page PDF dossiers from the Kaggle Loan Approval dataset schema,
injecting controlled anomalies (salary inflation, name mismatch, missing docs) for testing and live hackathon demos.
"""

import os
import json
import random
from typing import Dict, Any, List

SAMPLE_APPLICANTS = [
    {
        "applicant_name": "Aarav Sharma",
        "company_name": "Tata Consultancy Services Ltd",
        "income_annum": 1200000.0,
        "loan_amount": 3500000.0,
        "loan_term": 15,
        "cibil_score": 780,
        "education": "Graduate",
        "self_employed": "No",
        "no_of_dependents": 2,
        "assets_total": 4500000.0,
        "inject_anomaly": None  # Clean baseline application
    },
    {
        "applicant_name": "Priya Patel",
        "company_name": "Infosys Technologies Ltd",
        "income_annum": 960000.0,
        "loan_amount": 2500000.0,
        "loan_term": 10,
        "cibil_score": 745,
        "education": "Graduate",
        "self_employed": "No",
        "no_of_dependents": 1,
        "assets_total": 3000000.0,
        "inject_anomaly": None  # Clean baseline application
    },
    {
        "applicant_name": "Vikram Malhotra",
        "company_name": "Apex Global Solutions",
        "income_annum": 1800000.0,  # Stated on loan application: ₹1,50,000 / month
        "loan_amount": 6000000.0,
        "loan_term": 20,
        "cibil_score": 690,
        "education": "Graduate",
        "self_employed": "No",
        "no_of_dependents": 3,
        "assets_total": 5000000.0,
        "inject_anomaly": "SALARY_INFLATION"  # Payslip says 1,50,000, but Bank Credits only show 45,000!
    },
    {
        "applicant_name": "Sneha Kulkarni",
        "company_name": "Wipro Enterprises",
        "income_annum": 840000.0,
        "loan_amount": 2000000.0,
        "loan_term": 8,
        "cibil_score": 760,
        "education": "Graduate",
        "self_employed": "No",
        "no_of_dependents": 0,
        "assets_total": 2200000.0,
        "inject_anomaly": "NAME_MISMATCH"  # PAN says "Sneha R Kulkarni", Payslip says "Sneha Joshi"
    },
    {
        "applicant_name": "Rajesh Nair",
        "company_name": "Freelance IT Consultant",
        "income_annum": 1400000.0,
        "loan_amount": 4000000.0,
        "loan_term": 12,
        "cibil_score": 620,
        "education": "Graduate",
        "self_employed": "Yes",
        "no_of_dependents": 2,
        "assets_total": 2800000.0,
        "inject_anomaly": "MISSING_BANK_STATEMENT"  # Missing mandatory 3-month statement
    }
]


def generate_dossier_data(applicant: Dict[str, Any], output_dir: str):
    """Generates synthetic dossier metadata and saves JSON simulation files."""
    app_id = f"APP-{random.randint(10000, 99999)}"
    folder = os.path.join(output_dir, app_id)
    os.makedirs(folder, exist_ok=True)

    monthly_salary = applicant["income_annum"] / 12.0
    bank_credit = monthly_salary
    payslip_name = applicant["applicant_name"]
    pan_number = f"ABCDE{random.randint(1000, 9999)}F"

    # Inject deliberate anomalies based on test scenario
    anomaly = applicant.get("inject_anomaly")
    if anomaly == "SALARY_INFLATION":
        bank_credit = monthly_salary * 0.35  # Severe mismatch!
    elif anomaly == "NAME_MISMATCH":
        payslip_name = applicant["applicant_name"].replace("Kulkarni", "Joshi")

    metadata = {
        "application_id": app_id,
        "applicant_name": applicant["applicant_name"],
        "injected_anomaly": anomaly,
        "payslip": {
            "employee_name": payslip_name,
            "employer_name": applicant["company_name"],
            "gross_salary": round(monthly_salary, 2),
            "net_salary": round(monthly_salary * 0.88, 2),
            "epf_deduction": round(monthly_salary * 0.08, 2),
            "tds_deduction": round(monthly_salary * 0.04, 2)
        },
        "bank_statement": {
            "account_holder": applicant["applicant_name"],
            "bank_name": "HDFC Bank Ltd",
            "account_number": f"50100{random.randint(1000000, 9999999)}",
            "monthly_salary_credits": [round(bank_credit, 2)] * 3,
            "average_balance": round(bank_credit * 0.45, 2),
            "bounced_transactions": 2 if anomaly == "BOUNCED_TRANSACTIONS" else 0
        },
        "tax_return": {
            "assessee_name": applicant["applicant_name"],
            "pan_number": pan_number,
            "gross_total_income": round(applicant["income_annum"], 2),
            "total_tax_paid": round(applicant["income_annum"] * 0.12, 2)
        },
        "kyc": {
            "full_name": applicant["applicant_name"],
            "pan_number": pan_number,
            "dob": "1994-06-15",
            "aadhaar_masked": f"XXXX-XXXX-{random.randint(1000, 9999)}"
        },
        "tabular_features": {
            "no_of_dependents": applicant["no_of_dependents"],
            "education": applicant["education"],
            "self_employed": applicant["self_employed"],
            "income_annum": applicant["income_annum"],
            "loan_amount": applicant["loan_amount"],
            "loan_term": applicant["loan_term"],
            "cibil_score": applicant["cibil_score"],
            "assets_total": applicant["assets_total"]
        }
    }

    if anomaly == "MISSING_BANK_STATEMENT":
        metadata.pop("bank_statement")

    json_path = os.path.join(folder, "dossier_manifest.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Generated {app_id} | Anomaly: {anomaly or 'None (Clean)'} -> {folder}")


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic_dossiers")
    os.makedirs(out_dir, exist_ok=True)
    print("🚀 Generating Synthetic Loan Dossiers for FinScan AI...")
    for item in SAMPLE_APPLICANTS:
        generate_dossier_data(item, out_dir)
    print(f"\n🎉 Done! Synthetic test applications saved in {out_dir}")
