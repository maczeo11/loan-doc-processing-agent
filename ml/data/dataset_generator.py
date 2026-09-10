"""
Synthetic Document Dataset Generator & Grouped Split Builder.
Owned by Member 5 (Karthik).

Generates realistic text samples for document page classification across 5 target classes:
- application_form
- payslip
- bank_statement
- tax_acknowledgement
- id_card

Inviolable Rule from AGENTS.md:
Splits must be grouped strictly by applicant identity (`application_id`)
to prevent train/dev/test data leakage.
"""

import json
import os
import random
from typing import Dict, List, Any

DOCUMENT_CLASSES = [
    "application_form",
    "payslip",
    "bank_statement",
    "tax_acknowledgement",
    "id_card",
]

FIRST_NAMES = [
    "Aarav", "Priya", "Vikram", "Sneha", "Rajesh", "Ananya", "Rohan", "Kavita",
    "Siddharth", "Pooja", "Arjun", "Deepika", "Rahul", "Meera", "Aditya", "Neha",
    "Amit", "Divya", "Suresh", "Ritu", "Karan", "Swati", "Nikhil", "Shreya",
    "Varun", "Tanvi", "Gaurav", "Simran", "Manoj", "Aarti"
]

LAST_NAMES = [
    "Sharma", "Patel", "Malhotra", "Kulkarni", "Nair", "Verma", "Reddy", "Iyer",
    "Gupta", "Choudhury", "Bose", "Mehta", "Deshmukh", "Pillai", "Mishra", "Joshi",
    "Kapoor", "Bhat", "Rao", "Saxena"
]

COMPANIES = [
    "Tata Consultancy Services Ltd", "Infosys Technologies Ltd", "Wipro Enterprises",
    "HCL Technologies", "Cognizant Technology Solutions", "Tech Mahindra Ltd",
    "Reliance Industries Ltd", "Larsen & Toubro Infotech", "Accenture Solutions Pvt Ltd",
    "Apex Global Solutions", "Persistent Systems Ltd", "Capgemini India Pvt Ltd"
]

BANKS = [
    "HDFC Bank Ltd", "ICICI Bank Ltd", "State Bank of India", "Axis Bank Ltd",
    "Kotak Mahindra Bank", "Bank of Baroda", "Punjab National Bank", "IndusInd Bank"
]

CITIES = ["Mumbai", "Bengaluru", "Hyderabad", "Pune", "Chennai", "Delhi NCR", "Kolkata"]


def _random_pan() -> str:
    letters = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
    digits = "".join(random.choices("0123456789", k=4))
    last = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return f"{letters}{digits}{last}"


