# FinScan AI — Member 6 (Balaji) — Complete Guide in Simple English

---

## PART 1: WHAT IS THIS PROJECT?

---

### 1.1 The Real World Problem

Imagine you go to SBI bank to apply for a loan of 5 lakhs.

The bank manager tells you to bring:
- Last 3 months salary slips (payslips)
- 6 months bank statements
- Last year's Income Tax Return (ITR)
- Aadhar + PAN card

You submit all the documents. A bank employee called an **underwriter** then manually checks everything:

```
Payslip says:       Salary = Rs. 44,200/month
Bank statement:     Monthly credit = Rs. 44,200 (does it match payslip?)
ITR:                Annual income = Rs. 5,30,400 (does it match salary * 12?)
Loan EMI:           Rs. 2,800/month (is it under 50% of salary? → 6.3%, YES)
```

Doing this manually takes **24 to 72 hours**. One underwriter handles only 3–4 applications per day and gets exhausted.

**FinScan AI** does this entire process in **90 seconds**. But there is one critical rule:

> The AI never makes the final decision.
> Python code does the math.
> A human underwriter approves or rejects.

This rule is called **"Deterministic Code Decides."**

---

### 1.2 Why Not Just Use ChatGPT?

This is an important question — it may come up in interviews!

**Problems with using LLMs (ChatGPT, Gemini) for financial decisions:**

| Problem | Example |
|---------|---------|
| Hallucination | AI says "Salary is 45,000" but it is actually 44,200 |
| No source tracing | "DTI ratio is 42%" — where did that number come from? |
| No audit trail | RBI regulations require a full audit record — LLM cannot provide one |
| Math errors | LLMs sometimes get arithmetic wrong |

**How FinScan AI solves this:**

```
Step 1 — OCR (Azure Document Intelligence):
  Reads the salary slip PDF.
  Finds "Net Salary: 44,200" at page 1, position (100, 200) to (300, 220).
  Saves: EvidenceRef(doc_id="DOC-001", page=1, bounding_box=(100,200,300,220))

Step 2 — Python code (deterministic):
  salary = 44200          (taken from the EvidenceRef above)
  annual = salary * 12    = 530,400
  dti    = 2800 / 44200   = 6.33%  ✅ (well under the 50% limit)

Step 3 — LLM (only for writing a human-readable summary):
  "The applicant's salary of Rs. 44,200 has been verified from payslip page 1.
   The DTI ratio of 6.33% is within the acceptable limit of 50%."

Step 4 — Human underwriter:
  Views the PDF with highlighted boxes around key numbers.
  Clicks "APPROVE" or "REJECT".
```

Every single number can be traced back to a specific page and position in a document. This is called **Provenance-Grounded Architecture**.

---

### 1.3 Architectural Decision: Why Azure Document Intelligence (OCR) and Not Alternatives?

In our project, reading loan documents (salary slips, bank statements, ITR forms) is handled by Member 4 using **Azure Document Intelligence**. Why was this tool chosen over alternatives?

| Technology | Approach | Pros | Cons & Why Rejected for FinScan AI |
|---|---|---|---|
| **Azure Document Intelligence** (CHOSEN) | Pre-trained Document AI model | • Exact pixel-accurate bounding box coordinates<br>• Outstanding tabular extraction (debit/credit columns in bank statements)<br>• High confidence score per extracted field<br>• Native multi-page financial PDF processing | • Cloud API cost per page (mitigated by our Redis Spend Guard) |
| **Tesseract OCR / EasyOCR** | Open-source raw OCR engine | • Free and runs locally without network calls | ❌ **Fails on tables:** Collapses multi-column bank statement tables into scrambled text.<br>❌ **Inaccurate coordinates:** Only gives rough raw text blocks, not semantic fields.<br>❌ **No financial understanding:** Requires fragile regex patterns that break on every new bank statement format. |
| **AWS Textract** | Cloud Document AI | • Table and key-value extraction | ❌ More complex, deeply nested JSON hierarchy (`BlockType`, `Relationships`, `Ids`), requiring hundreds of lines of boilerplate parsing code.<br>❌ Higher latency per page compared to Azure's layout model. |
| **Pure Multimodal LLM** (e.g. GPT-4o / Claude Vision) | Send document image to LLM | • High general intelligence | ❌ **Hallucination risk:** Violates our core doctrine ("Deterministic code decides").<br>❌ **No geometric coordinates:** Cannot return pixel bounding boxes to draw highlight rectangles on the underwriter's PDF viewer.<br>❌ **10x higher cost and latency** per document. |

**How it is Useful for FinScan AI:**
Without Azure Document Intelligence's bounding boxes (`x, y, width, height`), Member 7's 3-panel UI could not highlight the exact salary figures on the PDF. Every number used in our loan math traces directly back to the physical coordinates returned by this tool.

---

## PART 2: TEAM STRUCTURE

---

### 2.1 The 8 Members and What They Do

```
┌─────────────────────────────────────────────────────────────────┐
│                     FinScan AI System                           │
├──────────────┬──────────────────────────────────────────────────┤
│  Member 7    │  React UI (Frontend Dashboard)                   │
│  (Frontend)  │  PDF viewer, 3-panel layout                      │
├──────────────┼──────────────────────────────────────────────────┤
│  Member 6    │  FastAPI + PostgreSQL + Redis + Infrastructure   │
│  (Balaji) ★ │  Docker + Caddy + S3 + SQS + EC2 + IAM          │
├──────────────┼──────────────────────────────────────────────────┤
│  Member 5    │  RAG (Retrieval Augmented Generation)            │
│  (RAG)       │  Credit policy search, answer grounding          │
├──────────────┼──────────────────────────────────────────────────┤
│  Member 4    │  Document Reading (OCR)                          │
│  (OCR)       │  Azure Document Intelligence, page extraction    │
├──────────────┼──────────────────────────────────────────────────┤
│  Member 3    │  LangGraph Pipeline Orchestration                │
│  (Pipeline)  │  Workflow nodes, state management                │
├──────────────┼──────────────────────────────────────────────────┤
│  Member 2    │  Worker Consumer + Queue + Storage Adapters      │
│  (Bhanu)     │  Job processing loop, heartbeat, delivery        │
├──────────────┼──────────────────────────────────────────────────┤
│  Member 1    │  Integration Lead + System Architecture          │
│  (Bhanu)     │  Contracts, wiring all components together       │
├──────────────┼──────────────────────────────────────────────────┤
│  Member 8    │  ML Document Classifier                          │
│  (ML)        │  TF-IDF, DistilBERT, document type detection     │
└──────────────┴──────────────────────────────────────────────────┘
```

Balaji's code is the **foundation** that all other members depend on.
Without Balaji's infrastructure, no other part of the system can run.

---

## PART 3: BALAJI'S RESPONSIBILITIES — EXPLAINED WITH REAL EXAMPLES

---

### 3.1 FastAPI Application — `apps/api/main.py`

**What is FastAPI?**

FastAPI is a Python web framework. Think of it as the **main entrance of a hotel**.
Every visitor (user/browser) comes through the entrance (FastAPI) and gets directed to the right room (API endpoint).

**Real Example:**

When a user wants to create a new loan application, the browser sends:
```http
POST /applications
Content-Type: application/json

{
  "applicant_name": "Ravi Kumar",
  "loan_amount": 500000,
  "loan_purpose": "Home Renovation"
}
```

FastAPI receives it, processes it, and replies:
```json
{
  "application_id": "APP-3F9A1B2C",
  "status": "UPLOADED"
}
```

**What the code does:**
```python
# apps/api/main.py
app = FastAPI(title="FinScan AI API")

# These 3 groups of routes are registered:
app.include_router(applications_router)  # /applications
app.include_router(documents_router)     # /applications/{id}/documents
app.include_router(review_router)        # /jobs, /applications/{id}/review
```

**App shutdown cleanup:**
```python
@asynccontextmanager
async def lifespan(app):
    yield  # App is running...
    await close_redis_client()  # When app stops, close Redis connection
```
When the app stops, this ensures the Redis connection is properly closed.
Without this, connections would pile up in memory — called a **memory leak**.

---

#### Deep Dive: What is a Memory Leak & Why Redis Cleanup Matters

**Real Life Analogy — The Hotel Tap:**

Imagine a hotel with 100 rooms. Each room has a water tap (representing a network connection).
- A guest checks in → **tap is turned on** (connection is created).
- Guest checks out → **tap should be turned off** (connection should be released).

Now imagine the housekeeping staff **forgets to close the tap** whenever a guest leaves:
```
Day 1:  Guest 1 leaves — tap left running.
Day 2:  Guest 2 leaves — tap left running.
...
Day 30: All 100 taps are wide open, water is flooding the hotel!
        New guests arrive, but the water tank is empty and pipes are jammed.
        The entire hotel is forced to shut down.
```

This is **exactly what a memory leak is**: resources (memory, file handles, or network sockets) are opened and used, but **never released when no longer needed**. Over time, they consume all available capacity until the application slows down, runs out of memory, or crashes completely.

**Applying This to Redis & FastAPI:**

Redis is an in-memory database running in a separate service or container. To communicate with Redis (for rate limiting, caching, or deduplication), FastAPI opens a **TCP network socket connection** — think of it like an active phone call between FastAPI and Redis.

```
WITHOUT close_redis_client():

  App starts  ──►  Opens TCP connection to Redis  (Connection 1 active)
  App restarts / stops ──►  Connection is ABANDONED (still held in memory / socket table)
  App starts again  ──►  Opens another connection (Connection 2 active)
  App restarts / stops ──►  Connection is ABANDONED (Connection 1 & 2 leaked)
  ...
  After many runs: Redis connection pool maxes out!
  Redis error: "max number of clients reached" (HTTP 503 Service Unavailable)
```

