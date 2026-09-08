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

## 👥 Team Work Breakdown & Responsibilities (8 Members)

To guarantee zero merge conflicts and smooth parallel development, every teammate has dedicated directory ownership. **Only edit files in your assigned directories.**

---

### 1. Bhanu Teja — Team Lead & Integrator, Async Cloud
* **Assigned Folders:** `worker/`, `adapters/`, `infra/`, root files (`Makefile`, `pyproject.toml`, `AGENTS.md`)
* **Branch Prefix:** `feat/worker-*`, `feat/cloud-*`
* **Core Responsibilities:**
  1. Maintain the worker execution engine (`worker/consumer.py`, `worker/main.py`) driving LangGraph with atomic leases and acknowledge-last commits.
  2. Implement queue adapters (`adapters/queue/pg_queue.py` and `sqs_queue.py`) with 3-attempt ceiling and DLQ safety.
  3. Manage Docker Compose orchestration (`infra/docker-compose.yml`) and cloud deployment.
  4. Perform code reviews and merge all pull requests into `main`.

---

### 2. Manjunath — API Endpoints, Contracts & Graph Orchestration
* **Assigned Folders:** `apps/api/routes/`, `core/contracts/`, `core/graph/`
* **Branch Prefix:** `feat/api-*`, `feat/graph-*`, `feat/contracts-*`
* **Core Responsibilities:**
  1. Build FastAPI REST endpoints in `apps/api/routes/applications.py`, `documents.py`, and `review.py`.
  2. Guard and evolve Pydantic schemas in `core/contracts/` (`evidence.py`, `facts.py`, `findings.py`, `state.py`) in coordination with Bhanu.
  3. Wire the LangGraph `StateGraph` nodes and conditional edges in `core/graph/workflow.py` and `core/graph/nodes.py`.
  4. Implement `interrupt()` for human underwriter sign-off.

---

### 3. Jeevan — Document Parsing, OCR Routing & Extractors
* **Assigned Folders:** `core/extraction/`
* **Branch Prefix:** `feat/ocr-*`, `feat/extract-*`
* **Core Responsibilities:**
  1. Implement PDF text extraction using PyMuPDF (`core/extraction/native_parser.py`) preserving word coordinates.
  2. Implement local CPU PaddleOCR fallback (`core/extraction/paddle_parser.py`) for scanned/raster pages.
  3. Implement page router (`core/extraction/router.py`) to auto-detect native vs scanned pages.
  4. Write fact extractors in `core/extraction/extractors/` (`payslip.py`, `bank_statement.py`, `tax_return.py`, `id_card.py`) ensuring **every extracted fact carries an `EvidenceRef`**.

---

### 4. Sravanthi — Deterministic Rules Engine, Synthetic Data & Reporting
* **Assigned Folders:** `core/rules/`, `core/reporting/`, `data/`
* **Branch Prefix:** `feat/rules-*`, `feat/reporting-*`, `feat/data-*`
* **Core Responsibilities:**
  1. Implement deterministic rules in `core/rules/`:
     - `completeness.py`: Verify all mandatory documents are present.
     - `salary_audit.py`: Reconcile payslip net salary with bank deposits within $\le 5\%$ tolerance.
     - `tax_audit.py`: Cross-check tax return gross income with annualized payslip earnings.
     - `identity.py`: Fuzzy-match PAN and applicant names across all documents.
  2. Maintain synthetic applicant dossiers with injected discrepancies in `data/synthetic_dossiers/`.
  3. Implement Credit Appraisal Memo (CAM) builder and JSON/PDF export in `core/reporting/`.

---

### 5. Karthik — Document Classifier ML & Evaluation
* **Assigned Folders:** `ml/`
* **Branch Prefix:** `feat/ml-*`, `feat/classifier-*`
* **Core Responsibilities:**
  1. Build and train baseline document classifier (`ml/classifier/baseline_tfidf.py`) using `scikit-learn` (TF-IDF + Logistic Regression).
  2. Build challenger classifier (`ml/classifier/challenger_distilbert.py`) using a lightweight DistilBERT encoder.
  3. Write evaluation harness (`ml/classifier/evaluate.py`) benchmarking Macro-F1 ($\ge 0.90$), latency, and RAM footprint.
  4. Export winning model bundle to `ml/artifacts/` (`.joblib`).

---

### 6. Balaji — Database Models, Outbox Pattern & Infrastructure
* **Assigned Folders:** `apps/api/db/`, `infra/`
* **Branch Prefix:** `feat/db-*`, `feat/infra-*`
* **Core Responsibilities:**
  1. Implement PostgreSQL schema tables in `apps/api/db/models.py` (`applications`, `documents`, `jobs`, `audit_events`).
  2. Manage async session pools in `apps/api/db/session.py`.
  3. Implement transactional outbox pattern to atomically commit application status changes and queue events.
  4. Configure rate limiting and token bucket spend guards in API routes.

---

### 7. Akshaya — Frontend Underwriter Reviewer SPA (React + Vite + pdf.js)
* **Assigned Folders:** `apps/ui/`
* **Branch Prefix:** `feat/ui-*`
* **Core Responsibilities:**
  1. Build the underwriter dashboard in React 18, Vite, TypeScript, and Tailwind CSS (`apps/ui/src/App.tsx`).
  2. Implement split-pane layout: original PDF viewer on the left, audit findings & sign-off on the right.
  3. Integrate `pdf.js` to render visual bounding-box highlights using `EvidenceRef` coordinates (`x0, y0, x1, y1`).
  4. Connect action buttons: **Approve**, **Flag Discrepancy**, and **Request Info** to `POST /applications/{id}/review`.
  5. Build chat panel for RAG policy queries against `POST /applications/{id}/questions`.

