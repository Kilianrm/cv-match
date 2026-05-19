# Planning Phase Guide

Welcome. This folder contains **planning templates** to help you think through CV Match systematically before you start coding.

**Goal**: Make thoughtful decisions about microservices, APIs, databases, and deployment. No rushing.

---

## How to Use These Documents

### Phase 1: Answer the Project Decisions (1-2 hours)

**File**: `01-project-decisions.md`

This is a **worksheet** with 12 sections. Fill it out thoughtfully:

1. **Problem & Users**: What are you solving?
2. **Core Features**: What's MVP-only?
3. **Data Flows**: How does a user get value?
4. **Microservices Boundaries**: Which services?
5. **Data & Databases**: Own DB or shared?
6. **Communication**: Async or sync?
7. **Deployment Target**: ECS? Kubernetes? Lambda?
8. **Infrastructure as Code**: CDK (confirmed), Terraform, or Pulumi?
9. **Observability**: Logs? Metrics? Tracing? Alerts?
10. **Timeline**: Hours/week? Which cloud skill first?
11. **Success Criteria**: What does "done" look like?
12. **Open Questions**: What are you uncertain about?

**Don't overthink**?just write your best guesses. This is a working document; change answers as you learn.

**Output**: A filled-out `01-project-decisions.md` with your answers.

---

### Phase 2: Define Each Microservice (1 week, 1-2 hours per service)

**File**: `02-service-definition-template.md` (blank template)  
**Reference**: `03-service-definition-example-parser.md` (filled example)

For **each microservice** you identified in Phase 1, create a copy of the template and fill it out:

```
Service 1: API Service
  ? docs/planning/service-api-definition.md

Service 2: CV Parser Service
  ? docs/planning/service-parser-definition.md

Service 3: Job Scraper Service
  ? docs/planning/service-scraper-definition.md

Service 4: Matching Service
  ? docs/planning/service-matcher-definition.md

Service 5: Email Service
  ? docs/planning/service-email-definition.md
```

**For each service, you'll capture:**
- Purpose & why it's separate
- What it receives (input) & produces (output)
- Data model (does it store anything?)
- APIs or message formats
- Dependencies on other services
- Error handling & recovery
- Scaling strategy (how many instances?)
- Deployment (Docker, CDK construct)
- Monitoring (logs, metrics, alerts)
- Testing strategy
- Known limitations

**Use the example (`03-service-definition-example-parser.md`) as a guide.** Don't need that much detail for MVP?just enough to think clearly.

**Output**: 5 service definition files, one per microservice.

---

### Phase 3: Integration Diagram (1-2 hours)

Create a **visual showing how services talk**:

```
??????????????????????????????????????????????
?                Frontend (React)            ?
?                S3 + CloudFront             ?
????????????????????????????????????????????
                 ? HTTPS
                 ?
        ???????????????????
        ?  ALB            ?
        ? (public, HTTPS) ?
        ???????????????????
                 ?
    ???????????????????????????
    ?            ?            ?
    ?            ?            ?
??????????  ??????????  ??????????
? API    ?  ? Health ?  ? Metrics?
?Service ?  ? Check  ?  ?Handler ?
??????????  ??????????  ??????????
    ?
    ?? SQS: parse_cv_requested
    ?     ?? Parser Service reads
    ?     ?? Parser Service ? RDS
    ?     ?? Parser Service ? S3
    ?
    ?? SQS: scrape_jobs_requested
    ?     ?? Scraper Service ? RDS
    ?
    ?? SQS: match_jobs_requested
    ?     ?? Matcher Service ? RDS
    ?
    ?? EventBridge: daily 9 AM UTC
          ?? SQS: send_digest_daily
                ?? Email Service ? SES
```

You can draw this in:
- Mermaid (if you have VS Code extension)
- Lucidchart, Figma, Draw.io (free)
- Even ASCII art on a piece of paper

**Output**: A diagram in your docs showing service communication.

---

### Phase 4: Data Model (2-3 hours)

Based on your service definitions, create a **unified database schema**:

**Tables needed:**
- Users
- CVs
- Parsed Profiles
- Job Offers
- Matches
- Email Digests
- (Any others?)

**For each table:**
- Columns & types
- Primary key
- Foreign keys
- Indexes
- Example rows