```
WITH close_redis_client() (Balaji's implementation):

  App starts  ──►  Opens connection pool to Redis
  App running ──►  Processes requests, checks rate limits
  App stops   ──►  LIFESPAN triggers cleanup hook
                   FastAPI sends TCP FIN packet to Redis: "We are hanging up now!"
                   Redis gracefully frees socket and memory slot ✅
                   FastAPI sets _redis_client = None (Python garbage collects memory) ✅
```

**How FastAPI's `lifespan` Context Manager Works:**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── [STARTUP PHASE] ──────────────────────────────────────────
    # Code BEFORE the `yield` runs when FastAPI starts up
    
    yield  # The app is alive and serving user traffic here!
    
    # ── [SHUTDOWN PHASE] ─────────────────────────────────────────
    # Code AFTER the `yield` runs when FastAPI receives SIGINT / SIGTERM (stop signal)
    await close_redis_client()   # <── Guaranteed to run on shutdown!
```

**Inside `close_redis_client()` (`core/rate_limit.py`):**

```python
async def close_redis_client():
    global _redis_client, _local_fake_redis
    if _redis_client is not None:
        await _redis_client.aclose()   # Gracefully closes TCP connection pool to Redis
        _redis_client = None           # Clears pointer so Python garbage collection frees memory
    _local_fake_redis = None           # Cleans up local mock dictionary for testing
```

> **Key Takeaway:** Opening a Redis connection without closing it is like making a phone call and putting the receiver down on the table without hanging up. The line stays busy forever. Eventually, the phone exchange has no free lines left. `close_redis_client()` ensures FastAPI always hangs up properly before shutting down.

---

#### Architectural Decision: Why FastAPI and Not Flask, Django, or Express.js?

| Framework | Architecture | Type Validation | Concurrency Model | Verdict & Why Rejected for FinScan AI |
|---|---|---|---|---|
| **FastAPI** (CHOSEN) | Modern ASGI Python micro-framework | Native Pydantic runtime enforcement | Non-blocking `async/await` event loop | ✅ **Selected:** Sub-millisecond routing, automatic Swagger docs (`/docs`), async I/O keeps server responsive while streaming PDFs or talking to S3/Redis. |
| **Flask** | Legacy WSGI Python micro-framework | Manual parsing (`request.json`) | Synchronous / blocking threads | ❌ **Thread Starvation:** When multiple users upload 20MB PDFs or await slow S3 uploads, Flask blocks entire worker threads, leading to HTTP 504 timeouts. No built-in schema validation. |
| **Django** | Monolithic "batteries-included" | Heavy Django Forms / Serializers | Historically synchronous (limited async) | ❌ **Unnecessary Bloat:** Includes template rendering, sessions, admin panel, and heavy sync ORM that we do not need for a headless async microservice. |
| **Express.js (Node.js)** | Event-driven JavaScript | Requires external libraries (Zod / Joi) | Asynchronous event loop | ❌ **Python AI Ecosystem Disconnect:** Member 3 (Rules Engine), Member 4 (OCR), and Member 5 (RAG) all write Python. Using Node.js would break contract-sharing and force cross-language RPCs. |

**How it is Useful for FinScan AI:**
FastAPI allows Balaji's API service to handle dozens of concurrent document uploads, status polling checks, and background outbox dispatches asynchronously on a single modest AWS EC2 instance without blocking or running out of worker threads.

---

### 3.2 Configuration System — `apps/api/config.py`

**What is a Configuration System?**

When you run the application on your local laptop vs. on AWS production, the settings are different.

| Setting | On Your Laptop | On AWS Production |
|---------|---------------|-------------------|
| Database | localhost:5432 | db:5432 (inside Docker) |
| File Storage | Local folder | S3 bucket |
| Job Queue | Postgres table | AWS SQS |

Pydantic `BaseSettings` reads all these values from a `.env` file automatically.

**Real example — `.env` file for local development:**
```bash
STORAGE_BACKEND=local
QUEUE_BACKEND=postgres
DATABASE_URL=postgresql+asyncpg://postgres:postgrespassword@localhost:5432/finscan
```

**Real example — `.env` file for production (same code, different settings):**
```bash
STORAGE_BACKEND=s3
QUEUE_BACKEND=sqs
S3_BUCKET=finscan-dossiers-production
SQS_QUEUE_URL=https://sqs.ap-south-1.amazonaws.com/123456789012/finscan-jobs-production
AWS_REGION=ap-south-1
```

**The Settings class:**
```python
class Settings(BaseSettings):
    STORAGE_BACKEND: Literal["local", "s3"] = "local"  # default is local
    QUEUE_BACKEND: Literal["postgres", "sqs"] = "postgres"
    MAX_SUBMISSIONS_PER_MIN: int = 5   # Rate limit
    MAX_ACTIVE_JOBS_PER_USER: int = 2  # Spend guard
    S3_BUCKET: str = "finscan-dossiers-dev"
    
    class Config:
        env_file = ".env"  # Reads values from .env file automatically
```

**The AsyncCompatibleDsn trick:**
```python
class AsyncCompatibleDsn(str):
    # The database URL starts with "postgresql+asyncpg://"
    # The async driver (asyncpg) needs it this way.
    # But the sync driver (psycopg) needs "postgresql://"
    # This class makes the same URL work for both drivers.
    def encode(self, ...):
        return self.replace("postgresql+asyncpg://", "postgresql://")
```

---

#### Architectural Decision: Why Pydantic BaseSettings and Not Raw `os.environ` or `python-dotenv`?

| Configuration Tool | Type Safety | Validation Timing | Enum / Choice Restrictions | Verdict & Why Rejected for FinScan AI |
|---|---|---|---|---|
| **Pydantic `BaseSettings`** (CHOSEN) | Strong, automated type coercion (int, bool, URL) | **Fail-Fast at boot time:** App refuses to start if settings are wrong | Native `Literal["local", "s3"]` enforcement | ✅ **Selected:** Catches misconfigurations before any request arrives; zero runtime type errors. |
| **`os.environ.get()`** (Standard Lib) | None — returns raw `str` only | Lazy / runtime failure: crashes when the variable is first accessed | None — accepts any arbitrary string | ❌ **Silent Failures:** If `STORAGE_BACKEND` is set to `"s33"`, `os.environ` won't complain until a document upload fails at runtime. String `"5"` causes `TypeError` unless manually cast to `int(val)` everywhere. |
| **`python-dotenv` alone** | None — just loads key-value pairs into `os.environ` | No validation | None | ❌ **No Schema Contract:** Loads environment variables into memory, but does not validate data types, missing required keys, or valid URL formats. |

**How it is Useful for FinScan AI:**
Financial systems cannot afford runtime crashes caused by misconfigured environment variables. Pydantic ensures that if AWS credentials, database URLs, or rate limit numbers are missing or invalid, the Docker container fails immediately upon startup, alerting Balaji before users are impacted.

---

### 3.3 Database Models — `apps/api/db/models.py`

**What is an ORM?**

ORM stands for Object Relational Mapper. Instead of writing raw SQL queries, you write Python classes and objects. The ORM converts them to SQL automatically.

**Without ORM (raw SQL):**
```sql
INSERT INTO applications (id, applicant_name, loan_amount, status)
VALUES ('APP-001', 'Ravi Kumar', 500000, 'UPLOADED');
```

**With SQLAlchemy ORM (Balaji's approach):**
```python
app_model = ApplicationModel(
    id="APP-001",
    applicant_name="Ravi Kumar",
    loan_amount=500000,
    status="UPLOADED"
)
session.add(app_model)
await session.commit()  # Converts and runs SQL automatically
```

**Balaji designed 6 database tables:**

---

#### Table 1: `applications` — The main loan application container

```python
class ApplicationModel(Base):
    __tablename__ = "applications"
    
    id              # "APP-3F9A1B2C"
    applicant_name  # "Ravi Kumar"
    loan_amount     # 500000.0
    loan_purpose    # "Home Renovation"
    status          # UPLOADED → QUEUED → PROCESSING → READY_FOR_REVIEW → REVIEWED
    state_json      # All extracted data: { "payslip": {...}, "findings": [...] }
    
    # One application can have many documents, jobs, and audit records
    documents:    List[DocumentModel]
    jobs:         List[JobModel]
    audit_events: List[AuditEventModel]
```

**How the status changes step by step:**
```
Ravi applies for a loan:
  status = "UPLOADED"

Ravi uploads PDF documents:
  status = "UPLOADED" (same — documents are added underneath)

Ravi clicks "Start Processing":
  status = "QUEUED"

Worker picks up and starts processing:
  status = "PROCESSING"

LangGraph pipeline finishes:
  status = "READY_FOR_REVIEW"

Underwriter approves:
  status = "REVIEWED"
  reviewer_decision = "APPROVED"
```

---

#### Table 2: `documents` — Metadata for each uploaded PDF

```python
class DocumentModel(Base):
    __tablename__ = "documents"
    
    id             = "DOC-AB12345"
    application_id = "APP-3F9A1B2C"   # Links back to the application
    filename       = "salary_slip_march.pdf"
    storage_uri    = "s3://finscan-dossiers-production/dossiers/APP-3F9A1B2C/..."
    sha256         = "a3f9c2b1d4e5..."  # File fingerprint for integrity
    size_bytes     = 245678
```

---

#### Table 3: `jobs` — Background processing job tracker

```python
class JobModel(Base):
    __tablename__ = "jobs"
    
    id             = "JOB-CD98765"
    application_id = "APP-3F9A1B2C"
    status         = "QUEUED"   # QUEUED → PROCESSING → COMPLETED or FAILED
    attempt_count  = 1          # How many times has this job been tried?
    error_message  = None       # Filled in if the job fails
```

---

#### Table 4: `outbox_events` — Guarantees jobs never get lost

```python
class OutboxEventModel(Base):
    __tablename__ = "outbox_events"
    
    id      = "uuid-xyz"
    payload = {"job_id": "JOB-CD98765", "application_id": "APP-3F9A1B2C", ...}
    status  = "PENDING"   # → PUBLISHED → FAILED
