# LangGraph Workflow Documentation

**Stateful Orchestration with Human-in-the-Loop Checkpoints**

---

## 📋 Overview

FinScan AI uses LangGraph for orchestrating the document processing pipeline. The StateGraph ensures transactional state management, checkpoint persistence, and explicit `interrupt()` points for human review.

---

## 🔄 StateGraph Architecture

```mermaid
stateDiagram-v2
    [*] --> UPLOADED: Application Created
    
    UPLOADED --> QUEUED: Job Published to Queue
    
    QUEUED --> PROCESSING: Worker Starts Processing
    
    PROCESSING --> Triage: triage_node
    
    Triage --> FAILED: Empty Dossier
    Triage --> OCRClassify: Valid Manifest
    
    OCRClassify --> ExtractFacts: ocr_and_classify_node
    
    ExtractFacts --> EvaluateRules: extract_facts_node
    
    EvaluateRules --> RetrievePolicy: evaluate_rules_node
    
    RetrievePolicy --> Synthesize: retrieve_policy_node
    
    Synthesize --> ValidateGrounding: synthesize_summary_node
    
    ValidateGrounding --> READY_FOR_REVIEW: validate_grounding_node
    
    READY_FOR_REVIEW --> Halt: interrupt() Checkpoint
    
    Halt --> REVIEWED: Human Approves
    Halt --> NEEDS_INFORMATION: Human Requests Info
    Halt --> CANCELLED: Human Cancels
    
    FAILED --> [*]
    REVIEWED --> [*]
    NEEDS_INFORMATION --> [*]
    CANCELLED --> [*]
    
    note right of Halt
        System PAUSES here
        Awaiting human decision
    end note
```

---

## 🧩 Node Execution Sequence

```mermaid
graph TB
    subgraph "Node 1: Triage"
        T1[triage_node] --> T2{Dossier Valid?}
        T2 -->|Empty| T3[Transition to FAILED]
        T2 -->|Valid| T4[Continue to OCR]
    end
    
    subgraph "Node 2: OCR & Classify"
        O1[ocr_and_classify_node] --> O2[Route PDF Pages]
        O2 --> O3[Native Text: PyMuPDF]
        O2 --> O4[Scanned: PaddleOCR]
        O2 --> O5[Fallback: Textract]
        O3 --> O6[Classify Pages]
        O4 --> O6
        O5 --> O6
    end
    
    subgraph "Node 3: Extract Facts"
        E1[extract_facts_node] --> E2[Payslip Extractor]
        E1 --> E3[Bank Statement Extractor]
        E1 --> E4[Tax Return Extractor]
        E1 --> E5[ID Card Extractor]
        E2 --> E6[Bind EvidenceRefs]
        E3 --> E6
        E4 --> E6
        E5 --> E6
    end
    
    subgraph "Node 4: Evaluate Rules"
        R1[evaluate_rules_node] --> R2[RULE-COMP-01]
        R2 --> R3[RULE-INC-01]
        R3 --> R4[RULE-TAX-01]
        R4 --> R5[RULE-ID-01]
        R5 --> R6[Aggregate Findings]
    end
    
    subgraph "Node 5: Retrieve Policy"
        P1[retrieve_policy_node] --> P2[Hybrid Search BM25+Dense]
        P2 --> P3[RRF Fusion]
        P3 --> P4[Ranked Policy Chunks]
    end
    
    subgraph "Node 6: Synthesize Summary"
        S1[synthesize_summary_node] --> S2[LLM Generates Narrative]
        S2 --> S3[Credit Appraisal Memo]
    end
    
    subgraph "Node 7: Validate Grounding"
        G1[validate_grounding_node] --> G2{All Claims Cited?}
        G2 -->|No| G3[Strip Ungrounded Claims]
        G2 -->|Yes| G4[Accept Memo]
        G3 --> G4
        G4 --> G5[State: READY_FOR_REVIEW]
    end
    
    subgraph "Node 8: Human Review (INTERRUPT)"
        H1[human_review_node] --> H2[interrupt() HALT]
        H2 --> H3{Wait for Resume}
        H3 -->|APPROVED| H4[State: REVIEWED]
        H3 -->|REJECTED| H5[State: FAILED]
        H3 -->|NEEDS_INFO| H6[State: NEEDS_INFORMATION]
    end
    
    T4 --> O1
    O6 --> E1
    E6 --> R1
    R6 --> P1
    P4 --> S1
    S3 --> G1
    G5 --> H1
    
    style H2 fill:#F44336,color:#FFF
    style G1 fill:#FF9800
    style R1 fill:#9C27B0
```

