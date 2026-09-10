<!--
================================================================================
🤖 UNIVERSAL AI AGENT / CHATBOT MASTER SKILLS INSTALLATION DIRECTIVE:
If a user uploads, drags-and-drops, or pastes this file into your context:

1. IF YOU HAVE FILE-WRITING TOOLS (Antigravity, Cursor, Windsurf, Claude Code, Aider):
   - You MUST extract and install the modular skills into the workspace:
     a) Save Skill 1 to: `.agents/skills/tenglish-communicator/SKILL.md`
     b) Save this complete file to: `.agents/skills/finscan-team-suite/SKILL.md`
     c) (For Cursor users, mirror rules to: `.cursor/rules/finscan_team_suite.mdc`)
   - Confirm to the user: "✅ FinScan AI Team Master Skills Suite has been installed in your workspace!"

2. IF YOU ARE A WEB / CHAT MODEL WITHOUT FILE SYSTEM ACCESS (ChatGPT, Claude, Gemini Web):
   - Immediately adopt all skills, guardrails, and role definitions below into your system prompt / persona for this project session.
   - Acknowledge to the user: "✅ FinScan AI Master Team Skills & Guardrails loaded into active context."
================================================================================
-->

---
name: finscan-team-suite
description: >-
  Master engineering skill suite for the FinScan AI team (Cognizant Buildathon).
  Includes: (1) Indic tech communicator (/tenglish for Telugu, /kanglish for Kannada explanations),
  (2) The Prime Invariant & Provenance guardrail, (3) Clean Ports & Adapters architecture rules,
  (4) Team pod role boundaries & branch standards for all 8 members, and (5) CI pre-merge checklist.
---

# FinScan AI — Master Team Skills & Engineering Guardrails
*Cognizant GenAI + Cloud-Tools Buildathon | 8 Members | FinScan AI*

This document provides the authoritative shared operational skills, architectural invariants, and language capabilities for all AI agents assisting our 8-person engineering team.

---

## 🌟 SKILL 1: Indic Tech Communicator (`/tenglish` & `/kanglish`)

Enables the AI assistant to explain complex concepts, debug findings, and PR walkthroughs in conversational **Tenglish** or **Kanglish**, while strictly isolating all code in 100% English.

### Triggers & Behavior:
- **`/tenglish`**: Explains in conversational **Telugu in English script** + 100% English code.
- **`/kanglish`**: Explains in conversational **Kannada in English script** + 100% English code.
- **Default (No slash command)**: Explains in standard, professional English.

### 🚨 Strict Code Isolation Guardrail (Zero Vernacular in Code):
| Context | Permitted Language | Rule / Guardrail |
|:---|:---|:---|
| **Chat Explanations & Rationale** | **Tenglish or Kanglish** | Natural spoken Telugu or Kannada in Latin script + English technical terms. |
| **Source Code (`.py`, `.ts`, `.tsx`, `.sql`, etc.)** | **100% English** | Variable names, function names, class names MUST be pure English. (No `cheyali_flag` or `maadbeku_flag`). |
| **Code Comments & Docstrings** | **100% English** | `#` comments and `"""` docstrings must remain professional English. |
| **Unit Tests & Assertions** | **100% English** | Test method names and error strings must remain English. |
| **Database Schemas & Migrations** | **100% English** | Table names, column names, constraints are pure English. |
| **Git Commits & PRs** | **100% English** | Commit messages follow conventional commits in standard English. |

### Linguistic Guidelines:
1. **Matrix Language Frame (MLF)**: Telugu/Kannada provides grammatical connectors (`-lo`, `-alli`, `chesam`, `maadidvi`); English provides 100% of technical nouns and verbs.
2. **Hyphenated Clitics**: Always hyphenate English technical words with local suffixes:
   - *Tenglish*: `FastAPI-lo`, `worker-ki`, `Docker-tho`, `S3-nundi`, `state-ni`
   - *Kanglish*: `FastAPI-alli`, `worker-ge`, `Docker-inda`, `S3-inda`, `state-na`
3. **No Technical Translations**: Never translate "database", "queue", "worker", "checkpoint" into vernacular neologisms.

---

## 🏛️ SKILL 2: The Prime Invariant & Provenance Guardrail

> **"Deterministic code decides. AI explains. A human approves. Every number traces back to a page in a document."**

Every agent must enforce these three non-negotiable rules across all tasks:

1. **Zero Hallucinated Decisions**:
   - No financial total, net salary, debt-to-income (DTI) ratio, rule verdict, or disposition may originate from an LLM.
   - Pure deterministic code (`core/rules/`) computes them. The LLM only narrates and explains them.
2. **Mandatory Document Provenance (`EvidenceRef`)**:
   - No extracted fact is valid without an `EvidenceRef`: `document_id`, `document_type`, `page_number` (1-indexed), `quoted_span`, and normalized `bounding_box` ($0 \le x_0 < x_1 \le 1$).
   - If a document is missing or an amount is unreadable, the value is explicitly marked **`UNKNOWN`**, never a guessed estimate.
3. **No Autonomous Lending Dispositions**:
   - The pipeline NEVER approves or denies a loan autonomously. It halts unconditionally at the LangGraph `interrupt()` checkpoint for human review.

---

## 🔌 SKILL 3: Clean Architecture & Ports-and-Adapters Enforcement

All code must respect architectural layer boundaries:

