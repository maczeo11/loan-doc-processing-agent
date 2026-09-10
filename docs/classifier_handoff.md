# FinScan AI Document Classifier: Remediation, Benchmark & Handoff Report

**Subsystem:** FinScan AI Document Classifier  
**Component Directory:** `ml/`, `data/`, `core/extraction/`  
**Subsystem Owner:** Karthik (Member 5)  
**Pipeline Version:** 2.0 (Remediated, Grounded, and Benchmarked)  
**Target Deployment:** Pure CPU (ARM64 / x86_64, AWS `t4g.medium`), Zero Network Inference  
**Document Date:** September 2026  

---

## 1. Executive Summary & Verification State

This document provides a factual, reproducible audit and handoff specification for the FinScan AI Document Classifier subsystem. All claims, metrics, and memory figures in this report reflect actual code execution, verified unit tests, and empirical evaluation outputs.

### Summary Status Table
| Item | Requirement / Target | Actual Empirical State | Status |
|---|---|---|---|
| **Canonical Labels** | 5 classes (`application_form`, `bank_statement`, `id_card`, `payslip`, `tax_acknowledgement`) | Implemented in `ml/classifier/baseline_tfidf.py` | **VERIFIED** |
| **Abstention Policy** | Reject empty, whitespace, and low-confidence inputs as `UNKNOWN` | Implemented via confidence rejection gate ($T^* = 0.40$) | **VERIFIED** |
| **Data Provenance** | Grounded in real Kaggle loan approval dataset | Sourced from `data/kaggle_loan_approval_dataset.csv` (SHA-256 verified) | **VERIFIED** |
| **Document Watermark** | Visible synthetic label on all synthetic documents | `SYNTHETIC DEMO — NOT VALID` stamped on all positive pages | **VERIFIED** |
| **Split Disjointness** | Double-disjoint: zero applicant overlap AND zero template family overlap | 0 applicant overlap, 0 template family overlap across Train, Dev, Test | **VERIFIED** |
| **Held-Out Test Macro-F1** | $\ge 0.9000$ | **0.9823** (Held-out unseen template families + negatives) | **VERIFIED** |
| **Inference Latency** | Median $< 20.0\text{ ms / page}$ | **5.72 ms / page** (p50), **7.37 ms / page** (p95) | **VERIFIED** |
| **Process Working Set RSS** | $< 500.0\text{ MB}$ | **154.95 MB** OS Working Set RSS (Python heap delta: 1.56 MB) | **VERIFIED** |
| **Unit Test Coverage** | 100% pass on all unit test suites | **27 / 27 unit tests passing** (`pytest tests/unit/`) | **VERIFIED** |
| **Runtime Network Dependencies** | Zero runtime downloads | Completely local execution (`scikit-learn`, `joblib`, `numpy`) | **VERIFIED** |

---

## 2. Task Formulation & Honest Identity

### 2.1 Task Boundary
The classifier performs **page-level document routing** from extracted text (extracted via PDF native text layer or OCR fallback).
- **Inputs:** Plain text strings extracted from a document page.
- **Outputs:** Canonical document class and calibrated confidence score: `(predicted_class, confidence)`.
- **Abstention (`UNKNOWN`):** Triggered if:
  1. Input string is empty or contains only whitespace (`abstention_reason: "empty_text"`).
  2. Maximum predicted class probability is below the calibrated threshold $T^*$ (`abstention_reason: "LOW_CONFIDENCE_..._BELOW_THRESHOLD_..."`).
  3. Out-of-domain or unidentifiable document text.

### 2.2 Explicit Non-Goals
To preserve strict architectural boundaries (per `AGENTS.md` Sections 6 and 8):
1. **No Credit Risk / Tabular Underwriting:** This subsystem does **not** predict loan approval status, credit risk, or default probability from tabular CSV rows. Tabular underwriting is performed by Member 4's deterministic rules engine (`core/rules/`).
2. **No Field Extraction:** Mathematical entity extraction (e.g. gross salary, account number, PAN) is performed by Member 3's fact extractors (`core/extraction/extractors/`).
3. **No LLM Fine-Tuning:** The classifier is a fast, deterministic, CPU-first TF-IDF pipeline; it does not invoke or fine-tune large language models.