---

### 8. Sai Mokshith — Hybrid RAG, Policy Knowledge & Grounding QA
* **Assigned Folders:** `core/rag/`, `policies/`, `eval/`
* **Branch Prefix:** `feat/rag-*`, `feat/eval-*`
* **Core Responsibilities:**
  1. Implement token-aware passage chunking (250–400 tokens) in `core/rag/chunking.py` preserving page provenance.
  2. Implement isolated FAISS exact vector index and BM25 lexical search in `core/rag/indexer.py` and `retriever.py`.
  3. Implement Reciprocal Rank Fusion (RRF) to combine dense and lexical scores: $\sum \frac{1}{60 + \text{rank}}$.
  4. Implement strict citation grounding check (`core/rag/grounding.py`) that drops ungrounded claims and abstains if evidence is absent.
  5. Maintain frozen 30-question evaluation set in `eval/questions.json`.

---

## 🛠️ Git Workflow & How to Push Code (Step-by-Step)

Follow this exact guide to avoid merge conflicts and keep our main branch clean and working at all times.

### Step 1: Clone the Repository
```bash
git clone https://github.com/maczeo11/loan-doc-processing-agent.git
cd loan-doc-processing-agent
```

### Step 2: Set Up Local Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Install dependencies and local packages in editable mode
pip install -r requirements.txt
pip install -e .
```

### Step 3: Create Your Feature Branch
**Never write code directly on `main`!** Always create a feature branch using your assigned prefix:

```bash
# Pull latest main first
git checkout main
git pull origin main

# Create and switch to your feature branch
# Example for Jeevan:
git checkout -b feat/ocr-native-parser

# Example for Akshaya:
git checkout -b feat/ui-pdf-viewer

# Example for Sravanthi:
git checkout -b feat/rules-salary-audit
```

### Step 4: Write Your Code Inside Your Assigned Folder
- Only modify files in your assigned directories.
- Look at `core/contracts/` to see the exact input/output shapes for your functions.
- If you need a change to `core/contracts/`, talk to Bhanu before modifying it.

### Step 5: Verify Tests Pass Locally
Before staging or committing, ensure your code doesn't break existing tests:
```bash
pytest
```
*Make sure you see **8 passed** (or more as you add tests)!*

### Step 6: Stage and Commit
Commit your changes using clear, conventional commit messages:
```bash
# Stage only files in your folder
git add core/extraction/
# or
git add apps/ui/

# Commit with a meaningful message
git commit -m "feat(ocr): implement native pdf word extraction using pymupdf"
```

### Step 7: Push Your Branch to GitHub
```bash
git push -u origin <your-branch-name>
# Example:
# git push -u origin feat/ocr-native-parser
```

*(Note for Windows users: If you experience GitHub token conflicts, run `$env:GITHUB_TOKEN = $null` in PowerShell before pushing).*

### Step 8: Open a Pull Request (PR)
1. Go to [https://github.com/maczeo11/loan-doc-processing-agent](https://github.com/maczeo11/loan-doc-processing-agent).
2. Click the **"Compare & pull request"** button for your branch.
3. Set base branch to **`main`**.
4. Title your PR clearly (e.g. `feat(ocr): add PyMuPDF text layer parser`).
5. In the description, list:
   - What you added/changed
   - Confirmation that `pytest` passed locally
6. Assign **Bhanu Teja (`maczeo11`)** as reviewer.
7. Once approved, Bhanu will merge your PR into `main`.

---

## 📂 Complete Repository Layout

```txt
loan-doc-processing-agent/
├── AGENTS.md               # System constitution, non-negotiables & boundaries
├── README.md               # Architecture documentation, team breakdown & onboarding
├── Makefile                # make install, test, lint, demo
├── pyproject.toml          # Editable package definitions (pip install -e .)
├── requirements.txt        # Frozen Python dependencies
├── .env.example            # Environment template
│
├── adapters/               # Hexagonal Ports & Adapters (Interchangeable local/cloud)
│   ├── llm/                # OpenCode Zen (cloud) & local Qwen GGUF (offline)
│   ├── queue/              # Postgres SKIP LOCKED (local) & SQS (cloud)
│   └── storage/            # Local Filesystem (local) & S3 (cloud)
│
├── apps/
│   ├── api/                # FastAPI REST backend & outbox models
│   │   ├── db/             # PostgreSQL session and schema models
│   │   ├── routes/         # applications, documents, review, jobs
│   │   ├── config.py       # Pydantic Settings
│   │   └── main.py         # Entrypoint (serves API & mounts UI)
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

## 🛡️ Non-Negotiable Rules for All Teammates

1. **Deterministic code decides, AI explains, a human approves.** Never use an LLM to calculate totals, compute financial ratios, or make approve/flag decisions.
2. **No fact without an `EvidenceRef`.** If evidence cannot be extracted with page and coordinates, the value is `UNKNOWN`.
3. **`core/` must NEVER import `boto3`, `celery`, or provider SDKs.** All cloud/external dependencies sit behind `adapters/`.
4. **Do NOT touch `core/contracts/` unilaterally.** Any contract modification must be approved by Bhanu.
5. **Never commit secrets or real customer data.** Use `.env` and synthetic dossiers in `data/`.
