# LangGraph Workflow Documentation

**Authoritative Stateful Orchestration with Human-in-the-Loop Checkpoints**  
*Owned by Member 2 (Bhanu Teja — Team Lead & Orchestration Lead)*

---

## 📋 Overview

FinScan AI utilizes **LangGraph** (`StateGraph`) as its core orchestration engine. The stateful pipeline coordinates document perception, ML classification, fact extraction, deterministic rules, hybrid policy RAG, and auditable narrative synthesis. 

The execution strictly enforces the **Prime Invariant**:
> *"Deterministic code decides. AI explains. A human approves. Every number traces back to a page in a document."*

---

## 🔄 Lifecycle State Transitions

The pipeline moves through 8 lifecycle states defined in [`core/contracts/state.py`](../core/contracts/state.py). Every transition is appended immutably to `status_history`.

```mermaid
stateDiagram-v2
    [*] --> UPLOADED: Dossier Manifest Created
    UPLOADED --> QUEUED: Outbox Job Enqueued
    QUEUED --> PROCESSING: Worker Picks Up Lease

    state PROCESSING {
        [*] --> Triage: Node 1 (triage_node)
        Triage --> OCRClassify: Valid Manifest
        OCRClassify --> ExtractFacts: Node 2 (ocr_and_classify_node)
        ExtractFacts --> EvaluateRules: Node 3 (extract_facts_node)
        EvaluateRules --> RetrievePolicy: Node 4 (evaluate_rules_node)
        RetrievePolicy --> SynthesizeSummary: Node 5 (retrieve_policy_node)
        SynthesizeSummary --> ValidateGrounding: Node 6 (synthesize_summary_node)
        ValidateGrounding --> [*]: Node 7 (validate_grounding_node)
    }

    Triage --> FAILED: Empty / Invalid Manifest
    ValidateGrounding --> READY_FOR_REVIEW: Citation Gate Passed

    state READY_FOR_REVIEW {
        Paused: ⏸ interrupt_before=["human_review"]
        Paused --> Checkpointed: Snapshot to SqliteSaver
    }

    READY_FOR_REVIEW --> REVIEWED: Underwriter Approves / Rejects
    READY_FOR_REVIEW --> NEEDS_INFORMATION: Underwriter Requests Info
    READY_FOR_REVIEW --> CANCELLED: Reviewer Cancels

    FAILED --> [*]
    REVIEWED --> [*]
    NEEDS_INFORMATION --> [*]
    CANCELLED --> [*]
```

---

## 🧩 Detailed Node Execution Pipeline