```

This table is the backbone of the **Transactional Outbox Pattern** (explained in Section 3.7).

---

#### Table 5: `audit_events` — A permanent, unchangeable record of every decision

```python
class AuditEventModel(Base):
    __tablename__ = "audit_events"
    
    # When the underwriter approves:
    from_status = "READY_FOR_REVIEW"
    to_status   = "REVIEWED"
    actor       = "underwriter_john"
    decision    = "APPROVED"
    notes       = "All documents verified. Salary consistent."
    timestamp   = "2026-09-11T10:30:00Z"
```

This table is **append-only** — records are never deleted. This is required for legal and regulatory compliance (RBI rules).

---

#### Table 6: `spend_ledger` — Tracks API cost usage

```python
class SpendLedgerModel(Base):
    __tablename__ = "spend_ledger"
    
    user_or_app_id = "ravi@example.com"
    action         = "document_process"
    cost_units     = 1.5
    timestamp      = "2026-09-11T10:00:00Z"
```

---

#### Architectural Decision: Why PostgreSQL and Not MongoDB, MySQL, or DynamoDB?

| Database | Data Model | Transaction Guarantees (ACID) | JSON Flexibility | Concurrency / Queue Locking | Verdict & Why Rejected for FinScan AI |
|---|---|---|---|---|---|
| **PostgreSQL** (CHOSEN) | Relational + Hybrid Object-Relational | Strict ACID with robust Write-Ahead Logging (WAL) | **Native `JSONB`** with GIN indexing | Native `SELECT ... FOR UPDATE SKIP LOCKED` | ✅ **Selected:** Perfect for banking: foreign key constraints protect integrity, `JSONB` stores dynamic OCR bounding boxes, and row locking powers our outbox dispatcher. |
| **MongoDB** | Document NoSQL | Eventual consistency by default; costly multi-document transactions | Native BSON | Optimistic concurrency / no skip-locked tables | ❌ **High Risk of Data Corruption:** No relational foreign keys means orphaned document records if an application is deleted. Partial failures during loan review write dirty state. |
| **MySQL** | Relational | ACID compliant | Limited JSON functions (slower than Postgres `JSONB`) | Locks entire index pages more aggressively | ❌ **Inferior JSON & Async Support:** Poor query performance on nested OCR coordinates. Python's `asyncpg` driver for Postgres is significantly faster and more mature than `aiomysql`. |
| **AWS DynamoDB** | Key-Value / Wide-Column NoSQL | Single-row ACID; limited multi-item transactions | Native JSON maps | Partition-key based; expensive scans | ❌ **Zero Flexibility for Underwriters:** Cannot run ad-hoc SQL joins to filter "all loans approved by Underwriter X with DTI > 40%". High query modeling complexity. |

**How it is Useful for FinScan AI:**
PostgreSQL guarantees that when an underwriter clicks "APPROVE", the updated loan status, the human decision notes, and the immutable `audit_events` row are committed together atomically. If the server loses power during that millisecond, Postgres rolls back completely — preventing orphaned or untraceable loan approvals.

---

### 3.4 Document Upload — `apps/api/routes/documents.py`

**Why is there so much validation?**

There are many attackers on the internet who try to:
1. **Path Traversal** — Upload a file with the name `../../etc/passwd` to access system files.
2. **File Type Spoofing** — Rename a virus `.exe` file to `salary.pdf` and upload it.
3. **DoS Attack** — Upload a 1 GB file to crash the server's memory.
4. **Rate Flooding** — Send 1000 uploads per second to overwhelm the server.

Balaji built defenses for all of these.

---

**Defense 1: Block Path Traversal**
```
Hacker tries to upload with filename: "../../etc/passwd"
```
```python
# Balaji's code checks:
if ".." in raw or "/" in raw or "\\" in raw:
    raise HTTPException(400, "Invalid filename: path traversal not permitted")

# Result: HTTP 400 Bad Request — attack is stopped!
```

---

**Defense 2: Detect Fake File Types (Magic Bytes)**
```
Hacker renames virus.exe to payslip.pdf.
Their HTTP request says Content-Type: application/pdf (a lie).
```
```python
# Balaji reads the first 64KB of the actual file content:
first_chunk = await file.read(65536)

# Every file format has a unique signature at the very start:
is_pdf  = first_chunk.startswith(b"%PDF")          # Real PDF starts with %PDF
is_jpeg = first_chunk.startswith(b"\xff\xd8\xff")  # Real JPEG starts with these bytes
is_png  = first_chunk.startswith(b"\x89PNG\r\n\x1a\n")

# An .exe file starts with b"MZ" — does not match any allowed format!
if not (is_pdf or is_jpeg or is_png or is_tiff):
    raise HTTPException(400, "Invalid file format. Content does not match allowed types.")
```

---

**Defense 3: Stop Large Files from Crashing Memory**
```python
# Do NOT load the full file into memory at once.
# Instead, read it in small 64 KB pieces:
max_bytes = 10 * 1024 * 1024  # 10 MB limit
total_bytes = 0

while True:
    chunk = await file.read(65536)   # Read 64 KB at a time
    if not chunk:
        break
    total_bytes += len(chunk)
    if total_bytes > max_bytes:
        raise HTTPException(413, "File exceeds the 10 MB limit")
```

---

**SHA-256 Hash — What is it and why?**

A SHA-256 hash is a unique "fingerprint" of a file. Even if one byte changes, the fingerprint completely changes.

```python
hasher = hashlib.sha256()
while reading chunks:
    hasher.update(chunk)  # Feed each piece to the hasher
sha256_digest = hasher.hexdigest()
# Result: "a3f9c2b1d4e5678901234567890abcdef..."
```

**Why is this useful?**
- Detect if the same file was uploaded twice.
- Detect if a file was corrupted during upload.
- Detect if someone tampered with the file later.

---

**Atomic Cleanup — If the database fails, delete from S3 too:**
```python
try:
    storage_uri = storage.put(key, file_data)   # Step 1: Upload to S3 — success
    session.add(doc_model)                       # Step 2: Save metadata to DB
    await session.commit()                       # Step 3: Commit to DB
except Exception as db_err:
    await session.rollback()
    # Problem: File is in S3 but database has no record of it.
    # This is called an "orphaned object" — it wastes space and money.
    # Solution: Delete the S3 file too:
    await asyncio.to_thread(storage.delete, key)
    raise HTTPException(500, "Failed to save document to database")
```

---

### 3.5 Redis Rate Limiter — `apps/api/middleware/rate_limit.py`

**What is Rate Limiting?**

Imagine a hotel restaurant with 1 waiter. If 100 guests try to order at the same time, the waiter cannot handle it. So the restaurant says: "Maximum 5 orders per table per minute."

Similarly, the FinScan API says: **"Maximum 5 file uploads per user per minute."**

**The Sliding Window Algorithm:**

Instead of a fixed 60-second window (which resets suddenly), a sliding window tracks the last 60 seconds continuously:

```
Time: 0s ─────────────────────── 60s
           [req1:5s][req2:15s][req3:30s][req4:45s][req5:50s]

At time = 55s, a new request arrives.
Looking back 60 seconds (from 55s → to -5s):
All 5 requests are still within the window → COUNT = 5
LIMIT = 5 → DENIED! (HTTP 429 Too Many Requests)

At time = 66s, another request arrives.
Looking back 60 seconds (from 66s → to 6s):
req1 was at 5s — that is now OUTSIDE the window! Expired.
COUNT = 4 → ALLOWED!
```

**How Redis stores this:**
```python
key = "rate_limit:upload:a3f9c2b1"   # Unique key per user

# Redis Sorted Set: score = timestamp
pipe.zadd(key, {f"{now}:{request_id}": now})

# Count requests in the last 60 seconds:
current_entries = await redis.zrangebyscore(key, cutoff, "+inf")
current_count   = len(current_entries)
```

**Real example with Ravi Kumar:**
```
5:00:01 AM — Upload 1 → count = 1 ✅ Allowed
5:00:10 AM — Upload 2 → count = 2 ✅ Allowed
5:00:20 AM — Upload 3 → count = 3 ✅ Allowed
5:00:35 AM — Upload 4 → count = 4 ✅ Allowed
5:00:50 AM — Upload 5 → count = 5 ✅ Allowed
5:00:55 AM — Upload 6 → count = 5 → BLOCKED! (HTTP 429)
5:01:02 AM — Upload 7 → Upload 1 expired → count = 4 ✅ Allowed again
```

**Fail-Closed — What happens when Redis is down?**
```python
try:
    allowed, remaining, retry_after = await check_rate_limit(...)
    if not allowed:
        raise HTTPException(429, "Rate limit exceeded")
except HTTPException:
    raise  # Normal denial — rethrow it
except Exception:
    # Redis is completely down — we do NOT know if the user is within limits.
    # Safe choice = DENY the request:
    raise HTTPException(503, "Service unavailable — rate limit cannot be verified")
```

When Redis is down, the system **denies** requests rather than allowing unknown traffic. This is called **"fail-closed"** — safe by default.

---

### 3.6 Redis Spend Guard — `apps/api/middleware/spend_guard.py`

**What problem does this solve?**

AWS Bedrock (for the LLM), Azure Document Intelligence (for OCR), and SQS (for queueing) all cost money per use. If one malicious user starts 1000 jobs at once, the AWS bill would be enormous!

**The rule:** Maximum **2 active jobs per user** at any time.

**How it works — Atomic reservation:**
```python
async with redis.pipeline(transaction=True) as pipe:
    await pipe.watch(active_key)   # Watch this key for changes by other requests
    
    # Check how many jobs this user currently has running:
    active_jobs = await redis.zrangebyscore(active_key, now, "+inf")
    if len(active_jobs) >= 2:
        await pipe.unwatch()
        return False   # Slot denied — user already at the limit
    
    pipe.multi()   # Begin the atomic transaction
    pipe.zadd(active_key, {job_id: now + 900})   # Reserve slot, expires in 15 min
    pipe.set(job_map_key, user_id)               # Reverse lookup for later release
    await pipe.execute()   # Commit atomically
    return True   # Slot successfully reserved
