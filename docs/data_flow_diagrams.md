# Data Flow Diagrams

**End-to-End Data Movement Through FinScan AI**

---

## 📊 Level 0: System Context Diagram

```mermaid
graph TB
    subgraph "External Entities"
        Underwriter[Bank Underwriter<br/>Manual Upload & Review]
        PolicyDB[Policy Documents<br/>External Knowledge Base]
        S3[Object Storage<br/>AWS S3 / Local FS]
    end
    
    subgraph "FinScan AI System"
        System[Loan Document<br/>Processing Agent]
    end
    
    Underwriter -->|Upload Dossier<br/>PDF Documents| System
    System -->|Return Status<br/>Findings & Memo| Underwriter
    Underwriter -->|Review Decision| System
    System -->|Decision Confirmation| Underwriter
    
    PolicyDB -->|Policy Guidelines| System
    System -->|Store Documents| S3
    S3 -->|Retrieve Documents| System
    
    style System fill:#336791,color:#FFF
    style Underwriter fill:#61DAFB
    style PolicyDB fill:#9C27B0
```

---

## 📊 Level 1: Major Data Flows

```mermaid
graph TB
    subgraph "External"
        U[Underwriter]
        S3[(S3 / Local Storage)]
        Policy[(Policy Corpus)]
    end
    
    subgraph "FinScan AI"
        API[FastAPI<br/>Application Layer]
        Queue[Job Queue]
        Worker[Worker Process]
        DB[(PostgreSQL<br/>State Store)]
        Cache[(Redis<br/>Rate Limiting)]
        
        OCR[OCR Router]
        Classifier[Document Classifier]
        Extractors[Fact Extractors]
        Rules[Rules Engine]
        RAG[Hybrid RAG]
        LLM[LLM Service]
    end
    
    U -->|1. Upload Dossier| API
    API -->|2. Rate Limit Check| Cache
    API -->|3. Store PDFs| S3
    API -->|4. Create Application| DB
    API -->|5. Publish Job| Queue
    
    Queue -->|6. Consume Job| Worker
    Worker -->|7. Load State| DB
    
    Worker -->|8. Route Pages| OCR
    S3 -->|Read PDFs| OCR
    OCR -->|9. Page Text| Classifier
    Classifier -->|10. Document Types| Extractors
    
    Extractors -->|11. Extracted Facts| Rules
    Rules -->|12. Findings| RAG
    
    Policy -->|Policy Chunks| RAG
    RAG -->|13. Retrieved Context| LLM
    LLM -->|14. Generated Memo| Worker
    
    Worker -->|15. Save Results| DB
    Worker -->|16. Acknowledge| Queue
    
    DB -->|17. Status Update| API
    U -->|18. Poll Status| API
    API -->|19. Return Findings| U
    
    U -->|20. Submit Decision| API
    API -->|21. Resume Graph| Worker
    Worker -->|22. Final State| DB
    API -->|23. Confirmation| U
    
    style API fill:#009688
    style Worker fill:#FF9800
    style Rules fill:#F44336
    style LLM fill:#9C27B0
```

---

## 📊 Level 2: Document Upload Flow

```mermaid
sequenceDiagram
    participant U as Underwriter
    participant UI as React SPA
    participant API as FastAPI
    participant S3 as Object Storage
    participant DB as PostgreSQL
    participant Q as Queue
    participant R as Redis
    
    U->>UI: Select Files to Upload
    UI->>UI: Validate File Size <10MB
    UI->>UI: Validate Total Pages ≤30
    
    UI->>API: POST /applications<br/>multipart/form-data
    
    API->>R: Check Rate Limit<br/>5 uploads/min
    R-->>API: OK
    
    API->>API: Generate Application ID<br/>APP-{UUID}
    
    loop For Each Document
        API->>API: Calculate SHA-256 Hash
        API->>API: Sanitize Filename
        API->>S3: Store File<br/>dossiers/{app_id}/{doc_id}_{filename}
        S3-->>API: storage_key
    end
    
    API->>DB: BEGIN TRANSACTION
    
    API->>DB: INSERT INTO applications<br/>(id, status='UPLOADED')
    
    loop For Each Document
        API->>DB: INSERT INTO documents<br/>(id, application_id, storage_key)
    end
    
    API->>DB: INSERT INTO outbox_jobs<br/>(job_id, application_id, status='PENDING')
    
    API->>DB: COMMIT
    
    API-->>UI: 202 Accepted<br/>{application_id, job_id}
    
    UI-->>U: Show Processing Status
    
    Note over Q,DB: Async Processing Begins
    
    Q->>Q: Outbox Poller Picks Up Job
    Q->>Q: Publish to Queue
```

