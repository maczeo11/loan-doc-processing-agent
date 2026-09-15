# 📚 FinScan AI — Module 4: Deterministic Rules Engine, Synthetic Data & Reporting
## 🎓 Complete Conceptual & Theory Guide for Mentor Explanation (Zero Code)
### **Owner:** Sravanthi (Member 4 — Financial Logic, Data & Reporting Architect)
### **Assigned Scope:** `core/rules/`, `core/reporting/`, `data/`, `scripts/generate_dossiers.py`

---

## 🧭 Table of Contents
1. [The 30-Second Elevator Pitch to Your Mentor](#1-the-30-second-elevator-pitch-to-your-mentor)
2. [The Real-World Banking Problem (Why This is a "HUMAN-ONLY ZONE")](#2-the-real-world-banking-problem-why-this-is-a-human-only-zone)
3. [Key Definitions in Simple Terms (The Module 4 Vocabulary)](#3-key-definitions-in-simple-terms-the-module-4-vocabulary)
4. [Pillar 1: The 5 Deterministic Financial Rules (Deep Dive)](#4-pillar-1-the-5-deterministic-financial-rules-deep-dive)
5. [Pillar 2: Core Safety Invariants (Non-Coercion & Non-Overwriting)](#5-pillar-2-core-safety-invariants-non-coercion--non-overwriting)
6. [Pillar 3: The Synthetic Dossier Generator & Controlled Anomalies](#6-pillar-3-the-synthetic-dossier-generator--controlled-anomalies)
7. [Pillar 4: The Credit Appraisal Memo (CAM) Builder & Exporter](#7-pillar-4-the-credit-appraisal-memo-cam-builder--exporter)
8. [End-to-End Walkthrough: Auditing Ravi Kumar’s Financial Dossier](#8-end-to-end-walkthrough-auditing-ravi-kumars-financial-dossier)
9. [Architectural Trade-Off & Decision Tables](#9-architectural-trade-off--decision-tables)
10. [Top 15 Mentor & Viva Defense Questions & Answers](#10-top-15-mentor--viva-defense-questions--answers)

---

## 1. The 30-Second Elevator Pitch to Your Mentor

> *"Respected Sir/Ma'am,  
> In FinScan AI, our core architectural law is: **Deterministic code calculates, AI explains, and a human approves.**  
> My responsibility as **Member 4 (Sravanthi)** was to build that calculation foundation and the executive reporting layer.  
>  
> I built three essential components:  
> 1. **The Deterministic Rules Engine:** A strictly human-written, mathematical audit engine in `core/rules/` that executes 5 core financial checks — verifying completeness, reconciling salary slips against bank credits within a 5% tolerance, cross-auditing tax filings, verifying multi-document identity, and proving bank balance arithmetic. Zero AI is used in any math.  
> 2. **The Synthetic Dossier Generator:** A data engine that generates coherent, realistic multi-document PDF dossiers from Kaggle tabular seeds with controlled fraud anomalies and mandatory synthetic watermarks, protecting customer data privacy.  
> 3. **The Credit Appraisal Memo (CAM) Builder:** An auditable reporting engine in `core/reporting/` that packages verified numbers, rule findings, and coordinate citations into a professional briefing document for bank sanction committees."*

---

## 2. The Real-World Banking Problem (Why This is a "HUMAN-ONLY ZONE")

### The Danger of Letting AI Do Math
In recent years, many tech startups tried using Large Language Models (like ChatGPT or GPT-4) to analyze loan documents and calculate debt ratios. In retail banking, this is an **absolute catastrophe**:

1. **Floating-Point Hallucination:**  
   LLMs are next-word predictors, not calculators. If you feed an LLM three payslips with net pay of ₹44,200 and a bank credit of ₹42,000, the LLM might hallucinate: *"The salary matches closely, difference is ₹1,200."* (Real difference is ₹2,200!). In banking, a ₹1,000 discrepancy can hide an undisclosed salary loan or payroll fraud.
2. **Non-Deterministic Inconsistency:**  
   If you run the exact same loan application through an LLM 10 times, it might pass it 7 times, flag it 2 times, and output a different ratio on the 10th run. **A bank cannot defend a non-deterministic lending decision in a court of law or before an RBI auditor.**
3. **Legal Regulatory Auditing:**  
   Under Reserve Bank of India (RBI) Fair Lending Practices and Model Risk Management guidelines, every loan rejection must provide a **traceable mathematical formula and exact page citation**. You cannot say *"The AI felt the income was insufficient."*

### The FinScan AI Solution: The "HUMAN-ONLY ZONE"
In our project codebase, the folder `core/rules/` is officially designated as a **HUMAN-ONLY ZONE**.  
- **No LLM prompts are allowed.**
- **No machine learning models are used.**
- **Every rule is pure, deterministic Python arithmetic written by human developers.**
- The AI only enters later (in Station 6) to read these pre-calculated numbers and format them into readable English sentences.

---

## 3. Key Definitions in Simple Terms (The Module 4 Vocabulary)

| Term | In Simple Words | Real-World Analogy | Role in FinScan AI |
| :--- | :--- | :--- | :--- |
| **Deterministic Rule** | A fixed formula that gives the exact same result every single time. | A pocket calculator: `2 + 2` is always `4`. | The mathematical checks in `core/rules/` (e.g. salary reconciliation). |
| **Tolerance Margin (5%)** | The acceptable percentage difference between two matching financial numbers. | Giving a shopkeeper ₹100 for a ₹98 bill and saying "keep the change". | Accounts for minor payroll deductions (canteen, professional tax) up to 5%. |
| **Finding** | The official certified output ticket of a rule check. | A lab blood test report slip. | A typed object containing `rule_id`, `verdict`, mathematical reason, and page citations. |
| **Verdict** | The outcome score of a rule: `PASS`, `FLAG`, or `UNKNOWN`. | A traffic light: Green (`PASS`), Red/Yellow (`FLAG`), or Broken (`UNKNOWN`). | The decision tag given to each rule check. |
| **Salary Reconciliation** | Cross-checking claimed salary against actual bank deposits. | Checking if the salary slip matches the SMS bank alert on payday. | `RULE-INC-01`: Payslip net pay must equal bank monthly credit. |
| **Tax Audit Consistency** | Checking if annual tax returns match monthly payslips multiplied by 12. | Multiplying monthly rent by 12 to see if it matches the annual house lease. | `RULE-TAX-01`: Annual ITR gross income must equal 12 × monthly gross salary. |
| **Fuzzy Matching** | String comparison that tolerates minor spelling variations or initials. | Recognizing that "R. Kumar" and "Ravi Kumar" are the same person. | `RULE-ID-01`: Name match must exceed 85% similarity threshold. |
| **Non-Coercion Invariant** | Never force or guess a `PASS` when data is missing or unreadable. | A medical lab writing "Sample Inconclusive" rather than guessing "Healthy". | If payslip salary is missing, verdict is strictly `UNKNOWN`, never a fake `PASS`. |
| **Non-Overwriting Invariant** | Every rule output has a unique ID and never overwrites another rule. | Keeping separate folders for Blood Test and X-Ray, never replacing one with the other. | `RULE-COMP-01` and `RULE-INC-01` both exist independently in the final memo. |
| **Synthetic Dossier** | Artificially generated loan files that look 100% real but use fake names. | Monopoly money or a stunt dummy in a car crash test. | Test dossiers generated by `scripts/generate_dossiers.py` using Kaggle seeds. |
| **Watermark Invariant** | A mandatory visible stamp on every page: `SYNTHETIC DEMO — NOT VALID`. | A bold red "SAMPLE" stamp across a dummy cheque leaf. | Legally prevents demo synthetic PDFs from being misused as fake loan documents. |
| **Credit Appraisal Memo (CAM)** | An executive briefing report summarizing the borrower's risk profile. | A doctor's comprehensive discharge summary or an architect's building report. | The final markdown/PDF document presented to the bank credit committee. |

---

## 4. Pillar 1: The 5 Deterministic Financial Rules (Deep Dive)

Sravanthi engineered **5 core deterministic rules** in `core/rules/`. Each rule addresses a specific vector of loan fraud or misrepresentation.

---

### 📋 Rule 1: `RULE-COMP-01` — Dossier Completeness Check
* 🎯 **Memory Hook:** *"All 5 documents present, or stop right there!"*
* 🏥 **Real-World Analogy:** Applying for an Indian Passport at the Seva Kendra. If you brought your Aadhaar and birth certificate but forgot your 10th marksheet, the counter officer stops you immediately.
* 📥 **What It Checks:** Verifies that the applicant uploaded all 5 mandatory loan dossier categories:
  1. Loan Application Form
  2. Salary Payslips (last 3 consecutive months)
  3. Bank Account Statement (3 to 6 months)
  4. Income Tax Return (ITR-V Acknowledgement or Form 16)
  5. Government-issued KYC Identity Proof (PAN / Aadhaar)
* ⚙️ **The Logic in Plain Words:**  
  The rule compares the list of uploaded document types against the required list.
  - If all 5 types exist → **Verdict: `PASS`**.
  - If any document is missing → **Verdict: `FLAG`** with a list of missing document names.
* ⚠️ **Failure Scenario:** A borrower uploads 3 payslips and an Aadhaar card, but no bank statement. `RULE-COMP-01` flags: *"Incomplete Dossier: Missing bank_statement and tax_return"*.

---

### 💰 Rule 2: `RULE-INC-01` — Salary vs. Bank Credit Reconciliation
* 🎯 **Memory Hook:** *"Payslip net pay must match the bank deposit within 5%!"*
* 🏥 **Real-World Analogy:** A tenant says: *"I paid you ₹20,000 rent yesterday."* You open your Google Pay / bank app. If the deposit says ₹20,000, you are satisfied. If the deposit says ₹12,000, you demand an explanation!
* 📥 **What It Checks:** Cross-examines the **Net Salary** on the payslip against the **Salary Credit Transaction** appearing in the bank account statement.
* ⚙️ **The Formula in Plain Words:**  
  $$\text{Discrepancy} = \frac{|\text{Payslip Net Salary} - \text{Bank Salary Deposit}|}{\text{Payslip Net Salary}}$$
  - If discrepancy is **$\le 0.05$ (within 5.0% tolerance)** → **Verdict: `PASS`**.
  - If discrepancy is **$> 0.05$ (exceeds 5%)** → **Verdict: `FLAG`**.
  - If payslip or bank credit is unreadable → **Verdict: `UNKNOWN`**.
* 💡 **Why 5% Tolerance?**  
  In corporate payroll, minor monthly fluctuations occur due to meal coupons (Sodexo), professional tax deductions (₹200), or transport allowances. A strict 0% tolerance would cause false alarms for genuine employees. 5% accommodates legitimate adjustments while catching real fraud.
* ⚠️ **Failure Scenario:** A fraudster uses Photoshop to edit their payslip to show ₹85,000, but their actual bank statement shows monthly salary credits of ₹35,000. Discrepancy is 58.8%! `RULE-INC-01` flags: *"Salary Reconcile Discrepancy: 58.8% exceeds 5.0% tolerance"*.

---

### 🏛️ Rule 3: `RULE-TAX-01` — Tax Return vs. Stated Income Audit
* 🎯 **Memory Hook:** *"Annual tax income must equal 12 times the monthly salary!"*
* 🏥 **Real-World Analogy:** A shopkeeper claims his business earns ₹1,00,000 every single month (₹12 Lakhs/year), but his official income tax filing to the government reports an annual income of only ₹3 Lakhs. Either he lied on his loan form, or he is evading taxes!
* 📥 **What It Checks:** Cross-checks the **Gross Total Income** declared on the government Income Tax Return (ITR) against the **Gross Salary** stated on the monthly payslip.
* ⚙️ **The Formula in Plain Words:**  
  1. Calculate Annualized Stated Income: $\text{Annual Gross} = \text{Monthly Gross Salary} \times 12$.
  2. Compare with ITR Gross Total Income:
     $$\text{Variance} = \frac{|\text{ITR Annual Income} - \text{Annualized Gross Salary}|}{\text{Annualized Gross Salary}}$$
  - If variance is within acceptable tax bounds (typically $\le 10\%$) → **Verdict: `PASS`**.
  - If variance exceeds bounds → **Verdict: `FLAG`**.
* ⚠️ **Failure Scenario:** Borrower states a monthly gross salary of ₹50,000 (Annualized = ₹6,00,000), but their ITR-V Acknowledgement shows Gross Total Income of only ₹2,80,000. `RULE-TAX-01` flags a severe variance.

---

### 🆔 Rule 4: `RULE-ID-01` & `RULE-ID-02` — Identity Consistency & Cross-KYC Match
* 🎯 **Memory Hook:** *"Name and PAN must match identically across all documents!"*
* 🏥 **Real-World Analogy:** Checking into an international flight. Your ticket says "Ravi Kumar", your passport says "Ravi Kumar", and your visa says "Ravi Kumar". If your visa suddenly says "Suresh Sharma", security will detain you!
* 📥 **What It Checks:**
  - **`RULE-ID-01`:** Compares the applicant's name and PAN card number from their primary KYC ID against the name printed on the payslips, bank statements, and tax returns.
  - **`RULE-ID-02`:** Cross-checks between two uploaded identity documents itself (e.g. an Aadhaar Card AND a separately uploaded PAN card) to catch swapped ID pairs.
* ⚙️ **The Logic in Plain Words:**  
  - **PAN Check:** Strict exact string matching (PAN format: 5 letters, 4 numbers, 1 letter — e.g. `ABCDE1234F`).
  - **Name Check:** Uses **fuzzy string matching** (Levenshtein distance algorithm):
    - Score $\ge 85\%$: Matches safely (e.g. "Ravi Kumar" vs "Ravi Kumar") → **`PASS`**.
    - Score $70\% - 84\%$: Minor variation (e.g. "Ravi K." vs "Ravi Kumar") → **`FLAG`** (requires underwriter visual verification).
    - Score $< 70\%$: Severe mismatch (e.g. "Ravi Kumar" vs "Vikram Malhotra") → **`FLAG`** (Critical identity alert!).

---

### 🏦 Rule 5: `RULE-BANK-01` — Bank Statement Arithmetic Validation
* 🎯 **Memory Hook:** *"Opening balance + Credits - Debits must equal Closing balance!"*
* 🏥 **Real-World Analogy:** Your bank passbook. If you had ₹10,000 on Jan 1st, deposited ₹40,000 during January, and spent ₹20,000, your balance on Jan 31st MUST be ₹30,000. If the passbook says ₹80,000, someone tampered with the numbers!
* 📥 **What It Checks:** The mathematical integrity of the bank statement summary table.
* ⚙️ **The Formula in Plain Words:**  
  $$\text{Expected Closing} = \text{Opening Balance} + \text{Total Credits} - \text{Total Debits}$$
  $$\text{Variance} = |\text{Expected Closing} - \text{Reported Closing Balance}|$$
  - If variance is zero (or within rounding cents) → **Verdict: `PASS`**.
  - If variance $> 0$ → **Verdict: `FLAG`** (Suspected bank statement document tampering/fabrication).
* ⚠️ **Failure Scenario:** A borrower uses a PDF editor to artificially inflate their closing bank balance from ₹5,000 to ₹1,50,000 without altering the transaction credit/debit totals. `RULE-BANK-01` detects that the math doesn't balance and flags the forgery instantly.

---

## 5. Pillar 2: Core Safety Invariants (Non-Coercion & Non-Overwriting)

In a bank audit, how you handle edge cases and missing data is what separates amateur software from enterprise banking systems. Sravanthi enforced two strict safety laws:

### 1. The Non-Coercion Invariant (Never Guess a PASS)
* **The Rule:** If a required document or data field is missing, blurry, or unreadable, the rule verdict **must strictly be `UNKNOWN` or `FLAG`**.
* **What is forbidden:** The system is **strictly forbidden from defaulting to `PASS`**.
* **Why it matters:** In banking, assuming missing information is "fine" leads to catastrophic non-performing loans (NPLs). If an applicant refuses to submit bank statements, the system must never assume their salary was deposited!

### 2. The Non-Overwriting Invariant (Independent Audits)
* **The Rule:** Every single rule produces a distinct, immutable `Finding` object identified by its permanent `rule_id` (`RULE-COMP-01`, `RULE-INC-01`, etc.).
* **What is forbidden:** One rule can never overwrite, hide, or erase the verdict of another rule.
* **Why it matters:** Even if an applicant passes identity, tax, and completeness with flying colors, the salary mismatch flag must remain clearly visible on the final Credit Appraisal Memo.

---

## 6. Pillar 3: The Synthetic Dossier Generator & Controlled Anomalies

### Why We Cannot Use Real Customer Data
Under the Indian **Digital Personal Data Protection Act (DPDP 2023)**, GDPR, and RBI privacy regulations, using real customer PAN cards, Aadhaar numbers, and bank statements in a software hackathon or demo is a **punishable legal offense**.

### How Sravanthi Built the Synthetic Data Engine (`scripts/generate_dossiers.py`)
To enable rigorous testing and live demonstrations without violating privacy laws, Sravanthi built a deterministic synthetic dossier generation engine:

```
[Kaggle Tabular Loan Dataset] (Real financial statistical distributions)
               │
               ▼
[Synthetic Dossier Engine (scripts/generate_dossiers.py)]
     • Replaces real names with fictional Indian names (Aarav Sharma, Priya Patel)
     • Replaces employers with corporate names (TCS, Infosys, Wipro)
     • Replaces banks with real banking formats (HDFC, SBI, ICICI)
     • Stamps every page with mandatory watermark
               │
               ▼
[Multi-Document PDF Loan Dossiers with Controlled Anomalies]
```

### The 4 Key Invariants of the Data Generator:
1. **The Prominent Watermark:**  
   Every single PDF page generated bears a bold, unremovable diagonal watermark across the canvas:  
   **`SYNTHETIC DEMO — NOT VALID`**.  
   This ensures that no generated PDF can ever be circulated or misused as a fake document in the real world.
2. **Kaggle Tabular Realism:**  
   Instead of generating random numbers, the engine reads real statistical distributions from Kaggle loan datasets (realistic salary-to-loan ratios, CIBIL scores, existing debt levels).
3. **Controlled Anomaly Injection:**  
   To test the rules engine, the generator deliberately introduces controlled discrepancies:
   - *Scenario A (Clean Borrower):* Everything matches 100% (All rules `PASS`).
   - *Scenario B (Salary Discrepancy):* Payslip net pay is edited to ₹60,000, while bank credits remain ₹44,200 (Triggers `RULE-INC-01 FLAG`).
   - *Scenario C (Missing Document):* Ommits the tax return (Triggers `RULE-COMP-01 FLAG`).
   - *Scenario D (Identity Mismatch):* Changes the name on the PAN card to a different person (Triggers `RULE-ID-01 FLAG`).
4. **Deterministic Reproducibility:**  
   Using fixed random seeds (`--seed 42`), the generator produces the **exact same byte-for-byte PDFs and numbers** every single time, making automated test suites completely reliable.

---

## 7. Pillar 4: The Credit Appraisal Memo (CAM) Builder & Exporter

### What is a Credit Appraisal Memo (CAM)?
In commercial and retail banking, when a loan is being considered, the underwriting team does not hand the bank manager a disorganized pile of raw bank statements and salary slips.  
Instead, they prepare an executive briefing paper called the **Credit Appraisal Memo (CAM)**. This document acts as the legal and financial summary upon which the loan sanction committee makes its decision.

### How Sravanthi Built the CAM Builder (`core/reporting/memo_builder.py`)
Sravanthi's reporting engine gathers the raw facts from Station 3, the deterministic math findings from Station 4, and the policy chunks from Station 5, assembling them into a standardized, structured document.

#### The 5 Sections of the FinScan AI CAM:
1. **Executive Summary & Applicant Profile:**  
   Applicant name, masked PAN, employer name, tenure, requested loan amount, and requested loan term.
2. **Income & Payroll Verification Table:**  
   Side-by-side reconciliation table comparing Payslip Net Salary vs. Bank Account Payroll Credit vs. ITR Annualized Income, displaying the exact calculated variance.
3. **Obligations & Debt-to-Income (DTI) Ratios:**  
   Existing monthly EMIs, proposed loan EMI, calculated DTI percentage, and post-EMI disposable income buffer.
4. **Deterministic Audit Findings (Pass / Flag Badges):**  
   A clear tabular scorecard of all 5 rules (`RULE-COMP-01` through `RULE-BANK-01`) showing the verdict badge, mathematical justification, and supporting evidence citations.
5. **Regulatory Policy Citations & Audit Footnotes:**  
   Every claim carries an exact footnote linking to the document ID, page number, and yellow bounding-box coordinates (e.g. `[DOC-001:Page 1 (100, 200)]`).

### Exporter (`core/reporting/exporter.py`):
Provides one-click export into:
- **Structured JSON:** For downstream banking core systems and database storage.
- **Formal PDF / Markdown Report:** For human underwriters to sign, print, and archive in the bank's regulatory loan file.

---

## 8. End-to-End Walkthrough: Auditing Ravi Kumar’s Financial Dossier

Here is the exact step-by-step narrative of how Sravanthi's module audits applicant **Ravi Kumar**:

```
1. INPUT ARRIVES:
   Extracted facts arrive from Station 3:
   • Payslip: Net Salary = ₹44,200 | Gross = ₹52,000 | Employer = Infosys
   • Bank Statement: Monthly Payroll Deposit = ₹44,200 | Opening = ₹10,000 | Closing = ₹34,200
   • Tax Return: Gross Total Income = ₹6,24,000
   • Identity: Name = "Ravi Kumar" | PAN = "ABCDE1234F"

2. RULE 1 EXECUTION (Completeness):
   Checks uploaded documents: Form, 3 Payslips, Bank, ITR, PAN.
   All 5 present.
   → Finding: RULE-COMP-01 = PASS

3. RULE 2 EXECUTION (Salary Reconciliation):
   Compares ₹44,200 (Payslip) vs ₹44,200 (Bank Credit).
   Variance = |44,200 - 44,200| / 44,200 = 0.0% (Well within 5% tolerance).
   → Finding: RULE-INC-01 = PASS (Variance 0.0%)

4. RULE 3 EXECUTION (Tax Audit):
   Calculates Annual Gross = ₹52,000 × 12 = ₹6,24,000.
   Compares with ITR Gross Total Income = ₹6,24,000.
   Variance = 0.0%.
   → Finding: RULE-TAX-01 = PASS (Variance 0.0%)

5. RULE 4 EXECUTION (Identity Check):
   Fuzzy matches "Ravi Kumar" across KYC, Payslip, and Bank Statement.
   Similarity score = 100%. PAN matches exactly.
   → Finding: RULE-ID-01 = PASS

6. RULE 5 EXECUTION (Bank Arithmetic):
   Expected Closing = ₹10,000 (Opening) + ₹44,200 (Salary) - ₹20,000 (Debits) = ₹34,200.
   Reported Closing = ₹34,200. Math balances perfectly.
   → Finding: RULE-BANK-01 = PASS

7. CAM MEMO GENERATION:
   Sravanthi's memo builder compiles all 5 PASS findings, creates the financial tables,
   attaches coordinate footnotes, and prepares the memo for the human underwriter.
```

---

## 9. Architectural Trade-Off & Decision Tables

When your mentor asks *"Why did you design the rules engine this way?"*, use these direct comparisons:

### 1. Pure Deterministic Python Math vs. LLM Arithmetic Prompting
| Criteria | Deterministic Python Math (Chosen) | LLM Arithmetic Prompting |
| :--- | :--- | :--- |
| **Mathematical Precision** | ✅ 100% exact; zero arithmetic errors | ❌ Hallucinates numbers; floating-point rounding errors |
| **Consistency / Reproducibility** | ✅ 100% reproducible; same inputs yield identical results | ❌ Non-deterministic; different results on repeated runs |
| **Execution Latency** | ✅ Microseconds (< 1 millisecond) | ❌ Slow (2 to 5 seconds per LLM call) |
| **Cost** | ✅ Free (CPU instruction execution) | ❌ Cloud API cost per token ($) |
| **Regulatory Compliance** | ✅ Fully auditable by RBI / banking regulators | ❌ Black-box reasoning; legally indefensible in court |
| **Verdict** | **Selected:** Inviolable requirement of the project Prime Invariant. | **Rejected:** Completely banned for financial arithmetic. |

---

### 2. Python `Decimal` vs. Standard `float` for Currency
| Criteria | Python `Decimal` (Chosen) | Standard `float` |
| :--- | :--- | :--- |
| **Binary Representation** | Exact decimal representation (base-10) | Binary floating-point approximation (base-2) |
| **Precision Issues** | Zero rounding anomalies (`0.1 + 0.2 == 0.3`) | Floating point error: `0.1 + 0.2 = 0.30000000000000004` |
| **Banking Suitability** | Standard requirement in financial ledger systems | Unacceptable for currency audits; causes false tolerance flags |
| **Verdict** | **Selected:** Ensures exact monetary accuracy down to the paise/cent. | **Rejected:** Prohibited in banking transaction calculations. |

---

## 10. Top 15 Mentor & Viva Defense Questions & Answers

### Q1: "What was your specific personal contribution as Sravanthi (Member 4)?"
> **Answer:**  
> *"I was the Financial Rules & Reporting Architect. I authored the 5 deterministic underwriting audit rules in `core/rules/`, built the synthetic loan dossier generator with Kaggle seeds and mandatory watermarking in `scripts/generate_dossiers.py`, and designed the Credit Appraisal Memo (CAM) builder and export engine in `core/reporting/`."*

### Q2: "Why is the rules engine called a 'HUMAN-ONLY ZONE'?"
> **Answer:**  
> *"Because under the Prime Invariant of FinScan AI, AI is strictly forbidden from doing math or deciding verdicts. Every single comparison—reconciling salary slips, computing tax ratios, and checking bank balance arithmetic—is written in pure, deterministic Python code by human engineers. AI only acts as an explanatory clerk later in the pipeline."*

### Q3: "Why did you implement a 5.0% tolerance margin in RULE-INC-01 instead of demanding an exact 0.0% match?"
> **Answer:**  
> *"In real-world corporate payroll, legitimate monthly salary slips experience minor deductions such as professional tax (₹200), Sodexo meal passes, or voluntary provident fund adjustments that might not reflect in the gross bank credit description. A 5.0% tolerance prevents false-positive flags on genuine salaried employees while strictly catching real fraudulent inflation."*

### Q4: "What happens if a borrower uploads their salary slip, but the bank statement is missing?"
> **Answer:**  
> *"The system enforces our **Non-Coercion Invariant**. In `RULE-COMP-01`, the missing bank statement causes an immediate `FLAG` for completeness. In `RULE-INC-01` (salary reconciliation), because the bank credit is unavailable, the verdict is strictly assigned as `UNKNOWN`—it is legally forbidden from defaulting to an assumed `PASS`."*

### Q5: "What is the difference between RULE-ID-01 and RULE-ID-02?"
> **Answer:**  
> *"`RULE-ID-01` compares the primary KYC proof against the employment documents (payslips and bank statements).  
> `RULE-ID-02` cross-checks between multiple identity documents themselves—for example, comparing an uploaded Aadhaar card against an uploaded PAN card. This specifically catches fraudsters who upload their own Aadhaar card alongside someone else's high-income PAN card."*

### Q6: "How do you perform name matching when people use initials or maiden names?"
> **Answer:**  
> *"In `RULE-ID-01`, we use fuzzy string matching based on the Levenshtein distance algorithm. A similarity score $\ge 85\%$ passes automatically. Scores between $70\%$ and $84\%$ generate a `FLAG` requiring underwriter visual confirmation, while scores below $70\%$ trigger a critical identity alert."*

### Q7: "What is RULE-BANK-01 and what fraud does it detect?"
> **Answer:**  
> *"`RULE-BANK-01` verifies bank statement mathematical integrity by checking if: $\text{Opening Balance} + \text{Total Credits} - \text{Total Debits} == \text{Closing Balance}$. It catches fraudsters who use PDF editing software to artificially type a large closing balance (e.g. ₹5,00,000) into their statement without modifying the underlying debit and credit transaction totals."*

### Q8: "Why did you use Kaggle tabular seeds to generate synthetic dossiers?"
> **Answer:**  
> *"Under data privacy laws (DPDP Act 2023 / GDPR), using real customer banking and PAN records in a hackathon demonstration is illegal. Kaggle loan datasets provide statistically realistic distributions of real Indian salaries, loan amounts, and credit scores. We map these distributions to completely fictional names and companies to ensure realism without privacy violations."*

### Q9: "Why is the watermark 'SYNTHETIC DEMO — NOT VALID' mandatory on every generated page?"
> **Answer:**  
> *"It is an essential legal safeguard. If synthetic, highly realistic bank statements and payslips generated by our system were ever leaked or emailed, the bold diagonal watermark ensures they can never be misused as counterfeit documents in actual real-world fraud."*

### Q10: "What is the Non-Overwriting Invariant?"
> **Answer:**  
> *"Every rule check generates a distinct `Finding` object keyed by its permanent `rule_id`. A later rule or subsequent step can never overwrite, suppress, or merge existing findings. If `RULE-INC-01` flags a salary discrepancy, that flag permanently appears on the underwriter's dashboard regardless of what other rules conclude."*

### Q11: "What is a Credit Appraisal Memo (CAM) and what does your memo builder do?"
> **Answer:**  
> *"A CAM is the official executive briefing document presented to senior bank managers and credit committees to decide loan approvals. My memo builder compiles applicant data, side-by-side salary reconciliation tables, DTI calculations, rule findings, and coordinate footnotes into an auditable Markdown/PDF format."*

### Q12: "How does your module support Akshaya's frontend UI?"
> **Answer:**  
> *"Every `Finding` produced by my rules engine links directly to the `EvidenceRef` coordinates extracted by Jeevan. When Akshaya's React UI renders the findings scorecard, clicking on a finding immediately highlights the exact yellow bounding box on the original PDF canvas."*

### Q13: "Why did you use Python's `Decimal` library instead of standard `float`?"
> **Answer:**  
> *"Standard floating-point numbers in computer hardware suffer from binary rounding errors (e.g. `0.1 + 0.2 = 0.30000000000000004`). In banking arithmetic, even a fractional paisa discrepancy can trigger a false-positive flag in financial audits. The `Decimal` library guarantees exact base-10 arithmetic."*

### Q14: "How did you test your rules engine?"
> **Answer:**  
> *"We built an automated test suite with synthetic applicant dossiers representing specific edge cases: clean applicants, intentional 20% salary discrepancies, missing tax returns, mismatched PAN initials, and tampered bank closing balances. The test suite verified that each scenario triggered the exact expected `PASS`, `FLAG`, or `UNKNOWN` verdict."*

### Q15: "If the evaluator asks you to summarize your contribution in one sentence, what will you say?"
> **Answer:**  
> *"I built the mathematical and reporting backbone of FinScan AI — guaranteeing 100% deterministic, audit-compliant financial calculations that eliminate LLM math hallucinations, while packaging findings into an executive Credit Appraisal Memo for human underwriter sign-off."*

---

## 🚀 11. Latest Production Enhancements & Architecture Updates

---

### 11.1 Signed CAM PDF Export with Official Underwriter Disposition Seal
* **The Upgrade in `core/reporting/exporter.py`:** Sravanthi integrated a bank-grade ReportLab PDF generation engine that transforms the Markdown memo into a formal, printable banking document.
* **The Official Disposition Seal:** When an underwriter approves or rejects an application, the generated PDF features a bold, double-bordered **official bank seal** (Green `[APPROVED]` or Red `[REJECTED]`) stamped across the signatory box, containing:
  - Reviewer ID and cryptographic audit signature.
  - UTC timestamp of sign-off.
  - Reviewer notes and mandatory justification text.
  - Verification QR-code block for paper-trail auditability.

---

### 11.2 Side-by-Side Financial Tables & Badge Formatting
* **Visual Polish:** The generated PDF organizes financial cross-checks into clean, shaded tabular grids:
  - Payslip Net Salary vs Bank Payroll Credits with explicit variance percentages.
  - Debt-to-Income (DTI) obligation limits and disposable income buffer calculation.
  - Color-coded `[PASS]`, `[FLAG]`, and `[UNKNOWN]` findings badges matching the React UI.

---

### 11.3 Browser-Side Demo PDF Generation Fallback (`demoPdfGenerator.ts`)
* **Hackathon & Demo Resilience:** Sravanthi paired the backend Python exporter with a client-side JavaScript PDF generator (`demoPdfGenerator.ts`). If the backend network is unavailable during a live demo or presentation, the React UI can still generate and download a pixel-perfect, signed CAM PDF directly in the browser!
