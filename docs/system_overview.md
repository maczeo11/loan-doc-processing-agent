# FinScan AI - System Overview

**GenAI-Enabled Loan Document Processing Agent**  
*Deterministic code decides. AI explains. A human approves.*

---

## 🎯 Executive Summary

FinScan AI is an intelligent loan document verification system designed for bank underwriters. It processes retail loan dossiers containing multiple document types, extracts financial facts with pixel-level evidence, and presents findings for human review.

### Key Value Propositions

| Feature | Traditional Process | FinScan AI | Benefit |
|---------|-------------------|------------|---------|
| **Processing Time** | 24-72 hours | ~90 seconds | 99% faster turnaround |
| **Accuracy** | Manual verification prone to errors | Deterministic arithmetic with evidence | Zero hallucinated numbers |
| **Audit Trail** | Scattered paper trail | Every fact traces to page coordinates | Full regulatory compliance |
| **Decision Authority** | Manual judgment | Human-in-the-loop sign-off | No autonomous AI decisions |

---

## 🏛️ System Architecture Overview

```mermaid
graph TB
    subgraph "Client Layer"
        UI[React SPA Dashboard]
        Underwriter[Bank Underwriter]
    end
    
    subgraph "API Gateway Layer"
        FastAPI[FastAPI REST API]
        Upload[Document Upload Endpoint]
        Review[Review Endpoints]
        Status[Status Polling]
    end
    
    subgraph "Processing Layer"
        Queue[Job Queue PG/SQS]
        Worker[Async Worker Consumer]
        LangGraph[LangGraph Orchestrator]
    end
    
    subgraph "Core Business Logic"
        OCR[OCR Router & Extraction]
        Classifier[Document Classifier]
        Extractors[Fact Extractors]
        Rules[Deterministic Rules Engine]
        RAG[Hybrid RAG System]
        Grounding[Grounding Validator]
    end
    
    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL)]
        Redis[(Redis Cache)]
        Storage[Object Storage Local/S3]
    end
    
    subgraph "AI/ML Layer"
        LLM[LLM: OpenCode Zen / Qwen]
        ML[Classifier: TF-IDF / DistilBERT]
    end
    
    Underwriter -->|Upload Dossier| UI
    UI -->|HTTP Request| FastAPI
    FastAPI --> Upload
    FastAPI --> Review
    FastAPI --> Status
    
    Upload -->|Store Documents| Storage
    Upload -->|Create Job| Queue
    Upload -->|Update Status| PostgreSQL
    
    Queue -->|Consume Job| Worker
    Worker -->|Execute Pipeline| LangGraph
    
    LangGraph --> OCR
    OCR --> Classifier
    Classifier --> Extractors
    Extractors --> Rules
    Rules --> RAG
    RAG --> Grounding
    
    OCR -->|Read PDFs| Storage
    Classifier --> ML
    RAG --> LLM
    Grounding --> LLM
    
    LangGraph -->|Checkpoint| PostgreSQL
    Rules -->|Save Findings| PostgreSQL
    Grounding -->|Save Memo| PostgreSQL
    
    Worker -->|Acknowledge| Queue
    
    Review -->|Resume Graph| LangGraph
    Review -->|Human Decision| PostgreSQL
    
    UI -->|Poll Status| Status
    Status -->|Read State| PostgreSQL
    
    FastAPI -->|Rate Limit| Redis
    LangGraph -->|Session Cache| Redis
    
    style UI fill:#61DAFB
    style FastAPI fill:#009688
    style LangGraph fill:#FF9800
    style PostgreSQL fill:#336791
    style LLM fill:#9C27B0
    style Rules fill:#F44336
```

---

## 🔄 Processing Pipeline Flow

