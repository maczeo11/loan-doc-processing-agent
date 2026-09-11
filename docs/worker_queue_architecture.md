# Worker & Queue Architecture

**Reliable Async Processing with At-Least-Once Delivery**

---

## 📋 Overview

FinScan AI uses a robust queue-based worker architecture to process loan dossiers asynchronously. The system ensures at-least-once delivery, idempotent processing, and atomic state commits.

---

## 🏗️ Queue Architecture Overview

```mermaid
graph TB
    subgraph "Producer: FastAPI"
        API[FastAPI Endpoint] --> Upload[POST /applications]
        Upload --> Validate[Validate Request]
        Validate --> Store[Store Documents]
        Store --> Outbox[Insert to Outbox Table]
        Outbox --> Commit[Commit Transaction]
        Commit --> Response[Return 202 Accepted]
    end
    
    subgraph "Queue Layer"
        Outbox --> Poller[Outbox Poller]
        Poller --> Queue{Environment}
        Queue -->|Local| PG[PostgreSQL<br/>FOR UPDATE SKIP LOCKED]
        Queue -->|Cloud| SQS[AWS SQS + DLQ]
    end
    
    subgraph "Consumer: Worker"
        Worker[Worker Process] --> Receive[Receive Delivery]
        Receive --> Lease[Acquire Lease Handle]
        Lease --> Process[Execute Pipeline]
        Process --> Heartbeat[Lease Heartbeat<br/>Every 10s]
        Heartbeat --> Extend[Extend Lease 30s]
        Extend --> Process
        
        Process --> Result{Success?}
        Result -->|Yes| CommitResult[Commit to PostgreSQL]
        Result -->|No| Fail[Handle Failure]
        
        CommitResult --> Ack[Acknowledge Message]
        Fail --> Nack[Fail Message]
        
        Nack --> Retry{attempt_count <= 3?}
        Retry -->|Yes| Requeue[Requeue for Retry]
        Retry -->|No| DLQ[Route to DLQ]
    end
    
    subgraph "Dead Letter Queue"
        DLQ --> Alert[Alert & Manual Review]
        Alert --> Investigate[Debug Poison Message]
    end
    
    style Queue fill:#FFF9C4
    style Heartbeat fill:#9C27B0
    style Ack fill:#81C784
    style DLQ fill:#E57373
```

---

## 🔄 At-Least-Once Delivery Protocol

```mermaid
sequenceDiagram
    participant API as FastAPI
    participant O as Outbox Table
    participant Q as Queue (PG/SQS)
    participant W as Worker
    participant DB as PostgreSQL
    
    API->>O: INSERT INTO outbox_jobs
    API->>DB: COMMIT (state + outbox)
    
    Note over O: Status: PENDING
    
    loop Polling Loop
        W->>Q: receive(max_n=10)
        Q->>Q: SELECT ... FOR UPDATE SKIP LOCKED
        Q-->>W: [Delivery(handle, JobRef)]
    end
    
    W->>W: Start Lease Heartbeat (10s interval)
    
    W->>DB: BEGIN TRANSACTION
    W->>DB: Process Application (LangGraph)
    W->>DB: UPDATE applications SET state = ?
    W->>DB: INSERT INTO findings
    
    alt Success
        W->>DB: COMMIT
        W->>Q: ack(handle)
        Q->>O: UPDATE outbox_jobs SET status = 'DISPATCHED'
    else Failure (Retryable)
        W->>DB: ROLLBACK
        W->>Q: fail(handle, retryable=True)
        Q->>Q: Increment attempt_count
        Q->>W: Requeue after delay
    else Failure (Non-Retryable)
        W->>DB: ROLLBACK
        W->>Q: fail(handle, retryable=False)
        Q->>Q: Route to DLQ
    end
    
    Note over W: Stop Lease Heartbeat
```

---

## 💓 Lease Heartbeat Mechanism

