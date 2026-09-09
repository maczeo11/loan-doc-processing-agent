# Handoff: Jeevan (Extraction) -> Sravanthi (Rules/Reporting/Data)

**Source checked:** `origin/feat/extract-perception-pipeline` is **fully merged into `main`** (merge-base check = YES, commit `b552d1a`, `a00293e`). Use `main` — no need to checkout Jeevan's branch.

**Jeevan owns:** `core/extraction/` — `native_parser.py`, `paddle_parser.py`, `router.py`, `extractors/{payslip,bank_statement,tax_return,id_card,base}.py`
**Contract owner (Manjunath):** `core/contracts/` — single source of truth, do NOT redefine locally.

---

## 1. What Sravanthi needs from Jeevan (rule inputs)

| Your rule | Function signature | Needs from Jeevan |
|---|---|---|
| `RULE-INC-01` `core/rules/salary_audit.py:11` | `audit_salary_vs_bank(payslip_net: MoneyFact, bank_salary_credit: MoneyFact, tolerance=0.10)` | `PayslipExtractor.net_salary` (monthly/net) + `BankStatementExtractor.average_salary_credit` (or `salary_credits[0]`) |
| `RULE-TAX-01` `core/rules/tax_audit.py:11` | `audit_tax_vs_income(stated_annual_income, itr_gross_income)` | `PayslipExtractor.gross_salary.amount * 12` + `TaxReturnExtractor.gross_total_income` (annual/gross) + `total_tax_paid` |
| `RULE-ID-01` `core/rules/identity.py:11` | `audit_identity_consistency(applicant, payslip_name, bank_name)` | `IdCardExtractor -> ApplicantFact(full_name, source_name, pan_number, source_pan)` + `PayslipExtractor.employee_name` + `BankStatementExtractor.account_holder` |
| `RULE-COMP-01` `core/rules/completeness.py:11` | `evaluate_completeness(uploaded_types, required_types)` | Presence = extractor succeeded per doc-type |
| CAM `core/reporting/memo_builder.py` | `build_appraisal_memo(state)` | `closing_balance, bounced_transactions, employer_name, assessment_year, pay_period_str` |

**Prime Invariant:** No `MoneyFact` without `source: EvidenceRef`. If span/bbox missing -> value is `UNKNOWN` (confidence 0.0), your rule MUST return `verdict="unknown"`, never `pass`.

## 2. How to call (copy-paste)

```python
from core.extraction.extractors.payslip import PayslipExtractor
from core.extraction.extractors.bank_statement import BankStatementExtractor
from core.extraction.extractors.tax_return import TaxReturnExtractor
from core.extraction.extractors.id_card import IdCardExtractor

# pages = output of router: List[{page_number, text, page_width, page_height, words:[{word, bbox}]}]
# See core/extraction/router.py:78 route_page_extraction() — native first, paddle fallback
payslip = PayslipExtractor().extract(doc_id="DOC-PAYSLIP-01", pages=pages_payslip)
bank = BankStatementExtractor().extract(doc_id="DOC-BANK-01", pages=pages_bank)
tax = TaxReturnExtractor().extract(doc_id="DOC-ITR-01", pages=pages_itr)
applicant = IdCardExtractor().extract(doc_id="DOC-KYC-01", pages=pages_kyc)

# then:
from core.rules.salary_audit import audit_salary_vs_bank
finding = audit_salary_vs_bank(payslip.net_salary, bank.average_salary_credit)
# finding.supporting_evidence = [payslip_net.source, bank_credit.source]
```

OCR routing happens BEFORE classification (`core/extraction/router.py:42 inspect_page_route`, threshold 50 chars / 5 words). Textract fallback is capped at 100 pages and OFF by default.

## 3. Live verified output shape (from main, 2026-09-09)

Input text: `Employee Name: Aarav Sharma / Employer: Tata Consultancy Services Ltd / Gross Salary: INR 100000 / Net Salary: INR 88000`

```json
{
  "employee_name": "Aarav Sharma",
  "employer_name": "Tata Consultancy Services Ltd",
  "gross_salary": {"amount": 100000.0, "currency": "INR", "period": "monthly", "basis": "gross",
    "source": {"document_id": "DOC-TEST", "document_type": "payslip", "page_number": 1,
      "quoted_span": "Gross Salary: INR 100000",
      "bounding_box": {"x0": 50.0, "y0": 50.0, "x1": 250.0, "y1": 70.0, "page_width": 600.0, "page_height": 800.0},
      "extraction_method": "pymupdf_native", "confidence": 0.95}},
  "net_salary": {"amount": 88000.0, "currency": "INR", "period": "monthly", "basis": "net",
    "source": {"document_id": "DOC-TEST", "document_type": "payslip", "page_number": 1,
      "quoted_span": "Net Salary: INR 88000",
      "bounding_box": {"x0": 50.0, "y0": 50.0, "x1": 250.0, "y1": 70.0, "page_width": 600.0, "page_height": 800.0},
      "extraction_method": "pymupdf_native", "confidence": 0.95}},
  "deductions_total": null,
  "pay_period_str": "Jan 2024"
}
```

