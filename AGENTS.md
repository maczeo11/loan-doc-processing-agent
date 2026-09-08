# AGENTS.md — FinScan AI

Loan Document Processing Agent. Cognizant GenAI + cloud-tools buildathon. 8 people, 7 days.

Read this file fully before writing code. If a change would contradict anything here, stop and ask the integrator (Bhanu) instead of improvising.

---

## 1. What this system does

A reviewer uploads a loan dossier (application form, payslip, bank statement, tax acknowledgement, ID proof). The system extracts fields with page-level evidence, flags missing documents and inconsistencies with deterministic code, generates a cited summary with an LLM, and pauses for a human to correct and sign off.

**The one rule that explains the whole design:**

> Deterministic code decides. AI explains. A human approves. Every number traces back to a page in a document.

Corollaries you must never violate:

- No total, disposition, pass/flag verdict or monetary value may originate from LLM output. Rules compute them; the LLM only narrates them.
- No extracted fact is accepted without an `EvidenceRef`. If evidence is missing, the value is `UNKNOWN`.
- The system never approves or denies a loan. It prepares a case for a human.

---

## 2. Tech stack (fixed — do not substitute)

| Layer | Choice |
| --- | --- |
| API | FastAPI + Pydantic v2 + Uvicorn |
| Orchestration | LangGraph, PostgreSQL checkpointer, `interrupt()` for human review |
| UI | React + Vite + TypeScript + Tailwind, built to static files, served by FastAPI same-origin |
| Datastore | PostgreSQL (authoritative), Redis (transient only) |
| Queue | SQS + DLQ in cloud mode, PostgreSQL table in local mode, behind one adapter |
| Objects | S3 (cloud) / local filesystem, behind one adapter |
| Documents | PyMuPDF native text first, PaddleOCR CPU second, AWS Textract third (off by default) |
| Retrieval | BM25 lexical + `BAAI/bge-small-en-v1.5` with FAISS exact, fused with RRF |
| Generation | OpenCode Zen (OpenAI-compatible), local Qwen3-4B Q4 GGUF for offline mode |
| Trained models | TF-IDF + logistic regression baseline vs. DistilBERT-class encoder challenger |

Do not introduce: Kubernetes, Kafka, Celery, MongoDB, Next.js, SSR, Redux, a component library, a second cloud, or a GPU cloud instance. If you think you need one, ask first.

---

## 3. Repository layout

```txt
finscan/
  apps/api/          FastAPI app; also serves the built UI
  apps/ui/           React + Vite + TypeScript reviewer SPA
  worker/            SQS/Postgres consumer driving the LangGraph graph
  core/contracts/    Pydantic models — the shared truth. Change carefully.
  core/extraction/   Parsing, OCR routing, field extraction, evidence capture
  core/rules/        Completeness + reconciliation. HUMAN-ONLY ZONE.
  core/rag/          Chunking, indexing, hybrid retrieval, grounding validation
  core/graph/        LangGraph nodes. Must not import boto3 or any SDK.
  core/reporting/    Summary assembly, PDF/JSON export
  ml/                Training scripts, evaluation, release bundle
  policies/          Versioned policy corpus
  data/manifests/    Dataset split manifests
  eval/              Frozen evaluation sets and harness
  tests/
  infra/             Docker Compose, deploy scripts
  docs/
```

---

## 4. Ports and adapters

Every external dependency sits behind a config-selected adapter so the same graph runs locally and on AWS: object storage, queue, OCR, embeddings, generation, telemetry.

**Rule:** `core/` must never import `boto3`, `celery`, or any provider SDK. If `core/graph/` imports a vendor SDK, the boundary is already broken.

Queue port — keep it to these five methods:

```py
publish(job_ref) -> None
receive(max_n) -> list[Delivery]      # Delivery carries an opaque lease handle
extend_lease(handle, seconds) -> None
ack(handle) -> None
fail(handle, retryable: bool) -> None
```

Semantics belong to the port, not the adapter: **delivery is at-least-once, handlers must be idempotent, results commit before ack.**

**Deliberately NOT a port:** PostgreSQL. We depend on `SELECT ... FOR UPDATE SKIP LOCKED`, row locks, transactional outbox commits and the LangGraph Postgres checkpointer. Do not abstract these behind a generic repository interface. `core/rules/` has no ports at all — pure functions over contracts.

