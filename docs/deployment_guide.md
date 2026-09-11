# Deployment Guide

**Local Development & Cloud Production Deployment**

---

## 📋 Overview

FinScan AI supports two deployment modes:
1. **Local Development**: Zero-cost, all services in Docker containers
2. **Cloud Production**: AWS EC2 with managed services, budget-controlled

---

## 🐳 Local Development Setup

### Architecture

```mermaid
graph TB
    subgraph "Developer Machine"
        subgraph "Docker Compose"
            PG[PostgreSQL 16<br/>Container]
            Redis[Redis 7<br/>Container]
            API[FastAPI<br/>Container :8000]
            Worker[Worker<br/>Container]
            UI[Vite Dev Server<br/>:5173]
        end
        
        Browser[Browser<br/>http://localhost:5173]
        DBAdmin[pgAdmin / DBeaver]
    end
    
    Browser --> UI
    Browser --> API
    
    UI --> API
    API --> PG
    API --> Redis
    Worker --> PG
    Worker --> Redis
    
    DBAdmin --> PG
    
    style PG fill:#336791
    style Redis fill:#DC382D
    style API fill:#009688
    style Worker fill:#FF9800
    style UI fill:#61DAFB
```

### Prerequisites

```mermaid
graph LR
    A[Prerequisites] --> B[Python 3.10+]
    A --> C[Docker Desktop]
    A --> D[Node.js 18+]
    A --> E[Git]
    
    B --> B1[python --version]
    C --> C1[docker --version]
    D --> D1[node --version]
    E --> E1[git --version]
    
    style A fill:#E3F2FD
```

### Step-by-Step Setup

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Git as GitHub
    participant Env as .env
    participant Docker as Docker Compose
    participant DB as PostgreSQL
    participant API as FastAPI
    
    Dev->>Git: git clone repo
    Dev->>Dev: cd loan-doc-processing-agent
    
    Dev->>Env: cp .env.example .env
    Dev->>Env: Edit .env with local config
    
    Dev->>Docker: docker-compose up -d postgres redis
    
    Docker->>DB: Start PostgreSQL
    Docker->>DB: Run migrations
    
    Dev->>Dev: python -m venv venv
    Dev->>Dev: source venv/bin/activate
    Dev->>Dev: pip install -r requirements.txt
    Dev->>Dev: pip install -e .
    
    Dev->>Dev: cd apps/ui && npm install
    
    Dev->>API: python -m uvicorn apps.api.main:app --reload
    
    Note over Dev,API: API running on http://localhost:8000
    
    Dev->>Dev: cd apps/ui && npm run dev
    
    Note over Dev,API: UI running on http://localhost:5173