---

## 📦 State Schema

```mermaid
classDiagram
    class LoanApplicationState {
        +str application_id
        +ApplicationStatus status
        +List~DocumentMeta~ documents
        +Optional~Dict~ extracted_facts
        +List~Finding~ findings
        +Optional~str~ credit_appraisal_memo
        +List~EvidenceRef~ evidence_refs
        +Optional~Dict~ reviewer_decision
        +int attempt_count
        +datetime created_at
        +datetime updated_at
    }
    
    class ApplicationStatus {
        <<enumeration>>
        UPLOADED
        QUEUED
        PROCESSING
        READY_FOR_REVIEW
        NEEDS_INFORMATION
        REVIEWED
        FAILED
        CANCELLED
    }
    
    class DocumentMeta {
        +str document_id
        +str document_type
        +str storage_key
        +int page_count
        +datetime uploaded_at
    }
    
    class ExtractedFacts {
        +Optional~PayslipFacts~ payslips
        +Optional~BankStatementFacts~ bank_statement
        +Optional~TaxReturnFacts~ tax_return
        +Optional~ApplicantFact~ applicant
    }
    
    class Finding {
        +str rule_id
        +str rule_name
        +FindingVerdict verdict
        +str reason
        +List~EvidenceRef~ supporting_evidence
        +str policy_version
    }
    
    class FindingVerdict {
        <<enumeration>>
        pass
        flag
        unknown
    }
    
    LoanApplicationState --> ApplicationStatus
    LoanApplicationState --> DocumentMeta
    LoanApplicationState --> ExtractedFacts
    LoanApplicationState --> Finding
    Finding --> FindingVerdict
```

---

## 🔀 Conditional Edge Routing

```mermaid
graph LR
    subgraph "Triage Node Routing"
        A[triage_node] --> B{Dossier Check}
        B -->|Empty or Corrupted| C[FAILED State]
        B -->|Valid Manifest| D[Continue to OCR]
    end
    
    subgraph "Human Review Routing"
        E[human_review_node] --> F{Reviewer Decision}
        F -->|APPROVED| G[REVIEWED State]
        F -->|REJECTED| H[FAILED State]
        F -->|NEEDS_INFO| I[NEEDS_INFORMATION State]
    end
    
    style B fill:#FFF9C4
    style F fill:#FFF9C4
```

---

## 💾 Checkpoint Persistence

```mermaid
sequenceDiagram
    participant N as LangGraph Node
    participant S as StateGraph
    participant C as PostgreSQL Checkpointer
    participant DB as PostgreSQL Database
    
    N->>S: Execute Node Logic
    S->>S: Update State Object
    
    S->>C: Save Checkpoint
    C->>DB: BEGIN TRANSACTION
    DB->>DB: UPDATE applications SET state = ?
    DB->>DB: INSERT INTO checkpoints (thread_id, checkpoint)
    DB->>C: COMMIT
    
    C-->>S: Checkpoint Saved
    
    alt Interrupt Point
        S->>S: Pause Execution
        S->>N: Return to Worker
        N->>N: Wait for Resume Signal
    else Continue
        S->>N: Proceed to Next Node
    end
    
    Note over S,DB: Atomic state persistence<br/>ensures crash recovery
```

---

## 🔄 Resume from Interrupt

```mermaid
sequenceDiagram
    participant U as Underwriter
    participant API as FastAPI Endpoint
    participant LG as LangGraph Runtime
    participant CP as Checkpointer
    participant DB as PostgreSQL
    
    Note over LG,DB: System is PAUSED at interrupt()
    
    U->>API: POST /applications/{id}/review
    API->>API: Validate decision: APPROVED|REJECTED|NEEDS_INFO
    
    API->>CP: Load Checkpoint (thread_id = app_id)
    CP->>DB: SELECT checkpoint FROM checkpoints
    DB-->>CP: Serialized State
    CP-->>API: LoanApplicationState
    
    API->>LG: graph.update_state(config, {"reviewer_decision": decision})
    LG->>DB: UPDATE state with decision
    
    API->>LG: graph.invoke(None, config=config)
    
    Note over LG: Resumes from interrupt point
    
    LG->>LG: Execute human_review_node
    LG->>LG: Transition to REVIEWED/FAILED/NEEDS_INFORMATION
    
    LG->>CP: Save Final Checkpoint
    CP->>DB: COMMIT Final State
    
    LG-->>API: Final State
    API-->>U: 200 OK + Updated Application
```

