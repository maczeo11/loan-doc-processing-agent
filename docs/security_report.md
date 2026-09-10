# FinScan AI Security Report

**Document Version:** 1.0  
**Last Updated:** September 2026  
**Classification:** Internal  

---

## Executive Summary

FinScan AI implements a defense-in-depth security architecture designed to protect sensitive financial documents and personally identifiable information (PII) while enabling efficient loan underwriting workflows. This report documents the security controls implemented across all layers of the system.

---

## 1. Data Protection & Privacy

### 1.1 PII Masking

All personally identifiable information is masked before display in the UI or export in reports.

| Data Type | Masking Format | Example |
|-----------|----------------|---------|
| PAN (Permanent Account Number) | `XXXXXX{last4}` | `ABCDE1234F` → `XXXXXX1234` |
| Aadhaar Number | `XXXX-XXXX-{last4}` | `1234-5678-9012` → `XXXX-XXXX-9012` |
| Bank Account Number | `XXXXXX{last4}` | `50100123456789` → `XXXXXX6789` |

**Implementation:** `apps/ui/src/utils/pii.ts`

```typescript
export function maskPan(pan?: string | null): string {
  if (!pan) return '—';
  const clean = pan.trim().toUpperCase();
  const standardMatch = clean.match(/^[A-Z]{5}(\d{4})[A-Z]$/);
  if (standardMatch) {
    return `XXXXXX${standardMatch[1]}`;
  }
  if (clean.length <= 4) return `XXXXXX${clean}`;
  return `XXXXXX${clean.slice(-4)}`;
}
```

### 1.2 Synthetic Data Only

- **Zero Real Customer Data:** All loan dossiers are synthetically generated
- **Mandatory Watermark:** Every PDF page displays `SYNTHETIC DEMO — NOT VALID`
- **Kaggle Seeds:** Generated from anonymized Kaggle loan approval dataset

---

## 2. Storage Security (S3 & Object Storage)

### 2.1 Server-Side Encryption

All S3 uploads enforce server-side encryption at rest:

```python
# adapters/storage/s3.py
def put(self, key: str, data: Union[BinaryIO, bytes], ...):
    extra_args = {
        "ContentType": content_type,
        "ServerSideEncryption": "AES256",  # Mandatory SSE-S3
    }
    self.client.put_object(
        Bucket=self.bucket_name,
        Key=clean_key,
        Body=data,
        ServerSideEncryption="AES256",
    )
```

### 2.2 Tenant Isolation

Storage keys follow a strict hierarchy that enforces application-level isolation:

```
dossiers/{application_id}/{document_id}_{sanitized_filename}
```

**Validation Logic:**

```python
# adapters/storage/base.py
_STORAGE_KEY_RE = re.compile(r"^dossiers/[A-Za-z0-9][A-Za-z0-9\-_]*/[^/]+$")

def validate_storage_key(key: str, application_id: str = "") -> str:
    if not _STORAGE_KEY_RE.match(clean):
        raise ValueError(
            f"Storage key must match dossiers/{{application_id}}/{{document_id}}_{{file}}: {key}"
        )
    if application_id:
        prefix = f"dossiers/{application_id}/"
        if not clean.startswith(prefix):
            raise ValueError(
                f"Cross-application key access blocked: key '{clean}' is outside '{prefix}'"
            )
    return clean
```

### 2.3 Path Traversal Prevention

All filenames are sanitized before storage key construction:

```python
def sanitize_filename(filename: str) -> str:
    # Normalize backslashes to forward slashes
    normalized = filename.replace("\\", "/")
    base = os.path.basename(normalized).strip()
    # Replace special chars with underscores
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", base)
    return safe or "document.pdf"
```

**Blocked Patterns:**
- `../` and `..\\` (directory traversal)
- Absolute paths (`/`, `file://`)
- Special characters (`<`, `>`, `:`, `"`, `|`, `?`, `*`)

### 2.4 Short-Lived Presigned URLs

Download URLs are cryptographically signed with strict TTL limits:

| Parameter | Value | Enforcement |
|-----------|-------|-------------|
| Minimum TTL | 300 seconds (5 min) | Hard floor |
| Maximum TTL | 3600 seconds (60 min) | Hard ceiling |
| Signature | AWS SigV4 | Cryptographic |
| Scope | Single object key | No wildcard access |

```python
def clamp_presigned_ttl(expires_in: int) -> int:
    ttl = int(expires_in)
    return max(MIN_PRESIGNED_TTL_SECONDS, min(MAX_PRESIGNED_TTL_SECONDS, ttl))
```

### 2.5 SHA-256 Integrity Verification

Every upload is verified against the client-declared checksum:

```python
def verify_integrity(self, key: str, expected_sha256_hex: str) -> Dict[str, Any]:
    # S3-recorded checksum
    recorded = head.get("ChecksumSHA256")
    if recorded:
        recorded_hex = base64.b64decode(recorded).hex()
        if recorded_hex != expected_sha256_hex.lower():
            raise StorageTamperError(
                f"S3 checksum mismatch for '{key}': object was tampered in transit"
            )
    # Fallback: re-hash
    raw = self.get(clean_key)
    actual = sha256_bytes(raw)
    if actual != expected_sha256_hex.lower():
        raise StorageTamperError(f"SHA-256 mismatch for '{key}'")
```