def _generate_application_form_page(applicant: Dict[str, Any], page_num: int = 1) -> str:
    name = applicant["name"]
    app_id = applicant["application_id"]
    loan_amt = applicant["loan_amount"]
    tenure = applicant["tenure"]
    cibil = applicant["cibil"]
    employer = applicant["employer"]
    city = applicant["city"]

    if page_num == 1:
        return f"""
        RETAIL LOAN APPLICATION FORM - APPLICANT DOSSIER
        Application Reference ID: {app_id}
        Branch: {city} Central Retail Hub | Date of Submission: 14-Aug-2025

        1. PERSONAL PARTICULARS
        Full Legal Name of Applicant: {name}
        Date of Birth: {applicant['dob']} | Gender: {applicant['gender']}
        Marital Status: Married | Dependents: {applicant['dependents']}
        Current Residential Address: Flat {random.randint(101, 909)}, {city}, India
        PAN Number: {applicant['pan']} | Mobile: +91 98{random.randint(10000000, 99999999)}

        2. EMPLOYMENT & OCCUPATIONAL DETAILS
        Primary Employer Name: {employer}
        Designation: Senior Specialist / Lead Associate
        Official Work Email: {name.lower().replace(' ', '.')}@{employer.lower().split()[0]}.com
        Employment Type: Salaried (Full Time Permanent)
        Total Work Experience: 7 Years 4 Months | Current Organization: 3 Years

        3. LOAN FACILITY DETAILS REQUESTED
        Facility Type: Home Loan / Personal Secured Loan
        Requested Sanction Amount: INR {loan_amt:,.2f}
        Requested Repayment Tenure: {tenure} Months | Preferred EMI Option: Reducing Balance
        Stated Gross Annual Income: INR {applicant['annual_income']:,.2f}
        Stated Net Monthly Income: INR {applicant['net_salary']:,.2f}
        Credit Bureau Score (CIBIL TransUnion v3): {cibil} (Valid as of current cycle)
        Existing Obligations / Running EMIs: Nil
        """
    else:
        return f"""
        RETAIL LOAN APPLICATION FORM - DECLARATION & TERMS (Page 2)
        Application Reference: {app_id} | Applicant: {name}

        4. ASSET & LIABILITY SUMMARY
        Immovable Properties Owned: Residential Apartment valued at INR {loan_amt * 1.5:,.2f}
        Liquid Assets / Fixed Deposits: INR {loan_amt * 0.4:,.2f} held across verified schedules.
        Vehicle / Other Assets: Four-wheeler passenger vehicle.

        5. UNDERTAKING & STATUTORY APPLICANT DECLARATION
        I, {name}, hereby declare that all information, particulars, and documents submitted
        in connection with this retail credit facility application are true, correct, and complete.
        I authorize FinScan AI and partner financing institutions to verify my identity records,
        cross-check payroll deposits with banking partners, pull tax filings from the IT Department,
        and authenticate KYC credentials with the respective statutory repositories.

        Applicant Signature: [Digitally signed by {name}]
        Date: 14-Aug-2025 | Place: {city}
        Enclosures: Stated 3-Month Payslips, 6-Month Bank Statements, ITR-V, Aadhaar & PAN copies.
        """


def _generate_payslip_page(applicant: Dict[str, Any], month_idx: int = 1) -> str:
    months = ["June 2025", "July 2025", "August 2025", "September 2025"]
    month_name = months[month_idx % len(months)]
    employer = applicant["employer"]
    name = applicant["name"]
    gross = applicant["gross_salary"]
    net = applicant["net_salary"]
    basic = round(gross * 0.50, 2)
    hra = round(gross * 0.25, 2)
    special = round(gross * 0.20, 2)
    medical = round(gross - (basic + hra + special), 2)
    epf = round(basic * 0.12, 2)
    pt = 200.0
    tds = round(gross - net - epf - pt, 2)
    if tds < 0:
        tds = 0.0

    return f"""
    PRIVATE & CONFIDENTIAL PAYSLIP
    {employer.upper()}
    Registered Corporate Office: Cyber City, Tower B, {applicant['city']}

    PAYSLIP FOR THE PERIOD: {month_name}
    Employee ID: EMP{random.randint(100000, 999999)} | Cost Center: India Tech Ops
    Employee Name: {name}
    Designation: Technical Lead / Principal Analyst
    PAN: {applicant['pan']} | UAN: 100{random.randint(100000000, 999999999)}
    Bank Name: {applicant['bank']} | Salary Account No: {applicant['bank_account_masked']}
    Days in Month: 30 | Paid Days: 30 | Loss of Pay (LOP): 0

    --------------------------------------------------------------------------------
    EARNINGS (INR)                      DEDUCTIONS (INR)
    --------------------------------------------------------------------------------
    Basic Salary          : {basic:,.2f}      Provident Fund (EPF)      : {epf:,.2f}
    House Rent Allow (HRA): {hra:,.2f}      Professional Tax (PT)     : {pt:,.2f}
    Special Allowance     : {special:,.2f}      Income Tax (TDS)          : {tds:,.2f}
    Medical Allowance     : {medical:,.2f}      Voluntary PF (VPF)        : 0.00
    --------------------------------------------------------------------------------
    GROSS EARNINGS        : INR {gross:,.2f}  TOTAL DEDUCTIONS          : INR {gross - net:,.2f}
    --------------------------------------------------------------------------------
    NET DISBURSED AMOUNT  : INR {net:,.2f}
    Amount in Words: Rupee disbursement processed via NEFT / corporate payroll clearing.
    This is an electronically generated salary document and requires no physical signature.
    """


