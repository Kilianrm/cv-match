# AWS Architecture - CV Match

## Overview

CV Match is deployed on AWS as a cloud-native microservices architecture. Core workloads run in containerized services on ECS Fargate, with event-driven asynchronous processing via SQS and EventBridge, managed persistence with Aurora PostgreSQL and S3, and integrated observability through CloudWatch and X-Ray.

## Deployment Diagram

```mermaid
graph TB
    subgraph "Frontend"
        S3_FE["AWS S3<br/>(Static Assets)"]
        CF["AWS CloudFront<br/>(CDN)"]
    end

    subgraph "Networking"
        ALB["Application Load Balancer<br/>(Public HTTPS)"]
        NG["Security Groups<br/>& NACLs"]
    end

    subgraph "Compute: ECS Fargate"
        API["API Service<br/>(FastAPI/Node)"]
        PARSER["Parser Worker"]
        SCRAPER["Scraper Worker"]
        MATCHER["Matcher Worker"]
        EMAIL_W["Email Worker"]
    end

    subgraph "Data Layer"
        RDS["RDS PostgreSQL<br/>(Multi-AZ)"]
        S3_CV["S3 Bucket<br/>(CV PDFs)"]
        SECRETS["Secrets Manager<br/>(DB password, API keys)"]
    end

    subgraph "Async & Scheduling"
        SQS["SQS Queue<br/>(parse, scrape, match jobs)"]
        EB["EventBridge Scheduler<br/>(Scrape and system-match schedules)"]
    end

    subgraph "External Services"
        COGNITO["Amazon Cognito<br/>(User auth)"]
        SES["Amazon SES<br/>(Email delivery)"]
    end

    subgraph "Observability"
        CW_LOGS["CloudWatch Logs"]
        CW_METRICS["CloudWatch Metrics"]
        XRAY["AWS X-Ray<br/>(Tracing)"]
    end

    CF --> S3_FE
    CF --> ALB
    ALB --> API

    API --> COGNITO
    API --> RDS
    API --> S3_CV
    API --> SQS
    API --> SECRETS

    SQS --> PARSER
    SQS --> SCRAPER
    SQS --> MATCHER
    SQS --> EMAIL_W

    PARSER --> RDS
    SCRAPER --> RDS
    MATCHER --> RDS
    EMAIL_W --> SES

    EB --> SQS

    API --> CW_LOGS
    PARSER --> CW_LOGS
    SCRAPER --> CW_LOGS
    MATCHER --> CW_LOGS
    EMAIL_W --> CW_LOGS

    API --> CW_METRICS
    API --> XRAY
```

## Service-by-Service Details

### Frontend
- **S3 Bucket**: Hosts React/Vue/Angular static app (dist/ files)
- **CloudFront**: CDN for fast global delivery, HTTPS, caching
- **Route 53**: Domain routing

### Public API Entry Point
- **Application Load Balancer**: Routes HTTP/HTTPS traffic to Fargate tasks
- **Security Groups**: Restrict inbound to ALB only
- **ACM Certificate**: Automatic HTTPS

### Compute: ECS Fargate
- **Cluster**: The ECS runtime boundary that groups the API and worker services and hosts their running tasks
- **Service: API**: Long-running public backend behind the ALB, using 1 task in cost-sensitive dev/test environments and 2 tasks when validating load balancing or basic availability in MVP environments
- **Service: Parser**: Queue-driven worker, starting with 1 task for MVP and scaling out only if parse backlog or processing time becomes too high
- **Service: Scraper**: Queue-driven worker, starting with 1 task for MVP and processing one source per scrape job (for example, LinkedIn or Indeed); scales out only when multiple source-specific jobs must run in parallel
- **Service: Matcher**: Queue-driven worker, starting with 1 task for MVP and scaling out only if matching jobs accumulate or completion time becomes too high
- **Service: Notifications**: Queue-driven worker, starting with 1 task for MVP and sending email digests only when eligible events are published by the matching flow

Each service is a Docker container defined in ECR (Elastic Container Registry).

### Database: Aurora PostgreSQL
- **Engine**:ard RDS PostgreSQL, but I chose Aurora PostgreSQL because it gives a stronger AWS-native story, better scalability, and higher avai PostgreSQL 14+ compatible
- **Why Aurora**: I considered standlability while keeping PostgreSQL compatibility
- **Multi-AZ**: Automatic failover and backups
- **Subnet Group**: Private subnets only (no public IP)
- **Security Group**: Ingress from Fargate tasks only
- **Backups**: Automated daily, retained for 7 days
- **Encryption**: Encryption at rest

### Storage: S3
- **Bucket 1**: User-uploaded CVs (private, encrypted)
- **Bucket 2**: Job scraping cache (TTL via lifecycle policies)
- **Bucket 3**: Application logs, exports, and optional deployment artifacts (for example, CDK assets)
- **Versioning**: Enabled on CV bucket
- **Access**: Via IAM role attached to Fargate task