```mermaid
sequenceDiagram
    participant U as Underwriter
    participant UI as React SPA
    participant API as FastAPI
    participant Q as Job Queue
    participant W as Worker
    participant LG as LangGraph
    participant OCR as OCR Router
    participant CL as Classifier
    participant EX as Extractors
    participant RL as Rules Engine
    participant RAG as Hybrid RAG
    participant GR as Grounding
    participant DB as PostgreSQL
    
    U->>UI: Upload Loan Dossier
    UI->>API: POST /applications
    
    API->>DB: Create Application Record
    API->>Q: Publish Job (JobRef)
    API->>DB: Insert Outbox Entry
    API-->>UI: 202 Accepted + job_id
    
    Note over U,DB: Async Processing Begins
    
    Q->>W: Receive Job (lease)
    W->>LG: Start Graph Execution
    
    LG->>OCR: Route PDF Pages
    OCR-->>LG: Page Text + Coordinates
    
    LG->>CL: Classify Pages
    CL-->>LG: Document Types
    
    LG->>EX: Extract Facts
    EX-->>LG: PayslipFacts, BankFacts, etc.
    
    LG->>RL: Run Deterministic Rules
    RL-->>LG: Findings (pass/flag/unknown)
    
    LG->>RAG: Retrieve Policy Context
    RAG-->>LG: Relevant Policy Chunks
    
    LG->>GR: Validate Grounding
    GR-->>LG: Validated Summary
    
    LG->>DB: Save Checkpoint (interrupt)
    LG-->>W: Pause at human_review_node
    
    W->>Q: Acknowledge Job
    W->>DB: Commit Results
    
    Note over U,DB: Human Review Phase
    
    loop Poll Status
        UI->>API: GET /applications/{id}
        API->>DB: Query State
        DB-->>API: READY_FOR_REVIEW
        API-->>UI: Status + Findings
    end
    
    UI->>U: Display Findings + Evidence
    U->>UI: Review & Decision
    UI->>API: POST /applications/{id}/review
    
    API->>LG: Resume Graph
    LG->>DB: Update State (REVIEWED)
    LG-->>API: Final State
    
    API-->>UI: Success
    UI-->>U: Decision Confirmed
```

---

## 🧩 Core Components Breakdown

### 1. Document Ingestion & Triage

```mermaid
graph LR
    subgraph "Document Upload"
        A[Upload Request] --> B["Validate File Size < 10MB"]
        B --> C[SHA-256 Deduplication]
        C --> D{Duplicate?}
        D -->|Yes| E[Return Existing ID]
        D -->|No| F[Store in Local/S3]
        F --> G[Generate Document ID]
        G --> H[Create Application Record]
        H --> I[Insert Outbox Job]
        I --> J[Return 202 Accepted]
    end
    
    style A fill:#E3F2FD
    style J fill:#C8E6C9
    style D fill:#FFF9C4
```

### 2. OCR Routing Strategy

```mermaid
graph TD
    Start[PDF Page] --> Check{Has Native Text?}
    
    Check -->|Yes| Route1[Route 1: PyMuPDF]
    Route1 --> Extract[Extract Text + Word Boxes]
    Extract --> Output[Page Text + Coordinates]
    
    Check -->|No| Check2{Page Quality?}
    Check2 -->|Good| Route2[Route 2: PaddleOCR CPU]
    Check2 -->|Poor/Capped| Route3[Route 3: AWS Textract]
    
    Route2 --> OCR[OCR Processing]
    Route3 --> OCR
    
    OCR --> Detect[Text Detection]
    Detect --> Parse[Parse Coordinates]
    Parse --> Output
    
    Output --> Validate{Valid Bounds?}
    Validate -->|Yes| Success[Return Page Data]
    Validate -->|No| Error[Mark UNKNOWN]
    
    style Route1 fill:#C8E6C9
    style Route2 fill:#FFF9C4
    style Route3 fill:#FFCCBC
    style Success fill:#81C784
    style Error fill:#E57373
```

### 3. Document Classification

```mermaid
graph TB
    subgraph "Training Phase"
        Data[Synthetic Dossiers] --> Split[Train/Dev/Test Split]
        Split --> Baseline[TF-IDF + LogReg]
        Split --> Challenger[DistilBERT Encoder]
        Baseline --> Eval[Evaluation Harness]
        Challenger --> Eval
        Eval --> Select{Best Model?}
        Select --> Winner[Serialize .joblib]
    end
    
    subgraph "Inference Phase"
        Page[Page Text] --> Model[Trained Classifier]
        Model --> Pred[Prediction + Confidence]
        Pred --> Threshold{"Confidence > T?"}
        Threshold -->|Yes| Class[Return Document Type]
        Threshold -->|No| Unknown[Return UNKNOWN]
    end
    
    style Winner fill:#81C784
    style Class fill:#64B5F6
    style Unknown fill:#FFB74D
```

### 4. Fact Extraction with Evidence