### 2.3 Honest Model Identity
- **Active Production Model:** Word `(1, 2)` + Character `(3, 5)` n-gram TF-IDF vectorizer coupled with balanced multi-class `LogisticRegression`.
- **Challenger Status (DistilBERT):** In the v1 codebase, a stub was created that silently executed an `SGDClassifier` fallback when `torch` and `transformers` were not present. In accordance with Section 8 of `AGENTS.md`, non-neural fallbacks are **never** labeled as DistilBERT or transformer models. Any future neural challenger requires an explicitly verified PyTorch environment.

---

## 3. Dataset Provenance & Double-Disjoint Split Architecture

### 3.1 Kaggle Dataset Provenance
- **Source File:** `data/kaggle_loan_approval_dataset.csv`
- **File Integrity (SHA-256):**  
  `4b5cd093d178378f4cfa8c107adb6e599b88be9d8a3b51f3b99c0d5914154e54`
- **Source Dataset Properties:** 4,269 loan applicant rows with 13 columns.
- **Provenance Manifest:** `ml/data/v2/provenance_manifest.json` tracks the exact Kaggle row ID, synthetic applicant ID, loan parameters, template family, and split partition for every generated sample.

### 3.2 Real Kaggle Attributes Grounding
70 applicants (Rows 1–70 of the Kaggle dataset) are used as grounding profiles. For each applicant:
- `income_annum`: Derived monthly gross salary $= \text{income\_annum} / 12$. Realistic deductions for EPF, TDS, and PT are computed to derive net pay.
- `loan_amount` and `loan_term`: Ground loan application forms, commercial loan summaries, and tax returns.
- `cibil_score`: Formats retail loan applications and underwriting notes.
- `residential_assets_value` + `commercial_assets_value` + `bank_asset_value`: Derive bank account opening balances, transaction credit volumes, and closing balances.

### 3.3 Structural Template Families (20 Total)
To eliminate layout memorization and measure true out-of-distribution generalization, 4 distinct structural template families were designed for each of the 5 canonical classes:

| Canonical Class | Family 1 (Train) | Family 2 (Train) | Family 3 (Dev) | Family 4 (Held-Out Test) |
|---|---|---|---|---|
| **`application_form`** | `APP_FORM_STD_RETAIL` | `APP_FORM_HOUSING_FIN` | `APP_FORM_DIGITAL_APP` | `APP_FORM_COMMERCIAL_SME` |
| **`bank_statement`** | `BANK_STMT_TABULAR_HDFC` | `BANK_STMT_SBI_PASSBOOK` | `BANK_STMT_WEALTH_OVERVIEW` | `BANK_STMT_NEOBANK_LEDGER` |
| **`id_card`** | `ID_PAN_CARD` | `ID_AADHAAR_CARD` | `ID_VOTER_EPIC` | `ID_PASSPORT_PAGE` |
| **`payslip`** | `PAYSLIP_CORP_TECH` | `PAYSLIP_MFG_VOUCHER` | `PAYSLIP_PUBLIC_SECTOR` | `PAYSLIP_CONSULTING_COMPACT` |
| **`tax_acknowledgement`** | `TAX_ACK_ITR1_SAHAJ` | `TAX_ACK_ITR2_4_SUGAM` | `TAX_ACK_INTIMATION_143_1` | `TAX_ACK_EFILING_RECEIPT` |

### 3.4 Negative & Out-of-Domain Samples
Dev and Held-Out Test sets include negative samples with expected ground truth `UNKNOWN`:
- **Syntactic Negatives:** Empty strings, whitespace-only strings, random alphanumeric gibberish tokens.
- **Out-of-Domain Negatives:** Commercial lease agreements, medical prescriptions, resume / CVs, shipping air waybills, utility bills (electricity / water), broadband invoices, hospital discharge summaries, employment offer letters, vendor purchase orders, vehicle insurance certificates.