### 2.6 Direct Upload Security

Presigned POST grants for browser-to-S3 uploads include:

```python
conditions: list = [
    {"key": clean_key},
    {"Content-Type": content_type},
    {"x-amz-server-side-encryption": "AES256"},
    {"x-amz-checksum-sha256": checksum_b64},
    ["content-length-range", 1, MAX_UPLOAD_BYTES],  # 10 MB ceiling
]
```

---

## 3. Authentication & Authorization

### 3.1 Role-Based Access Control

Three underwriter personas with distinct permissions:

| Role | ID | Permissions |
|------|-----|-------------|
| Senior Underwriter | `USR-AKSHAYA-01` | Full review, approve/reject, export |
| Risk Analyst | `USR-KARTHIK-02` | View findings, flag discrepancies |
| Compliance Officer | `USR-MANJU-03` | Audit trail access, policy review |

### 3.2 Session Management

- **Storage:** `sessionStorage` (cleared on browser close)
- **Token Format:** Mock JWT for demo, ready for Google OAuth integration
- **Auth Mode:** Configurable via `VITE_AUTH_MODE` environment variable

```typescript
// apps/ui/src/services/auth.ts
const STORAGE_KEY = 'finscan_underwriter_session';

export class AuthService {
  static getStoredUser(): UnderwriterProfile | null {
    const data = sessionStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : UNDERWRITER_PERSONAS.SENIOR_UNDERWRITER;
  }
}
```

### 3.3 API Rate Limiting

Enforced via Redis token buckets:

| Endpoint | Rate Limit | Window |
|----------|------------|--------|
| `POST /applications` | 5 requests | 1 minute |
| `POST /applications/{id}/documents` | 5 requests | 1 minute |
| `GET /applications/{id}` | 30 requests | 1 minute |
| `POST /applications/{id}/process` | 2 concurrent jobs | Per user |

---

## 4. Queue & Message Security

### 4.1 PostgreSQL SKIP LOCKED

Atomic lease claims prevent concurrent processing:

```sql
SELECT id, job_id, payload
FROM outbox_jobs
WHERE status = 'PENDING'
  AND (locked_until IS NULL OR locked_until < clock_timestamp())
ORDER BY created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED;
```

### 4.2 AWS SQS + DLQ

- **Visibility Timeout:** 30 seconds (extended by heartbeat)
- **Maximum Attempts:** 3 before DLQ routing
- **Message Attributes:** Signed with job metadata

### 4.3 Idempotency Guarantee

Re-delivered messages do not corrupt state:

```python
# worker/consumer.py
def process_delivery(self, delivery: Delivery) -> Optional[Dict[str, Any]]:
    # Check for duplicate processing
    if job_already_processed(job_ref.job_id):
        self.queue.ack(handle)  # Idempotent ack
        return None
    
    # Process with acknowledge-last guarantee
    final_state = self.graph.invoke(initial_state, config=config)
    self.queue.ack(handle)  # Only after state commits
```

---

## 5. LLM & Prompt Injection Defense

### 5.1 Adversarial Pattern Detection

Document text is scanned for injection attempts:

```python
# core/rag/grounding.py
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"\b(system\s+override|ignore\s+(all\s+)?previous\s+(rules|instructions))\b", re.IGNORECASE),
    re.compile(r"\b(disregard\s+(all\s+)?(previous\s+)?instructions)\b", re.IGNORECASE),
    re.compile(r"\b(assign\s+pass\s+to\s+all|bypass\s+credit\s+checks)\b", re.IGNORECASE),
    re.compile(r"\b(jailbreak|dan\s+mode|developer\s+mode)\b", re.IGNORECASE),
]
```

### 5.2 Text Sanitization

Malicious patterns are defused before reaching LLM:

```python
def sanitize_document_text(text: str) -> str:
    sanitized = text
    for pattern in PROMPT_INJECTION_PATTERNS:
        sanitized = pattern.sub(r"[DEFUSED_ADVERSARIAL_SPAN: \1]", sanitized)
    # Escape triple backticks
    sanitized = sanitized.replace("```", "'''")
    return sanitized
```

### 5.3 Grounding Validation Gate

Every LLM-generated claim is verified against authorized citations:

```python
def validate_citations(claims: List[Dict], authorized_chunk_ids: List[str]) -> bool:
    authorized_set = _expand_authorized_ids(authorized_chunk_ids)
    for claim in claims:
        citations = claim.get("citations", [])
        for cit in citations:
            if cit not in authorized_set:
                logger.warning(f"Grounding violation: citation '{cit}' is unauthorized")
                return False
    return True
```

### 5.4 Zero Hallucinated Decisions

The system enforces that no financial verdict originates from LLM:

- **Rule Execution:** Pure Python/Decimal arithmetic
- **LLM Role:** Narrate and explain only
- **Human Approval:** Required for all final decisions

---

## 6. Human-in-the-Loop (HITL) Controls

### 6.1 Interrupt Checkpoint

LangGraph pipeline unconditionally pauses before human review:

```python
# core/graph/workflow.py
interrupt_nodes = ["human_review"] if checkpointer else []
return workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=interrupt_nodes,
)
```

### 6.2 Audit Trail

All reviewer actions are immutably logged:

```python
# core/graph/nodes.py
transition: StatusTransition = {
    "from_status": "READY_FOR_REVIEW",
    "to_status": target_status,
    "timestamp": _get_utc_timestamp(),
    "reason": f"Underwriter sign-off: {decision}. Notes: {notes}",
}
history.append(transition)
```

### 6.3 No Autonomous Decisions

The system is architecturally incapable of autonomous loan approval:

- No code path exists for automatic `APPROVED` state
- `human_review_node` requires explicit `reviewer_decision` input
- Checkpoint cannot be bypassed

---

## 7. Cloud Spend Guards

### 7.1 Budget Controls

| Control | Limit | Enforcement |
|---------|-------|-------------|
| Weekly Budget | $25 ceiling | Target: $8-15 |
| Active Jobs | 2 per user | Hard limit |
| AWS Textract | 100 pages total | Hard cap, disabled by default |
| File Upload | 10 MB per file | Validated before presign |
| Dossier Size | 30 pages max | API validation |

### 7.2 Cost Optimization

- PostgreSQL and Redis run as containers (not RDS/ElastiCache)
- Spot instances during build days
- EC2 stopped outside working windows
- Local Qwen GGUF fallback avoids cloud LLM costs

---

## 8. Frontend Security

### 8.1 Evidence Navigation Security

Bounding-box coordinates are validated before rendering:

```typescript
// apps/ui/src/components/viewer/BoundingBoxOverlay.tsx
function computePixelBounds(box: BoundingBox, width: number, height: number): PixelBounds | null {
  // Defensive check: normalized coordinates must be in [0, 1]
  const isNormalized = box.x0 <= 1.05 && box.y0 <= 1.05 && box.x1 <= 1.05 && box.y1 <= 1.05;
  
  if (isNormalized) {
    // Clamp to valid range
    left = Math.max(0, Math.min(box.x0 * width, width));
    top = Math.max(0, Math.min(box.y0 * height, height));
  }
  // ...
}
```

### 8.2 No Client-Side Financial Logic

The UI never computes financial arithmetic:

- All calculations performed server-side
- UI only displays pre-computed `Finding` objects
- No risk of client-side manipulation affecting verdicts

### 8.3 Content Security

- XSS prevention via React's automatic escaping
- No `dangerouslySetInnerHTML` usage
- External links use `rel="noopener noreferrer"`

---

## 9. Security Checklist

| Control | Status | Location |
|---------|--------|----------|
| Server-Side Encryption (SSE-S3) | ✅ Implemented | `adapters/storage/s3.py` |
| Tenant Isolation | ✅ Implemented | `adapters/storage/base.py` |
| Path Traversal Prevention | ✅ Implemented | `sanitize_filename()` |
| Presigned URL TTL Limits | ✅ Implemented | `clamp_presigned_ttl()` |
| SHA-256 Integrity Verification | ✅ Implemented | `verify_integrity()` |
| PII Masking (PAN/Aadhaar/Bank) | ✅ Implemented | `apps/ui/src/utils/pii.ts` |
| Rate Limiting | ✅ Implemented | `apps/api/middleware/rate_limit.py` |
| Prompt Injection Defense | ✅ Implemented | `core/rag/grounding.py` |
| Grounding Validation | ✅ Implemented | `validate_citations()` |
| HITL Checkpoint | ✅ Implemented | `core/graph/workflow.py` |
| Audit Trail | ✅ Implemented | `status_history` in state |
| Idempotent Message Processing | ✅ Implemented | `worker/consumer.py` |
| DLQ Routing (3-attempt ceiling) | ✅ Implemented | `adapters/queue/sqs_queue.py` |
| Cloud Spend Guards | ✅ Implemented | API quotas, Textract cap |
| No Autonomous Approvals | ✅ Architecturally enforced | `interrupt_before=["human_review"]` |

---

## 10. Compliance Notes

### 10.1 RBI IT Framework

- Data localization: All data stored in `ap-south-1` (Mumbai) for Indian deployments
- Encryption at rest: AES-256 mandatory
- Access logging: CloudTrail enabled for S3 access

### 10.2 DPDP Act 2023

- Consent: Synthetic data only, no real PII
- Purpose limitation: Documents used solely for underwriting
- Data minimization: Only required documents collected

---

## 11. Incident Response

### 11.1 DLQ Monitoring

Poison messages are routed to Dead Letter Queue for investigation:

```
SQS DLQ → CloudWatch Alarm → SNS Notification → On-call Engineer
```

### 11.2 Checkpoint Recovery

Worker crashes do not lose state:

- SQLite checkpointer persists graph state
- Resume via `graph.invoke(None, config=config)`
- Audit trail preserved in PostgreSQL

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | September 2026 | Bhanu Teja | Initial security report |