```mermaid
graph LR
    subgraph "Extraction Pipeline"
        A[Classified Page] --> B[Payslip Extractor]
        A --> C[Bank Statement Extractor]
        A --> D[Tax Return Extractor]
        A --> E[ID Card Extractor]
        
        B --> F[PayslipFacts]
        C --> G[BankStatementFacts]
        D --> H[TaxReturnFacts]
        E --> I[ApplicantFact]
    end
    
    subgraph "Evidence Binding"
        F --> J[Bind EvidenceRef]
        G --> J
        H --> J
        I --> J
        
        J --> K[document_id]
        J --> L[page_number]
        J --> M[bounding_box x0,y0,x1,y1]
        J --> N[quoted_span]
    end
    
    subgraph "Output"
        K --> O[Verified Fact]
        L --> O
        M --> O
        N --> O
    end
    
    style O fill:#81C784
    style M fill:#FFB74D
```

### 5. Deterministic Rules Engine

```mermaid
graph TB
    subgraph "Rule Chain"
        Start[Extracted Facts] --> R1[RULE-COMP-01<br/>Completeness Check]
        R1 --> R2[RULE-INC-01<br/>Salary Audit]
        R2 --> R3[RULE-TAX-01<br/>Tax Audit]
        R3 --> R4[RULE-ID-01<br/>Identity Check]
    end
    
    subgraph "R2: Salary Audit"
        R2 --> S1{Payslip Net vs Bank Credit}
        S1 --> S2[Calculate Delta %]
        S2 --> S3{"Delta <= 5%?"}
        S3 -->|Yes| S4[verdict: pass]
        S3 -->|No| S5[verdict: flag]
        S3 -->|UNKNOWN| S6[verdict: unknown]
    end
    
    S4 --> Aggregate[Aggregate Findings]
    S5 --> Aggregate
    S6 --> Aggregate
    
    Aggregate --> Output[Structured Findings List]
    
    style Output fill:#81C784
    style S3 fill:#FFF9C4
```

---

## 🎯 Key Design Decisions

### 1. Deterministic vs AI

```mermaid
graph LR
    subgraph "Deterministic Code Decides"
        A[Financial Calculations] --> A1[Salary reconciliation]
        A --> A2[DTI computation]
        A --> A3[Pass/flag verdicts]
        A --> A4[Tolerance comparisons]
    end
    
    subgraph "AI Explains"
        B[LLM Tasks] --> B1[Narrative generation]
        B --> B2[Policy retrieval]
        B --> B3[Question answering]
        B --> B4[Summary synthesis]
    end
    
    subgraph "Human Approves"
        C[Human-in-the-Loop] --> C1[Review findings]
        C --> C2[Verify evidence]
        C --> C3[Final decision]
        C --> C4[Override if needed]
    end
    
    style A fill:#F44336
    style B fill:#9C27B0
    style C fill:#4CAF50
```

### 2. Why Not Use LLMs for Everything?

```mermaid
graph TD
    Problem[Problem: LLM Hallucination Risk] --> Risk1[Cannot verify financial math]
    Problem --> Risk2[No legal audit trail]
    Problem --> Risk3[Regulatory liability]
    Problem --> Risk4[Black box decisions]
    
    Solution[Solution: Provenance-Grounded Determinism] --> S1[Every number traces to page]
    Solution --> S2[Explicit bounding boxes]
    Solution --> S3[Human review checkpoint]
    Solution --> S4[Audit log immutability]
    
    Risk1 --> S1
    Risk2 --> S2
    Risk3 --> S3
    Risk4 --> S4
    
    style Problem fill:#E57373
    style Solution fill:#81C784
```

---

## 📊 Performance & Scalability

### Target Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| **End-to-End Processing** | < 90 seconds | Complete dossier processing from upload to review-ready |
| **OCR Throughput** | 10-15 pages/min | PaddleOCR CPU on ARM64 t4g.medium |
| **Classification Latency** | < 100ms p95 | TF-IDF baseline on CPU |
| **RAG Retrieval** | < 200ms p95 | FAISS exact flat search |
| **API Response Time** | < 50ms p95 | For non-processing endpoints |
| **Concurrent Jobs** | 2 per user | Queue lease isolation |
| **Budget Ceiling** | $25/week | Target $8-15 for cloud demo |

---

## 📚 Related Documentation

- [Architecture Details](architecture.md) - Detailed component boundaries
- [LangGraph Workflow](langgraph_workflow.md) - Pipeline orchestration
- [Worker & Queue Architecture](worker_queue_architecture.md) - Async processing
- [Data Flow Diagrams](data_flow_diagrams.md) - End-to-end data movement
- [Deployment Guide](deployment_guide.md) - Local and cloud deployment
- [Security Architecture](security_architecture.md) - Defense in depth