```mermaid
sequenceDiagram
    participant W as Worker Thread
    participant H as Heartbeat Thread
    participant Q as Queue
    participant P as Pipeline Processing
    
    W->>P: Start Long-Running Job (OCR/RAG)
    W->>H: Start Heartbeat Thread
    
    loop Every 10 seconds
        H->>Q: extend_lease(handle, seconds=30)
        Q-->>H: Success
        H->>H: Sleep 10s
    end
    
    P->>P: OCR Processing (30-60s)
    P->>P: RAG Retrieval (5-10s)
    P->>P: LLM Generation (10-20s)
    
    P-->>W: Processing Complete
    W->>H: Stop Heartbeat Thread
    W->>Q: ack(handle) or fail(handle)
    
    Note over H,Q: Prevents visibility timeout<br/>expiration during long jobs
```

### Why Lease Heartbeat?

```mermaid
graph LR
    subgraph "Without Heartbeat (PROBLEM)"
        A[Job Starts] --> B[Visibility Timeout: 30s]
        B --> C[Processing Takes: 45s]
        C --> D[Timeout Expires at 30s]
        D --> E[Another Worker Picks Up Job]
        E --> F[Dual Processing!]
    end
    
    subgraph "With Heartbeat (SOLUTION)"
        G[Job Starts] --> H[Visibility Timeout: 30s]
        H --> I[Heartbeat Every 10s]
        I --> J[Extend Lease +30s]
        J --> K[Processing Continues: 45s]
        K --> L[No Duplicate Pickup]
        L --> M[Clean Acknowledge]
    end
    
    style F fill:#E57373
    style M fill:#81C784
```

---

## 🔁 Retry Strategy & DLQ

```mermaid
graph TB
    Start[Job Received] --> Process{Execute Pipeline}
    
    Process -->|Success| Commit[Commit Results]
    Commit --> Ack[Acknowledge]
    Ack --> Done[Done ✓]
    
    Process -->|Exception| Catch[Catch Exception]
    Catch --> Classify{Error Type?}
    
    Classify -->|Transient<br/>(Network, Timeout)| Retryable[retryable = True]
    Classify -->|Permanent<br/>(Invalid Data, Corrupted File)| Permanent[retryable = False]
    
    Retryable --> CheckCount{attempt_count <= 3?}
    
    CheckCount -->|Yes| Increment[attempt_count++]
    Increment --> Requeue[Requeue with Delay]
    Requeue --> Backoff[Exponential Backoff<br/>1s → 5s → 30s]
    Backoff --> Start
    
    CheckCount -->|No| MaxRetries[Max Retries Exceeded]
    MaxRetries --> DLQ[Route to DLQ]
    Permanent --> DLQ
    
    DLQ --> Log[Log Error Details]
    Log --> Alert[Alert Team]
    Alert --> Manual[Manual Investigation]
    
    Manual --> Fix[Fix Root Cause]
    Fix --> Reprocess[Reprocess from DLQ]
    
    style Done fill:#81C784
    style DLQ fill:#E57373
    style Alert fill:#FF9800
```

### Retry Configuration

```mermaid
graph LR
    A[Attempt 1] -->|Fail| B[Retry after 1s]
    B --> C[Attempt 2]
    C -->|Fail| D[Retry after 5s]
    D --> E[Attempt 3]
    E -->|Fail| F[Retry after 30s]
    F --> G[Attempt 4]
    G -->|Fail| H[DLQ]
    
    style A fill:#C8E6C9
    style C fill:#FFF9C4
    style E fill:#FFCCBC
    style G fill:#FFCCBC
    style H fill:#E57373
```

---

## 🎯 Idempotency Design

```mermaid
graph TB
    subgraph "Idempotency Check"
        A[Job Arrives] --> B{job_id in DB?}
        
        B -->|No| C[New Job]
        C --> D[Process Normally]
        D --> E[Save Results]
        E --> F[Acknowledge]
        
        B -->|Yes| G{Processing Status?}
        
        G -->|COMPLETED| H[Return Existing Results]
        H --> I[Skip Acknowledgement]
        
        G -->|IN_PROGRESS| J[Wait for Completion]
        J --> K[Poll State]
        K --> L{State Changed?}
        L -->|No| K
        L -->|Yes| H
        
        G -->|FAILED| M{Retryable?}
        M -->|Yes| N[Reprocess]
        M -->|No| O[Return Error]
        
        N --> D
    end
    
    style C fill:#81C784
    style H fill:#64B5F6
    style J fill:#FFF9C4
```

