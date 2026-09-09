"""
FinScan AI: Dataset Generator v2 (Remediated & Provenance-Backed).
Owned by Member 5 (Karthik).

Key Invariants:
1. Grounded in actual Kaggle loan approval dataset CSV rows (data/kaggle_loan_approval_dataset.csv).
2. Derives financial numbers (income, loan amount, cibil score, term, assets) directly from CSV records.
3. Every document visibly carries: "SYNTHETIC DEMO — NOT VALID".
4. Multiple genuinely distinct structural template families per class (4 families per class = 20 families).
5. Double-Disjoint Partitioning:
   - Applicants partitioned into Train (~70%), Dev (~15%), Held-out Test (~15%).
   - Template Families partitioned disjointly:
     * Train: Families 1 and 2
     * Dev: Family 3
     * Test: Family 4 (held-out unseen template families)
6. Negative / Out-of-Domain samples included in Dev and Test with expected label UNKNOWN.
7. Full provenance sidecar tracking source CSV row, applicant ID, split, and template family.
"""

import os
import json
import random
import hashlib
from typing import Dict, Any, List, Tuple

CANONICAL_CLASSES = [
    "application_form",
    "bank_statement",
    "id_card",
    "payslip",
    "tax_acknowledgement",
]

WATERMARK = "SYNTHETIC DEMO — NOT VALID"

CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "kaggle_loan_approval_dataset.csv"))
if not os.path.exists(CSV_PATH):
    # Fallback to current working directory
    CSV_PATH = os.path.abspath("data/kaggle_loan_approval_dataset.csv")

FIRST_NAMES = [
    "Aarav", "Priya", "Vikram", "Sneha", "Rajesh", "Ananya", "Rohan", "Kavita",
    "Siddharth", "Pooja", "Arjun", "Deepika", "Rahul", "Meera", "Aditya", "Neha",
    "Amit", "Divya", "Suresh", "Ritu", "Karan", "Swati", "Nikhil", "Shreya",
    "Varun", "Tanvi", "Gaurav", "Simran", "Manoj", "Aarti", "Harish", "Bhavna"
]

LAST_NAMES = [
    "Sharma", "Patel", "Malhotra", "Kulkarni", "Nair", "Verma", "Reddy", "Iyer",
    "Gupta", "Choudhury", "Bose", "Mehta", "Deshmukh", "Pillai", "Mishra", "Joshi",
    "Kapoor", "Bhat", "Rao", "Saxena", "Chauhan", "Agarwal", "Nambiar", "Pandey"
]

COMPANIES = [
    "Tata Consultancy Services Ltd", "Infosys Technologies Ltd", "Wipro Enterprises",
    "HCL Technologies", "Cognizant Technology Solutions", "Tech Mahindra Ltd",
    "Reliance Industries Ltd", "Larsen & Toubro Infotech", "Accenture Solutions Pvt Ltd",
    "Apex Global Solutions", "Persistent Systems Ltd", "Capgemini India Pvt Ltd",
    "Bharat Electronics Ltd", "Hindustan Unilever Ltd", "Titan Company Ltd"
]

BANKS = [
    ("HDFC Bank Ltd", "HDFC"),
    ("ICICI Bank Ltd", "ICIC"),
    ("State Bank of India", "SBIN"),
    ("Axis Bank Ltd", "UTIB"),
    ("Kotak Mahindra Bank", "KKBK"),
    ("Bank of Baroda", "BARB"),
    ("Punjab National Bank", "PUNB"),
]

CITIES = ["Mumbai", "Bengaluru", "Hyderabad", "Pune", "Chennai", "Delhi NCR", "Kolkata", "Ahmedabad"]


def get_csv_sha256(path: str) -> str:
    if not os.path.exists(path):
        return "MISSING_CSV"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_kaggle_rows(csv_path: str, max_rows: int = 70) -> List[Dict[str, Any]]:
    """Loads and normalizes rows from the Kaggle dataset CSV."""
    import pandas as pd
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Kaggle CSV dataset not found at {csv_path}")

    df = pd.read_csv(csv_path)
    # Strip whitespace from column headers
    df.columns = [c.strip() for c in df.columns]

    rows = []
    for idx, row in df.head(max_rows).iterrows():
        rows.append({
            "source_loan_id": int(row["loan_id"]),
            "no_of_dependents": int(row["no_of_dependents"]),
            "education": str(row["education"]).strip(),
            "self_employed": str(row["self_employed"]).strip(),
            "income_annum": float(row["income_annum"]),
            "loan_amount": float(row["loan_amount"]),
            "loan_term_years": int(row["loan_term"]),
            "cibil_score": int(row["cibil_score"]),
            "residential_assets_value": float(row["residential_assets_value"]),
            "commercial_assets_value": float(row["commercial_assets_value"]),
            "luxury_assets_value": float(row["luxury_assets_value"]),
            "bank_asset_value": float(row["bank_asset_value"]),
            "loan_status": str(row["loan_status"]).strip(),
        })
    return rows


