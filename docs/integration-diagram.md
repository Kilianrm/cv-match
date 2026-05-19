# Integration Diagram

```mermaid
flowchart TB
  U[User] --> FE[Frontend Web App]
  FE -. register/login .-> AUTH[Auth Provider]
  AUTH -. access token .-> FE
  FE --> API[API Service]
  API -. token validation .-> AUTH
  EB[Scheduler]
  NOTE1[All cross-service references use UUIDs: user_id, cv_id]

  API -. upsert_cv\n{user_id,cv_id} .-> S3[(CV File Storage key: cv/user_id/cv_id.pdf)]
  API -. map_sub_to_user_id .-> RDS
  API --> RDS[(PostgreSQL)]

  API -. parse_cv_requested\n{user_id,cv_id,trace_id} .-> QP[(Parser Owned Queue)]
  EB -. scrape_jobs_requested .-> QS[(SQS Scraper Queue)]
  API -. match_jobs_requested\n{scope=user,user_id,cv_id} .-> QM[(SQS Matcher Queue)]

  QP --> PARSER[CV Parser Service]
  QS --> SCRAPER[Job Scraper Service]
  QM --> MATCHER[Matching Service]

  PARSER -. get_cv\n{user_id,cv_id}.-> S3
  PARSER -. upsert_parsed_cv\n{cv/user_id/cv_id} .-> RDS
  PARSER -. match_jobs_requested\n{scope=user,user_id,cv_id} .-> QM
  SCRAPER --> RDS
  SCRAPER -. match_jobs_requested\n(scope=system) .-> QM
  MATCHER -. store matches .-> RDS
  MATCHER -. new_matches_available\n{user_id,match_id} .-> NQ[(Notification Queue)]

  SCRAPER --> JOBS[External Job Platforms]

  %% Notification is sent only when matcher publishes new_matches_available
  NQ --> NOTIFICATION[Notification Service]
  NOTIFICATION --> SES[Notification Provider]
  NOTIFICATION --> RDS

  API --> FE
```