**Example schema snippet:**
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE cvs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  s3_url VARCHAR(1000) NOT NULL,
  uploaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE parsed_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  cv_id UUID NOT NULL REFERENCES cvs(id),
  skills TEXT[],
  years_experience INT,
  parsed_at TIMESTAMP DEFAULT NOW()
);
```

**Tools:**
- Use `docs/schema.md` for the SQL  
- Draw an ER diagram (Mermaid or Draw.io)

**Output**: `schema.md` with full database design.

---

### Phase 5: API Specification (2-3 hours)

List all REST endpoints your **API Service** exposes:

```
POST /auth/register
  Body: { email, password }
  Response: { user_id, token }

POST /auth/login
  Body: { email, password }
  Response: { user_id, token }

POST /cv/upload
  Body: multipart file (PDF)
  Response: { cv_id, job_id, status: "queued" }

GET /profile
  Response: { user_id, email, parsed_profile: {...} }

GET /matches
  Query: ?limit=10&score_min=70
  Response: [ { job_id, match_score, job_title, company, link } ]

POST /matches/{match_id}/optimize-cv
  Body: { target_job_id }
  Response: { optimization_suggestions: [...] }

PUT /email-digest/preferences
  Body: { frequency: "daily", send_time: "09:00" }
  Response: { updated: true }
```

**For each endpoint:**
- HTTP method & path
- Query parameters
- Request body (JSON schema)
- Response body (example)
- Authentication (JWT required?)
- Error codes (400, 401, 500, etc.)

**Output**: `docs/api-spec.md`

---

### Phase 6: Deployment Strategy (1-2 hours)

Answer:
1. **Where does each service run?** (ECS Fargate, same cluster or different?)
2. **How do they communicate?** (SQS, REST, gRPC?)
3. **Where is the database?** (RDS PostgreSQL in private subnet)
4. **Where is the storage?** (S3)
5. **How do we deploy?** (CDK constructs per service)

**Output**: `docs/deployment-strategy.md` (text + diagram)

---

## Timeline for Planning Phase

| Day | Task | Output |
|-----|------|--------|
| Day 1 | Fill `01-project-decisions.md` | Answers to all 12 sections |
| Day 2-3 | Define Service 1 (API) | `service-api-definition.md` |
| Day 3-4 | Define Service 2 (Parser) | `service-parser-definition.md` |
| Day 4-5 | Define Services 3-5 | 3 more definition files |
| Day 6 | Create integration diagram | `integration-diagram.md` or image |
| Day 7 | Design database schema | `schema.md` |
| Day 8 | List all API endpoints | `api-spec.md` |
| Day 9-10 | Deployment strategy | `deployment-strategy.md` |

**Total: ~2 weeks** of thoughtful planning before you write code.

---

## What You'll Have After Planning

1. **01-project-decisions.md**: Your product vision & constraints
2. **service-{name}-definition.md** (x5): Each service fully defined
3. **integration-diagram**: How services connect
4. **schema.md**: Complete database design
5. **api-spec.md**: All REST endpoints
6. **deployment-strategy.md**: Infrastructure decisions

**Then**: You can hand these to a developer (or start building) with very clear direction. No ambiguity. No "wait, how do these talk?"

---

## Tips for Success

**1. Write it down.** Don't keep decisions in your head. Write them in these docs.

**2. Change your mind.** These are drafts. As you learn, update them.

**3. Ask questions.** If something is unclear, write it in "Open Questions" section.

**4. Talk to others.** Share your decisions with a peer/mentor. Get feedback before building.

**5. Use the example.** `03-service-definition-example-parser.md` is a full example. Copy its structure.

**6. Don't over-engineer.** MVP just needs to work, not be perfect. You can improve post-MVP.

---

## Next: Once Planning Is Done

Once you've filled these out, we'll:
1. Review your decisions for consistency & feasibility
2. Create the CDK project structure based on your services
3. Build the backend MVP incrementally
4. Deploy to AWS and test

---

## Questions?

If you get stuck on any template section:
- Re-read the example
- Write your best guess
- Mark it as "needs review" and move on

You can always refine later.

**Start with `01-project-decisions.md` now.** Take your time. This is the foundation of everything that comes next.
