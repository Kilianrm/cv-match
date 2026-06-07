# AWS Architecture - CV Match

## Overview

CV Match is deployed on AWS as a cloud-native microservices architecture. Core workloads run in containerized services on ECS Fargate, with event-driven asynchronous processing via SQS and EventBridge, managed persistence with Aurora PostgreSQL and S3, and integrated observability through CloudWatch and X-Ray.

## Deployment Topology Diagram

Use this diagram to understand where each component is deployed in AWS and how infrastructure boundaries are organized.

- [docs/02-architecture/deployment-diagram.md](deployment-diagram.md)

## Integration Flow Diagram

Use this diagram to understand runtime interactions, asynchronous queues, and cross-service data flow.

- [docs/02-architecture/integration-diagram.md](integration-diagram.md)



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


## High-Level Data Flow

1. **User uploads CV (API)**
   - API receives PDF
    - Stores the file in S3 and writes upload metadata to Aurora PostgreSQL
   - Enqueues `parse_cv_requested` job to `CV Parser Owned Queue`
   - Returns job ID to frontend

2. **CV Parser Worker processes**
   - Dequeues `parse_cv_requested` from `CV Parser Owned Queue`
   - Fetches PDF from S3
   - Parses and normalizes data
    - Updates profile-related tables in Aurora PostgreSQL from parsed CV data
   - Deletes message from SQS
    - Enqueues `match_jobs_requested(scope=user,user_id,profile_id,trigger_type=upload)` job to `Matching Owned Queue`

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

## Scalability

### Horizontal
- **API Service**: ALB + auto-scaling, typically starting at 1 task in dev/test and 2 tasks in production-like MVP environments, then scaling horizontally based on CPU, memory, or request load
- **Worker Services**: Auto-scaling based on SQS queue depth
- **RDS**: Read replicas (optional) for reporting queries

### Vertical
- Fargate task sizes: 256 CPU / 512 MB to 4096 CPU / 30 GB
- RDS instance class: db.t3.micro to db.m5.4xlarge

## Performance

- Performance goals, bottleneck analysis, and optimization strategy are documented in [docs/02-architecture/performance.md](performance.md).


## Authentication

- Detailed authentication and authorization flows are documented in [docs/02-architecture/authentication.md](authentication.md).

## Security 

- Detailed controls, threat coverage, and incident practices are documented in [docs/02-architecture/security.md](security.md).

## Observability
- Observability standards, dashboards, alert rules, and operational monitoring are documented in [docs/02-architecture/observability.md](observability.md).

## Release and Operations
- Deployment environments, release flow, CI/CD policy, and rollback strategy are documented in [docs/02-architecture/release-operations.md](release-operations.md).