---

## 🛡️ Error Handling & Recovery

```mermaid
graph TB
    subgraph "Error Detection"
        A[Node Execution] --> B{Exception?}
        B -->|No| C[Continue Pipeline]
        B -->|Yes| D{Error Type}
    end
    
    subgraph "Error Classification"
        D -->|Retryable| E[Transient Error]
        D -->|Non-Retryable| F[Permanent Failure]
        
        E --> G[Extend Lease]
        G --> H[Retry Node]
        
        F --> I[Transition to FAILED]
        I --> J[Log to Audit]
        J --> K[Notify via DLQ]
    end
    
    subgraph "Recovery Strategies"
        H --> L{Retry Count <= 3?}
        L -->|Yes| A
        L -->|No| M[Route to DLQ]
        
        M --> N[Manual Investigation]
        N --> O[Fix & Reprocess]
    end
    
    style D fill:#FFF9C4
    style E fill:#FFCCBC
    style F fill:#E57373
    style O fill:#C8E6C9
```

---

## 🔍 Idempotency Guarantees

```mermaid
graph LR
    subgraph "Duplicate Job Scenario"
        A[Job Arrives] --> B{Job ID in DB?}
        B -->|No| C[Process Normally]
        B -->|Yes| D{Already Processed?}
        
        D -->|Yes| E[Skip Processing]
        D -->|No| F{In Progress?}
        
        F -->|Yes| G[Wait for Completion]
        F -->|No| H[Resume Processing]
        
        C --> I[Save Results]
        E --> J[Return Existing Results]
        G --> K[Poll for Results]
        H --> I
    end
    
    style B fill:#FFF9C4
    style D fill:#FFF9C4
    style F fill:#FFF9C4
    style I fill:#81C784
    style J fill:#64B5F6
```

---

## 📊 Node Execution Metrics

```mermaid
graph TB
    subgraph "Performance Benchmarks"
        A[OCR & Classify] --> A1["~5-10s<br/>(10-15 pages/min)"]
        B[Extract Facts] --> B1["~2-3s<br/>(rule-based extraction)"]
        C[Evaluate Rules] --> C1["<1s<br/>(deterministic math)"]
        D[Retrieve Policy] --> D1["~200ms<br/>(FAISS search)"]
        E[Synthesize Summary] --> E1["~3-5s<br/>(LLM generation)"]
        F[Validate Grounding] --> F1["<1s<br/>(citation check)"]
    end
    
    subgraph "Total Pipeline Time"
        Total --> T1["Normal Case: 15-20s"]
        Total --> T2["With OCR: 30-90s"]
        Total --> T3["With Textract: 60-120s"]
    end
    
    A1 --> Total
    B1 --> Total
    C1 --> Total
    D1 --> Total
    E1 --> Total
    F1 --> Total
    
    style T1 fill:#C8E6C9
    style T2 fill:#FFF9C4
    style T3 fill:#FFCCBC
```

---

## 🚫 Anti-Patterns to Avoid

### ❌ DON'T: Let LLM Make Financial Decisions

```mermaid
graph LR
    A[Extracted Facts] --> X[LLM: Calculate DTI]
    X --> Y[LLM: Approve/Reject]
    Y --> Z[Risk: Hallucination!]
    
    style Z fill:#E57373
```

### ✅ DO: Deterministic Rules + LLM Explanation

```mermaid
graph LR
    A[Extracted Facts] --> B[Deterministic Rule<br/>Calculate DTI]
    B --> C[Rule Verdict: pass/flag]
    C --> D[LLM: Explain Why]
    D --> E[Auditable Result]
    
    style E fill:#81C784
```

---

## 📚 Related Documentation

- [System Overview](system_overview.md) - Complete pipeline architecture
- **Contracts reference** - state schema in [`core/contracts/state.py`](../core/contracts/state.py); evidence/facts/findings alongside it
- [Worker Implementation](worker_queue_architecture.md) - Consumer loop details
- **Resume endpoint** - see [`apps/api/routes/review.py`](../apps/api/routes/review.py)
