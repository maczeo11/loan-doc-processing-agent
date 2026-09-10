# FinScan AI — Local Docker Compose Runtime (Phase 6)

Reproducible local development and demo environment running all core FinScan AI services.

---

## 1. Services Architecture

| Service | Image / Build | Role & Dependencies | Port / Access |
| :--- | :--- | :--- | :--- |
| **`db`** | `postgres:16-alpine` | Authoritative PostgreSQL 16 database. Healthchecked via `pg_isready`. | `5432` |
| **`redis`** | `redis:7-alpine` | Transient rate limiting, identity tracking, and spend guards. Healthchecked via `redis-cli ping`. | `6379` |
| **`migrate`** | `infra/Dockerfile.api` | One-shot migration service running `alembic upgrade head`. Waits for `db: service_healthy`. | None |
| **`api`** | `infra/Dockerfile.api` | FastAPI application. Waits for `migrate: service_completed_successfully`, `db`, and `redis`. Mounts shared `dossiers_storage`. | `8000` (internal / direct) |
| **`outbox-dispatcher`**| `infra/Dockerfile.api` | Standalone polling loop (`python -m apps.api.outbox_dispatcher`). Reads `PENDING` outbox events and pushes to PostgreSQL queue. | None |
| **`worker`** | `infra/Dockerfile.worker`| Asynchronous pipeline consumer (`python -m worker.main`). Claims queued jobs via `SELECT ... FOR UPDATE SKIP LOCKED`. | None |
| **`caddy`** | `caddy:2-alpine` | Reverse proxy routing incoming HTTP requests to `api:8000`. | `80` (public HTTP) |

---

## 2. Startup Instructions

### Validate Compose Specification
```bash
docker compose -f infra/docker-compose.yml config
```

### Start All Services
```bash
docker compose -f infra/docker-compose.yml up --build -d
```
*Note*: The `migrate` container automatically runs `alembic upgrade head` before `api`, `outbox-dispatcher`, and `worker` start.

---

## 3. Local Verification & Smoke-Test Flow

### Step 1: Verify Service Health & Caddy Reverse Proxy
```bash
# Verify Caddy proxies to FastAPI /health
curl -s http://localhost/health
# Expected output: {"status":"ok","service":"finscan-api","timestamp":"..."}
```

### Step 2: Create a Loan Application
```bash
curl -s -X POST http://localhost/applications   -H "Content-Type: application/json"   -d '{"applicant_name": "Demo Applicant", "loan_amount": 150000.0, "loan_purpose": "Home Refinance"}'
# Note the returned application_id (e.g. APP-XXXXXXXX)
```

### Step 3: Upload a Valid Document
```bash
curl -s -X POST http://localhost/applications/{APPLICATION_ID}/documents   -H "X-User-Id: demo-user"   -F "file=@tests/fixtures/sample_payslip.pdf;type=application/pdf"
```

### Step 4: Trigger Application Processing
```bash
curl -s -X POST http://localhost/applications/{APPLICATION_ID}/process   -H "X-User-Id: demo-user"
# Returns 202 Accepted with job_id (e.g. JOB-XXXXXXXX)
```

### Step 5: Check Job Status & Outbox Dispatch
```bash
# Poll job status
curl -s http://localhost/jobs/{JOB_ID}   -H "X-User-Id: demo-user"
```

### Step 6: Verify Persistence Across Container Recreation
```bash
# Restart or recreate the API container
docker compose -f infra/docker-compose.yml restart api

# Fetch the application; data survives intact from PostgreSQL volume
curl -s http://localhost/applications/{APPLICATION_ID}
```

---

## 4. Log Inspection

```bash
# View combined logs
docker compose -f infra/docker-compose.yml logs -f

# Inspect specific services
docker compose -f infra/docker-compose.yml logs -f api
docker compose -f infra/docker-compose.yml logs -f outbox-dispatcher
docker compose -f infra/docker-compose.yml logs -f worker
docker compose -f infra/docker-compose.yml logs -f migrate
```

---

## 5. Shutdown & Cleanup

```bash
# Stop containers while preserving database and storage volumes
docker compose -f infra/docker-compose.yml down

# Stop containers and remove persistent volumes (full reset)
docker compose -f infra/docker-compose.yml down -v
```

---

## 6. Worker & Queue Coordination Notes

1. **Queue Backend**: Configured with `QUEUE_BACKEND=postgres`. The `outbox-dispatcher` publishes jobs into the `outbox_jobs` table, and `worker` claims them using `SELECT ... FOR UPDATE SKIP LOCKED`.
2. **Shared Storage**: Both `api` and `worker` mount the named volume `dossiers_storage` at `/app/data/storage`. Files uploaded through the API are directly readable by the worker OCR parser without requiring S3 credentials during local demo runs.
3. **Database Driver Compatibility**: API uses async `asyncpg`, while outbox dispatcher and worker use `psycopg`. `apps/api/config.py` provides `AsyncCompatibleDsn` so both drivers operate seamlessly from a single unified `DATABASE_URL`.


---

# FinScan AI — AWS Cloud Deployment & Operations Automation (Phase 7)

