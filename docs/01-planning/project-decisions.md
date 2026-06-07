# Project Decisions Worksheet

---

## Section 1: Problem & Users

**What problem are you solving?**
> Job seekers face a fragmented and inefficient process across multiple platforms that often require repetitive profile setup and manual filtering of low-relevance opportunities. From my own experience as a job seeker, this creates high friction and low return on time invested. I am building a system where users upload a CV once and receive relevant, continuously updated job matches with minimal effort.

---

**Who is your target user?**
> My target users are active job seekers who want to reduce the time and effort required to find relevant opportunities. The primary segment includes early- to mid-career professionals in digital and technology-related roles who apply across multiple platforms and face repetitive workflows. Over time, the platform can expand to support job seekers from other industries with similar pain points.

---

**What is your unique value vs existing services (LinkedIn, Indeed)?**
> CV Math is focused on speed, simplicity and immediate value: users upload their CV once and start receiving relevant opportunities without long setup flows. Unlike generic job boards, the platform combines personalized daily recommendations with AI-based CV optimization for each selected job. The core differentiator is reducing friction and helping users apply faster with higher-quality,role-specific CVs.
---

## Section 2: Core Features (MVP Only)

- Feature 1: User registration and profile creation (auto-extracted from PDF)
- Feature 2: Job aggregation from selected sources (scrape and normalize job offers)
- Feature 3: Matching engine (score and rank jobs based on user profile)
- Feature 4: Opportunities dashboard ( show top matches with source link and fit score)
- Feature 5: Daily notification (email first, multi-channel ready)
- Feature 6: AI-powered CV optimization per job (generate role-specific suggestions + downloadable PDF)

**Features you'll skip for now (but might add later):**
- Match explanation per opportunity ( why this job was recommended)
- Preference filters (location, remote preference, seniority level)

---

## Section 3: Business Data Flows

1. User: Signs up with email and password
2. System: Create user account and authentication token
3. User: Upload CV PDF file
4. System: Extracts and parses CV -> creates user profile (skills,experiencie,education,seniority)
5. User: View opportunities dashboard with job matches
6. System: Matches user profile against job database -> scores and ranks opportunities.
7. User: Clicks on a job opportunit and selects "Optimize my CV for this job"
8. System: Generates AI-powered CV suggestions tailored to that job (highlight relevant skills,reword bullets for ATS, add keywords)
9. System: Daily at 9 AM UTC, send notifications with new matches for the day.
11. User: Can manage notification preferences (enable/disable, change frequency, change channel)

**Why this flow delivers value:**

- Minimal friction (upload once, get matches immediately)
- Continuous value (daily recommendations)
- Competitive advantge (AI CV optimization per job)
- User control (notification preferences)

---

## Section 4: Microservices Boundaries

We are using a microservices approach because the core workflows in CV Math are naturally independent and asyncrhonous (CV parsing, job scraping, matching, notifications, and AI CV optimization). This architecture lets each service scale independently, improves fault isolation, and enables faster iteration per domain without redeploying the entire system. It also aligns with our learning and portfolio goals by demonstrating cloud-native patterns on AWS, including event-driven communication, service ownership, observability, and infrastructure automation with CDK

**Which services do you want to build?**

### Loosely Coupled (Recommended for MVP)
```
- API Service (handles user requests, exposes REST API)
- CV Parser Service (extracts data from PDFs)
- Job Scraper Service (collects jobs from websites)
- Matching Service (scores and ranks jobs)
- Notification Service (sends daily digests)
```

---

## Section 5: Data & Databases

**For each service, should it have its own database or share?**