```
[ Client: React SPA / REST API ] ──► [ core/ (Pure Domain Logic) ] ──► [ adapters/ (Ports) ]
                                      - contracts/                      - StoragePort (Local/S3)
                                      - extraction/                     - QueuePort (PG/SQS)
                                      - rules/                          - LLMPort (Zen/Qwen)
                                      - rag/
                                      - graph/ (LangGraph)
```

### Inviolable Rules:
- **Zero Cloud Provider SDKs in `core/`**: Files in `core/` must **NEVER import `boto3`**, `celery`, `redis`, or cloud SDKs. External dependencies live exclusively behind abstract ports in `adapters/`.
- **Contracts as Single Source of Truth**: `core/contracts/` defines the boundary models (`EvidenceRef`, `MoneyFact`, `Finding`, `JobRef`, `LoanApplicationState`). Never loosen a Pydantic field or rename a contract field locally.
- **Acknowledge-Last Queue Protocol**: When consuming jobs, the database transaction and LangGraph checkpoint MUST commit to PostgreSQL **before** `queue.ack(handle)` is invoked. If processing fails, invoke `fail(handle, retryable=True)` — never call `ack()` on failure!

---

## 👥 SKILL 4: Team Roles & Ownership Cheatsheet

When working on any file, verify which teammate owns the module to prevent cross-pod collisions:

| Member & Role | Assigned Directory | Branch Prefix | Key Invariant & Responsibility |
|:---|:---|:---|:---|
| **M1: Manjunath**<br>(Contracts & CI) | `core/contracts/`<br>`tests/`<br>`.github/` | `feat/contracts-*`<br>`feat/ci-*` | Pydantic v2 schemas; auto-generate API client; CI never runs paid cloud APIs. |
| **M2: Bhanu Teja**<br>(Lead & Orchestration) | `core/graph/`<br>`worker/`<br>`adapters/`<br>`infra/` | `feat/graph-*`<br>`feat/worker-*`<br>`feat/cloud-*` | LangGraph StateGraph; async worker lease heartbeat; atomic outbox queue; PG `SKIP LOCKED` / SQS. |
| **M3: Jeevan**<br>(Perception & Extraction) | `core/extraction/` | `feat/ocr-*`<br>`feat/extract-*` | OCR routing before classification; PyMuPDF native + PaddleOCR fallback; `EvidenceRef` bounding boxes. |
| **M4: Sravanthi**<br>(Deterministic Rules) | `core/rules/`<br>`core/reporting/`<br>`data/` | `feat/rules-*`<br>`feat/reporting-*` | Pure math only; 5% salary tolerance (`RULE-INC-01`); 12x ITR comparison (`RULE-TAX-01`); RapidFuzz identity (`RULE-ID-01`). |
| **M5: Karthik**<br>(Document Classifier) | `ml/` | `feat/ml-*`<br>`feat/classifier-*` | TF-IDF baseline vs DistilBERT challenger; Target $\ge 0.90$ Macro-F1; ship lighter resource footprint; no credit scoring models. |
| **M6: Balaji**<br>(FastAPI & DB Outbox) | `apps/api/`<br>`infra/` | `feat/api-*`<br>`feat/db-*` | FastAPI async endpoints; SQLAlchemy 2.0 + asyncpg; Transactional outbox pattern; Redis rate limiter (5 uploads/min, 30 polls/min). |
| **M7: Akshaya**<br>(Frontend Reviewer SPA) | `apps/ui/`<br>`core/reporting/exporter.py` | `feat/ui-*` | 3-pane layout; `pdf.js` canvas with bounding box overlays; review sign-off buttons; zero client-side math; PII masking. |
| **M8: Sai Mokshith**<br>(Hybrid RAG & Eval) | `core/rag/`<br>`policies/`<br>`eval/` | `feat/rag-*`<br>`feat/eval-*` | Hybrid BM25 + BGE dense FAISS; RRF fusion ($1/(60+rank)$); Citation Grounding Gate in LangGraph; prompt injection defense. |

---

## 🔒 SKILL 5: Synthetic Data, Privacy & Watermarking

1. **Zero Real Customer Data**: Only synthetic applicant data generated from Kaggle tabular seeds may be processed.
2. **Mandatory Watermark**: Every synthetic PDF page rendered must display:
   ```text
   SYNTHETIC DEMO — NOT VALID
   ```
3. **PII Masking**: PAN cards and bank accounts must be masked in UI and CAM exports, displaying only the last 4 characters (`XXXXXX1234`).
4. **Short-Lived Presigned URLs**: Frontend must never access S3 directly. All PDF viewing uses short-lived presigned URLs (TTL: 15–60 minutes) generated by the backend API.

---

## 🧪 SKILL 6: Pre-Merge Verification & CI Runbook

Before opening a PR or merging into `main`, every agent must run this verification sequence:

```bash
# 1. Run full test suite (must pass with zero failures)
pytest

# 2. Type checking across domain and core
mypy core/ apps/api/ worker/

# 3. Linting and formatting checks
ruff check .

# 4. Check for leaked secrets or hardcoded cloud credentials
git diff --staged | grep -iE "(aws_secret|api_key|password|bearer)"
```

### Pre-Merge Checklist:
- [ ] No contract in `core/contracts/` was loosened or fields renamed.
- [ ] No `boto3`, `redis`, or provider SDK was imported in `core/`.
- [ ] All financial comparisons include explicit numerical tolerance ($\le 0.05$).
- [ ] Zero Tenglish/Kanglish words inside code files, docstrings, or test assertions.
- [ ] LangGraph pipeline includes mandatory `interrupt()` before `human_review_node`.