def _generate_bank_statement_page(applicant: Dict[str, Any], page_num: int = 1) -> str:
    bank = applicant["bank"]
    name = applicant["name"]
    acct = applicant["bank_account_masked"]
    net = applicant["net_salary"]
    closing = applicant["bank_balance"]

    return f"""
    {bank.upper()} - COMPREHENSIVE SAVINGS ACCOUNT STATEMENT
    Customer Relationship Number: CRN-{random.randint(10000000, 99999999)}
    Account Holder: {name}
    Account Number: {acct} | Account Type: Regular Salary Savings
    IFSC Code: {bank[:4].upper()}000{random.randint(1000, 9999)} | MICR: {random.randint(100000000, 999999999)}
    Branch Address: Retail Assets Division, {applicant['city']} Branch
    Statement Period: 01-Jun-2025 to 31-Aug-2025 | Page {page_num} of 3

    ACCOUNT SUMMARY
    Opening Balance: INR {closing * 0.85:,.2f}
    Total Credits: INR {net * 3 + 25000:,.2f} | Total Debits: INR {net * 2.1:,.2f}
    Closing Clear Balance: INR {closing:,.2f}

    TRANSACTION LEDGER DETAILS
    Date        | Description / Narration                | Chq/Ref No   | Debit (INR)  | Credit (INR) | Balance (INR)
    01-Jun-2025 | ACH CR - SALARY - {applicant['employer'][:12]} | CMS{random.randint(100000, 999999)} | -            | {net:,.2f}   | {closing + 12000:,.2f}
    04-Jun-2025 | UPI/Rent Payment/HDFC984210            | UPI{random.randint(100000, 999999)} | 25,000.00    | -            | {closing - 13000:,.2f}
    12-Jun-2025 | POS DEBIT / SUPERMARKET RETAIL         | POS{random.randint(100000, 999999)} | 4,210.00     | -            | {closing - 17210:,.2f}
    01-Jul-2025 | ACH CR - SALARY - {applicant['employer'][:12]} | CMS{random.randint(100000, 999999)} | -            | {net:,.2f}   | {closing + 18000:,.2f}
    15-Jul-2025 | ATM CASH WITHDRAWAL - DOMESTIC         | ATM{random.randint(100000, 999999)} | 10,000.00    | -            | {closing + 8000:,.2f}
    01-Aug-2025 | ACH CR - SALARY - {applicant['employer'][:12]} | CMS{random.randint(100000, 999999)} | -            | {net:,.2f}   | {closing:,.2f}

    Cheque returns / ECS dishonour charges for this period: NIL.
    Computer-generated bank account statement. End of statement records.
    """


def _generate_tax_acknowledgement_page(applicant: Dict[str, Any], page_num: int = 1) -> str:
    name = applicant["name"]
    pan = applicant["pan"]
    gross = applicant["annual_income"]
    deductions = 150000.0  # Section 80C
    taxable = max(0.0, gross - deductions)
    tax_paid = round(taxable * 0.12, 2)
    ack_no = f"{random.randint(100000000000000, 999999999999999)}"

    return f"""
    INDIAN INCOME TAX RETURN ACKNOWLEDGEMENT [ITR-V]
    Centralized Processing Centre (CPC), Bengaluru, Income Tax Department
    Assessment Year: 2025-26 | Financial Year: 2024-25
    Form: ITR-1 (SAHAJ) - For individuals having income from salaries, one house property, other sources

    PART A: GENERAL INFORMATION
    Permanent Account Number (PAN): {pan}
    Name of Assessee: {name.upper()}
    Status: Individual | Residential Status: Resident
    Aadhaar Number: {applicant['aadhaar_masked']}
    Filing Status: Filed on or before due date under section 139(1)
    Date of Filing: 22-Jul-2025 | Acknowledgement Number: {ack_no}

    PART B: COMPUTATION OF TOTAL INCOME AND TAX (INR)
    1. Gross Salary Income as per Form 16 (Section 17(1))     : {gross:,.2f}
    2. Less Standard Deduction u/s 16(ia)                      : 50,000.00
    3. Total Gross Income from Salaries                        : {gross - 50000:,.2f}
    4. Gross Total Income (GTI)                                : {gross:,.2f}
    5. Total Deductions under Chapter VI-A (80C, 80D, 80CCD)   : {deductions:,.2f}
    6. Total Taxable Income                                    : {taxable:,.2f}
    7. Net Tax Payable before relief                           : {tax_paid:,.2f}
    8. Taxes Paid / TDS Deposited by Employer (Form 26AS)      : {tax_paid:,.2f}
    9. Balance Refundable / Payable                            : 0.00

    VERIFICATION & E-AUTHENTICATION STATUS
    The return has been electronically verified (e-verified) using Aadhaar OTP verification.
    Digital Verification Token: EVC-{random.randint(100000, 999999)}
    DO NOT SEND THIS ACKNOWLEDGEMENT TO CPC BENGALURU AS IT HAS BEEN E-VERIFIED.
    """