| Service | Own DB? | Shared DB? | Reason |
|---------|---------|------------|--------|
| API Service | [ ] | [x] | The API manages core product data (users,profiles,matches,preferences). Shared DB keeps MVP simple and faster to deliver. |
| CV Parser Service | [ ] | [x] | Parser writes extracted CV profile data used by API and Matching; shared acces avoid synchronization complexity in MVP |
| Job Scraper Service | [x] | [ ] | |
| Matching Service | [ ] | [x] | Needs user/profile/match data from core domain; shared DB simplifies scroing and result persistence. |
| Notification Service | [ ] | [x ] | Needs user preferences and match results from core domain; shared DB reduces integration overhead |
| AI Optimization Service | [ ] | [x] | Reads user CV/profile and target job data, then stores optimization outputs; shared DB keeps the workflows straightforward in MVP.

**Note**: More services with own DBs = more complex, but better microservices design. Shared DB = simpler but less "micro".

---

## Section 6: Feature-to-service mapping:

```
1. User registration and profile creation -> API + CV Parser
2. Job aggregation -> Job Scraper
3. Matching engine -> Matching
4. Opportunities dashboard -> API (reads from matching data)
5. Daily notification -> Notification
6. AI CV Optimization -> AI Optimization
```


## Section 7: Communication Between Services

**How should services talk to each other?**


- **Async (Event Queue)**: Service A sends a message, Service B picks it up later
  - Tools: SQS, RabbitMQ, Kafka
  - Good for: Non-urgent work (parsing, scraping, email)
  - Trade-off: Delayed, but decoupled

**Which communication style for each service pair?**

| Interaction | Async or Sync? | Why? |
|-------------|----------------|------|
| API CV Parser | Async | CV parsing is background work and may take time; async keeps API fast and resilient |
| API Scraper | Async | Scraping is long-running and extrenal-source dependent; async prevents request blocking |
| API Matcher | Async | Matching can be compute-heavy and should run as a queued job for scalability. |
| API Notification | Async | Notifications are non-blocking and scheduled; async supports retries and failure isolation. |
| API AI CV Optimization | Async (default) / Sync (optional preview) | Full optimization can be slow, so async is safer; sync is only for very fast preview responses. |

---

## Section 8: Deployment Target

**Where do these services run?**

- [x] **ECS Fargate**: Containers, AWS managed (recommended for this project)
- [ ] **Kubernetes (EKS)**: More control, more complexity
- [ ] **Lambda**: Serverless, smaller services only
- [ ] **Mix**: Different services in different places

**Why?**
I choose ECS on Fargate because it provides a managed way to run containerized microservices on AWS while reducing infrastrucure management overhead.


---

## Section 9: Infrastructure as Code (IaC)

**How do you want to define and deploy your infrastructure?**

- [x] **AWS CDK + TypeScript**
- [ ] **Terraform**
- [ ] **Pulumi**
- [ ] **CloudFormation**


**Why?**
I chose AWS CDK with TypeScript because it provides a programmatic and strongly typed way to define infraestructure on AWS. This approach fits well with the project's architecture, improves maintanibility, and allows me to version, reuse, and automate infraestructure changes as part of the application lifecycle.


**Project structure you want?**
```
TBD
```

---

## Section 10: Observability & Monitoring

**What observability do you need per service?**

- [x] Logs Grafana Loki
- [x] Prometheus
- [x] Tracing: OpenTelemtry + Tempo
- [x] Alerting: Grafana Alerting
- [x] Cloud-native-integration; CloudWatch for AWS infreastructure signals.

**Minimum observability for each service:**

| Service | Logs | Metrics | Tracing | Alerts |
|---------|------|---------|---------|--------|
| API | Loki | Prometheus | Yes | Error rate > 5%, latency above threshold |
| Parser | Loki | Prometheus | Yes | Queue delay too high, parse failures |
| Scraper | Loki | Prometheus | Yes | Scraping failures, source unavailability |
| Matcher | Loki | Prometheus | Yes | Notification failures, retry spikes |
| Notification | Loki | Prometheus | Yes | Optimization failures, high response time |

Fill in with your choices: "CloudWatch", "Prometheus", "DataDog", "yes", "no", etc.

---