```mermaid
flowchart TD
    Start([Worker: job_ref received]) --> N1[Node 1: triage_node]

    %% Node 1
    N1 -->|Empty dossier| FailEnd[Status: FAILED<br/>route_after_triage: __end__] --> EndNode([END])
    N1 -->|Valid manifest| N2[Node 2: ocr_and_classify_node]

    %% Node 2
    subgraph Perception_Classification [Perception & Classification]
        N2 --> Router[OCR Router: native PyMuPDF -> CPU Paddle/Tesseract]
        Router --> CacheText[(Cache in document_texts)]
        CacheText --> MLClass[TF-IDF + Logistic Regression Classifier]
        MLClass --> RejectionGate{Confidence >= 0.40?}
        RejectionGate -->|Yes| AssignClass[Assign Canonical Class]
        RejectionGate -->|No / Exception| KeywordFallback[Keyword Heuristic Fallback]
        AssignClass --> RAGIndex[Index Application Dossier]
        KeywordFallback --> RAGIndex
    end

    RAGIndex --> N3[Node 3: extract_facts_node]

    %% Node 3
    subgraph Extraction [Fact Extraction with Provenance]
        N3 --> ReuseCache[Reuse cached document_texts]
        ReuseCache --> PExt[PayslipExtractor]
        ReuseCache --> BExt[BankStatementExtractor]
        ReuseCache --> TExt[TaxReturnExtractor]
        ReuseCache --> IExt[IdCardExtractor]
        PExt --> EvidenceRefs[Bind EvidenceRef: page_number + bbox]
        BExt --> EvidenceRefs
        TExt --> EvidenceRefs
        IExt --> EvidenceRefs
    end

    EvidenceRefs --> N4[Node 4: evaluate_rules_node]

    %% Node 4
    subgraph Deterministic_Rules [Deterministic Rules Engine - HUMAN ONLY]
        N4 --> R_COMP[RULE-COMP-01: Completeness Checklist]
        N4 --> R_INC[RULE-INC-01: Net Salary vs Bank Credits within 5%]
        N4 --> R_TAX[RULE-TAX-01: ITR Gross vs 12x Payslip Gross]
        N4 --> R_ID1[RULE-ID-01: Fuzzy Name & PAN Match]
        N4 --> R_ID2[RULE-ID-02: Cross-ID Consistency]
        N4 --> R_BANK[RULE-BANK-01: Balance Arithmetic open+cr-dr=close]
        R_COMP --> FindingsList[Aggregate Typed Findings: PASS / FLAG / UNKNOWN]
        R_INC --> FindingsList
        R_TAX --> FindingsList
        R_ID1 --> FindingsList
        R_ID2 --> FindingsList
        R_BANK --> FindingsList
    end

    FindingsList --> N5[Node 5: retrieve_policy_node]

    %% Node 5
    subgraph RAG_Retrieval [Finding-Aware Policy RAG]
        N5 --> QueryGen[Generate Queries from Rule Flags]
        QueryGen --> BM25[BM25 Lexical Search]
        QueryGen --> FAISS[FAISS Dense BGE-small Search]
        BM25 --> RRF[Reciprocal Rank Fusion RRF]
        FAISS --> RRF
        RRF --> CanonicalBackstop[Merge Canonical Backstop Clauses]
    end

    CanonicalBackstop --> N6[Node 6: synthesize_summary_node]

    %% Node 6
    subgraph Synthesis [CAM Narrative Synthesis]
        N6 --> MemoBuilder[build_appraisal_memo]
        MemoBuilder --> PromptIsolation[Wrap untrusted data in context_data tags]
        PromptIsolation --> LLMCall[OpenCodeZenLLM: Groq / Zen / Qwen]
        LLMCall --> DraftMemo[CAM Markdown with Bracketed Citations]
    end

    DraftMemo --> N7[Node 7: validate_grounding_node]

    %% Node 7
    subgraph Grounding_Gate [Citation Validation Firewall]
        N7 --> ParseCitations[Parse citation tokens]
        ParseCitations --> MatchAuth{All citations in retrieved_chunk_ids?}
        MatchAuth -->|Unauthorized| StripClaims[Drop Ungrounded Claim Blocks]
        MatchAuth -->|Authorized| RetainClaims[Validate & Sanitize Text]
        StripClaims --> UpdateStatus[Status: READY_FOR_REVIEW<br/>summary_grounded=True]
        RetainClaims --> UpdateStatus
    end

    UpdateStatus --> InterruptHalt{interrupt_before Checkpoint}
    InterruptHalt -->|Durable State Snapshot| SQLiteSave[(SqliteSaver: checkpoints.sqlite3)]
    SQLiteSave --> PausedHalt([⏸ Execution Paused for Underwriter])

    %% Node 8 Resume
    PausedHalt -->|POST /applications/id/review| ResumeCall[resume_application_review]
    ResumeCall --> N8[Node 8: human_review_node]
    N8 --> DecisionSwitch{reviewer_decision}
    DecisionSwitch -->|APPROVED / REJECTED| ReviewedStatus[Status: REVIEWED]
    DecisionSwitch -->|NEEDS_INFO| NeedsInfoStatus[Status: NEEDS_INFORMATION]
    ReviewedStatus --> CommitResult[(Commit to PostgreSQL)]
    NeedsInfoStatus --> CommitResult
    CommitResult --> FinalEnd([END])
```

---

## 📦 The Authoritative State Contract: `LoanApplicationState`

Defined in [`core/contracts/state.py`](../core/contracts/state.py), this `TypedDict` is the single source of truth passed across all nodes:

```mermaid
classDiagram
    class LoanApplicationState {
        +str application_id
        +ApplicationStatus status
        +List~StatusTransition~ status_history
        +List~str~ document_ids
        +Dict~str, str~ document_manifest
        +Optional~Dict~ document_bytes
        +Dict~str, str~ classified_types
        +Optional~Dict~ classification_metadata
        +Dict~str, int~ document_pages
        +Dict~str, str~ ocr_routes
        +Optional~Dict~ document_texts
        +Optional~ApplicantFact~ applicant
        +Optional~PayslipFacts~ payslip
        +Optional~BankStatementFacts~ bank_statement
        +Optional~TaxReturnFacts~ tax_return
        +Optional~List~ identity_documents
        +List~Finding~ findings
        +List~str~ missing_documents
        +List~str~ retrieved_chunk_ids
        +Optional~str~ summary_markdown
        +bool summary_grounded
        +bool review_paused
        +Optional~str~ reviewer_decision
        +Optional~str~ reviewer_notes
        +List~Dict~ corrections_applied
    }

    class Finding {
        +str rule_id
        +str rule_name
        +FindingVerdict verdict
        +str reason
        +List~EvidenceRef~ supporting_evidence
        +str policy_version
    }

    class EvidenceRef {
        +str document_id
        +str document_type
        +int page_number
        +str quoted_span
        +BoundingBox bounding_box
        +str extraction_method
        +float confidence
    }

    class BoundingBox {
        +float x0
        +float y0
        +float x1
        +float y1
        +Optional~float~ page_width
        +Optional~float~ page_height
    }

    LoanApplicationState --> Finding
    Finding --> EvidenceRef
    EvidenceRef --> BoundingBox
```

---

## 💾 Checkpoint Persistence & Interrupt Mechanism

The pipeline is compiled with:
```python
workflow.compile(
    checkpointer=SqliteSaver(db_path="data/storage/checkpoints.sqlite3"),
    interrupt_before=["human_review"],
)
```