```

**Real scenario:**
```
Ravi starts Job 1 → Redis stores: {JOB-1: expires 5:15 PM} → 1 active job
Ravi starts Job 2 → Redis stores: {JOB-1: 5:15PM, JOB-2: 5:30PM} → 2 active jobs
Ravi tries Job 3 → count = 2, limit = 2 → DENIED! (HTTP 429)

Job 1 finishes → Redis removes JOB-1 → only 1 active job remaining
Ravi tries Job 3 again → count = 1, limit = 2 → ALLOWED!
```

**TTL Safety Backstop:**
```python
pipe.zadd(active_key, {job_id: now + 900})   # Job slot expires in 15 minutes
```

If the worker crashes mid-job, the slot automatically disappears after 15 minutes. The user is never stuck waiting forever for a slot that will never be released.

---

#### Architectural Decision: Why Redis and Not In-Memory Python Dicts, Memcached, or DB Tables?

| Caching / State Tool | Multi-Process Safe | Data Structures (Sorted Sets) | Latency | Atomic Transactions | Verdict & Why Rejected for FinScan AI |
|---|---|---|---|---|---|
| **Redis** (CHOSEN) | Yes (centralized TCP service for all Docker containers) | Full support: Strings, Hashes, **Sorted Sets (`ZSET`)** | Sub-millisecond (<1ms in RAM) | `WATCH`, `MULTI`, `EXEC` pipelines | ✅ **Selected:** Powers sliding-window rate limiting and spend guard leases across multiple Uvicorn workers with zero race conditions. |
| **In-Memory Python `dict`** | ❌ Isolated to a single Python process | Basic dict / list only | Microseconds | Thread locks only (fails across processes) | ❌ **Multi-Worker Breakdown:** Uvicorn runs multiple worker processes. Process A cannot see Process B's memory. A user could exceed rate limits simply by hitting alternate workers. Wiped completely on restart. |
| **Memcached** | Yes | Simple key-value strings/blobs only | Sub-millisecond | Simple atomic increment (`INCR`), no pipelines | ❌ **Missing Complex Structures:** Memcached lacks Sorted Sets (`ZSET`). Without `ZSET`, we cannot query active jobs by timestamp score (`ZRANGEBYSCORE`) to implement spend guard leases with automatic TTLs. |
| **PostgreSQL Table** | Yes | Relational tables | 5–25ms (disk I/O and locking overhead) | Full SQL transactions | ❌ **Database Exhaustion:** Running an `UPDATE` or `INSERT` query on Postgres for every single API ping, health check, and route hit causes intense disk Write-Ahead Log (WAL) bloat and connection pool saturation. |

**How it is Useful for FinScan AI:**
Redis enables Balaji's **Rate Limiter** (preventing API DoS) and **Spend Guard** (capping concurrent AWS Bedrock / Azure OCR jobs at 2 per user) to evaluate in under 1 millisecond. Even if 10 requests arrive simultaneously, Redis executes the atomic pipeline sequentially, ensuring an applicant can never bypass our safety limit.

---

### 3.7 Transactional Outbox — `apps/api/db/outbox.py`

**The Problem — Jobs That Get Lost:**

In a naive system, processing looks like this:
```
Step 1: Save JobModel to database (commit) ✅
Step 2: Send job message to SQS ❌ (network error!)

Result: Job is in the database with status QUEUED,
        but no message was ever sent to SQS.
        The worker never picks it up.
        The job is SILENTLY LOST forever.
```

**The Transactional Outbox Solution:**

Instead of publishing to SQS directly, first save an `OutboxEventModel` record to the database — in the **same transaction** as the job:

```
Step 1 — SINGLE DATABASE TRANSACTION (all or nothing):
  ├── JobModel created (status = "QUEUED")
  └── OutboxEventModel created (status = "PENDING")
  → COMMIT (both saved together, or both rolled back if error)

Step 2 — Separate Outbox Dispatcher process (runs in background):
  → Polls the database: WHERE status = 'PENDING'
  → Publishes to SQS
  → Updates OutboxEventModel status = 'PUBLISHED'
```

**The magic SQL clause — SELECT FOR UPDATE SKIP LOCKED:**

Imagine 3 dispatcher workers running in parallel. Without locking, all 3 could pick the same job:
```sql
-- Worker 1 grabs row 1 (locks it)
-- Worker 2 sees row 1 is locked — SKIPS it — grabs row 2
-- Worker 3 sees rows 1 and 2 are locked — SKIPS them — grabs row 3

SELECT ... FOR UPDATE SKIP LOCKED
```

Each row is only picked up by exactly one worker. No duplicate processing.

**Guarantee:** A job is **never silently lost**. It will always eventually be delivered to the queue.

---

#### Architectural Decision: Why the Transactional Outbox Pattern and Not Direct Queue Publishing?

| Integration Pattern | Reliability Guarantee | Failure Modes & Risk | Performance Overhead | Verdict & Why Rejected for FinScan AI |
|---|---|---|---|---|
| **Transactional Outbox** (CHOSEN) | **Guaranteed At-Least-Once Delivery** | Event dispatcher retries until SQS confirms receipt | Minimal: 1 additional SQL insert in existing transaction | ✅ **Selected:** Solves the classic "Dual-Write Problem". Database commit and job queueing succeed or fail together as a single atomic unit. |
| **Direct Queue Publishing** (FastAPI → SQS) | Best-effort only (flawed) | **Silent Job Loss:** If API saves to DB but SQS network times out, DB commit stays, but SQS message is gone forever. Customer waits endlessly. | Slightly faster (saves 1 table write) | ❌ **Fatal in Banking:** In financial services, you can NEVER tell an applicant "we received your loan application" while the processing job silently vanished from the queue. |
| **Distributed Two-Phase Commit (2PC / XA)** | Atomic across systems | Network coordinator blocking / split-brain | Extreme latency penalty; locks resources | ❌ **Cloud Incompatible:** AWS SQS does not support XA distributed transactions; high complexity and brittle failure modes. |

**How it is Useful for FinScan AI:**
Even if AWS SQS is temporarily down for maintenance or experiences a network partition, applicants can still upload documents and submit applications. The jobs sit safely in PostgreSQL's `outbox_events` table as `PENDING`, and are dispatched automatically the second connectivity returns.

---

### 3.8 Worker Entrypoint — `worker/main.py`

**The Problem — Selecting the Right Storage and Queue:**

The same worker code must run in two very different environments:

| Environment | Queue | Storage |
|-------------|-------|---------|
| Local laptop | Postgres table | Local folder on disk |
| AWS Production | AWS SQS | AWS S3 |

**Before Balaji's fix — Broken code:**
```python
# OLD CODE (broken):
queue_adapter = SQSQueueAdapter(...)  # Hardcoded to SQS — breaks locally!
worker = ApplicationWorker(queue_adapter=queue_adapter)
# Storage adapter was never passed in!
# This means it always defaults to LocalFileSystemStorage — even in production!
```

**After Balaji's fix — Correct code:**
```python
def get_storage_adapter():
    backend = os.getenv("STORAGE_BACKEND", "local")
    if backend == "s3":
        bucket = os.getenv("S3_BUCKET", "finscan-dossiers-production")
        region = os.getenv("AWS_REGION", "ap-south-1")
        return S3Storage(bucket_name=bucket, region=region)
    
    base_dir = os.getenv("STORAGE_BASE_DIR", "data/storage")
    return LocalFileSystemStorage(base_dir=base_dir)

def create_worker():
    queue   = get_queue_adapter()     # SQS in production, Postgres locally
    storage = get_storage_adapter()   # S3 in production, local folder locally
    checkpointer = SqliteSaver(checkpoint_db)
    
    return ApplicationWorker(
        queue_adapter=queue,
        storage_adapter=storage,   # ← This was the missing piece!
        checkpointer=checkpointer
    )
```

**On production (AWS):**
```
STORAGE_BACKEND=s3
→ Creates S3Storage(bucket="finscan-dossiers-production", region="ap-south-1")
→ Worker downloads PDF bytes from S3
→ Sends bytes to OCR extractor
```

**On local laptop:**
```
STORAGE_BACKEND=local
→ Creates LocalFileSystemStorage(base_dir="/app/data/storage")
→ Worker reads PDF bytes from local disk
→ No AWS account needed!
```

---

#### Architectural Decision: Why AWS SQS and Not Celery, RabbitMQ, or Apache Kafka?

| Queueing System | Infrastructure Management | Failure Handling (Poison Pills) | Delivery & Retries | Operational Cost & Overhead | Verdict & Why Rejected for FinScan AI |
|---|---|---|---|---|---|
| **AWS SQS** (CHOSEN) | **100% Serverless:** Zero servers to patch or maintain | Built-in **Dead Letter Queue (DLQ)** after 3 retries | Visibility timeout with at-least-once delivery | Pay-per-request (pennies/month for our volume) | ✅ **Selected:** Maximum reliability with zero DevOps maintenance. Decoupled, auto-scaling, and supports DLQ out-of-the-box. |
| **Celery + RabbitMQ** | Heavy: Requires running and clustering a RabbitMQ broker | Custom dead-letter exchange configuration | Complex ACK/NACK semantics; risk of silent drop | High: Requires dedicated memory, disk monitoring, and Erlang updates | ❌ **High Operational Burden:** RabbitMQ brokers crash when disk/memory limits are exceeded. Celery state frequently drifts from our PostgreSQL state machine. |
| **Apache Kafka** | Extreme: Needs ZooKeeper/KRaft cluster, partition sizing | Manual dead-letter topic routing | Partition offset-based (head-of-line blocking if 1 message fails) | High minimum compute cost (multiple nodes) | ❌ **Over-Engineered for Jobs:** Kafka is an event stream (millions of metrics/sec), not an individual job queue. If one partition encounters a poisoned document, processing of subsequent loans on that partition halts. |

**How it is Useful for FinScan AI:**
Processing loan documents involves heavy OCR and LLM inference that takes 30–90 seconds per document. AWS SQS acts as a resilient buffer: if 50 applicants submit loans simultaneously, SQS absorbs the burst instantly. The background workers pull jobs steadily according to system capacity without dropping a single task.

---

### 3.9 S3 Storage Adapter — `adapters/storage/s3.py`

**What is AWS S3?**

Amazon S3 (Simple Storage Service) is like Google Drive, but for code. You store any file (PDF, image, video) and access it through an API. Files are called "objects" and are stored in "buckets."

**Our bucket:** `finscan-dossiers-production`
**File path format:** `dossiers/APP-3F9A1B2C/DOC-AB12345_salary_slip.pdf`

**Uploading a file:**
```python
def put(key, data):
    clean_key = "dossiers/APP-3F9A1B2C/DOC-AB12345_salary_slip.pdf"
    
    s3.put_object(
        Bucket="finscan-dossiers-production",
        Key=clean_key,
        Body=data,
        ContentType="application/pdf",
        ServerSideEncryption="AES256"   # File is encrypted at rest
    )
    # Returns the S3 address of the file:
    return "s3://finscan-dossiers-production/dossiers/APP-3F9A1B2C/..."
