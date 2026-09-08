# 🏦 FinScan AI: GenAI-Enabled Loan Document Processing Agent

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_Core-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![React](https://img.shields.io/badge/React-18_Vite_TS-61DAFB.svg)](https://react.dev/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind-3.4+-38B2AC.svg)](https://tailwindcss.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)

> **Cognizant GenAI + Cloud-Tools Buildathon**  
> **Team:** 8 Members | **Lead / Integrator:** Bhanu Teja | **Timeline:** 1 Week (7 Days)  
> **GitHub Repo:** [maczeo11/loan-doc-processing-agent](https://github.com/maczeo11/loan-doc-processing-agent)

---

## 🎯 The Core Doctrine

> **Deterministic code decides. AI explains. A human approves. Every number traces back to a page in a document.**

- **No hallucinated decisions:** No total, disposition, pass/flag verdict or monetary value originates from an LLM. Pure deterministic functions compute them; the LLM only narrates and explains them.
- **Evidence provenance:** Every extracted fact requires an `EvidenceRef` with document ID, page number, and bounding box coordinates. Missing facts return `UNKNOWN`, never a guess.
- **Human sign-off:** The system never autonomously approves or denies a loan. It prepares an auditable case dossier for human underwriters to inspect and approve.

---

## 🏛️ System Architecture

FinScan AI is organized as a **modular monolith with ports and adapters**, ensuring seamless offline/local development without paid cloud dependencies while supporting 1-click cloud deployment.

```
[ Underwriter / Loan Officer ]
              │ (Upload Dossier: Application, Payslips, Bank Statements, ITR, ID)
              ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. INGESTION & DOCUMENT TRIAGE (apps/api)                   │
│    • FastAPI Async Endpoint • SHA-256 Deduplication         │
│    • Local FileSystem / AWS S3 via StoragePort Adapter      │
│    • Transactional Outbox (PostgreSQL)                      │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. ASYNC WORKER & QUEUE LEASE (worker/ + adapters/queue)   │
│    • Local dev: PostgreSQL SKIP LOCKED Queue Adapter        │
│    • Cloud demo: AWS SQS + DLQ Queue Adapter                │
│    • Idempotent handling • Atomic leases • Acknowledge-last │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. PERCEPTION & HYBRID OCR (core/extraction)                │
│    • Route 1: Native PDF text layer (PyMuPDF) + Word boxes  │
│    • Route 2: Scanned pages -> PaddleOCR on CPU             │
│    • Route 3: AWS Textract (capped fallback, off by default)│
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. DOCUMENT CLASSIFICATION (ml/classifier)                  │
│    • Baseline: TF-IDF + Logistic Regression (fast, CPU)     │
│    • Challenger: DistilBERT-class encoder (seq 256)         │
│    • Auto-selection: Baseline ships if quality is comparable│
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. STRUCTURED FACT EXTRACTION (core/extraction/extractors)  │
│    • PayslipFacts, BankStatementFacts, TaxReturnFacts       │
│    • Strict Pydantic models with mandatory EvidenceRef      │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. DETERMINISTIC RECONCILIATION & RULES (core/rules)        │
│    • Completeness: Flag missing mandatory documents         │
│    • Salary Audit: Payslip net salary vs bank salary credits│
│    • Tax Audit: ITR income vs payslip annualized gross      │
│    • KYC Check: PAN & identity fuzzy matching               │
│    • Output: Structured Findings (pass / flag / unknown)    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. ISOLATED RAG & CITATION CHECK (core/rag)                 │
│    • Application Corpus + Authoritative Policy Corpus       │
│    • Hybrid Retrieval: BM25 Lexical + BGE-small Dense (RRF) │
│    • Exact FAISS Indexing with hard tenant isolation        │
│    • Grounding Validation: Drops ungrounded claims          │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. HUMAN-IN-THE-LOOP (HITL) WORKSPACE (apps/ui)             │
│    • LangGraph interrupt() checkpoint                       │
│    • React 18 + Vite + Tailwind underwriter SPA             │
│    • pdf.js visual bounding-box citation overlays           │
│    • Sign-off: One-click Approve, Flag Discrepancy, Export  │
└─────────────────────────────────────────────────────────────┘
```

---

## 👥 Team Roles & Branch Ownership (8 Members)

All development follows trunk-based workflow with short-lived feature branches targeting `main`:

| Member | Role | Branch Prefix | Primary Directories |
|---|---|---|---|
| **Bhanu Teja** | Tech Lead & Integrator, Async Cloud | `feat/worker-*`, `feat/cloud-*` | `worker/`, `adapters/`, `infra/`, root |
| **Manjunath** | API, Contracts & LangGraph | `feat/api-*`, `feat/contracts-*` | `apps/api/`, `core/contracts/`, `core/graph/` |
| **Jeevan** | Parsing, OCR Routing & Extractors | `feat/ocr-*`, `feat/extract-*` | `core/extraction/` |
| **Sravanthi** | Synthetic Data, Rules & Reporting | `feat/rules-*`, `feat/data-*` | `core/rules/`, `core/reporting/`, `data/` |
| **Karthik** | Document Classifier ML & Evaluation | `feat/ml-*`, `feat/classifier-*` | `ml/` |
| **Balaji** | API Database, Outbox & Deployment | `feat/db-*`, `feat/api-*` | `apps/api/db/`, `infra/` |
| **Akshaya** | React Reviewer SPA (pdf.js) | `feat/ui-*` | `apps/ui/` |
| **Sai Mokshith** | Hybrid RAG & Grounding Validation | `feat/rag-*`, `feat/eval-*` | `core/rag/`, `policies/`, `eval/` |

---

## 📂 Repository Layout

```txt
loan-doc-processing-agent/
├── AGENTS.md               # System constitution, non-negotiables & boundaries
├── Makefile                # Standard developer targets (install, test, lint, demo)
├── pyproject.toml          # Editable package definitions (core, adapters, worker, apps, ml)
├── requirements.txt        # Frozen Python dependencies
├── .env.example            # Environment template
│
├── adapters/               # Hexagonal Ports & Adapters (interchangeable)
│   ├── llm/                # OpenCode Zen (cloud) & local Qwen GGUF (offline)
│   ├── queue/              # Postgres SKIP LOCKED (local) & SQS (cloud)
│   └── storage/            # Local Filesystem (local) & S3 (cloud)
│
├── apps/
│   ├── api/                # FastAPI REST backend & outbox models
│   │   ├── db/             # PostgreSQL session and tables
│   │   ├── routes/         # applications, documents, review, jobs
│   │   ├── config.py       # Pydantic Settings
│   │   └── main.py         # Entrypoint (serves API & mounts built UI)
│   └── ui/                 # React 18 + Vite + TypeScript Reviewer SPA
│       ├── src/            # Underwriter dashboard & pdf.js overlays
│       └── package.json
│
├── core/                   # Pure business logic (NO vendor SDK imports allowed!)
│   ├── contracts/          # Pydantic schemas: EvidenceRef, MoneyFact, Finding, State
│   ├── extraction/         # OCR routing & typed extractors (Payslip, Bank, Tax, ID)
│   ├── graph/              # LangGraph nodes & workflow (StateGraph + interrupt)
│   ├── rag/                # Passage chunking, FAISS exact index, hybrid RRF, grounding
│   ├── reporting/          # Credit Appraisal Memo synthesis & JSON/PDF export
│   └── rules/              # Deterministic financial arithmetic (HUMAN-ONLY ZONE)
│
├── worker/                 # Consumer loop driving LangGraph with atomic leases & DLQ
│   ├── consumer.py         # Delivery handling & result commit before ack
│   └── main.py             # Worker startup
│
├── ml/                     # Document classification models
│   ├── artifacts/          # Serialized models (.joblib)
│   └── classifier/         # Baseline TF-IDF vs Challenger DistilBERT
│
├── policies/               # Authoritative underwriting guidelines for RAG
│   ├── credit_policy_v1.md
│   └── kyc_guidelines_v1.md
│
├── data/
│   ├── manifests/          # Frozen dataset split definitions
│   └── synthetic_dossiers/ # Generated synthetic applicant dossiers with injected fraud
│
├── eval/                   # Frozen 30-question benchmark set & test harness
│   └── questions.json
│
├── infra/                  # Local and Cloud deployment infrastructure
│   ├── Caddyfile           # Reverse proxy config
│   ├── Dockerfile.api      # API container
│   ├── Dockerfile.worker   # Worker container
│   └── docker-compose.yml  # Local Postgres, Redis, API, Worker stack
│
├── scripts/                # Synthetic dossier generators & maintenance
│   └── generate_dossiers.py
│
└── tests/                  # Automated test suite
    ├── smoke/              # Health check & golden-path smoke tests
    └── unit/               # Contract and rule assertion tests
```

---

## 🚀 Quick Start (Local Setup)

### 1. Clone & Set Up Python Environment

```bash
git clone https://github.com/maczeo11/loan-doc-processing-agent.git
cd loan-doc-processing-agent

# Create & activate virtualenv
python -m venv venv
venv\Scripts\activate      # Windows (PowerShell)
# source venv/bin/activate # macOS/Linux

# Install dependencies and editable packages
pip install -r requirements.txt
pip install -e .
```

### 2. Configure Environment

```bash
cp .env.example .env
# Default settings work out-of-the-box for local filesystem & PostgreSQL
```

### 3. Run Automated Tests

```bash
pytest tests/unit
```

### 4. Start Local Services with Docker Compose

```bash
cd infra
docker compose up -d db redis
cd ..
```

### 5. Run API & Worker Locally

In terminal 1 (API):
```bash
uvicorn apps.api.main:app --reload --port 8000
```

In terminal 2 (Worker):
```bash
python -m worker.main
```

In terminal 3 (UI):
```bash
cd apps/ui
npm install
npm run dev
```

---

## 🛡️ Human-Only Zones & Contribution Rules

To prevent hallucinations in critical paths, the following areas require strict human review before merging:
1. **Financial arithmetic in `core/rules/`** (no agent may write both a rule and its test unreviewed).
2. **Lease, outbox, and `SKIP LOCKED` SQL** in `adapters/queue/` and `apps/api/db/`.
3. **Contracts in `core/contracts/`** are the shared single source of truth — changes require integrator sign-off.
4. **`core/` must never import `boto3` or provider SDKs.** All cloud/hardware dependencies belong in `adapters/`.