```mermaid
sequenceDiagram
    autonumber
    participant W as Worker Consumer
    participant LG as LangGraph Runtime
    participant CP as SqliteSaver (checkpoints.sqlite3)
    participant UI as Underwriter UI (React)
    participant API as FastAPI (review.py)
    participant DB as PostgreSQL 16

    W->>LG: graph.invoke(initial_state, config={"thread_id": app_id})
    Note over LG: Executes Nodes 1 through 7...
    LG->>LG: Node 7: validate_grounding_node complete
    Note over LG,CP: Hits interrupt_before=["human_review"]
    LG->>CP: Snapshot state to checkpoints.sqlite3
    LG-->>W: Returns partial state (review_paused=True, status="READY_FOR_REVIEW")
    W->>DB: persist_pipeline_result(state)
    W->>W: queue.ack(handle)

    Note over UI,API: Underwriter reviews dossier, CAM memo, & bounding boxes

    UI->>API: POST /applications/{id}/review (decision="APPROVED", notes="...")
    API->>LG: resume_application_review(thread_id, decision, notes)
    LG->>CP: Load checkpoint for thread_id
    CP-->>LG: Frozen State
    LG->>LG: graph.update_state({"reviewer_decision": decision, ...})
    LG->>LG: Execute Node 8: human_review_node
    LG->>LG: Transition status to REVIEWED
    LG-->>API: Final State
    API->>DB: Commit status=REVIEWED, append audit log
    API-->>UI: 200 OK
```

---

## 🛡️ Error Handling, DLQ Routing & Poison Messages

```mermaid
flowchart TD
    Start[Delivery Received] --> CheckAttempts{attempt_count > 3?}
    CheckAttempts -->|Yes| DLQ[fail lease_handle, retryable=False<br/>Route to Dead Letter Queue DLQ]
    CheckAttempts -->|No| Lease[Start LeaseHeartbeat Thread]
    
    Lease --> RunGraph[Execute LangGraph Pipeline]
    RunGraph --> CheckResult{Execution Successful?}
    
    CheckResult -->|Success| CommitDB[Commit State to PostgreSQL 16]
    CommitDB --> AckQueue[queue.ack lease_handle]
    
    CheckResult -->|Exception Caught| Rollback[Rollback DB Transaction]
    Rollback --> FailRetry[queue.fail lease_handle, retryable=True<br/>Reset visibility timeout for redelivery]
    
    style DLQ fill:#FFCDD2,color:#B71C1C
    style AckQueue fill:#C8E6C9,color:#1B5E20
    style FailRetry fill:#FFF9C4,color:#F57F17
```

---

## 📊 Node Performance & Latency Budgets

```mermaid
gantt
    title FinScan AI Pipeline Node Latency Budget (Target: < 25s CPU)
    dateFormat  X
    axisFormat %s s

    section Ingestion
    Triage (Node 1)                 :0, 1
    section Perception
    OCR & Classification (Node 2)   :1, 10
    section Extraction
    Fact Extraction (Node 3)        :10, 14
    section Deterministic Rules
    Rules Engine (Node 4)           :14, 15
    section Policy RAG
    Hybrid Policy RAG (Node 5)      :15, 17
    section Synthesis
    CAM Memo Builder (Node 6)       :17, 21
    section Safety Firewall
    Grounding Gate (Node 7)         :21, 22
    section HITL Checkpoint
    Interrupt & SQLite Snapshot     :22, 23
```

---

## 🚫 Inviolable Architectural Anti-Patterns

### ❌ Anti-Pattern 1: Autonomous Lending Decisions
```mermaid
graph LR
    Facts[Extracted Facts] --> LLM[LLM / Black-box Model]
    LLM --> Decision[Approved / Rejected]
    Decision --> Harm[❌ VIOLATION: Zero Hallucinated Decisions]
    style Harm fill:#FFCDD2,color:#B71C1C
```

### ✅ Correct Pattern: Deterministic Rules + LLM Explanation + Human Sign-off
```mermaid
graph LR
    Facts[Extracted Facts] --> Rules[Deterministic Code in core/rules/]
    Rules --> Verdict[Verdict: PASS / FLAG with EvidenceRefs]
    Verdict --> LLM[LLM: Explains & Cites Policy]
    LLM --> Gate[Grounding Citation Gate]
    Gate --> Human[Underwriter Approves at interrupt checkpoint]
    style Human fill:#C8E6C9,color:#1B5E20
```

---

## 📚 Related Source Files

- **Orchestration Definition**: [`core/graph/workflow.py`](../core/graph/workflow.py)
- **Node Functions**: [`core/graph/nodes.py`](../core/graph/nodes.py)
- **State Contracts**: [`core/contracts/state.py`](../core/contracts/state.py)
- **Facts & Evidence Models**: [`core/contracts/facts.py`](../core/contracts/facts.py) and [`core/contracts/evidence.py`](../core/contracts/evidence.py)
- **Durable Checkpointer**: [`core/graph/checkpoint.py`](../core/graph/checkpoint.py)
- **Worker Execution Loop**: [`worker/consumer.py`](../worker/consumer.py)
- **Underwriter Sign-off Route**: [`apps/api/routes/review.py`](../apps/api/routes/review.py)