```

**Presigned URL — For the React PDF Viewer:**

The frontend React app needs to display the PDF to the underwriter. But the S3 bucket is private (no public access). The solution is a presigned URL:

```python
def get_signed_url(key, expires_in=3600):
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=3600  # This temporary link expires in 1 hour
    )
    return url
    # Example: "https://finscan-dossiers-production.s3.amazonaws.com/...?X-Amz-Signature=abc123"
```

The React app uses this URL to directly display the PDF from S3. The FastAPI server does not have to handle that download traffic at all.

**Security features:**
- AES-256 server-side encryption — files are encrypted when stored
- `dossiers/` prefix is required — prevents accidentally saving to the S3 root
- Presigned URLs only — no permanent public access to files
- IMDSv2 on EC2 — prevents credential theft from inside the machine

---

#### Architectural Decision: Why AWS S3 and Not Local EC2 Disk, AWS EFS, or Database BLOBs?

| Storage Solution | Durability & Availability | Scalability | Direct Browser Streaming | Cost Efficiency | Verdict & Why Rejected for FinScan AI |
|---|---|---|---|---|---|
| **AWS S3** (CHOSEN) | **99.999999999% (11 9s)** durability across 3 AZs | Virtually unlimited object capacity | **Presigned URLs:** Clients stream directly from S3 without touching API bandwidth | Low ($0.023/GB/mo) | ✅ **Selected:** Highly secure, tamper-proof, offloads all PDF viewing bandwidth from FastAPI server to AWS global network. |
| **Local EC2 Disk / EBS** | Single-disk failure risk; lost if EC2 instance terminates | Capped to disk volume size (e.g. 20 GB) | API must read from disk and stream to client (wastes API bandwidth) | Medium-High (paying for provisioned gigabytes) | ❌ **High Risk of Data Loss:** If the EC2 instance is terminated or resized, all applicant payslips are wiped out. Also prevents running multiple API servers in the future. |
| **AWS EFS (NFS Network Drive)** | High durability | Elastic auto-scaling | No native presigned URLs; API must proxy all file traffic | **Very High:** ~10x more expensive than S3 per GB ($0.30/GB/mo) | ❌ **Costly & Fragile:** Requires complex NFS mount configurations inside Docker containers; frequent mount timeout errors during heavy I/O. |
| **Database BLOBs (`bytea` in PostgreSQL)** | Tied to database backups | Bloats database buffer cache and table size | API must query database and stream bytes | Extremely high (DB storage is premium) | ❌ **Performance Nightmare:** Storing multi-megabyte PDFs in relational tables degrades database indexing, slows backups, and swamps PostgreSQL RAM. |

**How it is Useful for FinScan AI:**
When an underwriter reviews a 50-page loan document package, Member 7's React UI requests a 1-hour presigned URL from Balaji's API and streams the file directly from S3's high-speed CDN. The FastAPI server uses zero memory or CPU bandwidth streaming the PDF, keeping the API fast and responsive.

---

### 3.10 Docker Compose — `infra/docker-compose.yml`

**What is Docker and Docker Compose?**

Docker runs an application in a "container" — a self-contained, isolated box that has everything the app needs (Python, libraries, settings). It works the same on any machine.

Docker Compose manages **multiple containers at once** as a group.

This project needs 7 separate processes to run:
1. PostgreSQL database
2. Redis cache
3. Alembic migration (runs schema changes, then stops)
4. FastAPI API server
5. Outbox Dispatcher
6. Worker
7. Caddy reverse proxy

Starting all 7 manually on a server would be painful. Docker Compose handles all of them with one command:
```bash
docker compose up -d
```

**Why startup order matters:**

```yaml
# WRONG — crashes immediately:
api:
  depends_on: []   # API starts before DB is ready → "Connection Refused!"

# CORRECT — Balaji's approach:
api:
  depends_on:
    db:
      condition: service_healthy              # Wait for DB to pass health check
    redis:
      condition: service_healthy              # Wait for Redis to be ready
    migrate:
      condition: service_completed_successfully  # Wait for DB schema to be created
```

**Health checks — How does Compose know when a service is ready?**
```yaml
db:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres -d finscan"]
    # pg_isready checks if PostgreSQL is actually accepting connections
    interval: 5s    # Check every 5 seconds
    timeout: 5s
    retries: 5      # If it fails 5 times in a row, mark as unhealthy
```

**Port Security — A critical fix Balaji made:**

```yaml
# Before fix (insecure):
api:
  ports:
    - "8000:8000"   # Anyone on the internet can access port 8000 directly!

# After fix (secure):
api:
  expose:
    - "8000"        # Only accessible inside Docker's internal network

caddy:
  ports:
    - "80:80"       # Accept HTTP from the internet
    - "443:443"     # Accept HTTPS from the internet
```

The traffic path is now:
```
Internet User → Port 443 (Caddy) → Port 8000 (api container, internal only)
```

The API server itself is never directly exposed to the internet. Only Caddy can reach it.

**Environment-based configuration:**
```yaml
api:
  environment:
    QUEUE_BACKEND:   ${QUEUE_BACKEND:-postgres}    # Default: postgres (for local dev)
    STORAGE_BACKEND: ${STORAGE_BACKEND:-local}     # Default: local
    S3_BUCKET:       ${S3_BUCKET:-}                # Empty by default
```

On the production EC2 server, the `.env` file overrides these:
```bash
QUEUE_BACKEND=sqs
STORAGE_BACKEND=s3
S3_BUCKET=finscan-dossiers-production
```

Same `docker-compose.yml` file works for both local and production.

---

#### Architectural Decision: Why Docker Compose and Not Kubernetes (K8s) or Bare Metal Systemd?

| Deployment Model | Setup & Operational Complexity | Resource Overhead | Local & Prod Parity | Rollback & Reproducibility | Verdict & Why Rejected for FinScan AI |
|---|---|---|---|---|---|
| **Docker Compose** (CHOSEN) | **Minimal:** 1 human-readable YAML file defines all 7 services | Low: Zero control-plane RAM overhead | **100% Identical:** Same Compose file runs locally and on AWS EC2 | One command rollback: `docker compose down && docker compose up -d` | ✅ **Selected:** Maximum developer velocity, zero cluster management headaches, runs all 7 microservices cleanly on a single EC2 instance. |
| **Kubernetes (K8s / EKS)** | **Extreme:** Requires Ingress, Helm charts, CNI networking, RBAC policies, etcd | Heavy: Consumes 2–4 GB RAM solely for the Kubernetes control plane | Difficult to run full cluster locally on developer laptops (Minikube is heavy) | Complex Helm releases | ❌ **Massive Over-Engineering:** Adds days of DevOps overhead and cluster management fees ($73/month just for EKS control plane) with zero benefits for our single-instance setup. |
| **Bare Metal / Systemd** | Medium: Requires writing custom bash install scripts and systemd unit files | Lowest (runs on host OS) | ❌ Poor: "Works on my machine" bugs due to OS package drift (Python versions, `libpq`) | Brittle manual file replacements | ❌ **High Deployment Fragility:** Manual package updates can break production dependencies; difficult to ensure identical environments across the team. |

**How it is Useful for FinScan AI:**
With Docker Compose, any of our 8 team members can clone the repository, run `docker compose up -d`, and immediately have PostgreSQL, Redis, Alembic migrations, FastAPI, and Caddy running in healthy coordination without installing PostgreSQL or Redis manually on their computers.

---

### 3.11 Caddy — Production HTTPS — `infra/Caddyfile.production`

**What does Caddy do?**

Caddy is a **reverse proxy**. It sits in front of the FastAPI server and:
1. Handles all HTTPS (TLS) connections from users
2. Automatically gets and renews free SSL certificates (from Let's Encrypt)
3. Adds security headers to every response
4. Forwards requests to the FastAPI container

**Traffic path:**
```
User Browser → DNS → 13.207.15.137:443
                              ↓
                    Caddy (Port 443)
                    - Decrypts HTTPS request
                    - Validates certificate
                              ↓
              FastAPI api container (Port 8000, internal only)
```

**Caddy's automatic HTTPS:**
```
{
  email admin@finscan.demo.internal   # Email for Let's Encrypt
}

finscan.demo.internal {
  # Caddy automatically:
  # 1. Contacts Let's Encrypt
  # 2. Verifies domain ownership
  # 3. Downloads a free SSL certificate
  # 4. Renews it automatically before it expires

  reverse_proxy api:8000
}
```

**Security headers Balaji added:**
```
Strict-Transport-Security "max-age=31536000"
→ Browser must always use HTTPS for the next 1 year.
  Even if a user types "http://..." it gets redirected to "https://..."

X-Content-Type-Options "nosniff"
→ Browser must not guess the file type from content.
  Prevents a hacker from uploading JavaScript disguised as an image.

