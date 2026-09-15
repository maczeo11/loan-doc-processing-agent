# FinScan AI — Complete Project Tutorial for Member 6 (Balaji)

> **Your role:** You own the "plumbing" of the system — the HTTP API layer, the database, the rate limits, the cloud storage, and the infrastructure that holds everything together. Think of yourself as the **building's architect and plumber** — you don't cook the food (the AI) or run the restaurant rules (the rules engine), but without your pipes and walls, nothing works.

---

## 🗺️ Table of Contents
1. [Big Picture in Plain English](#1-big-picture)
2. [The 7 Docker Containers](#2-docker-containers)
3. [Every Module Explained](#3-every-module-explained)
4. [Your Files vs. Other Members' Files](#4-ownership-map)
5. [The Complete End-to-End Flow](#5-complete-flow)
6. [Key Analogies to Remember](#6-analogies)

---

## 1. Big Picture

**What does this system do in one sentence?**  
A bank underwriter uploads messy PDFs (payslips, bank statements, tax returns), and FinScan AI reads them, checks the numbers, and prepares a report — but **a human always makes the final call**.

**The Prime Law (tattoo this on your brain):**
> 🔴 **Deterministic code decides → AI explains → A human approves**

- A Python rule computes if salary matches bank deposits. Never the AI.
- The AI only writes the narrative/summary.
- A human underwriter must type the Application ID and click approve.

---

## 2. The 7 Docker Containers

Think of Docker Compose as running 7 separate programs on the same machine, each talking to each other over a private network.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Compose Network                       │
│                                                                 │
│  [caddy]   ←── HTTPS traffic ──→  [api]  ←→  [db] (Postgres)    │
│  Port 80/443                       Port 8000   Port 5432        │
│                                       │                         │
│                                    [redis]  [outbox-dispatcher] │
│                                    Port 6379                    │
│                                                                 │
│                            [worker] ←→ [db] ←→ [S3/local]       │
│                                                                 │
│                  [migrate] (runs once, then exits)              │
└─────────────────────────────────────────────────────────────────┘
```

| Container | Your File | What It Does |
|-----------|-----------|--------------|
| `caddy` | `infra/Caddyfile` | The front door — HTTPS, reverse proxy to `api:8000` |
| `db` | `infra/docker-compose.yml` | PostgreSQL — stores everything permanently |
| `redis` | `infra/docker-compose.yml` | Fast in-memory store for rate limits & job quotas |
| `migrate` | `infra/docker-compose.yml` | Runs Alembic once to create DB tables, then exits |
| `api` | `infra/Dockerfile.api` | **Your FastAPI server** — handles all HTTP requests |
| `outbox-dispatcher` | `apps/api/outbox_dispatcher.py` | **Your** background process — reads the outbox and pushes to queue |
| `worker` | `infra/Dockerfile.worker` | Bhanu's background AI processor — runs the LangGraph pipeline |

---

## 3. Every Module Explained

### 🔵 YOUR FILES (Member 6 — Balaji)

---

#### `apps/api/main.py` — The Front Door
**What it does:** This is where FastAPI starts. It plugs in all routes and middleware.

**Analogy:** Like the `main()` function in a restaurant — it opens the doors, assigns tables (routes), checks IDs at entry (auth), and closes gracefully.

**Key things it does:**
- Creates the `FastAPI` app object
- Attaches CORS (allows browser to call the API)
- Wires up all 4 routers: `applications`, `documents`, `review`, `uploads`
- Mounts the React UI at `/` (the `apps/ui/dist` folder)
- Exposes `/health` and `/health/ready` endpoints

**How it connects to your other files:**
```python
from apps.api.routes.applications import router  # YOUR route
from apps.api.middleware.rate_limit import close_redis_client  # YOUR middleware
```

**Example data flow:** A browser request to `POST /applications` hits `main.py` → gets routed to `applications.py` → validated → saved to PostgreSQL.

---

#### `apps/api/config.py` — The Settings Panel
**What it does:** Reads environment variables (from `.env` file or Docker env) and makes them available everywhere as `settings.SOME_VALUE`.

**Analogy:** Like a master control panel with switches. Every other file reads from here rather than hardcoding values.

**Key settings you defined:**
```python
STORAGE_BACKEND = "local" or "s3"
QUEUE_BACKEND = "postgres" or "sqs"
MAX_FILE_SIZE_MB = 10           # 10 MB file size limit
MAX_SUBMISSIONS_PER_MIN = 5     # Rate limit: 5 uploads per minute
MAX_ACTIVE_JOBS_PER_USER = 2    # Spend guard: max 2 concurrent jobs
DATABASE_URL = "postgresql+asyncpg://..."
REDIS_URL = "redis://localhost:6379/0"
```

**How other files use it:**
```python
from apps.api.config import settings
if settings.STORAGE_BACKEND == "s3":
    use_s3()
```

---

#### `apps/api/db/models.py` — The Database Blueprint
**What it does:** Defines the PostgreSQL table structures using SQLAlchemy ORM. Every table has a Python class.

**Analogy:** If PostgreSQL is a filing cabinet, `models.py` is the design sheet saying "drawer 1 has slots for name, amount, date..."

**Your 6 tables:**

| Table (Class) | Purpose | Key Columns |
|--------------|---------|-------------|
| `ApplicationModel` | One row per loan application | `id` (APP-XXXXX), `status`, `state_json` |
| `DocumentModel` | One row per uploaded PDF | `id`, `application_id`, `storage_uri`, `sha256` |
| `JobModel` | One row per processing job | `id` (JOB-XXXXX), `status`, `attempt_count` |
| `OutboxEventModel` | Pending messages to send to queue | `payload`, `status` (PENDING/PUBLISHED/FAILED) |
| `AuditEventModel` | Immutable log of every decision | `from_status`, `to_status`, `actor`, `decision` |
| `SpendLedgerModel` | Cost tracking per user | `cost_units`, `action` |
| `UserModel` | Authorized underwriters | `email`, `role`, `authorized` |

**Real example of `ApplicationModel`:**
```python
# After upload + processing, the row looks like:
id = "APP-A1B2C3D4"
applicant_name = "Priya Sharma"
loan_amount = 500000.0
status = "READY_FOR_REVIEW"      # Current lifecycle stage
state_json = {                    # Full pipeline result stored as JSON
    "payslip": {"gross_salary": {"amount": 75000, ...}},
    "findings": [{"rule_id": "RULE-INC-01", "verdict": "pass", ...}],
    "summary_markdown": "# Credit Appraisal Memo\n..."
}
```

---

#### `apps/api/db/outbox.py` — The Reliable Messenger
**What it does:** Implements the **Transactional Outbox Pattern** — the most important reliability pattern in the system.

**Analogy:** Imagine you're sending a letter AND updating a logbook **in the same pen stroke** (atomic). If the letter gets lost, you check the logbook and resend. The outbox IS that logbook.

**The problem it solves:**  
Without outbox: "Save to DB, THEN put job in queue" — if the server crashes between these two steps, the job is lost forever but the DB says it's queued.  
With outbox: "Save to DB AND outbox row in ONE transaction. The dispatcher reads the outbox and sends to queue."

**Two functions:**
1. `create_outbox_event()` — adds a `PENDING` row to `outbox_events` table (does NOT commit — the caller commits)
2. `dispatch_pending_outbox_events()` — reads `PENDING` rows, publishes to queue, marks `PUBLISHED`

**Real data flowing through it:**
```python
# In applications.py, POST /applications/{id}/process:
create_outbox_event(
    session=session,
    aggregate_type="application_job",
    aggregate_id="APP-A1B2C3D4",
    payload=JobRef(
        job_id="JOB-E5F6G7H8",
        application_id="APP-A1B2C3D4",
        attempt_count=1,
        metadata={"document_ids": ["DOC-1", "DOC-2"], ...}
    )
)
await session.commit()  # BOTH ApplicationModel + OutboxEventModel saved atomically
```

---

#### `apps/api/routes/applications.py` — The Application Manager
**What it does:** Handles creating, listing, fetching, and triggering processing of loan applications.

**Key endpoints:**

| Endpoint | What it does |
|---------|-------------|
| `POST /applications` | Creates a new application row in DB with status=`UPLOADED` |
| `GET /applications` | Lists recent applications for the UI dashboard |
| `GET /applications/{id}` | Returns full application state (facts, findings, memo) |
| `POST /applications/{id}/process` | **The big one** — queues the application for AI processing |
| `GET /applications/{id}/audit` | Returns the immutable audit trail |
| `GET /applications/{id}/export` | Downloads Credit Appraisal Memo as PDF or JSON |

**What happens in `POST /applications/{id}/process` (step by step):**
1. Lock the DB row (`SELECT FOR UPDATE`)
2. If already QUEUED/PROCESSING, return existing job (idempotency)
3. Check documents exist — reject with 409 if none
4. Check Redis spend guard — reject with 429 if user has 2 active jobs
5. Change status to `QUEUED`
6. Create `JobModel` row
7. Create `OutboxEventModel` row (the messenger)
8. **Commit all 3 changes in ONE transaction** ← this is the magic
9. Return `{"job_id": "JOB-...", "status": "QUEUED"}`

---

#### `apps/api/routes/uploads.py` — The Secure File Uploader
**What it does:** Implements presigned upload flow so browsers can upload directly to S3 without proxying all bytes through the API.

**Two-step flow:**
1. `POST /applications/{id}/uploads/presign` → Returns an S3 presigned POST URL + fields
2. Browser POSTs directly to S3 using that URL
3. `POST /applications/{id}/uploads/complete` → API verifies SHA-256 hash, registers `DocumentModel`

**Security things you built in:**
- SHA-256 checksum verification (tamper detection)
- File size ceiling (MAX_FILE_SIZE_MB = 10 MB)
- Content type whitelist (only PDF/image)
- Path traversal sanitization (`../` stripped)
- Short-lived URLs (15 min TTL)

---

#### `apps/api/routes/review.py` — The Underwriter Interface
**What it does:** Handles job status polling and the human review sign-off with the 3-tier friction gate.

**Key endpoints:**

| Endpoint | What it does |
|---------|-------------|
| `GET /jobs/{id}` | Check if the AI pipeline finished (rate-limited: 30 polls/min) |
| `POST /jobs/{id}/cancel` | Cancel a running job + releases Redis spend guard slot |
| `POST /applications/{id}/questions` | Ask a question about credit policy (RAG-powered) |
| `POST /applications/{id}/review` | **The human approves/rejects the loan** |

**The 3-tier friction gate in `POST /applications/{id}/review`:**
```
Tier 1: Pick APPROVED, REJECTED, or NEEDS_INFO
Tier 2: For REJECTED/NEEDS_INFO → notes must be ≥5 characters
Tier 3: Must type exact application ID (e.g., "APP-A1B2C3D4") to unlock submit
```

**What `submit_review()` writes to DB:**
```python
# Updates ApplicationModel
app_model.status = "REVIEWED"  # or "NEEDS_INFORMATION"
app_model.reviewer_id = "priya@bank.com"  # The logged-in email

# Writes immutable AuditEventModel
AuditEventModel(
    from_status="READY_FOR_REVIEW",
    to_status="REVIEWED",
    actor="priya@bank.com",
    decision="APPROVED",
    notes="Income verified. DTI within policy limits.",
)
```

---

#### `apps/api/middleware/rate_limit.py` — The Bouncer
**What it does:** Enforces sliding-window rate limits using Redis. Stops abuse and protects cloud costs.

**Analogy:** Like a nightclub bouncer with a clicker — "You've uploaded 5 times in the last minute, come back in 30 seconds."

**Two rate limits you enforce:**
1. **Upload rate:** `rate_limit_upload` → 5 uploads/minute per user
2. **Polling rate:** `rate_limit_polling` → 30 status polls/minute per user

**How the sliding window works:**
```
Redis sorted set: key = "rate_limit:upload:<user_hash>"
Each request adds a member with score = current_timestamp
Prune members older than 60 seconds
Count remaining → if ≥ limit → HTTP 429 Too Many Requests
```

**Identity resolution:** Uses `X-User-Id` header → hashed with SHA-256 for privacy. In local dev, falls back to client IP.

---

#### `apps/api/middleware/spend_guard.py` — The Budget Controller
**What it does:** Enforces "max 2 active jobs per user" using Redis sorted sets.

**Analogy:** Like a car park with 2 spaces per member. Before you park a new car, it checks if both spaces are taken. If you've already finished and left, those spaces are freed.

**Smart feature — lazy slot reclamation:**  
When you try to submit job 3 but have 2 active slots, it checks the DB: "Are those 2 jobs actually still running?" If they finished but the slots weren't released, it frees them automatically.

**Key functions:**
- `reserve_active_job_slot()` → atomically claims a slot before queuing
- `release_active_job_slot()` → frees slot after job finishes/cancels
- `release_active_job_by_id()` → looks up user from job ID → frees slot (used by cancel endpoint)

---

#### `adapters/storage/s3.py` — The Cloud Filing Cabinet
**What it does:** Stores and retrieves PDFs from AWS S3 with encryption and security.

**Your S3 security rules (from AGENTS.md):**
- All objects stored with `ServerSideEncryption: AES256`
- All keys follow `dossiers/{application_id}/{doc_id}_{filename}` — no cross-tenant access
- Filenames sanitized (strips `../`, replaces special chars)
- Download URLs are presigned (short-lived, cryptographic, never public)
- S3 Block Public Access enabled on production bucket

**Key methods:**
```python
s3.put(key, data)          # Upload bytes with AES256 encryption
s3.get(key)                # Download raw bytes
s3.get_signed_url(key)     # Generate 15-60 min presigned download URL
s3.generate_upload_url()   # Mint presigned POST URL for direct browser upload
s3.verify_integrity(key, sha256_hex)  # Tamper check after upload
s3.delete(key)             # Remove tampered/quarantined file
```

**Real example:**
```python
# Payslip uploaded by user "APP-A1B2C3D4":
key = "dossiers/APP-A1B2C3D4/DOC-1234_payslip_march.pdf"
s3.put(key, pdf_bytes, ServerSideEncryption="AES256")
# → stored at s3://finscan-dossiers-prod/dossiers/APP-A1B2C3D4/DOC-1234_payslip_march.pdf
```

---

#### `infra/` — The Data Center
**What you own in `infra/`:**

| File | What it does |
|------|-------------|
| `docker-compose.yml` | Defines all 7 containers |
| `Dockerfile.api` | Builds the FastAPI container |
| `Dockerfile.worker` | Builds the worker container |
| `Caddyfile` / `Caddyfile.production` | HTTPS reverse proxy config |
| `aws_setup.sh` | Creates S3 bucket, SQS queue, IAM roles |
| `ec2_setup.sh` | Provisions ARM EC2 instance (t4g.medium) |
| `deploy.sh` / `start.sh` / `stop.sh` | Deployment automation |
| `iam_policy.json` | Least-privilege AWS permissions |
| `rollback.sh` / `teardown.sh` | Disaster recovery scripts |

---

### 🟡 OTHER MEMBERS' FILES (that your code connects to)

---

#### `core/contracts/` — Manjunath's Files
**What they do:** Define the shared "shapes" of data. Like interfaces/schemas that everyone agrees on.

**How they connect to you:**
- `JobRef` (`jobs.py`) — you create this in `applications.py` when queuing a job
- `LoanApplicationState` (`state.py`) — the full pipeline state you save in `state_json`
- `EvidenceRef` (`evidence.py`) — every fact must cite a page/location; you persist these in DB
- `Finding` (`findings.py`) — rule results; you read and return them via `GET /applications/{id}`

**Real example — `JobRef` you create:**
```python
job_ref = JobRef(
    job_id="JOB-E5F6G7H8",
    application_id="APP-A1B2C3D4",
    attempt_count=1,
    created_at="2024-01-15T09:30:00Z",
    priority=0,
    metadata={
        "document_ids": ["DOC-1", "DOC-2"],
        "document_manifest": {"DOC-1": "dossiers/APP-A1B2C3D4/DOC-1_payslip.pdf"}
    }
)
```

---

#### `core/graph/` — Bhanu Teja's Files
**What they do:** The AI pipeline orchestration — LangGraph StateGraph that chains all the processing nodes.

**How they connect to you:**
- Your `outbox_dispatcher.py` sends `JobRef` → queue → worker picks it up → calls `build_application_graph()` (Bhanu's code)
- After the pipeline finishes, Bhanu's worker calls `persist_pipeline_result()` → updates your `ApplicationModel` in PostgreSQL
- When underwriter submits review via your `POST /applications/{id}/review`, you call `resume_application_review()` (Bhanu's function) to advance the LangGraph checkpoint

**The 8-node pipeline (Bhanu owns this):**
```
triage_node → ocr_and_classify_node → extract_facts_node → evaluate_rules_node
→ retrieve_policy_node → synthesize_summary_node → validate_grounding_node
→ [INTERRUPT] human_review_node → END
```

---

#### `core/extraction/` — Jeevan's Files
**What they do:** OCR and fact extraction from PDFs.

**How they connect to you:**  
The worker fetches raw bytes using **your** `S3Storage.get(key)` → passes those bytes to Jeevan's extractors → extractors return `PayslipFacts`, `BankStatementFacts`, etc. → saved back to your `ApplicationModel.state_json`.

**Real example of bytes flow:**
```
Your S3Storage.get("dossiers/APP-A1B2/DOC-1_payslip.pdf")
    → raw_bytes (the actual PDF content)
    → Jeevan's native_parser.py reads the text
    → Jeevan's payslip.py extracts: gross_salary=75000, net_salary=62000
    → Facts saved in LoanApplicationState
    → Your ApplicationModel.state_json updated by Bhanu's worker
```

---

#### `core/rules/` — Sravanthi's Files
**What they do:** 5 deterministic financial audit rules. Pure math, no AI.

**How they connect to you:**
- Results (typed `Finding` objects) are stored inside your `ApplicationModel.state_json["findings"]`
- Your `GET /applications/{id}` returns these findings to the React UI
- Your `GET /applications/{id}/export` includes findings in the exported CAM PDF

**Real findings you store and return:**
```json
{
  "rule_id": "RULE-INC-01",
  "rule_name": "Salary vs. Bank Credit Reconciliation",
  "verdict": "flag",
  "reason": "Payslip net salary ₹62,000 deviates >5% from bank average credit ₹55,000",
  "supporting_evidence": [...]
}
```

---

#### `ml/` — Karthik's Files
**What they do:** Classify each uploaded PDF page as `payslip`, `bank_statement`, `tax_return`, or `id_card`.

**How they connect to you:**  
The classifier runs inside Bhanu's `ocr_and_classify_node`. It has no direct connection to your API files. However, the classification result (`classified_types: {"DOC-1": "payslip"}`) is stored in your `ApplicationModel.state_json`.

---

#### `core/rag/` — (Bhanu's nodes, Manjunath's grounding)
**What they do:** Retrieve relevant credit policy paragraphs and verify the AI summary only cites authorized sources.

**How they connect to you:**  
Your `POST /applications/{id}/questions` endpoint directly calls the RAG retriever to answer policy questions for the underwriter.

```python
# In your review.py:
from core.rag.retriever import HybridRetriever
hits = retriever.retrieve_policy(question, top_k=5)
```

---

## 4. Ownership Map

```
C:\Users\balaj\Pictures\loan-doc-processing-agent-main\
│
├── apps/api/
│   ├── main.py                    ✅ YOU (Member 6)
│   ├── config.py                  ✅ YOU (Member 6)
│   ├── outbox_dispatcher.py       ✅ YOU (Member 6)
│   ├── storage.py                 ✅ YOU (Member 6)
│   ├── db/
│   │   ├── models.py              ✅ YOU (Member 6)
│   │   ├── outbox.py              ✅ YOU (Member 6)
│   │   └── session.py             ✅ YOU (Member 6)
│   ├── routes/
│   │   ├── applications.py        ✅ YOU (Member 6)
│   │   ├── documents.py           ✅ YOU (Member 6)
│   │   ├── review.py              ✅ YOU (Member 6)
│   │   ├── uploads.py             ✅ YOU (Member 6)
│   │   └── auth.py                ✅ YOU (Member 6)
│   └── middleware/
│       ├── rate_limit.py          ✅ YOU (Member 6)
│       └── spend_guard.py         ✅ YOU (Member 6)
│
├── adapters/storage/
│   ├── base.py                    ✅ YOU (Member 6) — shared with Bhanu
│   ├── s3.py                      ✅ YOU (Member 6)
│   └── local_fs.py                ✅ YOU (Member 6) — shared with Bhanu
│
├── infra/                         ✅ YOU (Member 6)
│   ├── docker-compose.yml
│   ├── Dockerfile.api / Dockerfile.worker
│   ├── Caddyfile / Caddyfile.production
│   ├── aws_setup.sh
│   ├── ec2_setup.sh
│   ├── deploy.sh / start.sh / stop.sh
│   └── iam_policy.json
│
├── worker/
│   ├── main.py                    ⭐ Bhanu (uses your S3Storage & config)
│   ├── consumer.py                ⭐ Bhanu (uses your StoragePort)
│   └── persistence.py             ⭐ Bhanu (writes to YOUR ApplicationModel)
│
├── core/contracts/                ⭐ Manjunath (you import JobRef, Finding, etc.)
├── core/graph/                    ⭐ Bhanu (you call resume_application_review)
├── core/extraction/               ⭐ Jeevan (uses bytes from YOUR S3Storage)
├── core/rules/                    ⭐ Sravanthi (results stored in YOUR state_json)
├── core/rag/                      ⭐ Bhanu/Manjunath (you call retriever in review.py)
├── core/reporting/                ⭐ Sravanthi (you call memo_builder in export)
├── ml/                            ⭐ Karthik (classifier called inside Bhanu's nodes)
└── apps/ui/                       ⭐ Akshaya (React SPA mounted by YOUR main.py)
```

---

## 5. Complete Flow

### "User Uploads a Payslip" → "Underwriter Approves the Loan"

---

### PHASE 1 — Application Creation

**Step 1.1:** Underwriter opens React UI (served by **your** `main.py` mounting `apps/ui/dist`)

**Step 1.2:** React calls `POST /applications` with `{applicant_name, loan_amount}`

```
React UI → Caddy (HTTPS) → YOUR apps/api/main.py → YOUR routes/applications.py
```

**YOUR code in `applications.py`:**
```python
app_id = "APP-A1B2C3D4"
app_model = ApplicationModel(id=app_id, status="UPLOADED", state_json={...})
session.add(app_model)
await session.commit()
# → DB row created: APP-A1B2C3D4 with status=UPLOADED
```

**Response:** `{"application_id": "APP-A1B2C3D4", "status": "UPLOADED"}`

---

### PHASE 2 — Document Upload

**Step 2.1:** React calls `POST /applications/APP-A1B2C3D4/uploads/presign`

```
React → YOUR rate_limit.py (check: < 5 uploads/min?) → YOUR uploads.py
```

**YOUR `uploads.py` calls `S3Storage.generate_upload_url()`:**
```python
# YOUR s3.py mints a presigned POST URL
grant = s3.generate_upload_url(
    key="dossiers/APP-A1B2C3D4/DOC-1_payslip.pdf",
    content_sha256_hex="abc123...",  # The SHA-256 the browser computed
)
# Returns: {"url": "https://s3.amazonaws.com/...", "fields": {...}}
```

**Step 2.2:** React POSTs the PDF **directly to S3** (no API involved — saves bandwidth)

**Step 2.3:** React calls `POST /applications/APP-A1B2C3D4/uploads/complete`

**YOUR `uploads.py → s3.verify_integrity()`:**
```python
# YOUR s3.py compares the S3-stored SHA-256 with what the browser declared
receipt = s3.verify_integrity("dossiers/APP-A1B2C3D4/DOC-1_payslip.pdf", "abc123...")
# If mismatch → HTTP 422, file is quarantined (deleted from S3)
# If match → register DocumentModel in DB
```

**YOUR `_register_document()` in `uploads.py`:**
```python
session.add(DocumentModel(
    id="DOC-1",
    application_id="APP-A1B2C3D4",
    filename="payslip.pdf",
    storage_uri="dossiers/APP-A1B2C3D4/DOC-1_payslip.pdf",
    sha256="abc123...",
    size_bytes=245120,
))
await session.commit()
# → DB: documents table has one row for this payslip
```

---

### PHASE 3 — Triggering AI Processing

**Step 3.1:** React calls `POST /applications/APP-A1B2C3D4/process`

```
React → YOUR rate_limit.py (check: < 5/min?) → YOUR applications.py
```

**YOUR `applications.py` does 8 things atomically:**
```python
# 1. Lock the DB row (prevents double-submission)
stmt = select(ApplicationModel).where(...).with_for_update()

# 2. Check it's in UPLOADED state (not already QUEUED)
assert app_model.status == "UPLOADED"

# 3. Check documents exist
doc_rows = (await session.execute(doc_stmt)).scalars().all()
assert len(doc_rows) > 0  # Must have at least 1 document

# 4. YOUR spend_guard.py: Does this user have < 2 active jobs?
slot_reserved = await reserve_active_job_slot(
    redis_client, user_id="hash_of_user_ip", job_id="JOB-E5F6G7H8", max_active=2
)
# → Redis: spend_guard:active:<user_hash> → {"JOB-E5F6G7H8": expire_timestamp}

# 5. Change app status to QUEUED
app_model.status = "QUEUED"

# 6. Create JobModel
session.add(JobModel(id="JOB-E5F6G7H8", status="QUEUED", attempt_count=1))

# 7. YOUR outbox.py: Create outbox event (the reliable messenger)
create_outbox_event(session, "application_job", "APP-A1B2C3D4", job_ref)
# → outbox_events table: {payload: {job_id, application_id, document_manifest, ...}, status: PENDING}

# 8. ONE atomic commit → all 3 rows saved or all roll back
await session.commit()
```

**Response:** `{"job_id": "JOB-E5F6G7H8", "status": "QUEUED"}`

---

### PHASE 4 — Outbox Dispatcher (Your Background Process)

**YOUR `outbox_dispatcher.py`** runs in its own Docker container, polling every 1 second:

```python
# YOUR outbox.py: dispatch_pending_outbox_events()
stmt = SELECT * FROM outbox_events WHERE status='PENDING' FOR UPDATE SKIP LOCKED LIMIT 10
# → Claims the row atomically. Another dispatcher instance won't see the same row.

# Validates the payload as a typed JobRef
job_ref = JobRef.model_validate(event.payload)

# Publishes to queue (Postgres queue or AWS SQS depending on config)
queue.publish(job_ref)

# Marks outbox row as PUBLISHED
event.status = "PUBLISHED"
await session.commit()
```

**For Postgres queue** (`QUEUE_BACKEND=postgres`):  
The job goes into the `jobs` table with a lease timestamp (Bhanu's `pg_queue.py`)

**For SQS** (`QUEUE_BACKEND=sqs`):  
The job is sent to AWS SQS (Bhanu's `sqs_queue.py`)

---

### PHASE 5 — Worker Picks Up the Job (Bhanu's Code, but uses YOUR S3)

**Bhanu's `worker/consumer.py`** polls the queue:
```python
deliveries = queue.receive(max_n=1)
# → Gets: {lease_handle: "...", job_ref: JobRef(...)}

# Starts a lease heartbeat thread (extends lock every 30s so no other worker steals it)
with LeaseHeartbeat(queue, handle):

    # 🔑 USES YOUR S3Storage.get() to fetch the actual PDF bytes!
    manifest = {"DOC-1": "dossiers/APP-A1B2C3D4/DOC-1_payslip.pdf"}
    for doc_id, storage_key in manifest.items():
        raw_bytes = YOUR_storage.get(storage_key)  # ← Your S3 code
        doc_bytes_map["DOC-1"] = raw_bytes          # ← 245,120 bytes of PDF

    # Runs Bhanu's LangGraph pipeline with these bytes
    final_state = graph.invoke(initial_state, config={"thread_id": "APP-A1B2C3D4"})
```

---

### PHASE 6 — LangGraph Pipeline (Bhanu's Nodes, using Everyone's Code)

**The pipeline runs 7 nodes sequentially:**

```
triage_node          → Validates documents exist. QUEUED → PROCESSING
        ↓
ocr_and_classify_node → Karthik's ML model classifies: "DOC-1 = payslip"
        ↓                (uses Jeevan's router.py to decide native vs OCR)
extract_facts_node   → Jeevan's payslip.py extracts: gross=₹75,000, net=₹62,000
        ↓                (with EvidenceRef: page 2, bounding_box x:0.1 y:0.3)
evaluate_rules_node  → Sravanthi's rules:
        ↓                RULE-COMP-01: ✅ All 5 document types found
        ↓                RULE-INC-01: ⚠️ Salary vs bank: WITHIN 5% tolerance
        ↓                RULE-TAX-01: ✅ ITR gross ≈ 12x monthly gross
        ↓                RULE-ID-01: ✅ Name matches across all docs
retrieve_policy_node → RAG: searches credit_policy.pdf for relevant passages
        ↓
synthesize_summary_node → LLM writes narrative:
        ↓                 "Applicant Priya Sharma's dossier shows consistent..."
        ↓                 (LLM ONLY narrates, never decides)
validate_grounding_node → Citation gate: every LLM claim must cite a retrieved chunk
        ↓                 (Prompt injection test: any injected "APPROVE ALL" → REJECTED)
[INTERRUPT CHECKPOINT]  → Pipeline PAUSES here. Saves state to SQLite checkpoint.
```

**What "interrupt" means:** LangGraph saves the entire state to a SQLite file and stops. The application status becomes `READY_FOR_REVIEW`. It's like a bookmark — can be resumed later.

---

### PHASE 7 — Write-Back to Your DB (Bhanu's `persistence.py` writes to YOUR tables)

```python
# Bhanu's worker/persistence.py calls your DB with the final state:
persist_pipeline_result(
    db_url="postgresql+asyncpg://...",
    job_id="JOB-E5F6G7H8",
    application_id="APP-A1B2C3D4",
    final_state={...}  # The complete LoanApplicationState dict
)

# This updates YOUR ApplicationModel:
app_model.status = "READY_FOR_REVIEW"
app_model.state_json = {
    "payslip": {"gross_salary": {"amount": 75000, ...}},
    "bank_statement": {"salary_credits": [...]},
    "findings": [{"rule_id": "RULE-INC-01", "verdict": "pass", ...}],
    "summary_markdown": "# Credit Appraisal Memo\n\nApplicant Priya Sharma...",
    "summary_grounded": True,
}

# This updates YOUR JobModel:
job_model.status = "COMPLETED"
```

**THEN** `queue.ack(handle)` is called — **only after** DB is committed. This is the "acknowledge-last" guarantee.

---

### PHASE 8 — Underwriter Reviews (Your Code Again)

**Step 8.1:** React polls `GET /jobs/JOB-E5F6G7H8` (your `review.py`, rate-limited to 30/min)  
→ Returns `{"status": "COMPLETED"}`

**Step 8.2:** React calls `GET /applications/APP-A1B2C3D4` (your `applications.py`)  
→ Returns the full `state_json` including findings, memo, facts

**Step 8.3:** React shows the Credit Appraisal Memo with the pdf.js document viewer

**Step 8.4:** Underwriter goes through the 3-tier friction gate:

```
Tier 1: Selects "APPROVED"
Tier 2: Types notes: "Income verified. DTI 38%. Approve."  (> 5 chars ✅)
Tier 3: Types "APP-A1B2C3D4" in the challenge field  ← must match exactly
Tier 4: Clicks [Sign Off]
```

**Step 8.5:** React calls `POST /applications/APP-A1B2C3D4/review`

**YOUR `review.py → submit_review()`:**
```python
# 1. Verify the underwriter is who they say they are (Google auth or mock)
actor_email = "priya.underwriter@bank.com"

# 2. Server-side friction gate validation
_enforce_review_invariants("APPROVED", notes, corrections, "APP-A1B2C3D4", "APP-A1B2C3D4")
# → confirm_app_id "APP-A1B2C3D4" == app_id "APP-A1B2C3D4" ✅

# 3. Update ApplicationModel
app_model.status = "REVIEWED"
app_model.reviewer_id = "priya.underwriter@bank.com"

# 4. Write immutable AuditEventModel (can never be deleted or edited)
session.add(AuditEventModel(
    from_status="READY_FOR_REVIEW",
    to_status="REVIEWED",
    actor="priya.underwriter@bank.com",
    decision="APPROVED",
    notes="Income verified. DTI 38%. Approve.",
    timestamp=utc_now()
))

# 5. Atomic commit
await session.commit()

# 6. Best-effort: Resume LangGraph checkpoint (Bhanu's function)
resume_application_review(thread_id="APP-A1B2C3D4", decision="APPROVED", ...)
```

**Response:** `{"application_id": "APP-A1B2C3D4", "decision": "APPROVED", "status": "REVIEWED"}`

**🎉 DONE. The loan application is approved with a full, immutable audit trail.**

---

## 6. Key Analogies to Remember

| Concept | Real-World Analogy |
|---------|-------------------|
| **FastAPI (`main.py`)** | Restaurant front desk — takes orders, routes to kitchen |
| **`config.py`** | Master control panel with all the switches |
| **PostgreSQL (`models.py`)** | The official filing cabinet — permanent, authoritative |
| **Redis (rate_limit, spend_guard)** | Bouncer with a clicker — fast, temporary memory |
| **S3 (`s3.py`)** | Fireproof vault for physical documents |
| **Transactional Outbox (`outbox.py`)** | Carbon copy — write the letter AND the logbook in one pen stroke |
| **Outbox Dispatcher** | Postman who checks the logbook and delivers letters |
| **Queue (SQS/Postgres)** | The actual mailbox the postman delivers to |
| **Worker (Bhanu's code)** | The back-office processing team that reads mail |
| **LangGraph Interrupt** | Bookmark — pipeline pauses and waits for human |
| **Rate Limiting** | Nightclub bouncer with a per-person click counter |
| **Spend Guard** | Car park with 2 spaces per member card |
| **AuditEventModel** | Stone tablet — you can write once, never erase |
| **EvidenceRef** | Footnote — every fact must cite its source page |

---

## Quick Cheat Sheet — Which File Handles What

| User Action | YOUR File |
|-------------|----------|
| Create application | `routes/applications.py` → `create_application()` |
| Upload payslip (presign) | `routes/uploads.py` → `presign_upload()` |
| Upload payslip (complete) | `routes/uploads.py` → `complete_upload()` → `s3.verify_integrity()` |
| Trigger processing | `routes/applications.py` → `trigger_processing()` |
| Check rate limit | `middleware/rate_limit.py` → `rate_limit_upload()` |
| Reserve job slot | `middleware/spend_guard.py` → `reserve_active_job_slot()` |
| Create outbox row | `db/outbox.py` → `create_outbox_event()` |
| Dispatch to queue | `outbox_dispatcher.py` → `dispatch_pending_outbox_events()` |
| Fetch job status | `routes/review.py` → `get_job_status()` |
| Cancel job | `routes/review.py` → `cancel_job()` |
| Ask policy question | `routes/review.py` → `ask_question()` (calls RAG) |
| Submit approval | `routes/review.py` → `submit_review()` |
| Download CAM PDF | `routes/applications.py` → `export_application()` |
| Store PDF in cloud | `adapters/storage/s3.py` → `S3Storage.put()` |
| Generate signed URL | `adapters/storage/s3.py` → `s3.get_signed_url()` |
| Run DB migrations | `infra/docker-compose.yml` → `migrate` container |
| Serve React UI | `apps/api/main.py` → `StaticFiles(directory=ui_dist_path)` |