Other extractors return same `MoneyFact+EvidenceRef` pattern:
- `BankStatementFacts{account_holder, bank_name, account_number_masked: "XXXXXX1234", salary_credits: MoneyFact[], average_salary_credit, closing_balance, bounced_transactions: int}`
- `TaxReturnFacts{assessee_name, pan_number, assessment_year, gross_total_income (annual/gross), total_tax_paid}`
- `ApplicantFact{full_name, source_name, dob/source_dob, pan_number/source_pan, aadhaar_masked/source_aadhaar}`

## 4. Contracts (frozen — do not loosen)

`core/contracts/evidence.py`:
```python
class BoundingBox(BaseModel):
    x0: float; y0: float; x1: float; y1: float
    page_width: Optional[float] = None; page_height: Optional[float] = None

class EvidenceRef(BaseModel):
    document_id: str
    document_type: str  # payslip | bank_statement | tax_acknowledgement | id_card
    page_number: int    # 1-indexed, ge=1
    quoted_span: str    # exact text from page
    bounding_box: Optional[BoundingBox] = None
    extraction_method: str = "pymupdf_native"  # | paddleocr_cpu
    confidence: float = 1.0  # 0.0 = UNKNOWN
```

`core/contracts/facts.py`:
```python
class MoneyFact(BaseModel):
    amount: float; currency: str = "INR"
    period: Literal["monthly","annual","one_time"] = "monthly"
    basis: Literal["gross","net","deduction","balance"] = "gross"
    source: EvidenceRef
class ApplicantFact(BaseModel):
    full_name: str; source_name: EvidenceRef
    dob: Optional[str]=None; source_dob: Optional[EvidenceRef]=None
    pan_number: Optional[str]=None; source_pan: Optional[EvidenceRef]=None
    aadhaar_masked: Optional[str]=None; source_aadhaar: Optional[EvidenceRef]=None
class PayslipFacts(BaseModel):
    employee_name: str; employer_name: str
    gross_salary: MoneyFact; net_salary: MoneyFact
    deductions_total: Optional[MoneyFact]=None; pay_period_str: Optional[str]=None
class BankStatementFacts(BaseModel):
    account_holder: str; bank_name: str; account_number_masked: str
    salary_credits: List[MoneyFact]=[]; average_salary_credit: Optional[MoneyFact]=None
    closing_balance: Optional[MoneyFact]=None; bounced_transactions: int=0
class TaxReturnFacts(BaseModel):
    assessee_name: str; pan_number: str; assessment_year: str
    gross_total_income: MoneyFact; total_tax_paid: Optional[MoneyFact]=None
```

`core/contracts/findings.py`:
```python
RuleVerdict = Literal["pass","flag","unknown"]
class Finding(BaseModel):
    rule_id: str; rule_name: str; verdict: RuleVerdict; reason: str
    supporting_evidence: List[EvidenceRef] = []
    policy_version: str = "v1.0"
```

Helpers `core/extraction/extractors/base.py`: `parse_monetary_amount("Rs. 1,50,000") -> 150000.0`, `make_unknown_evidence(doc_id, doc_type)`, `find_text_match_with_evidence(pages, pattern, doc_id, doc_type)`.

## 5. Synthetic dossiers — where to get them

Question was: "u can check if u can get synthetic dossiers from fest/data dossiers" — there is NO `test/data` or `fest/data` folder.

What exists in main:
- `data/synthetic_dossiers/APP-*/dossier_manifest.json` (5 apps: APP-25195, 29630, 58350, 86070, 91627) — JSON ground truth ONLY, no PDFs. E.g. APP-25195: payslip gross 100000/net 88000, bank credits [100000x3], ITR 1200000, KYC Aarav Sharma ABCDE1231F. Generated by `scripts/generate_dossiers.py`.
- `data/storage/dossiers/APP-*/DOC-*.pdf` — real uploaded PDFs to run Jeevan's router+extractors on.

Note: your unmerged branch `origin/feat/data-dossiers` (not in main yet) already has 50 dossiers `APP-00001..00050` + `dataset_splits.json` + improved `salary/tax/identity/completeness` rules. Merge that to main before demo or Sravanthi will test against stale 5-app set.

## 6. Ready-to-send message for Sravanthi

> Hi Sravanthi — checked Jeevan's branch `feat/extract-perception-pipeline`, it's already merged in `main`, so pull main. Your rules take `PayslipFacts.net_salary + Bank.average_salary_credit` (INC-01), `Payslip.gross*12 + ITR.gross_total_income` (TAX-01), `ApplicantFact + payslip employee_name + bank account_holder` (ID-01), each with `EvidenceRef(doc_id, type, page, span, bbox)`. Missing evidence = UNKNOWN -> verdict unknown. Full shapes + contracts + live JSON example in `docs/handoff-sravanthi-jeevan-extraction.md`. For test data use `data/synthetic_dossiers/*/dossier_manifest.json` (ground truth) + `data/storage/dossiers/*/*.pdf` (PDF bytes for extraction). Your `origin/feat/data-dossiers` 50-app set is NOT in main yet — please PR it.