X-Frame-Options "DENY"
→ The page cannot be embedded in an <iframe> on another website.
  Prevents "clickjacking" attacks.

-Server
→ Removes the "Server: Caddy" header.
  Hides the server software version from attackers.
```

---

#### Architectural Decision: Why Caddy and Not Nginx, Apache, or AWS ALB?

| Web Server / Reverse Proxy | TLS / SSL Certificate Handling | Configuration Complexity | Modern Protocols | Monthly Cost | Verdict & Why Rejected for FinScan AI |
|---|---|---|---|---|---|
| **Caddy** (CHOSEN) | **100% Automated:** Built-in Let's Encrypt & ZeroSSL auto-renewal | **Minimal:** 15 lines of clean, human-readable directives | HTTP/2 and **HTTP/3 (QUIC)** enabled by default | $0 (Runs in Docker on existing EC2) | ✅ **Selected:** Zero certificate renewal downtime, automated security headers, and ultra-lightweight Go-based binary. |
| **Nginx** | Manual: Requires Certbot, cron scripts, and reload hooks | Verbose: 50+ lines of low-level `proxy_set_header` boilerplate | HTTP/2 requires manual config; complex HTTP/3 compile | $0 | ❌ **High Maintenance Risk:** Certbot cron jobs fail silently when certificate challenges change. Expired certificates trigger scary red browser security warnings for bank underwriters. |
| **Apache HTTP Server** | Manual via Certbot | Complex XML-style `.conf` files | Heavy legacy thread-per-request architecture | $0 | ❌ **Outdated Architecture:** High memory consumption, slow under concurrent reverse proxy workloads compared to Caddy or Nginx. |
| **AWS Application Load Balancer (ALB)** | AWS Certificate Manager (ACM) | Configured via AWS Console / Terraform | HTTP/2 supported | **~$25–$40/month** (Base fee + LCU data processing charges) | ❌ **Unnecessary Monthly Bill:** For our single-instance deployment, paying $300+/year for an ALB when Caddy performs the exact same TLS termination for free inside Docker is wasteful. |

**How it is Useful for FinScan AI:**
Caddy acts as the armored front gate of our production server. It terminates HTTPS, injects strict HSTS (`Strict-Transport-Security`) and clickjacking prevention headers, and forwards requests internally to FastAPI without exposing port 8000 directly to the public internet.

---

### 3.12 EC2 Bootstrap and Deployment Scripts — `infra/`

**What is an EC2 instance?**

EC2 is an AWS virtual machine — basically a Linux server running in AWS's data centre. When you first launch one, it only has a bare Ubuntu operating system.

You then need to install Docker, clone the code, configure settings, and start the app.

**`ec2_setup.sh` — Automates the entire server setup:**
```bash
# Step 1: Detect the OS and install Docker
if command -v apt-get > /dev/null; then
    sudo apt-get install docker-ce docker-compose-plugin
fi

# Step 2: Create a dedicated non-root user for security
sudo useradd -r -s /usr/sbin/nologin finscan
# -r = system user (no home directory)
# -s /usr/sbin/nologin = this user cannot log into the shell (more secure)

# Step 3: Clone the repository
git clone --branch main https://github.com/.../loan-doc-processing-agent.git /opt/finscan/app

# Step 4: Lock down the .env file so only the owner can read it
chmod 600 /opt/finscan/app/.env   # Owner read/write only. No one else.
```

**`deploy.sh` — Deploys a new version safely:**
```bash
# 1. Save the currently running version (so we can roll back)
cp .current_release .previous_release

# 2. Switch to the new version
git fetch --tags origin
git checkout v1.2.0

# 3. Stamp the version into .env
./infra/version.sh --env .env
# Adds: GIT_SHA=abc123, BUILD_TIMESTAMP=2026-09-11T09:00:00Z

# 4. Start the services
docker compose up --build -d

# 5. Check that the new version is healthy
for 30 attempts:
    if curl http://localhost/health returns 200 OK:
        echo "v1.2.0" > .current_release
        echo "Deployment successful!"
        exit 0
    sleep 2 seconds