### 3.5 Double-Disjoint Partitioning Invariant
Partitions are strictly double-disjoint:
1. **Applicant ID Disjointness:**  
   $$\text{Train Applicants} \cap \text{Dev Applicants} = \emptyset$$  
   $$\text{Train Applicants} \cap \text{Test Applicants} = \emptyset$$  
   $$\text{Dev Applicants} \cap \text{Test Applicants} = \emptyset$$
2. **Template Family Disjointness:**  
   - **Train Split:** 48 applicants $\times$ Families 1 & 2 ($96 \text{ pages per class} \times 5 = 480 \text{ samples}$).
   - **Dev Split:** 11 applicants $\times$ Family 3 ($11 \text{ pages per class} \times 5 = 55$) + 8 negative samples = **63 samples**.
   - **Held-Out Test Split:** 11 applicants $\times$ Family 4 ($11 \text{ pages per class} \times 5 = 55$) + 8 negative samples = **63 samples**.
   - **Total Dataset Size:** 606 samples.
   - **Verification:** Verified by automated unit test `test_v2_splits_double_disjoint_property`.

---

## 4. Model Architecture & Hyperparameters

### 4.1 Feature Pipeline
```
Raw Input Text
      │
      ├───> Word TF-IDF Vectorizer
      │     (ngram_range=(1, 2), analyzer='word', sublinear_tf=True, max_features=12000)
      │
      └───> Character TF-IDF Vectorizer
            (ngram_range=(3, 5), analyzer='char_wb', sublinear_tf=True, max_features=25000)
      │
      ▼
FeatureUnion (37,000 concatenated n-gram sparse features)
      │
      ▼
LogisticRegression(class_weight='balanced', max_iter=1000, solver='lbfgs', random_state=42)
      │
      ▼
Class Probability Distribution P(C | x)
      │
      ▼
Rejection Gate: If max P(C | x) < T* (0.40) or input is empty -> Return UNKNOWN
```

### 4.2 Confidence Calibration & Optimal Threshold Selection
Threshold tuning was conducted **strictly on the Dev split** without touching the Held-out Test split.
- **Search Grid:** $T \in [0.10, 0.90]$ in increments of $0.05$.
- **Dev Metric:** Macro-F1 across 6 classes (5 canonical + `UNKNOWN`).
- **Optimal Threshold Result:** $T^* = 0.40$ achieved **Macro-F1 = 1.0000** on the 63 Dev samples, correctly rejecting all 8 negative samples while correctly routing all 55 positive samples.

---

## 5. Empirical Benchmark Results (Held-Out Test Generalization)

Evaluation was executed on the 63 held-out test samples (unseen Template Family 4 + unseen negative out-of-domain samples).

### 5.1 Global Metrics
- **Dataset Partition:** Held-Out Test (`ml/data/v2/splits_v2.json`)
- **Total Test Samples:** 63
- **Selected Threshold:** $T = 0.40$
- **Macro-F1 Score:** **0.9823** (Target: $\ge 0.9000$) — **PASSED**
- **Weighted-F1 Score:** **0.9842**
- **Classification Accuracy:** **0.9841** (62 / 63 correct)
- **Inference Latency p50 (Median):** **5.72 ms / page** (Target: $< 20.0\text{ ms}$) — **PASSED**
- **Inference Latency p95:** **7.37 ms / page**
- **Process Working Set RSS:** **154.95 MB** (Target: $< 500.0\text{ MB}$) — **PASSED**
- **Python Heap Allocation Delta:** **1.56 MB**

### 5.2 Per-Class Breakdown
```
                      precision    recall  f1-score   support

            UNKNOWN       0.89      1.00      0.94         8
   application_form       1.00      1.00      1.00        11
     bank_statement       1.00      1.00      1.00        11
            id_card       1.00      0.91      0.95        11
            payslip       1.00      1.00      1.00        11
tax_acknowledgement       1.00      1.00      1.00        11

           accuracy                           0.98        63
          macro avg       0.98      0.98      0.98        63
       weighted avg       0.99      0.98      0.98        63
```

### 5.3 Confusion Matrix
Rows represent ground truth; columns represent model predictions:

