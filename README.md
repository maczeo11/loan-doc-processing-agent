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

## ⚡ Quick Start

Runs entirely on your machine — CPU-only OCR, local Postgres queue, no cloud
account and no paid API key required.

**Prerequisites:** Python 3.11, Node 18+, Docker Desktop.

```bash
git clone https://github.com/maczeo11/loan-doc-processing-agent.git
cd loan-doc-processing-agent

python -m venv venv
venv\Scripts\activate          # Windows PowerShell
# source venv/bin/activate     # macOS / Linux

make install                   # pip install -e . + requirements.txt
cp .env.example .env           # defaults are correct for local dev
```

Then launch the stack. On Windows, one command does everything:

```bash
make demo-all                  # scripts/demo-local.ps1 — infra, migrate, api, outbox, worker, ui
```

Or start each piece in its own terminal (any OS):

```bash
make demo-infra                # 1. PostgreSQL + Redis in Docker
make demo-migrate              # 2. alembic upgrade head
make demo-api                  # 3. FastAPI    → http://localhost:8000/docs
make demo-outbox               # 4. outbox dispatcher
make demo-worker               # 5. LangGraph worker (ML inference on host)
make demo-ui                   # 6. Vite dev server → http://localhost:3000
```

Open **http://localhost:3000**. `make demo-stop` tears the containers down.

### Verifying your setup

```bash
make test                      # unit tests
make test-all                  # unit + integration + smoke
make lint                      # ruff + mypy
cd apps/ui && npm run build    # typecheck + production build of the SPA
```

> **Note:** CI (`.github/workflows/ci.yml`) runs `ruff`, the contract gate, and
> `pytest` — it does **not** build the SPA. A UI break reaches `main` with CI
> green, so run the `npm run build` above before merging frontend changes.

---

## 📊 Current Status

State of `main` as of **2026-09-11**. Full detail in
[`docs/implementation_status.md`](docs/implementation_status.md).

| Area | State |
|------|-------|
| Contracts, OCR routing, extraction, LangGraph orchestration, worker/queue | ✅ Working |
| Reviewer SPA (three-pane, evidence overlays, HITL sign-off, PII masking) | ✅ Working |
| Hybrid RAG + grounding gate | ✅ Working |
| **Deterministic rules engine** | ✅ **All 5 rules implemented & verified** |
| **Document viewing end-to-end** | ✅ **Working via streaming API (`GET /{id}/documents/{doc_id}`)** |