---

## 📊 Level 3: OCR & Classification Flow

```mermaid
graph TB
    subgraph "Input"
        A[PDF Document<br/>Multiple Pages]
    end
    
    subgraph "OCR Router"
        B[Page 1] --> Check1{Has Native Text?}
        B --> Check2{Has Native Text?}
        B --> Check3{Has Native Text?}
        
        Check1 -->|Yes| N1[Native Text Extraction<br/>PyMuPDF]
        Check1 -->|No| O1[OCR Route Selection]
        
        O1 --> Decision{Page Quality + Budget?}
        Decision -->|Good / Uncapped| Paddle[PaddleOCR CPU]
        Decision -->|Poor / Capped| Textract[AWS Textract]
        
        N1 --> Out1[Page Text 1<br/>+ Word Boxes]
        Paddle --> Out2[Page Text 2<br/>+ Coordinates]
        Textract --> Out3[Page Text 3<br/>+ Coordinates]
    end
    
    subgraph "Classification"
        Out1 --> C1[TF-IDF Vectorization]
        Out2 --> C1
        Out3 --> C1
        
        C1 --> Model[Trained Classifier<br/>.joblib Model]
        Model --> Pred[Prediction + Confidence]
        
        Pred --> Threshold{"Confidence > T?"}
        Threshold -->|Yes| Label[Document Type:<br/>payslip, bank_statement, etc.]
        Threshold -->|No| Unknown[Label: UNKNOWN]
    end
    
    subgraph "Output"
        Label --> D1[Classified Page 1]
        Unknown --> D2[Flagged Page 2]
        Label --> D3[Classified Page 3]
        
        D1 --> Output[Document Manifest:<br/>page → type mapping]
        D2 --> Output
        D3 --> Output
    end
    
    style Decision fill:#FFF9C4
    style Threshold fill:#FFF9C4
    style Output fill:#81C784
```

---

## 📊 Level 4: Fact Extraction Flow

```mermaid
graph TB
    subgraph "Input: Classified Pages"
        P1[Page: Payslip]
        P2[Page: Bank Statement]
        P3[Page: Tax Return]
        P4[Page: ID Card]
    end
    
    subgraph "Extractors"
        P1 --> E1[PayslipExtractor]
        P2 --> E2[BankStatementExtractor]
        P3 --> E3[TaxReturnExtractor]
        P4 --> E4[IDCardExtractor]
        
        E1 --> Parse1[Parse Fields<br/>with Regex Patterns]
        E2 --> Parse2[Parse Tables<br/>with Layout Analysis]
        E3 --> Parse3[Parse Key-Value Pairs]
        E4 --> Parse4[Parse Text Regions]
        
        Parse1 --> Loc1[Locate Bounding Boxes]
        Parse2 --> Loc2[Locate Table Cells]
        Parse3 --> Loc3[Locate Field Positions]
        Parse4 --> Loc4[Locate ID Fields]
    end
    
    subgraph "Evidence Binding"
        Loc1 --> Bind1[Create EvidenceRef]
        Loc2 --> Bind2[Create EvidenceRef]
        Loc3 --> Bind3[Create EvidenceRef]
        Loc4 --> Bind4[Create EvidenceRef]
        
        Bind1 --> Facts1[PayslipFacts:<br/>gross_salary: MoneyFact<br/>net_salary: MoneyFact<br/>source: EvidenceRef]
        
        Bind2 --> Facts2[BankStatementFacts:<br/>salary_credits: List[MoneyFact]<br/>account_holder: str<br/>source: EvidenceRef]
        
        Bind3 --> Facts3[TaxReturnFacts:<br/>gross_total_income: MoneyFact<br/>pan_number: str<br/>source: EvidenceRef]
        
        Bind4 --> Facts4[ApplicantFact:<br/>full_name: str<br/>pan_number: str<br/>source_name: EvidenceRef<br/>source_pan: EvidenceRef]
    end
    
    subgraph "Output: Structured Facts"
        Facts1 --> Aggregate[ExtractedFacts Dict]
        Facts2 --> Aggregate
        Facts3 --> Aggregate
        Facts4 --> Aggregate
        
        Aggregate --> Save[Save to Application State]
    end
    
    style Aggregate fill:#81C784
    style Save fill:#64B5F6
```

---

## 📊 Level 5: Rules Evaluation Flow