| Ground Truth \ Predicted | `UNKNOWN` | `application_form` | `bank_statement` | `id_card` | `payslip` | `tax_acknowledgement` | Total |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **`UNKNOWN`** | **8** | 0 | 0 | 0 | 0 | 0 | 8 |
| **`application_form`** | 0 | **11** | 0 | 0 | 0 | 0 | 11 |
| **`bank_statement`** | 0 | 0 | **11** | 0 | 0 | 0 | 11 |
| **`id_card`** | 1 | 0 | 0 | **10** | 0 | 0 | 11 |
| **`payslip`** | 0 | 0 | 0 | 0 | **11** | 0 | 11 |
| **`tax_acknowledgement`** | 0 | 0 | 0 | 0 | 0 | **11** | 11 |

**Analysis of the Single Abstention:**
Sample `APP-KAG-0066-ID_PASSPORT_PAGE` (unseen passport layout) yielded confidence $0.3975$, which is slightly below the threshold $T^* = 0.40$. Rather than misclassifying the document into an incorrect positive class, the model safely abstained with `UNKNOWN`. All 8 negative / out-of-domain samples were rejected with $100\%$ recall.

---

## 6. Repository File Layout & Artifacts

| File Path | Description |
|---|---|
| `data/kaggle_loan_approval_dataset.csv` | Source Kaggle loan dataset (4,269 rows, SHA-256 verified) |
| `ml/data/v2/dataset_generator_v2.py` | Provenance-grounded synthetic generator (20 template families, watermarked) |
| `ml/data/v2/splits_v2.json` | 606 double-disjoint samples (Train: 480, Dev: 63, Held-Out Test: 63) |
| `ml/data/v2/provenance_manifest.json` | Provenance manifest linking every sample to source Kaggle row IDs |
| `ml/classifier/baseline_tfidf.py` | TF-IDF pipeline, rejection gate, details contract, multi-page aggregation |
| `ml/classifier/train.py` | Training script for v2 baseline artifact |
| `ml/classifier/evaluate.py` | Dev threshold calibration, held-out evaluation, and latency/RSS benchmarking |
| `ml/artifacts/v2/baseline_tfidf.joblib` | Serialized production model bundle |
| `core/extraction/classifier_adapter.py` | Integration adapter service for LangGraph nodes and OCR router |
| `tests/unit/test_classifier_v2.py` | Automated tests verifying splits, provenance, rejection gates, and generalization |
| `audit/v2/evaluation_results_v2.json` | Machine-readable benchmark report with metrics and confusion matrix |
| `audit/v2/per_sample_predictions_v2.json` | Per-sample prediction log on the held-out test split |

---

## 7. Integration Contract for Downstream Consumers

Downstream components (Member 2's `core/graph/nodes.py` and Member 3's `core/extraction/router.py`) integrate via `core/extraction/classifier_adapter.py`:

```python
from core.extraction.classifier_adapter import classify_text, classify_document

# 1. Single Page Classification
page_type, confidence = classify_text("FORM NO. 16 Income Tax Assessment Year 2024-25")
# page_type -> "tax_acknowledgement", confidence -> 0.4666

# 2. Multi-Page Document Classification with Consensus Aggregation
doc_result = classify_document([
    "HDFC Bank Account Statement ...",
    "Account transactions ledger page 2 ..."
])
# doc_result -> {
#     "document_class": "bank_statement",
#     "confidence": 0.4285,
#     "total_pages": 2,
#     "requires_human_triage": False,
#     "page_results": [...]
# }
```

---

## 8. Exact Reproduction Commands

All commands run from repository root using standard Python environment:

```bash
# 1. Generate Remediated V2 Dataset & Provenance Manifest (606 samples)
python -m ml.data.v2.dataset_generator_v2

# 2. Train V2 TF-IDF Classifier Artifact
python -m ml.classifier.train

# 3. Run Calibration, Generalization Benchmark & Audit Generation
python -m ml.classifier.evaluate

# 4. Execute Full Unit Test Suite (27 tests)
pytest tests/unit/ -v
```