---

## 5. Contracts

`core/contracts/` is the shared truth. Never redefine a model locally, never rename a field, never loosen a type to make a test pass. Changes go through the integrator and land in one PR that updates every consumer.

Core shapes:

- `EvidenceRef` — document id, page number, quoted span text, bounding box. Every fact carries one.
- `MoneyFact` — amount, currency, period, gross-or-net, source `EvidenceRef`.
- `Finding` — rule id, verdict (`pass` / `flag` / `unknown`), human-readable reason, supporting evidence.

`unknown` is a first-class verdict. Values that genuinely cannot be compared must return `unknown`, never a guessed `pass`.

Application states: `UPLOADED`, `QUEUED`, `PROCESSING`, `READY_FOR_REVIEW`, `NEEDS_INFORMATION`, `REVIEWED`, `FAILED`, `CANCELLED`. Only these. Transitions are recorded, not overwritten.

---

## 6. API surface

Freeze the OpenAPI schema before generating anything from it. The SPA calls only these endpoints — never the database, never S3 directly (downloads use short-lived signed URLs issued by the API).

```txt
POST /applications
POST /applications/{id}/documents
POST /applications/{id}/process
GET  /jobs/{id}
POST /jobs/{id}/cancel
GET  /applications/{id}
POST /applications/{id}/questions
POST /applications/{id}/review
GET  /applications/{id}/export
```

Submission returns `202 Accepted` with a job id. Never block a request on processing.

---

## 7. Reliability controls (do not weaken)

1. **Idempotency** — request key scoped to user + body hash. Submitting twice yields one job.
2. **Transactional outbox** — job row and queue event commit in the same transaction.
3. **Worker leases + acknowledge-last** — atomic claim with an attempt token; results commit before the message is deleted.
4. **Rate limits and spend guards** — atomic Redis token buckets per reviewer; budget reserved in PostgreSQL before any paid call; `429` with `Retry-After`.
5. **Bounded retries + DLQ** — backoff with jitter on 429/5xx, three-delivery ceiling, DLQ alarm, reconciler so no job sits in `PROCESSING` forever.

Starting quotas: 2 active jobs per user, 5 submissions/min, 30 status polls/min, 10 MB per file, 30 pages per application, 1 worker.

One retry policy, ever. Do not add a framework that brings its own.

---

## 8. Pipeline order

Upload and validate → **OCR routing** → classify → extract with evidence → validate → rules → retrieve → generate summary → grounding check → checkpoint and pause for human.

**OCR routing happens before classification** — a scanned page has no text for the classifier to read yet. Route by page properties, not by document type:

1. Native text layer present → PyMuPDF text plus exact word coordinates. Preferred; most of our PDFs are self-generated.
2. No usable text layer → PaddleOCR on CPU (Tesseract as packaging fallback).
3. AWS Textract — **off by default**, hard-capped under 100 pages in code, only to demonstrate a managed-cloud OCR path. Never enable `FORMS` broadly.

Never train an OCR model.

---

## 9. RAG rules

Hybrid retrieval with grounding validation. Not agentic RAG, not GraphRAG, not multi-hop.

- Chunks 250–400 tokens. Top-10 lexical + top-10 dense, fused with RRF `Σ 1/(60 + rank)`. Pack 4–6 passages.
- FAISS **exact** search. The corpus is too small to justify ANN.
- Two corpora with different authority: the **policy library** is authoritative for rules; **per-application evidence** is quotable, but numbers come from the structured fact store.
- **Hard index isolation** — one index per application plus one approved policy index. Server code selects the index before retrieval; the index is never chosen from user or model input.
- Every generated claim must cite retrieved chunk ids belonging to the authorized application. Unsupported claims are dropped and the summary abstains.
- Document text is untrusted input. Prompt injection is tested explicitly.

No reranker unless it measurably beats the baseline on the frozen question set.

---

## 10. Models

