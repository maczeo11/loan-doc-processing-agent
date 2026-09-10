# FinScan AI Document Classifier: Model Selection & Architecture Trade-off

**Subsystem:** FinScan AI Document Classifier  
**Component Directory:** `ml/`, `docs/`  
**Subsystem Owner:** Karthik (Member 5)  
**Pipeline Version:** 2.0  
**Target Environment:** AWS `t4g.medium` (2 vCPU, 4 GB RAM, Linux ARM64), Pure CPU Execution  
**Document Date:** September 2026  

---

## 1. Executive Summary & Hardware Block Audit

In accordance with Section 8 of `AGENTS.md`, this selection document audits the production readiness of the **Baseline** (Word `(1,2)` + Char `(3,5)` TF-IDF + balanced `LogisticRegression`) versus the **Challenger** (DistilBERT sequence encoder: seq len 256, batch 2–4, AdamW 2e-5, $\le 3$ epochs).

### Hardware & Runtime Environment Audit
- **Deep Learning Runtime:** Neither `torch` nor `transformers` is installed in the target deployment environment (`ModuleNotFoundError: No module named 'torch'`).
- **Network Isolation:** The runtime environment operates under strict offline isolation; runtime downloads from HuggingFace Hub or PyPI are prohibited.
- **Hardware Profile:** The target host is a single AWS EC2 `t4g.medium` instance (ARM64 Graviton2, 2 vCPUs, 4 GB total RAM), which must simultaneously host FastAPI (`apps/api`), PostgreSQL 16, Redis, the async LangGraph orchestrator (`worker`), and the hybrid RAG index.
- **Honest Model Identity Rule:** In compliance with Section 8.4 of `AGENTS.md` ("No fallback linear classifier may be labeled as 'DistilBERT' or a transformer encoder. Neural architectures require verified PyTorch/Transformers execution"), we formally record the runtime dependency and hardware block rather than executing a simulated linear proxy under a transformer label.

---

## 2. Metrics Comparison: Baseline vs. Challenger

The table below contrasts the measured empirical metrics of the production TF-IDF baseline against the projected benchmarks of a DistilBERT sequence classifier under the `t4g.medium` deployment profile:

| Evaluation Dimension | Production Baseline (TF-IDF + LogisticRegression) | Challenger (DistilBERT Encoder) | Selection Winner |
|---|:---:|:---:|:---:|
| **Model Family** | Word `(1,2)` + Char `(3,5)` TF-IDF + Logistic Regression | DistilBERT 6-layer Transformer (`distilbert-base-uncased`) | Baseline (Simpler, Deterministic) |
| **Held-Out Test Macro-F1** | **`0.9823`** (Empirically verified on unseen families) | Projected: `0.9600` – `0.9850` | **Tie / Baseline** |
| **Held-Out Test Accuracy** | **`98.41%`** (62 / 63 correct) | Projected: `97.0%` – `98.5%` | **Tie / Baseline** |
| **Out-of-Domain Rejection** | **`100%`** (8 / 8 negatives rejected via $T^* = 0.40$) | Variable without explicit OOD calibration | **Baseline** |
| **Inference Latency (p50)** | **`5.97 ms / page`** (Measured on pure CPU) | ~`45.0` – `75.0 ms / page` (on ARM64 CPU) | **Baseline (10x faster)** |
| **Inference Latency (p95)** | **`7.40 ms / page`** | ~`90.0` – `120.0 ms / page` | **Baseline (14x faster)** |
| **Process Working Set RSS** | **`154.72 MB`** (Includes Python runtime) | ~`450.0` – `650.0 MB` (PyTorch + weights) | **Baseline (3.5x lower RAM)** |
| **Python Heap Delta** | **`1.53 MB`** | ~`260.0 MB` | **Baseline (170x lighter)** |
| **Artifact Size on Disk** | **`2.05 MB`** (`baseline_tfidf.joblib`) | ~`268.0 MB` (`pytorch_model.bin`) | **Baseline (130x smaller)** |
| **Runtime Dependencies** | `scikit-learn`, `numpy`, `joblib` | `torch`, `transformers`, `tokenizers`, `huggingface_hub` | **Baseline (Zero DL stack)** |
| **Deployment Suitability** | 100% ARM64 CPU native, instant startup | Heavy memory pressure on 4GB instance | **Baseline** |

---

## 3. Ship Decision & Footprint Rationale

**Ship Decision:** In strict accordance with the `AGENTS.md` footprint rule (*"Ship whichever classifier wins on quality AND resource footprint. If baseline gets 0.91 Macro-F1 and DistilBERT gets 0.92 for 400 MB of RAM, ship the baseline and document why"*), **the TF-IDF + LogisticRegression baseline is officially designated as the shipping production classifier.** The baseline achieves an exceptional **0.9823 Macro-F1** and **98.41% accuracy** across completely held-out, unseen structural template families, leaving virtually zero quality deficit to be closed by a transformer. Simultaneously, the baseline executes in **5.97 ms per page** with a minimal **154 MB total process RSS footprint** and zero PyTorch runtime dependencies, preserving vital memory and CPU cycles on our target `t4g.medium` instance for database transactions, asynchronous worker leases, and hybrid RAG retrieval. Deploying a 450+ MB deep neural encoder that introduces PyTorch bloat and 10x latency without measurable quality gains violates our core architectural invariants; therefore, the baseline ships.