> [!IMPORTANT]
> **PRE-PROVISIONING NOTICE:**  
> All automation scripts and configurations in this directory have been validated locally. **NO CLOUD RESOURCES HAVE BEEN PROVISIONED YET.** Executing `aws_setup.sh` or deploying to EC2 requires your team's real AWS credentials, domain name, and designated target instance ID.

---

## 7. Cloud Prerequisites

Before running any deployment script against AWS:

1. **AWS CLI Credentials:**
   Ensure your local terminal or CI/CD runner is authenticated:
   ```bash
   aws sts get-caller-identity
   ```
2. **Domain & DNS Records:**
   For automatic Let's Encrypt TLS in Caddy, configure an `A` record pointing your domain (e.g., `finscan.demo.internal` or `api.yourdomain.com`) to the EC2 instance's Elastic/Public IP.
3. **EC2 Security Group Rules:**
   - **Inbound:** Port `80` (HTTP) and `443` (HTTPS) open to `0.0.0.0/0`.
   - **Inbound:** Port `22` (SSH) restricted to authorized developer IPs only.
   - **Internal/Blocked:** Ports `5432` (PostgreSQL) and `6379` (Redis) must **NEVER** be open to the public internet; they communicate exclusively across the internal Docker bridge network.
4. **Architecture Compatibility (ARM64 vs. x86_64):**
   - The primary target instance is AWS Graviton `t4g.medium` (ARM64).
   - Docker build scripts and base images (`python:3.11-slim`, `postgres:16-alpine`, `redis:7-alpine`, `caddy:2-alpine`) natively support both `linux/arm64` and `linux/amd64`.
   - Native PyMuPDF wheels and dependencies compile without changes on both architectures.

---

## 8. Environment Variables Reference

| Variable | Default | Description |
| :--- | :--- | :--- |
| `AWS_REGION` | `us-east-1` | Target AWS region for S3, SQS, and EC2. |
| `PROJECT_PREFIX` | `finscan` | Namespace prefix for all cloud resources. |
| `ENVIRONMENT` | `production` | Deployment environment tag (`production`, `staging`, `demo`). |
| `BUCKET_NAME` | `finscan-dossiers-production` | Private S3 bucket for loan dossiers and audit artifacts. |
| `QUEUE_NAME` | `finscan-jobs-production` | Primary SQS job queue. |
| `DLQ_NAME` | `finscan-jobs-dlq-production` | Dead-Letter Queue (DLQ) with `maxReceiveCount=3`. |
| `EC2_INSTANCE_ID`| *(None)* | Explicit instance ID (e.g. `i-0123456789abcdef0`) for start/stop/teardown. |
| `DOMAIN_NAME` | `localhost` | FQDN for Caddy TLS and reverse proxying. |
| `ACME_EMAIL` | `admin@example.com` | Notification email for Let's Encrypt certificates. |
| `RELEASE_VERSION`| `1.0.0` | Semantic version stamp displayed on `/health`. |

---

## 9. Operations Automation Runbook

### A. S3 and SQS Cloud Provisioning
Creates the private S3 bucket (with default SSE-S3 encryption, all 4 public access blocks enabled, restrictive CORS, and multipart lifecycle rules) and the SQS primary queue and DLQ:
```bash
export AWS_REGION="us-east-1"
export PROJECT_PREFIX="finscan"
export DOMAIN_NAME="finscan.demo.internal"

./infra/aws_setup.sh
```

### B. EC2 Instance Profile IAM Policy
Apply the least-privilege policy defined in `infra/iam_policy.json` to the EC2 instance role:
```bash
aws iam create-policy \
    --policy-name FinScanInstancePolicy \
    --policy-document file://infra/iam_policy.rendered.json
```

### C. EC2 Host Bootstrap
Run on a fresh Amazon Linux 2023 or Ubuntu EC2 instance to install Docker, Docker Compose, Git, set up `/opt/finscan` with non-root ownership, and prepare the environment:
```bash
chmod +x infra/ec2_setup.sh
sudo ./infra/ec2_setup.sh
```

### D. Deploying a Release
Deploys an explicit release tag or Git commit SHA, records the previous release for rollback safety, runs Alembic migrations, starts Compose, and verifies `/health`:
```bash
# Deploy latest commit
./infra/deploy.sh

# Or deploy a specific release tag
./infra/deploy.sh v1.0.1
```

### E. Safe Rollback
Rolls back to the previously recorded release (from `.previous_release`) or to an explicit target ref without destructive `git reset --hard` commands:
```bash
# Rollback to the previous release
./infra/rollback.sh

# Or rollback to a specific known-good tag
./infra/rollback.sh v1.0.0
```

### F. Cost Controls: Stop & Start EC2
Stop the EC2 instance outside demo hours to cease hourly compute billing:
```bash
export EC2_INSTANCE_ID="i-0123456789abcdef0"

# Stop instance
./infra/stop.sh

# Start instance when needed
./infra/start.sh
```

### G. Scoped Resource Teardown
Clean up cloud resources created for FinScan AI. Defaults to **DRY-RUN** mode for safety:
```bash
# 1. Preview what would be deleted (DRY-RUN)
./infra/teardown.sh

# 2. Perform live deletion (requires --confirm)
./infra/teardown.sh --confirm
```