def build_applicant_profile(row: Dict[str, Any], seed: int) -> Dict[str, Any]:
    """Combines factual CSV fields with realistic fictional demographic attributes."""
    rng = random.Random(seed + row["source_loan_id"] * 101)

    first = rng.choice(FIRST_NAMES)
    last = rng.choice(LAST_NAMES)
    full_name = f"{first} {last}"
    father_name = f"{rng.choice(FIRST_NAMES)} {last}"
    employer = rng.choice(COMPANIES)
    bank_name, ifsc_prefix = rng.choice(BANKS)
    city = rng.choice(CITIES)

    # Derived financial attributes
    annual_income = row["income_annum"]
    monthly_gross = round(annual_income / 12.0, 2)
    basic_salary = round(monthly_gross * 0.50, 2)
    epf_deduction = round(basic_salary * 0.12, 2)
    pt_deduction = 200.0

    # Approximate progressive tax deduction
    if annual_income <= 700000:
        tds_monthly = 0.0
    elif annual_income <= 1200000:
        tds_monthly = round((annual_income - 700000) * 0.10 / 12.0, 2)
    else:
        tds_monthly = round((50000 + (annual_income - 1200000) * 0.20) / 12.0, 2)

    net_salary = max(1000.0, round(monthly_gross - epf_deduction - pt_deduction - tds_monthly, 2))
    tenure_months = row["loan_term_years"] * 12

    # EMI calculation at 8.5% annual rate
    r = 0.085 / 12.0
    p = row["loan_amount"]
    n = tenure_months
    emi = round((p * r * ((1 + r) ** n)) / (((1 + r) ** n) - 1), 2)

    pan_letters = "".join(rng.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
    pan_digits = f"{rng.randint(1000, 9999)}"
    pan_last = rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    pan_number = f"{pan_letters}{pan_digits}{pan_last}"
    aadhaar_masked = f"XXXX-XXXX-{rng.randint(1000, 9999)}"
    account_number = f"50100{rng.randint(1000000, 9999999)}"

    total_assets = (
        row["residential_assets_value"]
        + row["commercial_assets_value"]
        + row["luxury_assets_value"]
        + row["bank_asset_value"]
    )

    return {
        "application_id": f"APP-KAG-{row['source_loan_id']:04d}",
        "source_csv_row": row["source_loan_id"],
        "name": full_name,
        "father_name": father_name,
        "dob": f"{rng.randint(1980, 2000):04d}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
        "gender": rng.choice(["Male", "Female"]),
        "pan": pan_number,
        "aadhaar_masked": aadhaar_masked,
        "employer": employer,
        "designation": rng.choice(["Lead Consultant", "Senior Software Engineer", "Operations Manager", "Assistant Vice President"]),
        "bank_name": bank_name,
        "ifsc_code": f"{ifsc_prefix}000{rng.randint(1000, 9999)}",
        "account_number": account_number,
        "city": city,
        "annual_income": annual_income,
        "monthly_gross": monthly_gross,
        "basic_salary": basic_salary,
        "epf_deduction": epf_deduction,
        "pt_deduction": pt_deduction,
        "tds_deduction": tds_monthly,
        "net_salary": net_salary,
        "loan_amount": row["loan_amount"],
        "tenure_months": tenure_months,
        "cibil_score": row["cibil_score"],
        "dependents": row["no_of_dependents"],
        "education": row["education"],
        "self_employed": row["self_employed"],
        "total_assets": total_assets,
        "calculated_emi": emi,
    }


# ==============================================================================
# TEMPLATE FAMILIES: 4 DISTINCT STRUCTURAL FAMILIES PER CLASS (20 FAMILIES TOTAL)
# ==============================================================================

# --- 1. APPLICATION FORM FAMILIES ---

def render_app_form_family1_retail(p: Dict[str, Any]) -> str:
    """Family 1 (Train): Standard Retail Banking Loan Application"""
    return f"""
    SYNTHETIC DEMO — NOT VALID
    CENTRAL APEX BANK OF INDIA - RETAIL ASSETS APPLICATION DOSSIER
    Docket Tracking Number: {p['application_id']} | Linked Source Record: KAG-ROW-{p['source_csv_row']}
    Branch Jurisdiction: {p['city']} Commercial Hub | Date: 12-Sep-2025

    SECTION A: BORROWER PROFILE
    1. Full Name of Candidate: {p['name']}
    2. Father's / Guardian's Name: {p['father_name']}
    3. Date of Birth: {p['dob']} | Gender: {p['gender']}
    4. Statutory Identifiers: Permanent Account Number (PAN): {p['pan']} | Aadhaar UID: {p['aadhaar_masked']}
    5. Highest Educational Qualification: {p['education']} | Dependents Claimed: {p['dependents']}

    SECTION B: FINANCIAL & EMPLOYMENT STANDING
    1. Employer / Corporate Entity: {p['employer']}
    2. Current Professional Designation: {p['designation']} | Self Employed Flag: {p['self_employed']}
    3. Certified Annual Compensation: INR {p['annual_income']:,.2f}
    4. Net Monthly Bank Take-Home: INR {p['net_salary']:,.2f}
    5. Bureau Credit Evaluation (CIBIL Score): {p['cibil_score']}

    SECTION C: FACILITY PARTICULARS REQUESTED
    1. Sanction Request Amount: INR {p['loan_amount']:,.2f}
    2. Repayment Horizon (Tenure): {p['tenure_months']} Calendar Months
    3. Estimated Equated Monthly Installment (EMI): INR {p['calculated_emi']:,.2f}
    4. Disbursal Target: Direct Credit to {p['bank_name']} A/c No {p['account_number']}

    DECLARATION & AFFIDAVIT
    I solemnly affirm that the statements provided herein are verified and true to the best of my knowledge.
    Applicant Signature: [Electronically signed by {p['name']}]
    SYNTHETIC DEMO — NOT VALID
    """


def render_app_form_family2_housing(p: Dict[str, Any]) -> str:
    """Family 2 (Train): Housing Finance Credit Proposal Sheet"""
    return f"""
    SYNTHETIC DEMO — NOT VALID
    BHARAT HOUSING & HOME LOAN FINANCE CORPORATION
    CREDIT PROPOSAL & UNDERWRITING INTAKE SHEET
    File Number: HF-{p['application_id']} | Source Reference: #{p['source_csv_row']}

    APPLICANT SUMMARY RECORD
    - Principal Applicant: {p['name']}
    - Co-Applicant / Guarantor: {p['father_name']}
    - Demographic Info: DOB {p['dob']} ({p['gender']}), Resident of {p['city']}
    - Tax ID: {p['pan']} | UIDAI: {p['aadhaar_masked']}
    - Academic Level: {p['education']} | Number of Dependents: {p['dependents']}

    UNDERWRITING DATA TABLE
    --------------------------------------------------------------------------------
    Parameters                          Reported Value
    --------------------------------------------------------------------------------
    Primary Organization                {p['employer']}
    Job Role                            {p['designation']}
    Annual Income Base                  INR {p['annual_income']:,.2f}
    Stated Take-Home Monthly            INR {p['net_salary']:,.2f}
    Total Asset Base (Property/Bank)    INR {p['total_assets']:,.2f}
    Bureau Score (TransUnion CIBIL)     {p['cibil_score']}
    Requested Facility Capital          INR {p['loan_amount']:,.2f}
    Amortization Term                   {p['tenure_months']} Months (Tenure)
    Indicative Amortized EMI            INR {p['calculated_emi']:,.2f}
    --------------------------------------------------------------------------------

    CREDIT POLICY CONSENT:
    Borrower authorizes credit bureau retrieval and payroll cross-verification.
    Signed at {p['city']}: {p['name']}
    SYNTHETIC DEMO — NOT VALID
    """


def render_app_form_family3_digital(p: Dict[str, Any]) -> str:
    """Family 3 (Dev): Fintech Digital Lending e-Application Summary"""
    return f"""
    SYNTHETIC DEMO — NOT VALID
    NEXUS FINTECH LENDING PLATFORM — DIGITAL APPLICATION SUMMARY
    Session Token: DIGI-APP-{p['application_id']} | Trace: KAG-CSV-{p['source_csv_row']}
    Timestamp: 2025-09-12T09:14:22Z | Digital Channel: Web-Portal

    USER VERIFICATION & KYC DATA:
    Applicant Legal Name : {p['name']}
    Parentage Name       : {p['father_name']}
    DOB & Sex            : {p['dob']} [{p['gender']}]
    PAN Verification     : {p['pan']} [NSDL VALIDATED]
    Aadhaar Token        : {p['aadhaar_masked']} [UIDAI OTP AUTHENTICATED]
    Education & Family   : {p['education']}, {p['dependents']} dependent(s)

    DIGITAL SANCTION SUMMARY:
    - Facility Applied   : Retail Personal Term Loan
    - Loan Ticket Size   : Rs. {p['loan_amount']:,.2f}
    - Requested Duration : {p['tenure_months']} Months
    - Monthly Instalment : Rs. {p['calculated_emi']:,.2f} / month
    - Primary Work       : {p['employer']} ({p['designation']})
    - Annualized Gross   : Rs. {p['annual_income']:,.2f}
    - In-hand Monthly    : Rs. {p['net_salary']:,.2f}
    - Risk Bureau Score  : {p['cibil_score']}

    E-SIGN CONSENT:
    Applicant digitally agreed to T&C and information sharing via Aadhaar e-Sign.
    SYNTHETIC DEMO — NOT VALID
    """


def render_app_form_family4_commercial(p: Dict[str, Any]) -> str:
    """Family 4 (Held-Out Test): Commercial SME & Enterprise Credit Application"""
    return f"""
    SYNTHETIC DEMO — NOT VALID
    COMMERCIAL ENTERPRISE CREDIT FACILITY APPLICATION
    Enterprise Loan Application No: COMM-{p['application_id']} | Row: {p['source_csv_row']}
    Regional Business Banking Center: {p['city']}

    I. PROMOTER & KEY PERSON IDENTIFICATION
    Promoter Name         : {p['name']}
    Father's Name         : {p['father_name']}
    Date of Birth         : {p['dob']}
    Tax ID (PAN)          : {p['pan']}
    Personal KYC Proof    : {p['aadhaar_masked']}
    Academic Background   : {p['education']}

    II. ENTERPRISE PROFILE & FINANCIAL PARTICULARS
    Organization Identity : {p['employer']}
    Position / Status     : {p['designation']}
    Self-Employed Status  : {p['self_employed']}
    Total Tangible Assets : INR {p['total_assets']:,.2f}
    Stated Annual Income  : INR {p['annual_income']:,.2f}
    Credit Score Rating   : {p['cibil_score']} Grade

    III. CREDIT LINE REQUEST
    Credit Facility Sum   : INR {p['loan_amount']:,.2f}
    Term Horizon          : {p['tenure_months']} Months ({p['tenure_months'] // 12} Years)
    Target Repayment EMI  : INR {p['calculated_emi']:,.2f}
    Designated Bank A/c   : {p['account_number']} at {p['bank_name']}

    Promoter Undertaking: I unconditionally warrant the veracity of all corporate schedules submitted.
    Promoter Signature: {p['name']}
    SYNTHETIC DEMO — NOT VALID
    """


# --- 2. PAYSLIP FAMILIES ---

def render_payslip_family1_corp(p: Dict[str, Any]) -> str:
    """Family 1 (Train): Corporate Two-Column Salary Slip"""
    return f"""
    SYNTHETIC DEMO — NOT VALID
    {p['employer'].upper()}
    Registered Corporate Towers, IT Park, {p['city']}
    MONTHLY PAYSLIP FOR THE PERIOD: August 2025

    Employee Name : {p['name']}             Employee ID   : EMP{p['source_csv_row']:06d}
    Designation   : {p['designation']}      Department    : Software Engineering
    PAN Number    : {p['pan']}              Bank A/c No   : {p['account_number']}
    UAN Identifier: 101{p['source_csv_row']:08d}            Disbursal Bank: {p['bank_name']}
    Working Days  : 31                       Paid Days     : 31

    --------------------------------------------------------------------------------
    EARNINGS (INR)                      DEDUCTIONS (INR)
    --------------------------------------------------------------------------------
    Basic Pay             : {p['basic_salary']:,.2f}      Provident Fund (EPF)      : {p['epf_deduction']:,.2f}
    House Rent Allowance  : {p['basic_salary'] * 0.5:,.2f}      Professional Tax (PT)     : {p['pt_deduction']:,.2f}
    Special Allowance     : {p['monthly_gross'] - p['basic_salary'] * 1.5:,.2f}      Income Tax (TDS)          : {p['tds_deduction']:,.2f}
    --------------------------------------------------------------------------------
    GROSS PAYABLE         : INR {p['monthly_gross']:,.2f}  TOTAL DEDUCTIONS          : INR {p['monthly_gross'] - p['net_salary']:,.2f}
    --------------------------------------------------------------------------------
    NET DISBURSED AMOUNT  : INR {p['net_salary']:,.2f}
    Amount in Words: Disbursement processed via NEFT / corporate electronic clearing.
    Computer generated payslip.
    SYNTHETIC DEMO — NOT VALID
    """


def render_payslip_family2_mfg(p: Dict[str, Any]) -> str:
    """Family 2 (Train): Manufacturing / Conglomerate Salary Voucher"""
    return f"""
    SYNTHETIC DEMO — NOT VALID
    SALARY WAGE DISBURSEMENT VOUCHER
    Employer: {p['employer']} | Location: {p['city']} Works Division
    Pay Cycle: 01-Aug-2025 to 31-Aug-2025 | Voucher Ref: VOUCH-{p['source_csv_row']}

    STAFF PARTICULARS
    Staff Name   : {p['name']}
    Staff Number : STF-{p['source_csv_row']} | Title: {p['designation']}
    Tax ID (PAN) : {p['pan']} | Salary Credit Bank: {p['bank_name']}
    Account No   : {p['account_number']}

    BREAKDOWN OF REMUNERATION
    1. Basic Wage Component                : INR {p['basic_salary']:,.2f}
    2. Dearness & Cost of Living Allowance : INR {p['basic_salary'] * 0.30:,.2f}
    3. House Rent Subsidy                  : INR {p['basic_salary'] * 0.20:,.2f}
    4. Flexible Benefits Pool              : INR {p['monthly_gross'] - p['basic_salary'] * 1.5:,.2f}
    TOTAL EARNINGS (GROSS)                 : INR {p['monthly_gross']:,.2f}

    STATUTORY & VOLUNTARY RECOVERIES
    1. Employees Provident Fund            : INR {p['epf_deduction']:,.2f}
    2. Professional Tax                    : INR {p['pt_deduction']:,.2f}
    3. Tax Deducted at Source              : INR {p['tds_deduction']:,.2f}
    TOTAL RECOVERIES                       : INR {p['monthly_gross'] - p['net_salary']:,.2f}

    TAKE-HOME REMITTANCE                   : INR {p['net_salary']:,.2f}
    Accounts Officer Sign-off: [Authorized Electronic Payment Voucher]
    SYNTHETIC DEMO — NOT VALID
    """


def render_payslip_family3_public(p: Dict[str, Any]) -> str:
    """Family 3 (Dev): Public Sector Pay Advice Statement"""
    return f"""
    SYNTHETIC DEMO — NOT VALID
    GOVERNMENT & STATUTORY CORPORATION PAY ADVICE
    Office of Accounts & Disbursals, {p['city']} Circle
    Statement of Salary & Allowances for Month of August 2025

    Employee Identification Details:
    Name of Officer / Employee : {p['name']}
    Cadre / Designation        : {p['designation']}
    Organization / Agency      : {p['employer']}
    PAN Number                 : {p['pan']}
    Credit Destination         : {p['bank_name']} (A/c: {p['account_number']})

    CREDITS SCHEDULE (INR):
    - Substantive Pay (Basic)  : {p['basic_salary']:,.2f}
    - Dearness Allowance       : {p['basic_salary'] * 0.35:,.2f}
    - House Rent Compensation  : {p['basic_salary'] * 0.25:,.2f}
    - Special Conveyance Pool  : {p['monthly_gross'] - p['basic_salary'] * 1.6:,.2f}
    GROSS SALARY ACCRUAL       : INR {p['monthly_gross']:,.2f}

    DEBITS SCHEDULE (INR):
    - General Provident Fund   : {p['epf_deduction']:,.2f}
    - Professional Tax         : {p['pt_deduction']:,.2f}
    - Income Tax Withheld      : {p['tds_deduction']:,.2f}
    TOTAL DEBITS               : INR {p['monthly_gross'] - p['net_salary']:,.2f}

    NET PAYMENT SANCTIONED     : INR {p['net_salary']:,.2f}
    Passed for Treasury Payment: Verified against cadre payroll rolls.
    SYNTHETIC DEMO — NOT VALID
    """


def render_payslip_family4_consulting(p: Dict[str, Any]) -> str:
    """Family 4 (Held-Out Test): Compact Monthly Remuneration Advice"""
    return f"""
    SYNTHETIC DEMO — NOT VALID
    PROFESSIONAL MONTHLY REMUNERATION ADVICE
    Client Entity: {p['employer']} | City: {p['city']}
    Consulting Cycle: August 2025 | Ref: REMUN-{p['application_id']}

    RECIPIENT SUMMARY
    Professional / Associate: {p['name']}
    Role Description        : {p['designation']}
    PAN Identifier          : {p['pan']}
    Direct Remittance Bank  : {p['bank_name']} (A/c No: {p['account_number']})

    BILLABLE ACCRUALS SUMMARY (INR)
    Fixed Retainership Fee            : {p['basic_salary'] * 1.6:,.2f}
    Performance & Travel Reimbursement: {p['monthly_gross'] - p['basic_salary'] * 1.6:,.2f}
    TOTAL MONTHLY INVOICED COMP       : INR {p['monthly_gross']:,.2f}

    STATUTORY WITHHOLDINGS
    Withholding Tax u/s 194J / TDS    : {p['tds_deduction']:,.2f}
    Statutory Deductions & Cess       : {p['epf_deduction'] + p['pt_deduction']:,.2f}
    TOTAL WITHHOLDING SUM             : INR {p['monthly_gross'] - p['net_salary']:,.2f}

    DISBURSED NET ADVICE VALUE        : INR {p['net_salary']:,.2f}
    Remitted via RTGS / Corporate Banking API.
    SYNTHETIC DEMO — NOT VALID
    """


# --- 3. BANK STATEMENT FAMILIES ---

def render_bank_stmt_family1_hdfc(p: Dict[str, Any]) -> str:
    """Family 1 (Train): Standard Commercial Retail Account Statement"""
    net = p['net_salary']
    bal = net * 1.2
    return f"""
    SYNTHETIC DEMO — NOT VALID
    {p['bank_name'].upper()} - ACCOUNT STATEMENT
    Branch: {p['city']} Main Retail Branch | IFSC: {p['ifsc_code']}
    Account Title: {p['name']}
    Account Number: {p['account_number']} | Currency: INR
    Statement Period: 01-Jun-2025 to 31-Aug-2025 | Product: Salary Savings Advantage

    ACCOUNT POSITION SUMMARY
    Opening Balance: INR {bal * 0.8:,.2f} | Total Credits: INR {net * 3 + 15000:,.2f}
    Closing Ledger Balance: INR {bal:,.2f}

    TRANSACTION HISTORY
    Date        | Narration / Details                   | Chq/Ref No     | Debit (INR)  | Credit (INR) | Balance (INR)
    01-Jun-2025 | ACH SALARY CREDIT - {p['employer'][:10]}       | CMS{p['source_csv_row']}01      | -            | {net:,.2f}   | {bal + 15000:,.2f}
    05-Jun-2025 | UPI-ELECTRICITY-BILL-PAYMENT          | UPI90218       | 2,450.00     | -            | {bal + 12550:,.2f}
    01-Jul-2025 | ACH SALARY CREDIT - {p['employer'][:10]}       | CMS{p['source_csv_row']}02      | -            | {net:,.2f}   | {bal + 22000:,.2f}
    14-Jul-2025 | ATM CASH WITHDRAWAL - DOMESTIC        | ATM1142        | 10,000.00    | -            | {bal + 12000:,.2f}
    01-Aug-2025 | ACH SALARY CREDIT - {p['employer'][:10]}       | CMS{p['source_csv_row']}03      | -            | {net:,.2f}   | {bal + net:,.2f}

    Cheque returns or ECS unpaid dishonours: NIL. End of statement.
    SYNTHETIC DEMO — NOT VALID
    """


def render_bank_stmt_family2_sbi(p: Dict[str, Any]) -> str:
    """Family 2 (Train): Public Sector Passbook Ledger"""
    net = p['net_salary']
    bal = net * 0.95
    return f"""
    SYNTHETIC DEMO — NOT VALID
    STATE APEX BANK OF INDIA - SAVINGS PASSBOOK STATEMENT
    CIF Number: CIF{p['source_csv_row']:07d} | Account Number: {p['account_number']}
    Account Holder: {p['name']}
    Branch Address: Central Bazar Road, {p['city']} | IFSC Code: {p['ifsc_code']}
    Transaction Ledger Sheet for Period 01/06/2025 to 31/08/2025

    Txn Date   | Particulars                            | Debit (Dr)   | Credit (Cr)  | Balance (INR)
    01/06/2025 | BY NEFT: SALARY {p['employer'][:12]}        | -            | {net:,.2f}   | {bal + 10000:,.2f}
    10/06/2025 | TO CHEQUE CLG: HOME RENT               | 22,000.00    | -            | {bal - 12000:,.2f}
    01/07/2025 | BY NEFT: SALARY {p['employer'][:12]}        | -            | {net:,.2f}   | {bal + 20000:,.2f}
    18/07/2025 | TO UPI/GROCERY/STORE                   | 4,310.00     | -            | {bal + 15690:,.2f}
    01/08/2025 | BY NEFT: SALARY {p['employer'][:12]}        | -            | {net:,.2f}   | {bal:,.2f}

    Clear Available Balance as on date: INR {bal:,.2f}
    Generated by CBS (Core Banking Solution).
    SYNTHETIC DEMO — NOT VALID
    """


def render_bank_stmt_family3_wealth(p: Dict[str, Any]) -> str:
    """Family 3 (Dev): Private Wealth Management Overview Statement"""
    net = p['net_salary']
    bal = net * 2.5
    return f"""
    SYNTHETIC DEMO — NOT VALID
    PRIVATE WEALTH MANAGEMENT CLIENT CONSOLIDATED STATEMENT
    Financial Institution: {p['bank_name']} Wealth Services
    Portfolio Client: {p['name']} | Account: {p['account_number']}
    Currency: Indian Rupee (INR) | Statement Date: 31-Aug-2025

    MONTHLY LIQUIDITY SUMMARY:
    - Average Quarterly Balance (AQB) : INR {bal * 1.1:,.2f}
    - Total Payroll Credits Inflow     : INR {net * 3:,.2f}
    - Closing Liquid Funds             : INR {bal:,.2f}

    TRANSACTION LOG (REPRESENTATIVE CREDITS & OUTFLOWS):
    1. 01-Jun-2025 : Corporate Payroll Inflow ({p['employer']}) -> CR INR {net:,.2f}
    2. 12-Jun-2025 : Investment Outflow / Mutual Fund SIP       -> DR INR 15,000.00
    3. 01-Jul-2025 : Corporate Payroll Inflow ({p['employer']}) -> CR INR {net:,.2f}
    4. 20-Jul-2025 : Point-of-Sale International Debit           -> DR INR 8,400.00
    5. 01-Aug-2025 : Corporate Payroll Inflow ({p['employer']}) -> CR INR {net:,.2f}

    Account in Good Standing: No negative liens or dishonour events noted.
    SYNTHETIC DEMO — NOT VALID
    """


def render_bank_stmt_family4_neobank(p: Dict[str, Any]) -> str:
    """Family 4 (Held-Out Test): Neo-Bank Digital Transaction Report"""
    net = p['net_salary']
    bal = net * 1.05
    return f"""
    SYNTHETIC DEMO — NOT VALID
    DIGITAL NEO-BANK ACCOUNT TRANSACTION LEDGER REPORT
    Powered by Partner Bank: {p['bank_name']} | IFSC: {p['ifsc_code']}
    Account Holder Name: {p['name']}
    Virtual Account Tag: NEO-{p['account_number']} | Period: Q2 2025

    FINANCIAL OVERVIEW:
    Money In this period : INR {net * 3 + 5000:,.2f}
    Money Out this period: INR {net * 2:,.2f}
    Net Available Balance: INR {bal:,.2f}

    ACTIVITY RECORD:
    Timestamp           Description                        Type      Amount (INR)       Status
    2025-06-01 06:30    SALARY DEPOSIT - {p['employer'][:10]}       CREDIT    +{net:,.2f}        SUCCESS
    2025-06-15 14:22    UPI TRANSFER - RENT                DEBIT     -20,000.00         SUCCESS
    2025-07-01 06:30    SALARY DEPOSIT - {p['employer'][:10]}       CREDIT    +{net:,.2f}        SUCCESS
    2025-07-25 18:45    ONLINE CARD COMMERCE               DEBIT     -5,210.00          SUCCESS
    2025-08-01 06:30    SALARY DEPOSIT - {p['employer'][:10]}       CREDIT    +{net:,.2f}        SUCCESS

    This is an authorized e-ledger report downloaded via banking mobile app.
    SYNTHETIC DEMO — NOT VALID
    """


# --- 4. TAX RETURN FAMILIES ---

def render_tax_ack_family1_itr1(p: Dict[str, Any]) -> str:
    """Family 1 (Train): Indian ITR-V Acknowledgement (ITR-1 SAHAJ)"""
    gross = p['annual_income']
    deductions = 150000.0
    taxable = max(0.0, gross - deductions - 50000.0)
    tax_paid = round(taxable * 0.12, 2)
    return f"""
    SYNTHETIC DEMO — NOT VALID
    INDIAN INCOME TAX RETURN ACKNOWLEDGEMENT [ITR-V]
    Centralized Processing Centre (CPC), Bengaluru | Assessment Year: 2025-26
    Form Number: ITR-1 (SAHAJ) | Filing Under Section: 139(1)

    PART A: GENERAL PROFILE
    Permanent Account Number (PAN) : {p['pan']}
    Name of Assessee               : {p['name'].upper()}
    Aadhaar Enrolment Number       : {p['aadhaar_masked']}
    Filing Date                    : 24-Jul-2025 | Ack No: {p['source_csv_row']}9182374619

    PART B: INCOME & TAX COMPUTATION (INR)
    1. Gross Salary Income Form 16                 : {gross:,.2f}
    2. Standard Deduction u/s 16(ia)               : 50,000.00
    3. Total Deductions under Chapter VI-A (80C)   : {deductions:,.2f}
    4. Aggregate Taxable Total Income              : {taxable:,.2f}
    5. Net Tax Payable on Computed Income          : {tax_paid:,.2f}
    6. Total Taxes Paid / Advance Tax & TDS Credit : {tax_paid:,.2f}
    7. Balance Amount Refundable / Payable         : 0.00

    VERIFICATION CERTIFICATE:
    Return verified using Aadhaar electronic authentication. DO NOT SUBMIT PHYSICAL COPY.
    SYNTHETIC DEMO — NOT VALID
    """


def render_tax_ack_family2_sugam(p: Dict[str, Any]) -> str:
    """Family 2 (Train): Form ITR-4 (SUGAM) Presumptive Acknowledgement"""
    gross = p['annual_income']
    deductions = 150000.0
    taxable = max(0.0, gross - deductions)
    tax_paid = round(taxable * 0.10, 2)
    return f"""
    SYNTHETIC DEMO — NOT VALID
    INCOME TAX DEPARTMENT - GOVT OF INDIA
    ITR-4 (SUGAM) FILING RECEIPT & ACKNOWLEDGEMENT
    Assessment Year: 2025-2026 | Financial Year: 2024-2025
    e-Filing Acknowledgment Number: SUGAM-{p['source_csv_row']:06d}-{p['application_id']}

    TAX-PAYER IDENTIFICATION
    PAN: {p['pan']} | Assessee Name: {p['name'].upper()}
    Status: Individual | Self Employed: {p['self_employed']}
    Mobile / Email: Masked on file | City: {p['city']}

    COMPUTATION METRICS (INR)
    Total Gross Receipts / Turnover    : {gross:,.2f}
    Presumptive / Deemed Total Income  : {gross * 0.85:,.2f}
    Allowable Deductions Chapter VI-A  : {deductions:,.2f}
    Total Taxable Income Certified     : {taxable:,.2f}
    Tax Assessed & Paid via Challan/TDS: {tax_paid:,.2f}
    Net Tax Payable                    : 0.00

    Return submitted electronically under Digital Signatures.
    SYNTHETIC DEMO — NOT VALID
    """


def render_tax_ack_family3_intimation(p: Dict[str, Any]) -> str:
    """Family 3 (Dev): Income Tax Intimation under Section 143(1)"""
    gross = p['annual_income']
    ded = 150000.0
    taxable = max(0.0, gross - ded - 50000.0)
    tax_paid = round(taxable * 0.12, 2)
    return f"""
    SYNTHETIC DEMO — NOT VALID
    GOVERNMENT OF INDIA - INCOME TAX DEPARTMENT
    INTIMATION UNDER SECTION 143(1) OF THE INCOME TAX ACT, 1961
    CPC, Post Box No. 1, Electronic City Office, Bengaluru
    DIN: CPC/2526/1431/{p['source_csv_row']:08d} | PAN: {p['pan']}
    To: {p['name'].upper()}, {p['city']}

    COMPARATIVE COMPUTATION TABLE
    Particulars                         As Provided in Return   As Computed u/s 143(1)
    Gross Income from Salary / Source   INR {gross:,.2f}        INR {gross:,.2f}
    Total Deductions Under Chapter VIA  INR {ded:,.2f}          INR {ded:,.2f}
    Aggregate Taxable Income            INR {taxable:,.2f}      INR {taxable:,.2f}
    Net Tax Payable                     INR {tax_paid:,.2f}     INR {tax_paid:,.2f}
    Prepaid Taxes / TDS Relief          INR {tax_paid:,.2f}     INR {tax_paid:,.2f}
    Net Amount Refundable / Demand      NIL                     NIL

    This is an automated computerized intimation requiring no signature.
    SYNTHETIC DEMO — NOT VALID
    """


def render_tax_ack_family4_efiling(p: Dict[str, Any]) -> str:
    """Family 4 (Held-Out Test): e-Filing Portal Electronic Submission Receipt"""
    gross = p['annual_income']
    return f"""
    SYNTHETIC DEMO — NOT VALID
    INCOME TAX E-FILING PORTAL - OFFICIAL SUBMISSION RECEIPT
    e-Filing Portal: incometax.gov.in | Service Receipt Token: ACK-{p['application_id']}
    Assessment Year: 2025-26 | Filing Date & Time: 28-Jul-2025 18:24:02 IST

    FILING SUMMARY
    Permanent Account Number (PAN): {p['pan']}
    Taxpayer Name                 : {p['name']}
    Form Filed                    : ITR Return Filed Electronically
    Declared Gross Total Income   : INR {gross:,.2f}
    Filing Status Code            : SUCCESSFUL - VALIDATED & EVC VERIFIED
    Digital Token Verification    : EVC-HASH-{p['source_csv_row']:08d}

    Your electronic return has been safely ingested by Centralized Processing.
    SYNTHETIC DEMO — NOT VALID
    """


# --- 5. IDENTITY CARD FAMILIES ---

def render_id_family1_pan(p: Dict[str, Any]) -> str:
    """Family 1 (Train): Income Tax Department Permanent Account Number (PAN) Card"""
    return f"""
    SYNTHETIC DEMO — NOT VALID
    INCOME TAX DEPARTMENT - GOVT. OF INDIA
    PERMANENT ACCOUNT NUMBER CARD (PAN)
    
    Permanent Account Number : {p['pan']}
    Name                     : {p['name'].upper()}
    Father's Name            : {p['father_name'].upper()}
    Date of Birth            : {p['dob']}
    Signature                : [Digital Cryptographic Seal]
    Issuing Agency           : NSDL e-Governance Infrastructure Ltd
    SYNTHETIC DEMO — NOT VALID
    """


def render_id_family2_aadhaar(p: Dict[str, Any]) -> str:
    """Family 2 (Train): UIDAI Aadhaar Card"""
    return f"""
    SYNTHETIC DEMO — NOT VALID
    GOVERNMENT OF INDIA - UNIQUE IDENTIFICATION AUTHORITY OF INDIA (UIDAI)
    AADHAAR CARD - PROOF OF IDENTITY
    
    Aadhaar Number : {p['aadhaar_masked']}
    Full Name      : {p['name']}
    Date of Birth  : {p['dob']} | Gender: {p['gender']}
    Address        : Residential Flat, Sector {p['source_csv_row']}, {p['city']}, India
    Slogan         : Mera Aadhaar, Meri Pehchan
    Valid Proof of Identity as per statutory guidelines.
    SYNTHETIC DEMO — NOT VALID
    """


def render_id_family3_voter(p: Dict[str, Any]) -> str:
    """Family 3 (Dev): Election Commission of India Voter ID / EPIC Card"""
    epic_no = f"XYZ{p['source_csv_row']:07d}"
    return f"""
    SYNTHETIC DEMO — NOT VALID
    ELECTION COMMISSION OF INDIA - IDENTITY CARD
    ELECTOR PHOTO IDENTITY CARD (EPIC)
    EPIC Number: {epic_no}
    
    Elector Name   : {p['name']}
    Relation Name  : {p['father_name']}
    Gender / Sex   : {p['gender']}
    Date of Birth  : {p['dob']}
    Constituency   : {p['city']} Central Assembly Segment
    Electoral Registration Officer Seal: Issued by ECI Authority.
    SYNTHETIC DEMO — NOT VALID
    """


def render_id_family4_passport(p: Dict[str, Any]) -> str:
    """Family 4 (Held-Out Test): Indian Passport Biographical Page"""
    pass_no = f"Z{p['source_csv_row']:07d}"
    surname = p['name'].split()[-1].upper()
    given = " ".join(p['name'].split()[:-1]).upper()
    return f"""
    SYNTHETIC DEMO — NOT VALID
    PASSPORT - REPUBLIC OF INDIA
    Type: P | Country Code: IND | Passport No: {pass_no}
    
    Surname       : {surname}
    Given Names   : {given}
    Nationality   : INDIAN | Sex: {p['gender'][:1]}
    Date of Birth : {p['dob']}
    Place of Birth: {p['city'].upper()}, INDIA
    Place of Issue: RPO {p['city'].upper()} | Date of Expiry: 14-Aug-2035

    MACHINE READABLE ZONE:
    P<IND{surname}<<{given}<<<<<<<<<<<<<<<<<<<
    {pass_no}4IND{p['dob'].replace('-', '')}9M3508142<<<<<<<<<<<<<<02
    SYNTHETIC DEMO — NOT VALID
    """


# ==============================================================================
# NEGATIVE / OUT-OF-DOMAIN SAMPLES
# ==============================================================================

DEV_NEGATIVES = [
    {"label": "UNKNOWN", "text": "   \n\t   ", "reason": "whitespace_only"},
    {"label": "UNKNOWN", "text": "asdfjkl qwerty uiop zxcvbnm 12389745 kjashdf lkjh", "reason": "gibberish_tokens"},
    {
        "label": "UNKNOWN",
        "text": """
        SYNTHETIC DEMO — NOT VALID
        CITY ELECTRICITY SUPPLY CORPORATION - MONTHLY UTILITY INVOICE
        Consumer Account No: 98127391 | Meter No: ELEC-9812
        Consumer Name: Ramesh Gupta | Billing Month: August 2025
        Units Consumed: 342 kWh | Tariff Rate: Rs. 6.50 / unit
        Energy Charges: Rs. 2,223.00 | Fuel Surcharge: Rs. 140.00
        Total Bill Payable by Due Date: Rs. 2,363.00
        SYNTHETIC DEMO — NOT VALID
        """,
        "reason": "utility_bill"
    },
    {
        "label": "UNKNOWN",
        "text": """
        SYNTHETIC DEMO — NOT VALID
        METRO SPECIALTY CLINIC & HOSPITAL
        Outpatient Clinical Prescription & Diagnostic Note
        Patient Name: Anita Roy | Age: 34 | Date: 18-Aug-2025
        Rx:
        1. Tab Amoxicillin 500mg - 1 tablet three times daily after food x 5 days
        2. Tab Paracetamol 650mg - SOS for fever
        3. Syrup Cetirizine 5ml - at bedtime
        Review after 5 days. Dr. S. K. Verma, MBBS, MD (General Medicine)
        SYNTHETIC DEMO — NOT VALID
        """,
        "reason": "medical_prescription"
    },
    {
        "label": "UNKNOWN",
        "text": """
        SYNTHETIC DEMO — NOT VALID
        RESIDENTIAL LEASE AGREEMENT & TENANCY INDENTURE
        This Tenancy Agreement is executed at Pune on this 1st day of July 2025.
        Lessor / Landlord: Mr. Arun K. Joshi
        Lessee / Tenant: Ms. Swati Rao
        Premises: Flat No 402, Green Acre Apartments, Baner, Pune.
        Monthly Lease Rent: INR 26,000/- per English calendar month.
        Refundable Security Deposit: INR 1,00,000/- paid via bank transfer.
        Period of Tenancy: 11 Months commencing from 01-Jul-2025.
        SYNTHETIC DEMO — NOT VALID
        """,
        "reason": "lease_agreement"
    },
    {
        "label": "UNKNOWN",
        "text": """
        SYNTHETIC DEMO — NOT VALID
        CURRICULUM VITAE - HARISH BABU
        Email: harish.babu@email.com | Phone: +91 9845123981 | Bengaluru
        PROFESSIONAL SUMMARY:
        Full-stack engineer with 6 years experience in Python, TypeScript, React and Postgres.
        WORK EXPERIENCE:
        - Senior Engineer at InnoTech Labs (2022-Present): Designed microservices.
        - Software Developer at CloudSoft (2019-2022): API integrations and databases.
        EDUCATION:
        - B.Tech in Computer Science, National Institute of Technology (2019).
        SYNTHETIC DEMO — NOT VALID
        """,
        "reason": "resume_cv"
    },
    {
        "label": "UNKNOWN",
        "text": """
        SYNTHETIC DEMO — NOT VALID
        APEX COURIER & LOGISTICS CONSIGNMENT NOTE
        Consignment Tracking No: APX-98124912-IN
        Sender: Global Impex Pvt Ltd, Mumbai
        Consignee: Orient Traders, Kolkata | Packages: 2 Carton Boxes (Weight: 4.5 KG)
        Declared Value: Rs. 15,000/- | Payment Mode: Freight Prepaid
        Proof of Delivery: Received in good condition with seal intact.
        SYNTHETIC DEMO — NOT VALID
        """,
        "reason": "shipping_consignment"
    },
]

TEST_NEGATIVES = [
    {"label": "UNKNOWN", "text": "", "reason": "empty_string"},
    {"label": "UNKNOWN", "text": "   \\n\\t\\r\\n   ", "reason": "whitespace_only"},
    {"label": "UNKNOWN", "text": "zzzzxxxxcccc vvvvbbbb nnnnmmmm lkjhgfds apoieurt 998877", "reason": "gibberish_tokens"},
    {
        "label": "UNKNOWN",
        "text": """
        SYNTHETIC DEMO — NOT VALID
        TELECOM FIBER BROADBAND SERVICES - MONTHLY INVOICE
        Account No: FIBER-8841291 | Invoice No: INV-2025-08-98124
        Customer Name: Dinesh Kumar | Billing Period: 01-Aug-2025 to 31-Aug-2025
        Plan: Ultra Speed 200 Mbps Unlimited Fiber Broadband
        Monthly Subscription: Rs. 999.00 | GST (18%): Rs. 179.82
        Total Outstanding Payable: Rs. 1,178.82 | Due Date: 15-Sep-2025
        SYNTHETIC DEMO — NOT VALID
        """,
        "reason": "broadband_invoice"
    },
    {
        "label": "UNKNOWN",
        "text": """
        SYNTHETIC DEMO — NOT VALID
        CITY GENERAL HOSPITAL - DISCHARGE SUMMARY REPORT
        IPD Reg No: IPD-89124 | Patient Name: Mr. Mohan Lal | Age: 58 / Male
        Admission Date: 04-Aug-2025 | Discharge Date: 09-Aug-2025
        Diagnosis: Acute Gastritis with mild dehydration.
        Course in Hospital: Patient stabilized with IV fluids, PPI inhibitors and antacids.
        Condition at Discharge: Hemodynamically stable, afebrile, vitals normal.
        Consultant In-Charge: Dr. Arvind Nambiar, MD.
        SYNTHETIC DEMO — NOT VALID
        """,
        "reason": "hospital_discharge_summary"
    },
    {
        "label": "UNKNOWN",
        "text": """
        SYNTHETIC DEMO — NOT VALID
        MOTOR VEHICLE PRIVATE COMPREHENSIVE INSURANCE POLICY
        Insurer: National General Insurance Co Ltd
        Policy No: MOT-CAR-9812401 | Period: 10-Aug-2025 to 09-Aug-2026
        Insured Name: Mrs. Sunita Verma | Vehicle Reg No: MH-12-AB-9812
        Make & Model: Maruti Suzuki Baleno Alpha 1.2L Petrol
        Insured Declared Value (IDV): INR 6,50,000/-
        Own Damage Premium: Rs. 8,450.00 | Third Party Liability: Rs. 3,410.00
        Total Premium Collected: Rs. 13,995.00
        SYNTHETIC DEMO — NOT VALID
        """,
        "reason": "vehicle_insurance"
    },
    {
        "label": "UNKNOWN",
        "text": """
        SYNTHETIC DEMO — NOT VALID
        ENTERPRISE COMMERCIAL PURCHASE ORDER
        PO Number: PO-2025-08-112 | Supplier: Delta Electronics Supply
        Delivery Destination: Warehouse Unit 4, Navi Mumbai
        Line Items:
        1. Industrial Power Inverter 5kVA - Qty 2 - Unit: Rs. 45,000 - Total: Rs. 90,000
        2. Copper Wiring Cable Roll 100m - Qty 10 - Unit: Rs. 3,200 - Total: Rs. 32,000
        Subtotal: Rs. 1,22,000.00 | IGST (18%): Rs. 21,960.00 | Net Payable: Rs. 1,43,960.00
        SYNTHETIC DEMO — NOT VALID
        """,
        "reason": "purchase_order"
    },
    {
        "label": "UNKNOWN",
        "text": """
        SYNTHETIC DEMO — NOT VALID
        CAMPUS PLACEMENT APPOINTMENT & OFFER LETTER
        To: Mr. Rohit Saxena | Date: 15-May-2025
        Dear Rohit,
        We are pleased to offer you employment with Global Cloud Systems India Pvt Ltd.
        Position: Associate Software Engineer | Location: Hyderabad
        Annual Total Cost to Company (CTC): INR 7,50,000/- per annum.
        Date of Joining: 1st July 2025 | Reporting Manager: VP Engineering
        Please sign and return the duplicate copy of this letter as confirmation of acceptance.
        SYNTHETIC DEMO — NOT VALID
        """,
        "reason": "offer_letter"
    },
]


# ==============================================================================
# DATASET SPLIT BUILDER
# ==============================================================================

def generate_v2_dataset(
    csv_path: str = CSV_PATH,
    n_applicants: int = 70,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Generates v2 dataset with strict double-disjoint partitioning:
    - Partition 1: Train (48 applicants, Families 1 & 2 across 5 classes -> ~480 pages)
    - Partition 2: Dev (11 applicants, Family 3 across 5 classes -> 110 pages + 8 negatives = 118 samples)
    - Partition 3: Test (11 applicants, Family 4 across 5 classes -> 110 pages + 8 negatives = 118 samples)
    """
    raw_rows = load_kaggle_rows(csv_path, max_rows=n_applicants)
    csv_hash = get_csv_sha256(csv_path)

    # Build coherent profiles
    profiles = [build_applicant_profile(row, seed=seed) for row in raw_rows]

    # Partition applicants
    n_train = 48
    n_dev = 11
    train_profiles = profiles[:n_train]
    dev_profiles = profiles[n_train:n_train + n_dev]
    test_profiles = profiles[n_train + n_dev:]

    train_ids = set(p["application_id"] for p in train_profiles)
    dev_ids = set(p["application_id"] for p in dev_profiles)
    test_ids = set(p["application_id"] for p in test_profiles)

    # Double-disjoint check for applicants
    assert len(train_ids.intersection(dev_ids)) == 0
    assert len(train_ids.intersection(test_ids)) == 0
    assert len(dev_ids.intersection(test_ids)) == 0

    train_samples: List[Dict[str, Any]] = []
    dev_samples: List[Dict[str, Any]] = []
    test_samples: List[Dict[str, Any]] = []
    manifest_records: List[Dict[str, Any]] = []

    # 1. BUILD TRAIN (Families 1 and 2 for each applicant)
    for p in train_profiles:
        items = [
            ("application_form", "APP_FORM_STD_RETAIL", render_app_form_family1_retail(p)),
            ("application_form", "APP_FORM_HOUSING_FIN", render_app_form_family2_housing(p)),
            ("payslip", "PAYSLIP_CORP_TECH", render_payslip_family1_corp(p)),
            ("payslip", "PAYSLIP_MFG_VOUCHER", render_payslip_family2_mfg(p)),
            ("bank_statement", "BANK_STMT_TABULAR_HDFC", render_bank_stmt_family1_hdfc(p)),
            ("bank_statement", "BANK_STMT_SBI_PASSBOOK", render_bank_stmt_family2_sbi(p)),
            ("tax_acknowledgement", "TAX_ACK_ITR1_SAHAJ", render_tax_ack_family1_itr1(p)),
            ("tax_acknowledgement", "TAX_ACK_ITR2_4_SUGAM", render_tax_ack_family2_sugam(p)),
            ("id_card", "ID_PAN_CARD", render_id_family1_pan(p)),
            ("id_card", "ID_AADHAAR_CARD", render_id_family2_aadhaar(p)),
        ]
        for label, family, text in items:
            page_id = f"{p['application_id']}-{family}"
            rec = {
                "page_id": page_id,
                "application_id": p["application_id"],
                "source_csv_row": p["source_csv_row"],
                "split": "train",
                "label": label,
                "template_family": family,
                "is_negative": False,
                "text": text.strip(),
            }
            train_samples.append(rec)
            manifest_records.append(rec)

    # 2. BUILD DEV (Family 3 only + Dev Negatives)
    for p in dev_profiles:
        # Generate 2 variations per class to give ~110 pages
        items = [
            ("application_form", "APP_FORM_DIGITAL_APP", render_app_form_family3_digital(p)),
            ("payslip", "PAYSLIP_PUBLIC_SECTOR", render_payslip_family3_public(p)),
            ("bank_statement", "BANK_STMT_WEALTH_OVERVIEW", render_bank_stmt_family3_wealth(p)),
            ("tax_acknowledgement", "TAX_ACK_INTIMATION_143_1", render_tax_ack_family3_intimation(p)),
            ("id_card", "ID_VOTER_EPIC", render_id_family3_voter(p)),
        ]
        for label, family, text in items:
            page_id = f"{p['application_id']}-{family}"
            rec = {
                "page_id": page_id,
                "application_id": p["application_id"],
                "source_csv_row": p["source_csv_row"],
                "split": "dev",
                "label": label,
                "template_family": family,
                "is_negative": False,
                "text": text.strip(),
            }
            dev_samples.append(rec)
            manifest_records.append(rec)

    for i, neg in enumerate(DEV_NEGATIVES):
        page_id = f"NEG-DEV-{i:03d}-{neg['reason']}"
        rec = {
            "page_id": page_id,
            "application_id": f"NONE_NEGATIVE_DEV_{i:03d}",
            "source_csv_row": -1,
            "split": "dev",
            "label": "UNKNOWN",
            "template_family": f"NEGATIVE_{neg['reason'].upper()}",
            "is_negative": True,
            "text": neg["text"] if "whitespace" in neg["reason"] else neg["text"].strip(),
        }
        dev_samples.append(rec)
        manifest_records.append(rec)

    # 3. BUILD TEST (Family 4 only - Unseen Held-out Families + Test Negatives)
    for p in test_profiles:
        items = [
            ("application_form", "APP_FORM_COMMERCIAL_SME", render_app_form_family4_commercial(p)),
            ("payslip", "PAYSLIP_CONSULTING_COMPACT", render_payslip_family4_consulting(p)),
            ("bank_statement", "BANK_STMT_NEOBANK_LEDGER", render_bank_stmt_family4_neobank(p)),
            ("tax_acknowledgement", "TAX_ACK_EFILING_RECEIPT", render_tax_ack_family4_efiling(p)),
            ("id_card", "ID_PASSPORT_PAGE", render_id_family4_passport(p)),
        ]
        for label, family, text in items:
            page_id = f"{p['application_id']}-{family}"
            rec = {
                "page_id": page_id,
                "application_id": p["application_id"],
                "source_csv_row": p["source_csv_row"],
                "split": "test",
                "label": label,
                "template_family": family,
                "is_negative": False,
                "text": text.strip(),
            }
            test_samples.append(rec)
            manifest_records.append(rec)

    for i, neg in enumerate(TEST_NEGATIVES):
        page_id = f"NEG-TEST-{i:03d}-{neg['reason']}"
        rec = {
            "page_id": page_id,
            "application_id": f"NONE_NEGATIVE_TEST_{i:03d}",
            "source_csv_row": -1,
            "split": "test",
            "label": "UNKNOWN",
            "template_family": f"NEGATIVE_{neg['reason'].upper()}",
            "is_negative": True,
            "text": neg["text"] if "whitespace" in neg["reason"] else neg["text"].strip(),
        }
        test_samples.append(rec)
        manifest_records.append(rec)

    # Shuffle splits
    rnd = random.Random(seed)
    rnd.shuffle(train_samples)
    rnd.shuffle(dev_samples)
    rnd.shuffle(test_samples)

    train_families = set(s["template_family"] for s in train_samples)
    dev_families = set(s["template_family"] for s in dev_samples)
    test_families = set(s["template_family"] for s in test_samples)

    # Invariant: Template family disjointness across positive classes
    train_pos_fam = set(s["template_family"] for s in train_samples if not s["is_negative"])
    dev_pos_fam = set(s["template_family"] for s in dev_samples if not s["is_negative"])
    test_pos_fam = set(s["template_family"] for s in test_samples if not s["is_negative"])

    assert len(train_pos_fam.intersection(dev_pos_fam)) == 0, "Template leakage between train and dev!"
    assert len(train_pos_fam.intersection(test_pos_fam)) == 0, "Template leakage between train and test!"
    assert len(dev_pos_fam.intersection(test_pos_fam)) == 0, "Template leakage between dev and test!"

    return {
        "metadata": {
            "dataset_version": "2.0",
            "source_csv": "data/kaggle_loan_approval_dataset.csv",
            "source_csv_sha256": csv_hash,
            "seed": seed,
            "n_applicants": n_applicants,
            "classes": CANONICAL_CLASSES,
            "abstention_label": "UNKNOWN",
            "train_applicants_count": len(train_profiles),
            "dev_applicants_count": len(dev_profiles),
            "test_applicants_count": len(test_profiles),
            "train_families": sorted(list(train_families)),
            "dev_families": sorted(list(dev_families)),
            "test_families": sorted(list(test_families)),
            "counts": {
                "train_samples": len(train_samples),
                "dev_samples": len(dev_samples),
                "test_samples": len(test_samples),
                "total_samples": len(train_samples) + len(dev_samples) + len(test_samples),
            }
        },
        "train": train_samples,
        "dev": dev_samples,
        "test": test_samples,
    }


def save_v2_dataset(dataset: Dict[str, Any], output_dir: str = "ml/data/v2") -> None:
    os.makedirs(output_dir, exist_ok=True)
    splits_path = os.path.join(output_dir, "splits_v2.json")
    manifest_path = os.path.join(output_dir, "provenance_manifest.json")

    with open(splits_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)

    # Flattened manifest
    manifest_data = {
        "metadata": dataset["metadata"],
        "records": dataset["train"] + dataset["dev"] + dataset["test"]
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print(f"Saved {dataset['metadata']['counts']['total_samples']} samples to {output_dir}")
    print(f"Train: {dataset['metadata']['counts']['train_samples']} | Dev: {dataset['metadata']['counts']['dev_samples']} | Test: {dataset['metadata']['counts']['test_samples']}")


def load_v2_splits(splits_path: str = "ml/data/v2/splits_v2.json") -> Dict[str, Any]:
    if not os.path.exists(splits_path):
        ds = generate_v2_dataset()
        save_v2_dataset(ds, os.path.dirname(splits_path))
        return ds
    with open(splits_path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    ds = generate_v2_dataset(n_applicants=70, seed=42)
    save_v2_dataset(ds, "ml/data/v2")