def _generate_id_card_page(applicant: Dict[str, Any], id_type: str = "pan") -> str:
    name = applicant["name"]
    pan = applicant["pan"]
    dob = applicant["dob"]
    aadhaar = applicant["aadhaar_masked"]

    if id_type == "pan":
        return f"""
        INCOME TAX DEPARTMENT - GOVT. OF INDIA
        PERMANENT ACCOUNT NUMBER CARD (PAN)

        Permanent Account Number: {pan}
        Name: {name.upper()}
        Father's Name: {applicant['father_name'].upper()}
        Date of Birth: {dob}
        Cardholder Signature: [Signed Digitally]
        QR Code: [PAN Digital Cryptographic Signature Verified]
        Issued by National Securities Depository Limited (NSDL)
        """
    else:
        return f"""
        GOVERNMENT OF INDIA - UNIQUE IDENTIFICATION AUTHORITY OF INDIA (UIDAI)
        AADHAAR CARD - PROOF OF IDENTITY

        Enrollment No: 1045/{random.randint(10000, 99999)}/{random.randint(10000, 99999)}
        To: {name}
        Address: Flat {random.randint(101, 909)}, {applicant['city']}, India

        Aadhaar Number: {aadhaar}
        Name: {name}
        DOB: {dob} | Gender: {applicant['gender']}
        Mera Aadhaar, Meri Pehchan
        Valid Proof of Identity for statutory KYC under RBI master directions.
        """


def generate_synthetic_applicants(n_applicants: int = 60, seed: int = 42) -> List[Dict[str, Any]]:
    """Generates synthetic applicant profiles for dataset creation."""
    random.seed(seed)
    applicants = []
    for i in range(n_applicants):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        full_name = f"{first} {last}"
        father = f"{random.choice(FIRST_NAMES)} {last}"
        annual_inc = random.choice([720000.0, 960000.0, 1200000.0, 1500000.0, 1800000.0, 2400000.0])
        gross_sal = round(annual_inc / 12.0, 2)
        net_sal = round(gross_sal * 0.88, 2)
        loan_amt = annual_inc * random.choice([2.5, 3.0, 3.5, 4.0])

        app = {
            "application_id": f"APP-{10000 + i}",
            "name": full_name,
            "father_name": father,
            "dob": f"{random.randint(1982, 1999):04d}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            "gender": random.choice(["Male", "Female"]),
            "dependents": random.choice([0, 1, 2, 3]),
            "pan": _random_pan(),
            "aadhaar_masked": f"XXXX-XXXX-{random.randint(1000, 9999)}",
            "employer": random.choice(COMPANIES),
            "bank": random.choice(BANKS),
            "bank_account_masked": f"50100{random.randint(1000000, 9999999)}",
            "annual_income": annual_inc,
            "gross_salary": gross_sal,
            "net_salary": net_sal,
            "bank_balance": round(net_sal * random.uniform(0.3, 1.8), 2),
            "loan_amount": loan_amt,
            "tenure": random.choice([60, 120, 180, 240]),
            "cibil": random.randint(650, 820),
            "city": random.choice(CITIES),
        }
        applicants.append(app)
    return applicants