### Idempotency Invariant

> **Processing the same job ID multiple times MUST produce the same result without duplicating findings or corrupting state.**

```mermaid
graph LR
    subgraph "Guarantee"
        A[Job ID: JOB-123] --> B[First Processing]
        B --> C[Finding ID: F-001]
        
        A --> D[Duplicate Delivery]
        D --> E[Second Processing]
        E --> F[Same Finding ID: F-001]
        
        C --> G[No Duplicate Findings]
        F --> G
    end
    
    style G fill:#81C784
```

---

## 📦 Outbox Pattern Implementation

```mermaid
erDiagram
    applications ||--o{ documents : contains
    applications ||--o| outbox_jobs : triggers
    outbox_jobs ||--o| job_attempts : tracks
    
    applications {
        uuid id PK
        varchar application_id UK "APP-25195"
        varchar status "QUEUED, PROCESSING, etc"
        jsonb state "LoanApplicationState"
        timestamp created_at
        timestamp updated_at
    }
    
    documents {
        uuid id PK
        varchar document_id UK "DOC-UUID"
        varchar application_id FK
        varchar document_type
        varchar storage_key
        int page_count
    }
    
    outbox_jobs {
        uuid id PK
        varchar job_id UK "JOB-UUID"
        varchar application_id FK "APP-25195"
        jsonb payload "JobRef"
        varchar status "PENDING, DISPATCHED, FAILED"
        int retry_count
        timestamp created_at
        timestamp dispatched_at
    }
    
    job_attempts {
        uuid id PK
        varchar job_id FK
        int attempt_number
        timestamp started_at
        timestamp completed_at
        varchar result "SUCCESS, FAILURE"
        text error_message
    }
```

---

## 🚀 Worker Startup & Configuration

```mermaid
graph TB
    subgraph "Worker Initialization"
        Start[Worker Process Starts] --> Config[Load Configuration]
        Config --> Env[Read Environment Variables]
        
        Env --> QueueType{QUEUE_TYPE?}
        QueueType -->|local| PG[PostgreSQL Adapter]
        QueueType -->|sqs| SQS[SQS Adapter]
        
        PG --> Init1[Initialize PG Connection Pool]
        SQS --> Init2[Initialize SQS Client]
        
        Init1 --> Consumer[Start Consumer Loop]
        Init2 --> Consumer
    end
    
    subgraph "Consumer Loop"
        Consumer --> Poll[Poll for Jobs]
        Poll --> Receive[Receive Deliveries]
        Receive --> Process[Process Each Job]
        Process --> Ack[Acknowledge]
        Ack --> Poll
    end
    
    subgraph "Graceful Shutdown"
        Signal[SIGTERM Signal] --> Stop[Stop Accepting New Jobs]
        Stop --> Wait[Wait for In-Flight Jobs]
        Wait --> Complete{All Jobs Done?}
        Complete -->|Yes| Exit[Clean Exit]
        Complete -->|No| Wait
    end
    
    style Start fill:#E3F2FD
    style Exit fill:#C8E6C9
    style Signal fill:#FFF9C4
```

---

## 📊 Queue Adapter Interface

```mermaid
classDiagram
    class QueuePort {
        <<abstract>>
        +publish(job_ref: JobRef) None
        +receive(max_n: int) List~Delivery~
        +extend_lease(handle: str, seconds: int) None
        +ack(handle: str) None
        +fail(handle: str, retryable: bool) None
    }
    
    class PGQueueAdapter {
        -AsyncSession session
        -str queue_table
        +publish(job_ref: JobRef) None
        +receive(max_n: int) List~Delivery~
        +extend_lease(handle: str, seconds: int) None
        +ack(handle: str) None
        +fail(handle: str, retryable: bool) None
    }
    
    class SQSAdapter {
        -boto3 client
        -str queue_url
        -str dlq_url
        +publish(job_ref: JobRef) None
        +receive(max_n: int) List~Delivery~
        +extend_lease(handle: str, seconds: int) None
        +ack(handle: str) None
        +fail(handle: str, retryable: bool) None
    }
    
    class Delivery {
        +str handle
        +JobRef job_ref
        +int attempt_count
        +datetime received_at
    }
    
    class JobRef {
        +str job_id
        +str application_id
        +int attempt_count
        +str created_at
        +int priority
        +Dict metadata
    }
    
    QueuePort <|-- PGQueueAdapter : implements
    QueuePort <|-- SQSAdapter : implements
    QueuePort --> Delivery : returns
    Delivery --> JobRef : contains
```