All production readiness items in [`AGENTS.md` §9 — Production Readiness](AGENTS.md#9-production-readiness--resolution-status) are **100% resolved and merged**:

1. **`GET /applications/{id}/documents/{doc_id}` is live on `main`.** The SPA streams verified PDF bytes directly to `pdf.js` with SHA-256 integrity verification, falling back gracefully to client-side generation in demo mode.
2. **`RULE-TAX-01` and `RULE-ID-01` are fully implemented** with pure Decimal arithmetic, auto-annualization ($12 \times \text{monthly}$), $10\%$ tolerance, and RapidFuzz token-sorted matching ($\ge 85\%$).
3. **`RULE-BANK-01` verifies bank statement balance arithmetic** with Decimal precision ($Opening + Credits - Debits = Closing$).
4. **All 355 automated tests passing** across unit, integration, and smoke test suites (`pytest`).

---

## 💡 Executive Pitch for Evaluators & Judges

### 🎙️ The 30-Second Elevator Pitch
> **FinScan AI** cuts retail loan document verification from **48 hours to 90 seconds** while completely eliminating GenAI hallucination risks. By enforcing a strict architectural firewall where **deterministic code computes financial math** and **AI only narrates verified findings**, every single number on the screen traces back to an exact pixel-level bounding box on an uploaded page. Underwriters audit verified flags in a split-screen dashboard and sign off in one click.

---

### 🚨 The Problem: The Underwriting Bottleneck & The "GenAI Trap"
- **The Manual Burden:** Retail loan origination requires cross-referencing 5+ disparate document types (payslips, 6-month bank statements with varying formats, ITR-V tax acknowledgements, and KYC cards). Manual underwriting takes 24–72 hours per dossier, is error-prone, and burns costly underwriter hours on basic cross-checking.
- **The GenAI Trap:** Banks cannot deploy off-the-shelf LLMs or "chat-with-your-doc" wrappers to approve loans. LLMs hallucinate numbers, fail basic arithmetic, cannot provide legally binding audit trails, and introduce severe regulatory liability (RBI / Fair Lending compliance).
- **The Core Dilemma:** How can banks automate document verification at GenAI speed *without* risking a single hallucinated number or unauthorized credit decision?

---

### 🛡️ The FinScan AI Solution
FinScan AI solves this by introducing **Provenance-Grounded Deterministic Verification**:
1. **Zero Hallucinated Numbers:** Pure Python rules execute all financial calculations (salary-to-bank credit reconciliation within $5\%$ tolerance, tax-to-salary annualization, DTI limits). The LLM is **never** permitted to calculate totals or assign pass/fail verdicts.
2. **Atomic Evidence Citations:** Every extracted entity carries an `EvidenceRef` containing document ID, page number, and bounding-box coordinates (`x0, y0, x1, y1`). Missing data defaults to `UNKNOWN`, never a guess.
3. **Underwriter-in-the-Loop:** LangGraph unconditionally pauses execution at an `interrupt()` checkpoint, presenting underwriters with visual bounding-box highlights on original PDFs. The human remains the sole decision-maker.

---

### 🏆 Evaluator Scorecard: How FinScan AI Delivers on Hackathon Rubrics

| Evaluation Criteria | How FinScan AI Excels | Where to Inspect |
| :--- | :--- | :--- |
| **System Architecture & Rigor** | Modular monolith with Hexagonal Ports & Adapters; LangGraph stateful orchestration; PostgreSQL transactional outbox. | [`adapters/`](adapters), [`core/graph/`](core/graph) |
| **Safety, Provenance & Compliance** | Zero autonomous lending decisions; strict bounding-box provenance; prompt-injection firewall; grounding validator drops unverified claims; sign-off gated on `READY_FOR_REVIEW` + findings behind a dual-sign challenge. See [Current Status](#-current-status) for which rules are live today. | [`core/contracts/`](core/contracts), [`core/rag/grounding.py`](core/rag/grounding.py), [`docs/frontend_architecture.md`](docs/frontend_architecture.md#human-in-the-loop-consensus--two-step-dual-sign-confirmation) |
| **Cloud & Cost Engineering** | Runs 100% free locally (CPU OCR, Postgres queue, local Qwen GGUF) and deploys on AWS for under $15 total budget ($25 hard ceiling). | [`infra/`](infra), [`AGENTS.md`](AGENTS.md) |
| **Reviewer UX & Productivity** | 3-pane React 18 + Vite dashboard with interactive `pdf.js` canvas highlights, discrepancy badges, and 1-click sign-off. | [`apps/ui/`](apps/ui) |
| **Team Parallelism & CI/CD** | 8 teammates working concurrently across isolated module boundaries, each with an assigned branch prefix and pre-written tests; GitHub Actions gates every PR on ruff, contract integrity, and pytest. | [`README.md#-team-work-breakdown--ownership-8-members`](#-team-work-breakdown--ownership-8-members), [`tests/`](tests), [`.github/workflows/ci.yml`](.github/workflows/ci.yml) |

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

### 🔒 Object Storage & S3 Security Architecture

All document assets (uploaded PDFs, parsed manifests, generated CAM artifacts) are managed through the abstract [`StoragePort`](adapters/storage/base.py) with enterprise banking security defaults:

1. **Server-Side Encryption at Rest (SSE-S3 / SSE-KMS):** Every object written to S3 is encrypted with mandatory `ServerSideEncryption="AES256"` (or AWS KMS). Unencrypted object writes are blocked at both client adapter and S3 bucket policy levels.
2. **Tenant & Dossier Partitioning:** Storage keys strictly follow the canonical hierarchy `dossiers/{application_id}/{document_id}_{sanitized_filename}` via `build_storage_key()`. The storage adapter strictly validates that operations cannot escape or manipulate path prefixes.
3. **Path Traversal & Filename Sanitization:** Input filenames are stripped of directory traversal sequences (`../`, `..\\`) and sanitized into safe alphanumeric ASCII strings before key creation.
4. **Short-Lived Cryptographic Presigned URLs:** Neither the browser frontend nor external consumers ever get direct public access to S3 buckets. Document rendering in `pdf.js` uses time-bounded presigned GET URLs (TTL 15–60 min).
5. **Zero Public Access:** AWS S3 Block Public Access is enabled across all 4 controls (bucket and account levels).

---

## 👥 Team Work Breakdown & Ownership (8 Members)

| Member | Owns |
| :--- | :--- |
| **1. Manjunath** | API contracts and generated client, integration, CI, release checklist and demo. Keeps the evaluation harness. |
| **2. Bhanu Teja** | LangGraph worker — leases, pause/resume, recovery. Designs the SQS + DLQ and S3 layout. Model serving inside the worker. **Lead:** architecture, gate calls, viva. |
| **3. Jeevan** | PDF text with coordinates, OCR routing, evidence extraction and page-span validation. |
| **4. Sravanthi** | Synthetic dossier generator with ground truth, plus the deterministic rules — completeness, salary, tax and bank arithmetic. |
| **5. Karthik** | Classifier training (baseline vs. encoder) on the local GPU, splits and evaluation, MLflow, release bundle. |
| **6. Balaji** | FastAPI, PostgreSQL/outbox. **Host cloud:** EC2, Caddy HTTPS, Compose, provisions SQS/S3/IAM, stop-start and teardown. Bundle rollback and version stamping. |
| **7. Akshaya** | Reviewer SPA — three-pane dashboard, evidence overlays, corrections, PDF/JSON export. |
| **8. Sai Mokshith** | Hybrid RAG with citation checks, injection guardrails, the 30-question set, integrated QA. |

---

### 1. Manjunath — Contracts, API Client, Integration & Evaluation Harness
* **Assigned Folders:** `core/contracts/`, `tests/`, `.github/workflows/` (CI), generated API client
* **Branch Prefix:** `feat/contracts-*`, `feat/ci-*`, `feat/integration-*`
* **Core Responsibilities:**
  1. API contracts single source of truth in `core/contracts/` (`evidence.py`, `facts.py`, `findings.py`, `state.py`).
  2. Generate typed API client from OpenAPI schema (no handwritten fetch calls).
  3. Continuous Integration (CI) configuration, test automation pipelines, and regression gates.
  4. Keeps and runs the evaluation harness against frozen benchmarks.
  5. Coordinates release checklist and demo rehearsal.

---

### 2. Bhanu Teja — Team Lead, LangGraph Agent Core & Async Worker
* **Assigned Folders:** `core/graph/`, `worker/`, `adapters/` (storage, queue, llm), root architecture (`AGENTS.md`, `Makefile`, `pyproject.toml`)
* **Branch Prefix:** `feat/graph-*`, `feat/worker-*`, `feat/cloud-*`
* **Core Responsibilities:**
  1. **LangGraph Worker Core:** StateGraph workflow (`core/graph/workflow.py`, `nodes.py`), state transitions, and `interrupt()` human-review checkpoints.
  2. **Worker Resilience:** Consumer loop (`worker/consumer.py`, `main.py`) with atomic leases, acknowledge-last commits, recovery, and DLQ handling.
  3. **Cloud & Async Design:** Architecture of SQS + DLQ and S3 layout behind clean adapter interfaces.
  4. **Model Serving:** Local model serving fallback (Qwen GGUF) inside the worker runtime.
  5. **Team Leadership:** System architecture, code review / gating calls for all PRs, and viva defense.

---

### 3. Jeevan — PDF Text Extraction, OCR Routing & Evidence Extraction
* **Assigned Folders:** `core/extraction/`
* **Branch Prefix:** `feat/ocr-*`, `feat/extract-*`
* **Core Responsibilities:**
  1. PDF text extraction with exact word coordinates using PyMuPDF (`core/extraction/native_parser.py`).
  2. Local CPU PaddleOCR fallback (`core/extraction/paddle_parser.py`) for scanned documents.
  3. Dynamic OCR routing (`core/extraction/router.py`) prioritizing native text $\rightarrow$ PaddleOCR $\rightarrow$ capped Textract fallback.
  4. Structured fact extractors in `core/extraction/extractors/` (`payslip.py`, `bank_statement.py`, `tax_return.py`, `id_card.py`).
  5. Page-span and bounding-box validation ensuring **no fact is accepted without an `EvidenceRef`**.

---

### 4. Sravanthi — Synthetic Dossiers, Ground Truth & Deterministic Rules
* **Assigned Folders:** `scripts/generate_dossiers.py`, `data/`, `core/rules/`, `core/reporting/`
* **Branch Prefix:** `feat/rules-*`, `feat/data-*`, `feat/reporting-*`
* **Core Responsibilities:**
  1. Synthetic loan dossier generator with ground truth manifests and deliberate inconsistency injection (`scripts/generate_dossiers.py`, `data/synthetic_dossiers/`).
  2. **Deterministic Rules Engine (`core/rules/`):**
     - `completeness.py`: Verify presence of all required documents in dossier.
     - `salary_audit.py`: Reconcile payslip net salary against verified bank payroll deposits ($\le 5\%$ tolerance).
     - `tax_audit.py`: Cross-check tax return gross income against payslip annualized figures.
     - `identity.py`: Fuzzy-match PAN and applicant names across all documents.
  3. Credit Appraisal Memo (CAM) builder and narrative assembly in `core/reporting/memo_builder.py`.

---

### 5. Karthik — Document Classifier ML, Splits, MLflow & Release Bundle
* **Assigned Folders:** `ml/`
* **Branch Prefix:** `feat/ml-*`, `feat/classifier-*`
* **Core Responsibilities:**
  1. Train document classifier baseline on local GPU: TF-IDF + Logistic Regression (`ml/classifier/baseline_tfidf.py`).
  2. Train challenger model: DistilBERT-class sequence encoder (`ml/classifier/challenger_distilbert.py`, seq 256, batch 2–4).
  3. Dataset splits and frozen manifest evaluation (`ml/classifier/evaluate.py`).
  4. Track experiments with MLflow, benchmark Macro-F1 ($\ge 0.90$) vs latency vs RAM footprint.
  5. Package and serialize winning release bundle into `ml/artifacts/` (`.joblib`).

---

### 6. Balaji — FastAPI Backend, PostgreSQL Outbox & Host Cloud Infrastructure
* **Assigned Folders:** `apps/api/`, `infra/`
* **Branch Prefix:** `feat/api-*`, `feat/db-*`, `feat/infra-*`
* **Core Responsibilities:**
  1. Build FastAPI REST endpoints (`apps/api/main.py`, `routes/applications.py`, `documents.py`, `review.py`).
  2. PostgreSQL schema, migrations, and transactional outbox table (`apps/api/db/models.py`, `session.py`).
  3. Atomic Redis token buckets, rate limiting, and spend guards.
  4. **Host Cloud Operations:** EC2 t4g provisioning, Caddy HTTPS reverse proxy (`infra/Caddyfile`), Docker Compose (`infra/docker-compose.yml`), SQS/S3/IAM setup, scheduled stop-start, teardown, bundle rollback, and version stamping.

---

### 7. Akshaya — Reviewer SPA (React + Vite + pdf.js)
* **Assigned Folders:** `apps/ui/`, `core/reporting/exporter.py`
* **Branch Prefix:** `feat/ui-*`
* **Core Responsibilities:**
  1. Build underwriter reviewer SPA using React 18, Vite, TypeScript, and Tailwind CSS (`apps/ui/`).
  2. Three-pane dashboard: dossier document index, center PDF viewer, and right audit findings & actions.
  3. Visual evidence bounding-box overlays on PDF pages using `pdf.js` and `EvidenceRef` coordinates.
  4. HITL corrections, question-answering chat panel, and human sign-off triggers (`POST /applications/{id}/review`).
  5. PDF and JSON dossier audit export download integration.

---

### 8. Sai Mokshith — Hybrid RAG, Citation Checks, Injection Guardrails & QA
* **Assigned Folders:** `core/rag/`, `policies/`, `eval/`
* **Branch Prefix:** `feat/rag-*`, `feat/eval-*`
* **Core Responsibilities:**
  1. Passage chunking (250–400 tokens) with strict metadata provenance (`core/rag/chunking.py`).
  2. Isolated FAISS exact index and BM25 lexical search fused with Reciprocal Rank Fusion (RRF) (`core/rag/retriever.py`, `indexer.py`).
  3. Hard index isolation: application documents vs authoritative policy library (`policies/`).
  4. Citation grounding validator (`core/rag/grounding.py`): verify all claims cite retrieved chunks from authorized dossiers; drop ungrounded claims.
  5. Prompt injection guardrails on untrusted PDF inputs.
  6. Maintain and run the frozen 30-question benchmark set (`eval/questions.json`, 18 dev / 12 held-out) for integrated QA.

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
├── docs/                   # Architecture references (see Documentation Map below)
│
├── audit/                  # Immutable audit-event records
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

## 📚 Documentation Map

Start with [`AGENTS.md`](AGENTS.md) — it is the system constitution and
overrides anything here if the two disagree.

| Document | Read it when you need to… |
|----------|---------------------------|
| [`AGENTS.md`](AGENTS.md) | Know the non-negotiables, module boundaries, and your ownership |
| [`docs/system_overview.md`](docs/system_overview.md) | Get the 10,000-ft view before touching anything |
| [`docs/architecture.md`](docs/architecture.md) | Understand ports/adapters and the module graph |
| [`docs/implementation_status.md`](docs/implementation_status.md) | **See what actually works today vs. what is a stub** |
| [`docs/langgraph_workflow.md`](docs/langgraph_workflow.md) | Add or reorder a pipeline node, or touch `interrupt()` |
| [`docs/worker_queue_architecture.md`](docs/worker_queue_architecture.md) | Work on leases, DLQ, idempotency, or commit-before-ack |
| [`docs/data_flow_diagrams.md`](docs/data_flow_diagrams.md) | Trace a document from upload to signed decision |
| [`docs/frontend_architecture.md`](docs/frontend_architecture.md) | Change the SPA — **read the design-token and regression-watchlist sections first** |
| [`docs/classifier_selection.md`](docs/classifier_selection.md), [`docs/classifier_handoff.md`](docs/classifier_handoff.md) | Work on document classification or swap the model |
| [`docs/security_architecture.md`](docs/security_architecture.md), [`docs/security_report.md`](docs/security_report.md) | Touch auth, storage keys, PII, or prompt-injection defences |
| [`docs/deployment_guide.md`](docs/deployment_guide.md) | Deploy to AWS or debug the container stack |

---

## 🛡️ Non-Negotiable Rules for All Teammates

1. **Deterministic code decides, AI explains, a human approves.** Never use an LLM to calculate totals, compute financial ratios, or make approve/flag decisions.
2. **No fact without an `EvidenceRef`.** If evidence cannot be extracted with page and coordinates, the value is `UNKNOWN`.
3. **`core/` must NEVER import `boto3`, `celery`, or provider SDKs.** All cloud/external dependencies sit behind `adapters/`.
4. **Do NOT touch `core/contracts/` unilaterally.** Any contract modification must be approved by Bhanu.
5. **Never commit secrets or real customer data.** Use `.env` and synthetic dossiers in `data/`.
