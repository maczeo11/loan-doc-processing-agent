# 🏦 FinScan AI: GenAI-Enabled Loan Document Processing & Underwriting Agent

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_Core-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![LightGBM](https://img.shields.io/badge/LightGBM-Tabular_ML-brightgreen.svg)](https://lightgbm.readthedocs.io/)
[![Langfuse](https://img.shields.io/badge/Langfuse-LLMOps_Tracing-purple.svg)](https://langfuse.com/)
[![Notion Documentation](https://img.shields.io/badge/Notion-Live_Project_Doc-black.svg)](https://app.notion.com/p/Loan-Document-Processing-Agent-Master-Architecture-1-Week-Project-Plan-3d490e25dc1b818ab96dea600d6d8e87)

> **Cognizant Hackathon / Buildathon Project**  
> **Team:** 8 Members | **Lead:** Technical Team Lead (Bhanu) | **Timeline:** 1 Week (7 Days)  
> **Live Notion Workspace:** [FinScan AI Master Architecture & Sprint Board](https://app.notion.com/p/Loan-Document-Processing-Agent-Master-Architecture-1-Week-Project-Plan-3d490e25dc1b818ab96dea600d6d8e87)

---

## 📖 Overview

Banks receive vast volumes of unstructured loan documents (payslips, multi-page bank statements, ITR returns, and KYC proofs). Manual underwriting is error-prone, takes 24–72 hours, and is vulnerable to fraud.

**FinScan AI** is an autonomous multi-agent document processing and credit underwriting system that:
1. **Parses & Extracts** key financial entities via hybrid Azure Document Intelligence + local PaddleOCR.
2. **Identifies Missing Documents** in applicant dossiers automatically.
3. **Cross-Reconciles & Detects Inconsistencies** (e.g., stated salary vs. bank payroll credits vs. ITR income).
4. **Combines Tabular ML with GenAI**: Evaluates creditworthiness using a **LightGBM model** trained on the Kaggle *Loan Approval Prediction Dataset*, explained via **SHAP values**, alongside an LLM-synthesized **Credit Appraisal Memo (CAM)**.
5. **Provides a Human-in-the-Loop (HITL) Dashboard** with visual bounding-box citations, discrepancy alerts, and one-click approvals.

---

## 🏛️ System Architecture

```
[ Applicant / Loan Officer ]
             │ (Upload Dossier: Payslip, Bank Stmt, ITR, KYC)
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. INGESTION & DOCUMENT TRIAGE LAYER                        │
│    • FastAPI Async Endpoint • SHA-256 Deduplication         │
│    • File Type Routing (PDF, PNG, JPG) • S3 Storage         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. PERCEPTION & HYBRID EXTRACTION ENGINE                    │
│    • Azure Document Intelligence (Prebuilt Layout & IDs)    │
│    • Local PaddleOCR / PyMuPDF (Fast Table & Text Fallback) │
│    • Multimodal VLM (GPT-4o-mini / Bedrock Claude 3 Haiku)  │
│    • Pydantic Strict JSON Schema Validation                 │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. AGENTIC ORCHESTRATION CORE (LangGraph StateGraph)        │
│    ├─ Triage & Completeness Checker Node                    │
│    ├─ Parallel Specialized Extractor Nodes (Payslip, Bank)  │
│    ├─ Cross-Document Reconciliation & Math Audit Node       │
│    ├─ Fraud & Tampering Heuristic Node                      │
│    ├─ Tabular ML Scoring Node (LightGBM + SHAP Attribution) │
│    └─ Credit Appraisal Memo Synthesis Node                  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. HUMAN-IN-THE-LOOP (HITL) DECISION & AUDIT LAYER          │
│    • LangGraph Checkpointer & Breakpoints (interrupt_before)│
│    • Underwriter Streamlit Dashboard                        │
│    • Visual Bounding-Box Citations & Discrepancy Flags      │
│    • One-Click Approval / Override / PDF Export             │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. OBSERVABILITY & LLMOps INFRASTRUCTURE                    │
│    • Langfuse Tracing (Latency, Cost, Prompt Versions)      │
│    • MLflow Model Registry & Artifact Store                 │
│    • Ragas / DeepEval Benchmark Test Harness                │
└─────────────────────────────────────────────────────────────┘
```

---

## 💻 Compute & Infrastructure Strategy

| Infrastructure | Allocated Workload | Cost / Free Tier Allocation |
| :--- | :--- | :--- |
| **Local Workstation**<br>*(RTX 3050 6GB, 16GB RAM, Ryzen 7)* | • Rapid development & LightGBM tabular model training (3 sec).<br>• Local PaddleOCR processing.<br>• **Ollama Edge Fallback** (`qwen2.5:7b-instruct` / `llama3.2:3b` in ~4GB VRAM) for offline banking demo. | **$0.00** |
| **Azure for Students**<br>*($100 Credit + Free Tier)* | • **Azure Document Intelligence** (500 free pages/month).<br>• **Azure App Service / Container Apps** for hosting the public Streamlit UI. | **$0.00** |
| **AWS Cloud**<br>*($100 Credits + Free Tier)* | • **AWS S3**: Document vault for encrypted PDFs and JSON schemas.<br>• **AWS Bedrock**: Claude 3 Haiku (extraction) & Claude 3.5 Sonnet (CAM synthesis).<br>• **EC2 t3.medium**: FastAPI backend & Langfuse Docker. | **~$15.00**<br>(Leaves $85 buffer) |

---

## 👥 Team Work Breakdown Structure (8 Members)

| Pod | Role | Owner | Core Deliverables |
| :--- | :--- | :--- | :--- |
| **Leadership** | Lead Architect & Integration | **Member 1 (You)** | Architecture design, Pydantic contracts, code reviews, pitch deck & demo. |
| **Agent Core** | LangGraph Agent Engineer | **Member 2** | StateGraph, extraction nodes, conditional routing, HITL breakpoints. |
| **Vision/OCR** | Document Parsing & OCR | **Member 3** | Azure Document Intelligence client, PaddleOCR fallback, table parsing. |
| **Logic & Rules** | Reconciliation & Fraud Engine | **Member 4** | Cross-doc fuzzy matching, salary vs bank audit, anomaly detection. |
| **Tabular ML** | Credit Scoring & SHAP | **Member 5** | Kaggle dataset preprocessing, LightGBM training, SHAP attribution. |
| **Backend/DB** | FastAPI Backend & Storage | **Member 6** | REST endpoints (`/upload`, `/process`, `/review`), AWS S3, SQLite/Postgres. |
| **Frontend UI** | Streamlit UI/UX Engineer | **Member 7** | Multi-tab dashboard, PDF viewer, discrepancy cards, SHAP plots. |
| **LLMOps/CI** | MLOps & Evaluation | **Member 8** | Langfuse tracing, Ragas test harness, Docker compose, cloud deployment. |

---

## 📅 1-Week Sprint Schedule

- **Day 1:** System contracts, GitHub repo setup, generate 25 synthetic applicant dossiers with injected fraud cases.
- **Day 2:** Baseline OCR extraction working; LightGBM model trained on Kaggle dataset (>95% ROC-AUC).
- **Day 3:** LangGraph StateGraph operational; cross-document salary vs bank reconciliation implemented.
- **Day 4:** End-to-end localhost pipeline: Upload ➡️ Parse ➡️ Cross-Reconcile ➡️ ML Approval Score + SHAP.
- **Day 5:** Human-in-the-Loop breakpoint (`interrupt_before`), Credit Memo PDF export, and Ragas accuracy benchmark.
- **Day 6:** Cloud deployment (AWS S3 + Azure App Service) + RTX 3050 edge mode verification.
- **Day 7:** Code freeze, pitch deck finalization, 5-minute live demo rehearsal.

---

## 🚀 Quick Start (Local Setup)

```bash
# 1. Clone repository
git clone https://github.com/maczeo11/loan-doc-processing-agent.git
cd loan-doc-processing-agent

# 2. Setup virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Fill in Azure Document Intelligence, AWS Bedrock / OpenAI, and Langfuse keys

# 5. Generate synthetic loan dossiers
python scripts/generate_dossiers.py

# 6. Train Kaggle Tabular Credit Model
python ml/train_credit_model.py

# 7. Start FastAPI Backend
uvicorn app.main:app --reload --port 8000

# 8. Start Streamlit UI
streamlit run frontend/app.py
```