---

## 🔍 Monitoring & Observability

```mermaid
graph TB
    subgraph "Metrics Collection"
        Worker[Worker Process] --> Metrics[Prometheus Metrics]
        
        Metrics --> M1[Jobs Processed]
        Metrics --> M2[Processing Duration]
        Metrics --> M3[Queue Depth]
        Metrics --> M4[Retry Count]
        Metrics --> M5[DLQ Size]
        Metrics --> M6[Lease Extensions]
    end
    
    subgraph "Logging"
        Worker --> Logs[Structured Logs]
        Logs --> L1[job_id]
        Logs --> L2[application_id]
        Logs --> L3[node_name]
        Logs --> L4[duration_ms]
        Logs --> L5[status]
        Logs --> L6[error_details]
    end
    
    subgraph "Alerting"
        Metrics --> AlertManager[Alert Manager]
        AlertManager --> A1[DLQ Not Empty > 5min]
        AlertManager --> A2[Processing Time > 120s]
        AlertManager --> A3[Retry Rate > 10%]
        AlertManager --> A4[Worker Crashes]
    end
    
    subgraph "Dashboards"
        Metrics --> Grafana[Grafana Dashboard]
        Logs --> Grafana
        
        Grafana --> D1[Real-time Queue Status]
        Grafana --> D2[Processing Pipeline Health]
        Grafana --> D3[Error Rate Trends]
    end
    
    style AlertManager fill:#E57373
    style Grafana fill:#64B5F6
```

---

## 🛡️ Failure Scenarios & Handling

```mermaid
graph TB
    subgraph "Scenario 1: Worker Crash"
        A1[Worker Processing Job] --> A2[Crash: SIGKILL]
        A2 --> A3[Lease Expires]
        A3 --> A4[Job Returns to Queue]
        A4 --> A5[Another Worker Picks Up]
        A5 --> A6[Idempotency Prevents Duplicate]
    end
    
    subgraph "Scenario 2: Database Unavailable"
        B1[Worker Commits Results] --> B2[DB Connection Lost]
        B2 --> B3[Rollback Transaction]
        B3 --> B4[Fail Message retryable=True]
        B4 --> B5[Requeue for Retry]
    end
    
    subgraph "Scenario 3: Corrupted Document"
        C1[OCR Processing] --> C2[File Corrupted]
        C2 --> C3[Parser Exception]
        C3 --> C4[Fail Message retryable=False]
        C4 --> C5[Route to DLQ]
        C5 --> C6[Manual Investigation]
    end
    
    subgraph "Scenario 4: LLM Timeout"
        D1[LLM Generation] --> D2[Timeout > 60s]
        D2 --> D3[Extend Lease Failed]
        D3 --> D4[Message Redelivered]
        D4 --> D5[Retry with Fresh Lease]
    end
    
    style A6 fill:#81C784
    style B5 fill:#FFF9C4
    style C5 fill:#FF9800
    style D5 fill:#64B5F6
```

---

## 📚 Related Documentation

- [LangGraph Workflow](langgraph_workflow.md) - Pipeline orchestration
- [System Overview](system_overview.md) - Complete architecture
- **Outbox dispatcher** - see [`apps/api/outbox_dispatcher.py`](../apps/api/outbox_dispatcher.py) and [`adapters/queue/`](../adapters/queue/)
- [Deployment Guide](deployment_guide.md) - Queue provisioning