```

---

## ☁️ Cloud Production Deployment

### Architecture

```mermaid
graph TB
    subgraph "AWS Cloud"
        subgraph "VPC"
            subgraph "EC2 t4g.medium ARM64"
                Caddy[Caddy Reverse Proxy<br/>HTTPS Let's Encrypt]
                
                subgraph "Docker Containers"
                    API_Prod[FastAPI Container]
                    Worker_Prod[Worker Container]
                    PG_Prod[PostgreSQL Container]
                    Redis_Prod[Redis Container]
                end
            end
            
            SQS[SQS Queue + DLQ]
            S3[S3 Bucket<br/>Block Public Access]
        end
        
        IAM[IAM Roles<br/>Least Privilege]
        CW[CloudWatch Logs]
    end
    
    Internet[Internet Users] -->|HTTPS| Caddy
    
    Caddy --> API_Prod
    API_Prod --> PG_Prod
    API_Prod --> Redis_Prod
    API_Prod --> SQS
    API_Prod --> S3
    
    Worker_Prod --> SQS
    Worker_Prod --> S3
    Worker_Prod --> PG_Prod
    
    API_Prod --> CW
    Worker_Prod --> CW
    
    API_Prod --> IAM
    Worker_Prod --> IAM
    
    style Caddy fill:#61DAFB
    style API_Prod fill:#009688
    style SQS fill:#9C27B0
    style S3 fill:#FF9800
```

### Cost Breakdown

```mermaid
pie title "Weekly Budget Allocation ($25 Ceiling)"
    "EC2 t4g.medium (50 hrs @ $0.034/hr)" : 1.70
    "EBS gp3 (20 GB)" : 0.46
    "SQS (first 1M requests free)" : 0.00
    "S3 (5 GB storage + requests)" : 0.12
    "Data Transfer (minimal)" : 0.50
    "Buffer for Overages" : 2.22
    "Total Used" : 5.00
    "Remaining Buffer" : 20.00
```

### Provisioning Steps

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant AWS as AWS Console
    participant EC2 as EC2 Instance
    participant S3 as S3 Bucket
    participant SQS as SQS Queue
    participant IAM as IAM
    
    Dev->>AWS: Create EC2 Key Pair
    AWS-->>Dev: Download .pem key
    
    Dev->>AWS: Launch t4g.medium Instance
    AWS->>EC2: Ubuntu 22.04 LTS ARM64
    EC2->>EC2: Attach IAM Role: FinScanEC2Role
    
    Dev->>IAM: Create IAM Policy
    IAM->>IAM: s3:PutObject, s3:GetObject<br/>sqs:SendMessage, sqs:ReceiveMessage
    IAM->>EC2: Attach Role to Instance
    
    Dev->>S3: Create Bucket: finscan-docs
    S3->>S3: Enable Block Public Access
    S3->>S3: Enable Server-Side Encryption
    
    Dev->>SQS: Create Queue: finscan-jobs
    SQS->>SQS: Visibility Timeout: 300s
    SQS->>SQS: Redrive Policy: DLQ after 3 failures
    
    Dev->>SQS: Create DLQ: finscan-dlq
    
    Dev->>EC2: SSH into Instance
    Dev->>EC2: Install Docker & Docker Compose
    Dev->>EC2: Install Git
    
    Dev->>EC2: git clone repo
    Dev->>EC2: Configure .env with AWS resources
    
    Dev->>EC2: docker-compose -f docker-compose.prod.yml up -d
    
    EC2->>EC2: Start Caddy, API, Worker, Postgres, Redis
    
    Dev->>EC2: Verify HTTPS via Caddy
    
    Note over Dev,EC2: Application Live<br/>https://finscan.example.com
```

### Security Configuration

```mermaid
graph TB
    subgraph "Network Security"
        SG[Security Group] --> Inbound[Inbound Rules]
        SG --> Outbound[Outbound Rules]
        
        Inbound --> Rule1[Port 22 SSH<br/>Your IP Only]
        Inbound --> Rule2[Port 443 HTTPS<br/>0.0.0.0/0]
        Inbound --> Rule3[Port 80 HTTP<br/>Redirect to HTTPS]
        
        Outbound --> Rule4[All Traffic<br/>0.0.0.0/0]
    end
    
    subgraph "IAM Permissions"
        Role[EC2 IAM Role] --> S3Perm[S3 Access<br/>finscan-docs/*]
        Role --> SQSPerm[SQS Access<br/>finscan-jobs, finscan-dlq]
        Role --> CWPerm[CloudWatch Logs<br/>finscan-*]
    end
    
    subgraph "Encryption"
        Storage[S3 Encryption] --> SSE[SSE-S3 or SSE-KMS]
        Transit[Transit Encryption] --> HTTPS[HTTPS Only]
        DB[Database Encryption] --> PGEncr[PostgreSQL Encryption at Rest]
    end
    
    style SG fill:#F44336
    style Role fill:#FF9800
    style Storage fill:#9C27B0
```

---

## 🔧 Configuration Management

### Environment Variables

```mermaid
graph LR
    subgraph "Required Variables"
        A[DATABASE_URL] --> A1[PostgreSQL Connection String]
        B[REDIS_URL] --> B1[Redis Connection String]
        C[QUEUE_TYPE] --> C1["local" or "sqs"]
        D[STORAGE_TYPE] --> D1["local" or "s3"]
        E[LLM_PROVIDER] --> E1["local" or "opencode"]
    end
    
    subgraph "Cloud-Specific"
        F[AWS_REGION] --> F1["us-east-1"]
        G[SQS_QUEUE_URL] --> G1["https://sqs..."]
        H[S3_BUCKET] --> H1["finscan-docs"]
    end
    
    subgraph "Optional"
        I[TEXTRACT_ENABLED] --> I1["false" (default)]
        J[TEXTRACT_MAX_PAGES] --> J1["100" (cap)]
        K[BUDGET_CEILING] --> K1["25" (dollars)]
    end
    
    style A fill:#E57373
    style C fill:#FFF9C4
    style I fill:#C8E6C9
```

---

## 🚀 Deployment Workflow

### Local Development

```mermaid
graph LR
    A[Code Changes] --> B[Run Tests<br/>pytest]
    B --> C{Tests Pass?}
    C -->|No| D[Fix Issues]
    D --> A
    C -->|Yes| E[Commit & Push]
    E --> F[Create PR]
    F --> G[Review & Merge]
    G --> H[CI Runs Tests]
    H --> I{CI Pass?}
    I -->|No| D
    I -->|Yes| J[Merged to Main]
    
    style C fill:#FFF9C4
    style I fill:#FFF9C4
    style J fill:#C8E6C9
```

### Production Deployment

```mermaid
graph TB
    subgraph "Pre-Deployment"
        A[Merge to Main] --> B[CI Tests Pass]
        B --> C[Build Docker Images]
        C --> D[Run Migrations Locally]
    end
    
    subgraph "Deployment"
        D --> E[SSH to EC2]
        E --> F[git pull origin main]
        F --> G[Stop Running Containers]
        G --> H[Pull New Images]
        H --> I[Run DB Migrations]
        I --> J[Start Containers]
    end
    
    subgraph "Post-Deployment"
        J --> K[Health Check<br/>GET /health]
        K --> L{Healthy?}
        L -->|Yes| M[Monitor Logs]
        L -->|No| N[Rollback<br/>docker-compose down<br/>docker-compose up -d --build previous]
        N --> O[Investigate Issue]
    end
    
    style K fill:#FFF9C4
    style L fill:#FFF9C4
    style M fill:#C8E6C9
    style N fill:#E57373
```

---

## 📊 Monitoring & Logging

### Log Aggregation

```mermaid
graph TB
    subgraph "Application Logs"
        API[FastAPI Logs] --> CW[CloudWatch Logs]
        Worker[Worker Logs] --> CW
        Caddy[Caddy Logs] --> CW
    end
    
    subgraph "Log Streams"
        CW --> Stream1[/finscan/api]
        CW --> Stream2[/finscan/worker]
        CW --> Stream3[/finscan/caddy]
    end
    
    subgraph "Log Insights Queries"
        Stream1 --> Query1[Error Rate by Endpoint]
        Stream2 --> Query2[Job Processing Duration]
        Stream3 --> Query3[HTTPS Request Latency]
    end
    
    subgraph "Alerting"
        Query1 --> Alert1[Error Rate > 5%]
        Query2 --> Alert2[Processing > 120s]
        Query3 --> Alert3[p95 Latency > 1s]
    end
    
    style CW fill:#FF9800
    style Alert1 fill:#E57373
    style Alert2 fill:#E57373
    style Alert3 fill:#E57373
```

### Health Checks

```mermaid
sequenceDiagram
    participant Monitor as CloudWatch/External
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Redis as Redis
    participant S3 as S3
    
    loop Every 30 seconds
        Monitor->>API: GET /health
        API->>DB: SELECT 1
        DB-->>API: OK
        API->>Redis: PING
        Redis-->>API: PONG
        
        alt S3 Configured
            API->>S3: HEAD bucket
            S3-->>API: OK
        end
        
        alt All Checks Pass
            API-->>Monitor: 200 OK {status: "healthy"}
        else Any Check Fails
            API-->>Monitor: 503 {status: "unhealthy", reason: "..."}
        end
    end
```

---

## 🔁 Rollback Strategy

```mermaid
graph TB
    subgraph "Rollback Triggers"
        A[Health Check Failure] --> Rollback[Initiate Rollback]
        B[Error Rate Spike > 10%] --> Rollback
        C[Latency p95 > 2s] --> Rollback
        D[Manual Decision] --> Rollback
    end
    
    subgraph "Rollback Procedure"
        Rollback --> Stop[Stop Current Containers]
        Stop --> Identify[Identify Previous Version<br/>git log --oneline -n 10]
        Identify --> Checkout[git checkout <previous-commit>]
        Checkout --> Rebuild[Rebuild Images<br/>docker-compose build]
        Rebuild --> Restart[Start Containers<br/>docker-compose up -d]
        Restart --> Verify[Health Check]
        
        Verify --> E{Healthy?}
        E -->|Yes| F[Notify Team<br/>Rollback Complete]
        E -->|No| G[Escalate to Manual Debug]
    end
    
    style Rollback fill:#F44336
    style F fill:#C8E6C9
    style G fill:#E57373
```

---

## 💰 Cost Optimization

### Instance Scheduling

```mermaid
graph TB
    subgraph "Work Hours (9 AM - 9 PM IST)"
        A[Start Instance] --> B[Process Jobs]
        B --> C[Serve Demo Requests]
        C --> D[Active Monitoring]
    end
    
    subgraph "Non-Work Hours (9 PM - 9 AM IST)"
        E[Stop Instance] --> F[Zero Compute Cost]
        F --> G[Queue Jobs in SQS<br/>for Next Day]
    end
    
    subgraph "Cost Savings"
        H[24/7 Running] --> H1["$2.38/day"]
        I["12/7 Running (50%)"] --> I1["$1.19/day"]
        J[Weekly Cost] --> J1["$8.33 vs $16.66"]
    end
    
    style F fill:#C8E6C9
    style I1 fill:#C8E6C9
```

### Resource Right-Sizing

```mermaid
graph LR
    subgraph "Instance Selection"
        A[t4g.micro - 1 vCPU, 1GB] --> A1["✗ Insufficient for OCR"]
        B[t4g.small - 2 vCPU, 2GB] --> B1["△ May struggle with OCR + LLM"]
        C[t4g.medium - 2 vCPU, 4GB] --> C1["✓ Optimal for demo"]
        D[t4g.large - 2 vCPU, 8GB] --> D1["✗ Over-provisioned for demo"]
    end
    
    style A1 fill:#E57373
    style B1 fill:#FFCCBC
    style C1 fill:#C8E6C9
    style D1 fill:#FFF9C4
```

---

## 📚 Related Documentation

- [System Overview](system_overview.md) - Architecture components
- [Worker Architecture](worker_queue_architecture.md) - Queue configuration
- [Security Architecture](security_architecture.md) - IAM and encryption setup
- **Health endpoints** - see [`apps/api/main.py`](../apps/api/main.py); live OpenAPI at `http://localhost:8000/docs`