# 6. If health check never passed — tell the user to roll back
echo "ERROR: Deployment failed. Run: ./infra/rollback.sh"
exit 1
```

**`rollback.sh` — Goes back to the previous version:**
```bash
ROLLBACK_REF=$(cat .previous_release)   # e.g., "v1.1.0"
git checkout $ROLLBACK_REF
docker compose up --build -d
# Health check verify
echo "$ROLLBACK_REF" > .current_release
echo "Rollback to $ROLLBACK_REF successful!"
```

---

#### Architectural Decision: Why Single-Instance EC2 and Not AWS Lambda or AWS ECS/EKS?

| Compute Model | Background Worker Support | Execution Time Limits | Cold Starts | Cost Predictability | Verdict & Why Rejected for FinScan AI |
|---|---|---|---|---|---|
| **AWS EC2 Virtual Machine** (CHOSEN) | **Native:** Long-running SQS pollers and outbox dispatchers run 24/7 | **No timeout:** Jobs can process complex 100-page bank statements | Zero cold starts; server is always warm | **100% Fixed & Predictable:** ~$30/month flat (`t3.medium`) | ✅ **Selected:** Perfect fit for running our coordinated 7-container Docker Compose stack with zero timeout constraints. |
| **AWS Lambda** (Serverless Functions) | ❌ Poor: Cannot run continuous polling loops; requires EventBridge triggers | **Hard 15-minute cap:** Long-running batch document analysis times out | **5–15s Cold Starts:** Loading heavy Python AI libraries causes latency spikes | Variable; high execution costs under steady loan traffic | ❌ **Runtime Constraints:** Cannot host persistent PostgreSQL, Redis, or Caddy containers. Continuous outbox polling is awkward and costly on Lambda. |
| **AWS ECS / EKS** (Managed Containers) | Excellent | No timeout | Zero cold starts | High: Fargate vCPU/GB per-second billing + EKS control plane fees ($73/mo) | ❌ **Premature Complexity:** Adds complex task definitions, ALB configurations, and CloudWatch log groups for a workload that easily fits on a single EC2 instance. |

**How it is Useful for FinScan AI:**
By deploying on an EC2 instance, Balaji's background worker and outbox dispatcher run continuously without interruption, polling SQS and PostgreSQL in real-time with sub-millisecond local network latency between the app and its Redis/Postgres containers.

---

### 3.13 IAM Policy — `infra/iam_policy.json`

**What is IAM?**

AWS Identity and Access Management (IAM) controls what the EC2 server is allowed to do on AWS.

If we gave the EC2 instance full admin access, a hacker who compromised the server could:
- Delete all S3 files
- Create new EC2 instances (costing thousands of dollars)
- Read other AWS accounts' data

Instead, we give **only the minimum permissions needed** — called the **Principle of Least Privilege**.

**What Balaji's IAM policy allows:**
```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::finscan-dossiers-production/*"
      // Only objects inside our specific bucket. Not any other S3 bucket.
    },
    {
      "Effect": "Allow",
      "Action": ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage"],
      "Resource": "arn:aws:sqs:ap-south-1:123456789012:finscan-jobs-production"
      // Only our specific queue. Not any other SQS queue.
    }
  ]
}
```

**What is NEVER allowed:**
```
s3:*          → No wildcard S3 permissions
Resource: "*" → No permission on all resources
iam:*         → Never! Cannot create or modify IAM roles
ec2:*         → Never! Cannot launch more EC2 instances
```

**No hardcoded credentials:**

The EC2 instance has an "IAM Role" attached to it. When the code runs, boto3 automatically gets temporary credentials from the role:
```python
import boto3
s3 = boto3.client("s3", region_name="ap-south-1")
# No access key ID or secret key in the code!
# boto3 gets the credentials from the IAM Role automatically.
```

---

## PART 4: COMPLETE PROJECT FLOW — WHERE IS BALAJI'S CODE USED?

---

### 4.1 End-to-End Example: Ravi Kumar Applies for a Loan

---

**STEP 1: Create the Application**

```
Ravi opens the React web app and fills in the loan form.
He clicks "Submit".

→ Browser sends: POST /applications
  Body: { "applicant_name": "Ravi Kumar", "loan_amount": 500000 }

[★ BALAJI — apps/api/main.py]
  FastAPI receives the request.

[★ BALAJI — apps/api/routes/applications.py → create_application()]
  Generates application ID: "APP-3F9A1B2C"
  Creates ApplicationModel(id="APP-3F9A1B2C", status="UPLOADED")

[★ BALAJI — apps/api/db/models.py]
  Saves the record to the PostgreSQL "applications" table.

← Browser receives: { "application_id": "APP-3F9A1B2C", "status": "UPLOADED" }

React shows: "Application created! Now upload your documents."
```

---

**STEP 2: Upload a PDF Document (Salary Slip)**

```
Ravi drags his salary_slip.pdf into the upload box.

→ Browser sends: POST /applications/APP-3F9A1B2C/documents
  Header: X-User-Id: ravi@example.com
  Body: (multipart file upload)

[★ BALAJI — middleware/rate_limit.py → rate_limit_upload()]
  Hashes identity: sha256("ravi@example.com") → "a3f9c2b1"
  Checks Redis: Has ravi uploaded more than 5 times in the last 60 seconds?
  Answer: No (first upload) → ALLOWED

[★ BALAJI — documents.py → upload_document()]
  sanitize_filename("salary_slip.pdf") → "salary_slip.pdf" ✅ (safe)
  Generates document ID: "DOC-AB12345"

  Streams the file in 64 KB chunks:
  - Chunk 1: validate_file_signature → starts with b"%PDF" ✅ (real PDF)
  - Chunk 1, 2, 3...: accumulate SHA-256 hash
  - Total bytes: 245,678 < 10 MB ✅ (within size limit)

  Builds storage path: "dossiers/APP-3F9A1B2C/DOC-AB12345_salary_slip.pdf"

[★ BALAJI — adapters/storage/s3.py → S3Storage.put()]
  Uploads file to S3 with AES-256 encryption.
  Returns: "s3://finscan-dossiers-production/dossiers/APP-3F9A1B2C/DOC-AB12345_salary_slip.pdf"

[★ BALAJI — apps/api/db/models.py → DocumentModel]
  Saves document metadata to PostgreSQL "documents" table.
  Updates ApplicationModel.state_json:
    document_ids: ["DOC-AB12345"]
    document_manifest: {"DOC-AB12345": "s3://..."}
  Commits the database transaction.

← Browser receives: { "document_id": "DOC-AB12345", "sha256": "a3f9c2b1...", "size_bytes": 245678 }

React shows: "Upload successful!"
```

---

**STEP 3: Click "Start Processing"**

```
Ravi clicks the "Start Processing" button.

→ Browser sends: POST /applications/APP-3F9A1B2C/process

[★ BALAJI — applications.py → trigger_processing()]
  Locks the application row in PostgreSQL:
    SELECT * FROM applications WHERE id='APP-3F9A1B2C' FOR UPDATE
  Checks status: "UPLOADED" → can proceed ✅
  Checks documents: DOC-AB12345 exists ✅

[★ BALAJI — middleware/spend_guard.py → reserve_active_job_slot()]
  Checks Redis: How many active jobs does Ravi have right now?
  Answer: 0, which is less than the limit of 2 → ALLOWED
  Atomically reserves slot in Redis.
  Redis now stores: { "JOB-CD98765": expires_at_5:15PM }

  In a SINGLE ATOMIC DATABASE TRANSACTION:

  [★ BALAJI — models.py → JobModel]
    Creates JobModel(id="JOB-CD98765", status="QUEUED", attempt_count=1)

  [★ BALAJI — db/outbox.py → create_outbox_event()]
    Creates OutboxEventModel(status="PENDING", payload={ "job_id": "JOB-CD98765", ... })

  Updates ApplicationModel.status = "QUEUED"
  Appends to state_json.status_history: {from: "UPLOADED", to: "QUEUED"}

  → COMMIT — all 3 changes saved together, or none at all.

← Browser receives: { "job_id": "JOB-CD98765", "status": "QUEUED" }

React shows: "Processing started! Job ID: JOB-CD98765"
```

---

**STEP 4: Outbox Dispatcher Publishes the Job (Background)**

```
The Outbox Dispatcher is a separate background process running continuously.

[★ BALAJI — outbox_dispatcher.py → run_dispatcher_loop()]
  Polls every 1 second.

[★ BALAJI — db/outbox.py → dispatch_pending_outbox_events()]
  Runs: SELECT * FROM outbox_events WHERE status='PENDING' FOR UPDATE SKIP LOCKED
  Finds: OutboxEventModel with payload { "job_id": "JOB-CD98765", ... }

  Validates the payload against the JobRef schema.

[★ BALAJI — adapters/queue/sqs_queue.py → SQSQueue.publish()]
  (On production)
  Sends a message to SQS: "finscan-jobs-production" queue.

  Updates OutboxEventModel.status = "PUBLISHED"
  Commits to database.

  Logs: "Dispatched: claimed=1, published=1"
```

---

**STEP 5: Worker Picks Up the Job**

```
[★ BALAJI — worker/main.py → create_worker()]
  get_queue_adapter() → SQSQueue (because QUEUE_BACKEND=sqs in .env)
  get_storage_adapter() → S3Storage (because STORAGE_BACKEND=s3 in .env)
  Creates ApplicationWorker(queue=SQSQueue, storage=S3Storage, checkpointer=SqliteSaver)

[BHANU — worker/consumer.py → ApplicationWorker.start()]
  Polls SQS for new messages.
  Receives: { "job_id": "JOB-CD98765", "application_id": "APP-3F9A1B2C" }

[BHANU — LeaseHeartbeat starts]
  Background thread runs every 10 seconds.
  Extends SQS visibility timeout by 30 seconds.
  This prevents the message from being re-delivered if the job takes a long time.

[BHANU — process_delivery()]
  Gets document manifest from the job payload:
    { "DOC-AB12345": "s3://finscan-dossiers-production/dossiers/APP-3F9A1B2C/..." }

[★ BALAJI — adapters/storage/s3.py → S3Storage.get()]
  Downloads the PDF bytes from S3.
  Returns raw bytes of salary_slip.pdf in memory.
```

---

**STEP 6: LangGraph AI Pipeline Runs**

```
[MEMBER 4 — OCR Extractor]
  Sends PDF bytes to Azure Document Intelligence.
  Receives: "Net Salary: 44,200" at page 1, bounding box (100, 200, 300, 220).
  Creates: PayslipFacts(net_salary=MoneyFact(amount=44200, page=1, bbox=...))

[MEMBER 3 — LangGraph Pipeline nodes]
  → classify_document_node
  → extract_payslip_node
  → extract_bank_statement_node
  → extract_tax_return_node
  → run_deterministic_rules_node  ← Python code does the math!
    dti = 2800 / 44200 = 6.33%
    findings = [{ rule: "DTI", result: "PASS", value: 6.33 }]

[MEMBER 5 — RAG]
  Retrieves relevant credit policy text:
    "Debt-to-Income ratio must be under 50%"
  Validates that 6.33% < 50% → PASS

[MEMBER 3 — LangGraph interrupt()]
  Pipeline pauses and marks: "Human review required"

[BHANU — Worker commits results to database]
  Updates ApplicationModel.state_json:
    payslip: { net_salary: 44200, ... }
    findings: [{ rule: "DTI", result: "PASS", value: 6.33 }]
    summary_markdown: "Ravi's application has been verified..."
  Updates ApplicationModel.status = "READY_FOR_REVIEW"

[BHANU — Acknowledges the SQS message]
  Calls SQS delete_message → removes the message from the queue (job done!)

[★ BALAJI — middleware/spend_guard.py → release_active_job_slot()]
  Removes the reservation from Redis.
  Redis now stores: {} (0 active jobs for Ravi)
  Ravi can now start a new job.
```

---

**STEP 7: React UI Polls for Status**

```
React app automatically checks the job status every 3 seconds.

→ Browser sends: GET /jobs/JOB-CD98765

[★ BALAJI — middleware/rate_limit.py → rate_limit_polling()]
  Checks Redis: has Ravi polled more than 30 times in the last 60 seconds?
  Answer: No → ALLOWED

[★ BALAJI — review.py → get_job_status()]
  Reads JobModel from PostgreSQL.
  Returns: { "status": "COMPLETED" }

React detects "COMPLETED" → fetches the full application details.

→ Browser sends: GET /applications/APP-3F9A1B2C

[★ BALAJI — applications.py → get_application()]
  Reads ApplicationModel from PostgreSQL.
  Returns: entire state_json with all findings and extracted facts.

React renders the 3-panel dashboard:
  Left panel:   PDF with bounding boxes drawn around key numbers
  Center panel: Table of extracted facts (salary, income, DTI ratio)
  Right panel:  Findings with PASS / FAIL badges
  Bottom:       "APPROVE" and "REJECT" buttons
```

---

**STEP 8: Underwriter Reviews and Approves**

```
The bank underwriter reviews everything and clicks "APPROVE".

→ Browser sends: POST /applications/APP-3F9A1B2C/review
  Body: {
    "decision": "APPROVED",
    "reviewer_id": "underwriter_john",
    "notes": "All documents verified. Salary is consistent."
  }

[★ BALAJI — review.py → submit_review()]
  Locks the application row: SELECT FOR UPDATE
  Checks status: "READY_FOR_REVIEW" ✅ (can be reviewed)

  Updates ApplicationModel:
    status = "REVIEWED"
    reviewer_id = "underwriter_john"
    state_json.reviewer_decision = "APPROVED"
    state_json.status_history → appends {from: READY_FOR_REVIEW, to: REVIEWED}

[★ BALAJI — models.py → AuditEventModel]
  Creates a permanent, immutable audit record:
    from_status = "READY_FOR_REVIEW"
    to_status   = "REVIEWED"
    actor       = "underwriter_john"
    decision    = "APPROVED"
    notes       = "All documents verified. Salary is consistent."
    timestamp   = "2026-09-11T11:30:00Z"

  This record can NEVER be deleted. It is the legal proof of the decision.

  → COMMITS both changes atomically to the database.

← Browser receives: { "decision": "APPROVED", "status": "REVIEWED" }

React shows: "Loan APPROVED! ✅"
```

---

## PART 5: THEORY — KEY CONCEPTS EXPLAINED SIMPLY

---

### 5.1 Hexagonal Architecture (Ports and Adapters)

This is one of the core design principles of the project.

**The idea:** The business logic (LangGraph, rules) should not care whether storage is S3 or a local folder. It should only care about the *interface* (a set of methods like `put`, `get`, `exists`).

```
         ┌────────────────────────────────────────────┐
         │          External World                    │
         │  Browser   SQS   S3   PostgreSQL           │
         └──────┬──────┬────┬────────┬───────────────┘
                │      │    │        │
         ┌──────▼──────▼────▼────────▼───────────────┐
         │          Adapters Layer        (Balaji + Bhanu)
         │  FastAPI   SQSQueue   S3Storage             │
         │  PostgresQueue   LocalFileSystemStorage     │
         └──────────────────────┬─────────────────────┘
                                │ (implements)
         ┌──────────────────────▼─────────────────────┐
         │          Ports / Interfaces   (Bhanu defines)
         │  QueuePort   StoragePort                    │
         └──────────────────────┬─────────────────────┘
                                │ (uses)
         ┌──────────────────────▼─────────────────────┐
         │          Core Business Logic  (Members 3,4,5)
         │  LangGraph   Rules   Extractors             │
         └────────────────────────────────────────────┘
```

The core never imports `boto3` or `psycopg` directly. It only calls `StoragePort.get()` and `QueuePort.publish()`. In tests, you can swap S3 for a fake in-memory storage — no actual AWS account needed.

---

### 5.2 At-Least-Once Delivery

Queue systems (like SQS) guarantee that a message will be delivered **at least once** — but not necessarily **exactly once**. The same message might be delivered twice in edge cases (e.g., network timeout).

Because of this, job handlers must be **idempotent** — running the same job twice must have the same result as running it once:

```python
def process_job(job_id):
    job = db.get(job_id)
    if job.status == "COMPLETED":
        return   # Already done — skip safely, no side effects
    # Do the actual processing...
    job.status = "COMPLETED"
    db.commit()
```

---

### 5.3 Atomic Transactions

A database transaction is "all or nothing":

```python
async with session.begin():
    session.add(JobModel(...))           # Change 1
    session.add(OutboxEventModel(...))   # Change 2
    app_model.status = "QUEUED"         # Change 3
# Commit → All 3 changes are saved together.
# If anything goes wrong → All 3 changes are rolled back.
# The database is never left in a half-saved state.
```

If the power goes out mid-transaction, PostgreSQL automatically rolls back to the previous consistent state.

---

### 5.4 CAP Theorem (Brief)

In any distributed system, you can only guarantee 2 of these 3 things:
- **C** — Consistency: Every read gets the most recent data
- **A** — Availability: The system always responds
- **P** — Partition Tolerance: Works even when the network is unreliable

FinScan AI's choices:
- **PostgreSQL** → Prioritises C + P (Consistency first)
- **Redis** → Prioritises A + P (Availability first, eventual consistency)

---

### 5.5 OWASP Security Defenses

OWASP is a list of the top security vulnerabilities in web applications. Balaji's code defends against several of them:

| OWASP Category | Attack | Balaji's Defense |
|---------------|--------|-----------------|
| Broken Access Control | Path traversal upload | `..` and `/` blocked in filenames |
| Cryptographic Failures | Unencrypted data | AES-256 in S3, HTTPS via Caddy |
| Injection | SQL injection | SQLAlchemy parameterized queries |
| Insecure Design | Unchecked API abuse | Fail-closed rate limiting and spend guards |
| Security Misconfiguration | API port exposed | Port 8000 only internal, Caddy on 443 |
| Credential Exposure | Access keys in code | IAM Role — no hardcoded keys |

---

## PART 6: COMPLETE MAP — WHERE IS BALAJI'S CODE TRIGGERED?

---

```
USER ACTION                          BALAJI'S CODE THAT RUNS
──────────────────────────────────────────────────────────────────
Create Application    ──────────────► applications.py → create_application()
                                      models.py → ApplicationModel INSERT
                                      db/session.py → get_db()

Upload PDF           ─────────────► rate_limit.py → rate_limit_upload()
                                     documents.py → sanitize_filename()
                                     documents.py → validate_file_signature()
                                     documents.py → upload_document()
                                     s3.py → S3Storage.put()          (production)
                                     local_fs.py → put()              (local dev)
                                     models.py → DocumentModel INSERT
                                     models.py → ApplicationModel UPDATE

Start Processing     ─────────────► applications.py → trigger_processing()
                                     spend_guard.py → reserve_active_job_slot()
                                     models.py → JobModel INSERT
                                     outbox.py → create_outbox_event()
                                     models.py → OutboxEventModel INSERT
                                     ← All 5 changes in 1 single transaction!

Outbox Dispatch      ─────────────► outbox_dispatcher.py → run_dispatcher_loop()
(Background process)                 outbox.py → dispatch_pending_outbox_events()
                                     sqs_queue.py → SQSQueue.publish()  (production)
                                     pg_queue.py → publish()            (local dev)

Worker Startup       ─────────────► worker/main.py → get_queue_adapter()
                                     worker/main.py → get_storage_adapter()
                                     worker/main.py → create_worker()
                                     → Passes S3Storage and SQSQueue into Bhanu's Worker

PDF Read by Worker   ─────────────► s3.py → S3Storage.get()           (production)
(Bhanu's code calls it)              local_fs.py → get()               (local dev)

OCR + LangGraph      ─────────────► [Members 3, 4, 5 — NOT Balaji's code]
Pipeline Runs

Results Saved        ─────────────► models.py → ApplicationModel UPDATE (state_json)
(After pipeline)                     models.py → JobModel status = COMPLETED

Job Completes        ─────────────► spend_guard.py → release_active_job_slot()
                                     Redis slot is freed for the user

Poll Job Status      ─────────────► rate_limit.py → rate_limit_polling()
                                     review.py → get_job_status()
                                     models.py → JobModel SELECT

Get Application Data ─────────────► applications.py → get_application()
                                     models.py → ApplicationModel SELECT

Underwriter Reviews  ─────────────► review.py → submit_review()
                                     models.py → ApplicationModel UPDATE
                                     models.py → AuditEventModel INSERT

Cancel a Job         ─────────────► review.py → cancel_job()
                                     spend_guard.py → release_active_job_by_id()
                                     models.py → JobModel status = CANCELLED
                                     models.py → AuditEventModel INSERT

Health Check         ─────────────► main.py → health_check()
                                     config.py → settings.RELEASE_VERSION

Server Bootstrap     ─────────────► infra/ec2_setup.sh
Deploy New Version   ─────────────► infra/deploy.sh + infra/version.sh
Emergency Rollback   ─────────────► infra/rollback.sh
Clean Teardown       ─────────────► infra/teardown.sh (dry-run by default!)
```

---

## FINAL SUMMARY — BALAJI'S IMPACT ON THE SYSTEM

```
Without Balaji's code:

├── No API           → Member 7's React UI has no server to talk to
├── No Database      → Data cannot be saved — everything disappears on restart
├── No Rate Limiting → Server can be overwhelmed by too many requests
├── No Spend Guard   → AWS costs could spiral out of control
├── No Outbox        → Processing jobs can silently disappear
├── No S3 Selection  → Worker crashes in production (always uses local storage)
├── No Docker Setup  → Services cannot start in the right order
├── No Caddy         → No HTTPS, no security headers, no SSL certificate
├── No EC2 Scripts   → Cannot deploy to AWS
└── No IAM Policy    → AWS account could be compromised
```

**Balaji is like the foundation of a building.**
Every other team member's work (UI, AI pipeline, OCR, RAG, ML) sits on top of Balaji's infrastructure.
Remove the foundation — everything collapses.

---

> **Tests: 180/180 passed ✅ | Ruff: Clean ✅ | AWS Deployment: Ready 🟢**

---

## 🚀 PART 10: LATEST PRODUCTION ENHANCEMENTS & ARCHITECTURE UPDATES

---

### 10.1 `PgBouncer` Connection Pooling (Port 6432 vs 5432)

**The Real-World Problem:**
In high-throughput production, Gunicorn manages 4 concurrent worker processes, and the async worker runs parallel jobs. Each worker maintains its own SQLAlchemy connection pool. Without pooling, connections quickly exceed PostgreSQL's default `max_connections = 100`, crashing the database with `too many connections` errors!

**The Solution:**
Balaji integrated **`PgBouncer`** in transaction-pooling mode on port `6432`:
- **`DATABASE_URL` (Port 6432):** All standard API queries and background worker tasks route through `PgBouncer`. Hundreds of concurrent web requests efficiently share a small pool of 20 physical Postgres connections.
- **`ALEMBIC_DATABASE_URL` (Port 5432):** Database migrations bypass PgBouncer and connect directly to Postgres on `:5432` because schema DDL commands (table creation/alteration) cannot run through transaction pooling.
- **`DATABASE_STATEMENT_CACHE_SIZE=0`:** Configured in `session.py` to ensure `asyncpg` remains 100% compatible with PgBouncer's transaction mode.

---

### 10.2 Gunicorn Process Supervisor with `UvicornWorker`

Instead of running a single raw Uvicorn process, production now uses **Gunicorn** to supervise worker processes:
- Controlled by `API_WORKERS` setting (default 4).
- **Auto-Crash Recovery:** If a worker process crashes due to an out-of-memory error, Gunicorn instantly restarts a fresh worker without dropping traffic or crashing other workers.
- **Graceful Zero-Downtime Reloads:** Allows code updates without disconnecting active users.

---

### 10.3 Native Systemd Service Topology

Balaji upgraded the EC2 deployment topology from Docker Compose to native, production-grade **systemd** daemon services:
- `finscan-api.service`: Supervises the FastAPI Gunicorn web application.
- `finscan-worker.service`: Runs the background queue consumer daemon 24/7.
- `finscan-outbox-dispatcher.service`: Dedicated poller dispatching pending outbox jobs into the queue.
- **Auto-Restart on Reboot:** If the EC2 instance reboots, all three services start automatically in the correct dependency order.

---

### 10.4 Eager RAG Warmup in FastAPI Lifespan

**The Bottleneck:**
Previously, the RAG policy index was loaded lazily when the first user asked a question. This caused the first user to experience an 8-to-12-second delay while the entire policy corpus was embedded.

**The Fix:**
Balaji added an eager RAG warmup to the FastAPI `lifespan` startup hook in `main.py`. The shared `IndexManager` singleton loads and embeds the policy corpus into memory before accepting any web traffic. The first request is served in under 15 milliseconds!

---

### 10.5 Smart Redis Q&A Answer Caching

Underwriters frequently ask common questions about loan files (e.g. *"What is the DTI ratio?"*).
- Balaji added Redis caching for `/applications/{id}/questions`.
- **Cache Key:** Composite key based on `(application_id, question, dossier.updated_at)`.
- **Instant Invalidation:** If the dossier changes (document reclassification, pipeline re-run, or underwriter decision), the cache is immediately invalidated so stale answers are never served.

---

### 10.6 Elevated Pipeline Re-Run Support (`POST /applications/{id}/process`)

Previously, `/process` was restricted to newly uploaded applications.
Balaji enhanced the endpoint to support **re-running the verification pipeline from active and supplemental states**. If an underwriter reclassifies a document or uploads supplementary files, they can trigger an elevated re-verification run with a single click from the UI!