| Role | Model | Trained by us? |
| --- | --- | --- |
| Document classifier baseline | TF-IDF + logistic regression | Yes |
| Document classifier challenger | DistilBERT-class encoder, seq 256, batch 2–4, AdamW ~2e-5, ≤3 epochs | Yes |
| Embeddings | `BAAI/bge-small-en-v1.5`, 384-dim | No — frozen |
| Generation | OpenCode Zen, `https://opencode.ai/zen/v1`, key in `OPENCODE_API_KEY` | No |
| Offline fallback | Qwen3-4B-Instruct-2507 Q4 GGUF, 4,096 ctx | No |

**Selection rule:** ship whichever classifier wins on measured quality *and* resource footprint. If TF-IDF gets 0.91 macro-F1 and the encoder gets 0.92 for 400 MB of RAM, ship the baseline and say why.

Freeze the generation model version on Day 1. Free Zen models rotate and get withdrawn; use free models for development and a pinned paid model on demo day. Check the auto-top-up setting.

Targets: ≥0.90 macro-F1 classification, ≥0.95 extraction exact match, ≥0.90 Recall@5.

---

## 11. Data

The Kaggle file is ~84 KB of tabular rows. It is a **ground-truth seed, not a corpus** — never describe or treat it as documents.

Each row generates one coherent synthetic dossier with discrepancies injected deliberately. Every page is watermarked **SYNTHETIC DEMO — NOT VALID**. Split by group so template families and synthetic identities never leak across train/dev/held-out. Splits live in `data/manifests/` and are frozen once set.

Medium-tier targets: ~35 dossiers (25 dev / 6 held-out / 4 demo), ~500 labelled pages, 30 RAG eval questions (18 dev / 12 held-out).

No real customer data, ever.

---

## 12. Working with AI agents

Agentic tools are permitted and expected. These rules keep the output credible.

**Human-only zones — no agent authorship, mandatory second review:**

1. Financial arithmetic in `core/rules/`
2. Lease, outbox and `SKIP LOCKED` SQL
3. IAM policies, bucket policies, secret handling
4. Prompt-injection guardrails and the grounding validator

**Process rules:**

- One worktree or branch per pod. Small, reviewed PRs. Cap PR size so review stays real.
- Never let one agent write both a rule and its test unreviewed — you get a test that asserts the bug. For the money rules, a human writes the assertion; an agent may implement.
- Generate the API client from the frozen OpenAPI schema. Never hand-write fetch calls.
- The owner of a file must be able to explain every line in it.
- Scan agent-written code for hardcoded secrets and licence issues before merge.
- Note AI assistance in the README, along with these verification rules.
- Watch the agent-tool quota the way you watch the AWS budget.

**Good uses:** document HTML/Jinja templates, React components and `pdf.js` overlays, Pydantic models, migrations, Compose files, test fixtures and edge-case enumeration, docstrings, README.

---

## 13. Cost discipline

Target **$8–$15 for the week**, hard ceiling **$25**, alerts at $5 / $10 / $20.

- One ARM `t4g.medium`; spot on build days, on-demand on demo day; stopped outside work windows.
- PostgreSQL and Redis as containers, not RDS/ElastiCache.
- HTTPS via Caddy + Let's Encrypt on a free wildcard-DNS hostname, or the Student Pack domain.
- Cache aggressively: extraction by file hash, indexes as immutable snapshots, generation by (content hash, policy version, prompt version).
- **Never restructure the architecture to chase a credit.** Notably: do not move the datastore off PostgreSQL for the MongoDB Atlas credit.

---

## 14. Testing and definition of done

A task is done when: contracts updated, unit tests pass, the golden-path smoke test passes, `make demo` still reproduces demo state, no secrets committed, and the owner can explain the code.

CI runs lint, type check, schema check, rule tests and retrieval regression on the frozen eval set. **CI never makes paid API calls** — use the fake in-memory adapters.

Day 6 failure tests: kill the worker mid-stage and resume, deliver a duplicate message, force a DLQ and reconcile, exhaust a rate limit, simulate a provider 429, run the offline local-model path.

---

## 15. Non-negotiables

1. Deterministic code decides, AI explains, a human approves.
2. No fact without evidence; `UNKNOWN` beats a guess.
3. PostgreSQL is authoritative. Redis is disposable.
4. `core/` imports no provider SDK.
5. One cloud on the critical path.
6. Contracts change in one PR, through the integrator.
7. The AWS deployment runs without anyone's laptop.
8. No real customer data, and no autonomous lending decision.