def build_pages_for_applicant(applicant: Dict[str, Any]) -> List[Dict[str, str]]:
    """Builds multiple document pages across all 5 classes for a single applicant."""
    pages = []
    app_id = applicant["application_id"]

    # 1. Application form (2 pages)
    for p in range(1, 3):
        pages.append({
            "application_id": app_id,
            "label": "application_form",
            "text": _generate_application_form_page(applicant, page_num=p)
        })

    # 2. Payslips (3 monthly pages)
    for m in range(3):
        pages.append({
            "application_id": app_id,
            "label": "payslip",
            "text": _generate_payslip_page(applicant, month_idx=m)
        })

    # 3. Bank statements (3 pages)
    for p in range(1, 4):
        pages.append({
            "application_id": app_id,
            "label": "bank_statement",
            "text": _generate_bank_statement_page(applicant, page_num=p)
        })

    # 4. Tax return acknowledgement (1 page)
    pages.append({
        "application_id": app_id,
        "label": "tax_acknowledgement",
        "text": _generate_tax_acknowledgement_page(applicant, page_num=1)
    })

    # 5. ID cards (2 pages: PAN and Aadhaar)
    pages.append({
        "application_id": app_id,
        "label": "id_card",
        "text": _generate_id_card_page(applicant, id_type="pan")
    })
    pages.append({
        "application_id": app_id,
        "label": "id_card",
        "text": _generate_id_card_page(applicant, id_type="aadhaar")
    })

    return pages


def create_grouped_splits(
    n_applicants: int = 60,
    train_ratio: float = 0.70,
    dev_ratio: float = 0.15,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Partitions applicants strictly by `application_id` to guarantee zero data leakage.
    Returns dictionary with train, dev, and test partitions containing text, label, and metadata.
    """
    applicants = generate_synthetic_applicants(n_applicants=n_applicants, seed=seed)
    random.seed(seed)
    shuffled_apps = applicants.copy()
    random.shuffle(shuffled_apps)

    n_train = int(len(shuffled_apps) * train_ratio)
    n_dev = int(len(shuffled_apps) * dev_ratio)

    train_apps = shuffled_apps[:n_train]
    dev_apps = shuffled_apps[n_train:n_train + n_dev]
    test_apps = shuffled_apps[n_train + n_dev:]

    train_ids = set(a["application_id"] for a in train_apps)
    dev_ids = set(a["application_id"] for a in dev_apps)
    test_ids = set(a["application_id"] for a in test_apps)

    # Invariant: Zero applicant ID overlap
    assert len(train_ids.intersection(dev_ids)) == 0, "Leakage between train and dev!"
    assert len(train_ids.intersection(test_ids)) == 0, "Leakage between train and test!"
    assert len(dev_ids.intersection(test_ids)) == 0, "Leakage between dev and test!"

    def flatten_pages(app_list: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        all_pages = []
        for app in app_list:
            all_pages.extend(build_pages_for_applicant(app))
        random.shuffle(all_pages)
        return all_pages

    train_pages = flatten_pages(train_apps)
    dev_pages = flatten_pages(dev_apps)
    test_pages = flatten_pages(test_apps)

    return {
        "metadata": {
            "n_applicants": n_applicants,
            "train_applicants": list(train_ids),
            "dev_applicants": list(dev_ids),
            "test_applicants": list(test_ids),
            "classes": DOCUMENT_CLASSES,
            "total_pages": len(train_pages) + len(dev_pages) + len(test_pages),
        },
        "train": train_pages,
        "dev": dev_pages,
        "test": test_pages,
    }


def save_splits(splits: Dict[str, Any], output_path: str = "ml/data/splits.json") -> None:
    """Saves splits to a JSON file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(splits, f, indent=2)
    print(f"Saved {splits['metadata']['total_pages']} pages to {output_path}")


def load_splits(splits_path: str = "ml/data/splits.json") -> Dict[str, Any]:
    """Loads frozen dataset splits from JSON file."""
    if not os.path.exists(splits_path):
        splits = create_grouped_splits()
        save_splits(splits, splits_path)
        return splits
    with open(splits_path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    splits_file = os.path.join(os.path.dirname(__file__), "splits.json")
    dataset = create_grouped_splits(n_applicants=60, seed=42)
    save_splits(dataset, splits_file)
    print(f"Train pages: {len(dataset['train'])} | Dev pages: {len(dataset['dev'])} | Test pages: {len(dataset['test'])}")
