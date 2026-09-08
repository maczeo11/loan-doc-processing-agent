# KYC & Customer Due Diligence Guidelines (v1.0)

**Effective Date:** 2026-01-01  
**Classification:** Regulatory Compliance

---

## 1. Identity Verification Requirements

1.1 **Permanent Account Number (PAN)**  
- Mandatory for all financial credit assessments exceeding ₹50,000.
- Name on PAN card must match the applicant name on the loan application form and salary payslip with a fuzzy match confidence score >= 85%.

1.2 **Proof of Address / Identity**  
- Acceptable documents: Passport, Aadhaar Card, Voter ID, Driving Licence.
- Date of birth must match across all uploaded identity records.

---

## 2. Inconsistency Handling

2.1 **Name Mismatches**  
If initials or maiden names cause minor discrepancy (fuzzy score 70%–84%), finding must be assigned `flag` with reason "Reviewer verification required for name variation". If fuzzy score < 70%, finding must be `flag` with reason "Critical identity mismatch".

2.2 **Missing Documents**  
If PAN or Primary ID is unreadable or absent, rule `RULE-KYC-001` returns `flag`.