**Note:** Infrastructure as code source stays in the repository; AWS may use S3 internally for deployment assets, but that is separate from product storage.

### Async: SQS + EventBridge
- **SQS Queue**: Standard queue, 5-minute visibility timeout
        - Message types: [`TO BE DEFINED`]
    - Scrape job unit: one message per source so workers can process sources independently
  - DLQ: Captures failed messages for replay
- **EventBridge Rules**:
    - Triggers scheduled scrape jobs
    - Triggers scheduled system-scope matching jobs (for example, with an offset after scraping)

### Auth: Cognito

Detailed authentication and authorization flows are documented in [docs/02-architecture/authentication.md](authentication.md).

### Secrets: Secrets Manager
- **Secret Scope**: Stores sensitive runtime configuration only (database credentials, third-party API keys, and AI provider credentials)
- **Least-Privilege Access**: Each ECS service task role reads only the secrets it needs; secrets are not shared broadly across services
- **Runtime Retrieval**: Services fetch secrets at startup or via periodic refresh, avoiding hardcoded credentials in code, images, or environment files committed to source control
- **Rotation Policy**: Automatic rotation enabled where supported (for example, database credentials), with periodic manual rotation for external provider keys that do not support native rotation
- **Auditability**: Access to secrets is logged with CloudTrail and monitored for unusual read patterns

### Observability
- Observability standards, dashboards, alert rules, and operational monitoring are documented in [docs/02-architecture/observability.md](observability.md).

### Deployment Operations
- Deployment environments, release flow, CI/CD policy, and rollback strategy are documented in [docs/02-architecture/deployment.md](deployment.md).

## High-Level Data Flow

1. **User uploads CV (API)**
   - API receives PDF
   - Upsert in S3
   - Enqueues `parse_cv_requested` job to `CV Parser Owned Queue`
   - Returns job ID to frontend

2. **CV Parser Worker processes**
   - Dequeues `parse_cv_requested` from `CV Parser Owned Queue`
   - Fetches PDF from S3
   - Parses and normalizes data
   - Upsert CV profile to Aurora PostgreSQL
   - Deletes message from SQS
   - Enqueues `match_jobs_requested(scope=user,user_id,cv_id,trigger_type = upload)` job to `Matching Owned Queue`

3. **Job Scraper Worker processes one source per job**
    - A scheduled workflow enqueues ` scrape_jobs_requested(source,trace_id,trigger_type=scheduled)` job to `Job Scraper Owned Queue`
    - Job scraper worker processes dequeues `scrape_jobs_requested(source,trace_id,trigger_type=scheduled)` from SQS
    - A scraper task connects to the target external job platform source (for example LinkedIn, Indeed, or InfoJobs), fetches raw offers, and normalizes them
    - Upserts normalized offers to Aurora PostgreSQL
    - Deletes message from `Job Scraper Owned Queue`

4. **Matcher Worker runs periodically**
    - Dequeues `match_jobs_requested` from `Job Matching Owned Queue`
     - If `scope=user`, computes matches only for the requested user profile
     - If `scope=system`, computes matches for all eligible users against newly available job offers
    - Fetches user profile + all available jobs
    - Scores and ranks matches
    - Writes matches to Aurora PostgreSQL
    - If `scope=system`, enqueues `notify_requested(match_id,trigger_type=scheduled)` to `Notification Owned Queue` 
    - Deletes message from `Job Matching Owned Queue`

5. **Notification Worker sends digest emails when eligible**
    - Dequeues `notify_requested` from `Notification Owned Queue`
    - Sends digest email via SES
    - Records digest in Aurora PostgreSQL
    - Deletes message from `Notification Owned Queue`

## Security Model

Detailed controls, threat coverage, and incident practices are documented in [docs/02-architecture/security.md](security.md).

## Scalability

### Horizontal
- **API Service**: ALB + auto-scaling, typically starting at 1 task in dev/test and 2 tasks in production-like MVP environments, then scaling horizontally based on CPU, memory, or request load
- **Worker Services**: Auto-scaling based on SQS queue depth
- **RDS**: Read replicas (optional) for reporting queries

### Vertical
- Fargate task sizes: 256 CPU / 512 MB to 4096 CPU / 30 GB
- RDS instance class: db.t3.micro to db.m5.4xlarge

## Cost Estimation (USD/month, free tier included)

| Service | Usage | Cost |
|---------|-------|------|
| ECS Fargate | 100 GB-hours/month (4 services) | $20 |
| Aurora PostgreSQL | Serverless or small provisioned cluster | $15+ |
| S3 | 100 GB stored, 1M requests | $5 |
| ALB | 1 LCU equivalent | $18 |
| CloudFront | 1 TB transfer | $85 |
| SQS | 1M messages/month | $0.40 |
| SES | 50k emails/month | $0 (free tier) |
| **Total** | | **~$143** |

Free tier can reduce this by ~30%.