```mermaid
graph TB
    subgraph "Input: Extracted Facts"
        Facts[ExtractedFacts Dict]
    end
    
    subgraph "Rule Chain"
        Facts --> R1[RULE-COMP-01<br/>Completeness Check]
        
        R1 --> C1{All Required Docs Present?}
        C1 -->|Yes| C2[Finding: verdict=pass]
        C1 -->|No| C3[Finding: verdict=flag<br/>reason=Missing documents]
        
        C2 --> R2[RULE-INC-01<br/>Salary Audit]
        C3 --> R2
        
        R2 --> S1[Extract Payslip Net Salary]
        S1 --> S2[Extract Bank Salary Credits]
        S2 --> S3[Calculate Average Bank Credit]
        S3 --> S4[Compare: |payslip - bank| / payslip]
        S4 --> S5{"Delta <= 5%?"}
        
        S5 -->|Yes| S6[Finding: verdict=pass]
        S5 -->|No| S7[Finding: verdict=flag<br/>reason=Salary mismatch]
        S5 -->|UNKNOWN| S8[Finding: verdict=unknown<br/>reason=Missing data]
        
        S6 --> R3[RULE-TAX-01<br/>Tax Audit]
        S7 --> R3
        S8 --> R3
        
        R3 --> T1[Extract ITR Gross Income]
        T1 --> T2[Annualize Payslip Gross<br/>monthly_gross × 12]
        T2 --> T3[Compare Values]
        T3 --> T4{Match Within Tolerance?}
        
        T4 -->|Yes| T5[Finding: verdict=pass]
        T4 -->|No| T6[Finding: verdict=flag<br/>reason=Income mismatch]
        
        T5 --> R4[RULE-ID-01<br/>Identity Check]
        T6 --> R4
        
        R4 --> I1[Extract Name from ID]
        I1 --> I2[Extract Name from Payslip]
        I2 --> I3[Extract PAN from ID]
        I3 --> I4[Extract PAN from Tax Return]
        I4 --> I5[Fuzzy Match Names]
        I5 --> I6[Compare PANs]
        I6 --> I7{All Match?}
        
        I7 -->|Yes| I8[Finding: verdict=pass]
        I7 -->|No| I9[Finding: verdict=flag<br/>reason=Identity mismatch]
    end
    
    subgraph "Output: Aggregated Findings"
        C2 --> Results[Findings List]
        C3 --> Results
        S6 --> Results
        S7 --> Results
        S8 --> Results
        T5 --> Results
        T6 --> Results
        I8 --> Results
        I9 --> Results
        
        Results --> Output[Pass Count: X<br/>Flag Count: Y<br/>Unknown Count: Z]
    end
    
    style S5 fill:#FFF9C4
    style T4 fill:#FFF9C4
    style I7 fill:#FFF9C4
    style Output fill:#81C784
```

---

## 📊 Level 6: Hybrid RAG Flow

```mermaid
graph TB
    subgraph "Indexing Phase"
        Docs[Policy Documents] --> Chunk[Passage Chunking<br/>250-400 tokens]
        Chunk --> Meta[Add Metadata:<br/>doc_id, page, chunk_id]
        Meta --> Embed[Generate Embeddings<br/>BAAI/bge-small-en-v1.5]
        
        Meta --> Index1[Build BM25 Index<br/>Lexical Search]
        Embed --> Index2[Build FAISS Index<br/>Dense Search]
    end
    
    subgraph "Retrieval Phase"
        Query[Underwriter Question] --> Preprocess[Normalize Query]
        
        Preprocess --> BM25[BM25 Search<br/>Top-K Results]
        Preprocess --> Dense[Dense Search<br/>FAISS Top-K Results]
        
        BM25 --> R1[Results Set 1<br/>with BM25 Scores]
        Dense --> R2[Results Set 2<br/>with Dense Scores]
        
        R1 --> RRF["Reciprocal Rank Fusion<br/>Score = Σ 1/(60 + rank)"]
        R2 --> RRF
        
        RRF --> Ranked[Ranked Results<br/>with Final Scores]
    end
    
    subgraph "Isolation Enforcement"
        App1[Application A Chunks] --> Scope1[Index Scope: app_id=A]
        App2[Application B Chunks] --> Scope2[Index Scope: app_id=B]
        Policy[Policy Corpus] --> ScopeP[Index Scope: policy]
        
        Scope1 --> Filter[Query Filter:<br/>app_id=current_app OR scope=policy]
        Scope2 --> Filter
        ScopeP --> Filter
        
        Filter --> Preprocess
    end
    
    subgraph "Output"
        Ranked --> TopN[Top-N Retrieved Chunks]
        TopN --> Context[Context for LLM:<br/>Policy + Application Facts]
    end
    
    style RRF fill:#9C27B0
    style Filter fill:#F44336
    style Context fill:#81C784
```

---

## 📊 Level 7: Human Review Flow

```mermaid
sequenceDiagram
    participant U as Underwriter
    participant UI as React SPA
    participant API as FastAPI
    participant LG as LangGraph
    participant DB as PostgreSQL
    
    Note over LG,DB: System PAUSED at interrupt()
    
    loop Poll Status (≥2s interval)
        UI->>API: GET /applications/{id}
        API->>DB: SELECT state FROM applications
        DB-->>API: state.status = 'READY_FOR_REVIEW'
        API-->>UI: {status, findings, memo}
    end
    
    UI->>U: Display 3-Pane Dashboard
    
    Note over UI: Left: Document Index<br/>Center: PDF with Highlights<br/>Right: Findings & Actions
    
    UI->>API: GET /documents/{doc_id}/presigned-url
    API->>API: Generate Presigned URL<br/>TTL: 60 min
    API-->>UI: {presigned_url}
    
    UI->>UI: Render PDF with pdf.js
    UI->>UI: Draw Bounding Boxes<br/>from EvidenceRef coords
    
    U->>UI: Review Findings
    U->>UI: Click on Highlighted Fact
    UI->>UI: Scroll to Evidence
    UI->>UI: Zoom to Bounding Box
    
    alt Approve
        U->>UI: Click "Sign Off"
        UI->>API: POST /applications/{id}/review<br/>{decision: "APPROVED", notes: "..."}
    else Reject
        U->>UI: Click "Flag Discrepancy"
        UI->>API: POST /applications/{id}/review<br/>{decision: "REJECTED", notes: "..."}
    else Request Info
        U->>UI: Click "Request Information"
        UI->>API: POST /applications/{id}/review<br/>{decision: "NEEDS_INFO", notes: "..."}
    end
    
    API->>LG: graph.update_state(config, {"reviewer_decision": decision})
    LG->>DB: UPDATE state with decision
    
    API->>LG: graph.invoke(None, config)
    
    LG->>LG: Resume from interrupt()
    LG->>LG: Execute human_review_node
    
    alt APPROVED
        LG->>DB: UPDATE status = 'REVIEWED'
    else REJECTED
        LG->>DB: UPDATE status = 'FAILED'
    else NEEDS_INFO
        LG->>DB: UPDATE status = 'NEEDS_INFORMATION'
    end
    
    LG->>DB: INSERT INTO audit_log<br/>(actor, action, timestamp, rationale)
    
    LG-->>API: Final State
    API-->>UI: 200 OK {status}
    UI-->>U: Confirmation Message
```

---

## 📊 Data Transformation Summary

```mermaid
graph LR
    subgraph "Input Transformations"
        A1[PDF Binary] -->|OCR| A2[Page Text + Coordinates]
        A2 -->|Classification| A3[Document Type Labels]
        A3 -->|Extraction| A4[Raw Field Values]
    end
    
    subgraph "Evidence Binding"
        A4 -->|Locate in Source| B1[Bounding Box x0,y0,x1,y1]
        B1 -->|Create Reference| B2[EvidenceRef with Provenance]
        B2 -->|Bind to Fact| B3[MoneyFact with Source]
    end
    
    subgraph "Rule Processing"
        B3 -->|Compare Values| C1[Numeric Comparison<br/>with Tolerance]
        C1 -->|Determine Verdict| C2[Finding: pass/flag/unknown]
        C2 -->|Aggregate| C3[Findings List]
    end
    
    subgraph "RAG Retrieval"
        C3 -->|Query Generation| D1[Natural Language Query]
        D1 -->|Hybrid Search| D2[Retrieved Policy Chunks]
        D2 -->|Context Assembly| D3[Context for LLM]
    end
    
    subgraph "LLM Synthesis"
        D3 -->|Prompt Engineering| E1[LLM Generation]
        E1 -->|Grounding Check| E2[Validated Claims]
        E2 -->|Format| E3[Credit Appraisal Memo]
    end
    
    subgraph "Human Decision"
        E3 -->|Review & Sign-off| F1[Human Verdict]
        F1 -->|State Transition| F2[Final Application State]
    end
    
    style B2 fill:#FF9800
    style C2 fill:#F44336
    style E2 fill:#9C27B0
    style F1 fill:#4CAF50
```

---

## 📚 Related Documentation

- [System Overview](system_overview.md) - Component architecture
- [LangGraph Workflow](langgraph_workflow.md) - Pipeline execution
- [Worker Architecture](worker_queue_architecture.md) - Queue processing
- **API reference** - live OpenAPI at `http://localhost:8000/docs` once `make demo-api` is running; routes in [`apps/api/routes/`](../apps/api/routes/)
