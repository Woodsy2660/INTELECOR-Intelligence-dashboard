# INTELECOR — Backend Architecture

## Overview

INTELECOR is a practice intelligence platform that sits on top of Gentu practice management software. It pulls data from Gentu's APIs and CSV billing exports, computes analytics, and serves results to a React dashboard. The architecture is designed around three principles: data minimisation (store the least patient data possible), analytical depth (provide meaningful historical trends), and privacy compliance (meet Australian Privacy Act requirements by design, not by policy).

The system does not replicate Gentu's database. It processes operational data transiently in memory, stores only computed aggregates permanently, and pulls patient-level detail directly from Gentu's API in real-time when the user needs it. The only permanent raw data in PostgreSQL is billing records imported from CSV exports — because no billing API exists, and financial analytics is the core value proposition.

---

## Architecture Pattern: Hybrid Transient Cache + Permanent Results

This is Approach C from the architecture evaluation. It combines three data handling strategies in a single system:

**Permanent storage** — billing CSV records (de-identified) and computed analytics snapshots live in PostgreSQL indefinitely. These power historical trend analysis and period-over-period comparisons.

**Transient processing** — operational data from Gentu's APIs (appointments, documents, referrals) is pulled into memory, processed through analytics modules, and discarded. Only the computed aggregates persist. Raw patient data never touches the disk.

**Real-time pass-through** — patient-level detail screens (unsigned letter queue, revenue leakage flags) call the Gentu API directly at render time. The dashboard displays current-state data from Gentu without storing it. This eliminates patient-identifiable records from PostgreSQL entirely.

---

## What Lives in PostgreSQL

Three tables. Nothing else.

### tenants
Practice configuration. One row per onboarded practice.

```
id                  — unique tenant identifier
name                — practice display name
practice_name       — legal entity name
abn                 — Australian Business Number
contact_email       — primary contact
config              — JSON blob: active modules, MBS items tracked,
                      alert thresholds, report preferences, adapter settings
active              — boolean
created_at          — timestamp
updated_at          — timestamp
```

This table contains no patient data. It drives system behaviour — which analytics modules run, what thresholds trigger alerts, when email digests are sent.

### billing_events
Financial records imported from Gentu CSV exports. Permanent storage.

```
invoice_id          — unique identifier (e.g. INV-20260406-001)
tenant_id           — links to tenants table
patient_id          — Gentu internal ID only (e.g. pat_10234, NOT a name)
practitioner_id     — Gentu internal ID
provider_number     — Medicare provider number (practitioner, not patient)
location            — practice location name
appointment_id      — links to Gentu appointment (for leakage cross-referencing)
invoice_date        — date invoice created
service_date        — date service provided
mbs_item            — Medicare Benefits Schedule item number (e.g. 110, 55126)
item_description    — MBS item description
schedule_fee        — MBS schedule fee
charged_amount      — amount practice charged
billing_type        — private / bulk_bill / dva / eclipse_no_gap / eclipse_known_gap
claim_status        — draft / submitted / accepted / rejected / pending
payment_status      — unpaid / partial / paid
medicare_benefit    — amount paid by Medicare
gap_amount          — difference between charged and Medicare benefit
patient_paid        — amount received from patient
insurer_paid        — amount received from private health insurer
dva_amount          — amount received from DVA
total_received      — sum of all payments
outstanding         — charged minus total received
claim_submitted_date
claim_processed_date
payment_received_date
referring_doctor    — referring doctor name (kept for referral source analysis)
referring_provider_no
notes               — free text
```

**Privacy note:** The adapter strips patient names, dates of birth, Medicare numbers, addresses, and contact details during CSV import. The `patient_id` field is Gentu's internal identifier — meaningless without access to Gentu's patient database. A billing record reading "pat_10234 was billed $350 for MBS 110 on 6 April 2026" is not reasonably identifiable under the Privacy Act without cross-referencing Gentu.

**Why this is stored permanently:** There is no Gentu API for billing data. CSV exports are the only source. If the data isn't stored at import time, it's lost. Financial trend analysis (monthly revenue, collection rate trends, billing mix shifts) requires historical records spanning months.

### analytics_results
Pre-computed metric snapshots. One row per module per period per tenant. Permanent, accumulating.

```
id                  — unique identifier
tenant_id           — links to tenants table
module              — financial / operations / documents
period_type         — daily / weekly / monthly
period_start        — start of the analysis period
period_end          — end of the analysis period
results             — JSON blob containing all computed metrics
generated_at        — when this snapshot was computed
```

**The results JSON contains only aggregate numbers.** No patient IDs, no names, no clinical information. Example for an operations weekly snapshot:

```json
{
  "total_scheduled": 52,
  "total_completed": 48,
  "total_dna": 4,
  "total_cancelled": 3,
  "completion_rate": 92.3,
  "dna_rate": 7.7,
  "new_patient_count": 14,
  "followup_count": 26,
  "procedure_count": 8,
  "new_patient_ratio": 29.2,
  "by_type": {
    "Initial Consultation": 14,
    "Follow-up Consultation": 26,
    "Echocardiogram - TTE": 6,
    "Exercise Stress Echo": 2,
    "Telehealth Consultation": 4
  },
  "by_status": {
    "completed": 48,
    "did_not_arrive": 4,
    "cancelled": 3,
    "booked": 0
  },
  "by_day": {
    "Monday": {"completed": 12, "dna": 1, "cancelled": 0},
    "Wednesday": {"completed": 10, "dna": 2, "cancelled": 1},
    "Thursday": {"completed": 14, "dna": 0, "cancelled": 1},
    "Friday": {"completed": 12, "dna": 1, "cancelled": 1}
  },
  "referral_sources": [
    {"practice": "Surry Hills Medical Centre", "count": 6},
    {"practice": "Drummoyne Family Practice", "count": 4},
    {"practice": "Woollahra Medical", "count": 3}
  ]
}
```

This is what powers historical trend charts. The dashboard queries `SELECT results FROM analytics_results WHERE module = 'operations' AND period_type = 'weekly' ORDER BY period_start DESC LIMIT 10` and plots the values from each week's snapshot. No raw patient data is needed.

---

## What Does NOT Live in PostgreSQL

There are no tables for:

- **Appointments** — processed in memory, aggregated, discarded
- **Patients** — never stored; patient IDs appear only in billing_events
- **Documents / Letters** — processed in memory for aggregate counts; individual letter queue pulled from Gentu API in real-time
- **Referrals** — processed in memory for source analysis; individual referral status pulled from Gentu API in real-time
- **Practitioners** — configuration stored in tenants.config; schedule data pulled from Gentu API

---

## Data Flow: Step by Step

### Pipeline Run (every 15 minutes via Celery)

```
1. Celery beat triggers pipeline task for each active tenant

2. Pipeline calls adapter.get_appointments(tenant_id, start_date, end_date)
   → Gentu Healthcare API returns JSON with appointments + nested patient data
   → Adapter translates into Pydantic Appointment models
   → Data exists in Python process memory only

3. Pipeline calls adapter.get_documents(tenant_id, start_date, end_date)
   → Gentu Letters API returns JSON with letter records
   → Adapter translates into Pydantic Document models
   → Data exists in Python process memory only

4. Pipeline calls adapter.get_referrals(tenant_id, start_date, end_date)
   → Gentu Bookings API returns JSON with referral records
   → Adapter translates into Pydantic Referral models
   → Data exists in Python process memory only

5. Pipeline loads billing data from PostgreSQL billing_events table
   → Already stored from CSV import
   → Loaded into Pydantic BillingEvent models

6. Analytics modules run against in-memory data:
   
   Financial module:
   → Input: billing_events (from DB) + appointments (from memory)
   → Computes: total billed, total received, outstanding, collection rate,
     revenue by billing type, revenue by MBS item, leakage flag counts
   → Output: FinancialSummary (aggregate numbers only)
   
   Operations module:
   → Input: appointments (from memory) + referrals (from memory)
   → Computes: completion rate, DNA rate, new patient ratio,
     appointments by type, by day, referral source counts
   → Output: AppointmentSummary (aggregate numbers only)
   
   Documents module:
   → Input: documents (from memory)
   → Computes: unsigned count, signed-but-unsent count,
     average days to sign, age bracket distribution,
     weekly created vs signed counts
   → Output: DocumentSummary (aggregate numbers only)

7. Analytics results saved to PostgreSQL analytics_results table
   → One row per module with JSON results blob
   → Timestamped for historical trend queries

8. In-memory appointment, document, and referral data is garbage collected
   → Raw patient data no longer exists anywhere in INTELECOR's infrastructure
   → Pipeline function returns, memory is freed

9. Pipeline logs completion via structlog
```

### Dashboard API Request (user loads a screen)

```
Overview / Financial / Operations screens:
  → FastAPI reads from analytics_results table
  → Returns pre-computed aggregates
  → Sub-10ms response time
  → No Gentu API call needed
  → No patient data involved

Documents screen (unsigned letter queue):
  → FastAPI reads aggregate metrics from analytics_results
    (unsigned count, age brackets, backlog trend)
  → For the letter queue table: FastAPI calls Gentu Letters API
    in real-time to fetch current unsigned letters
  → Returns combined response to frontend
  → Patient-level letter data comes from Gentu, passes through
    to the frontend, is never written to PostgreSQL

Financial screen (leakage flags table):
  → FastAPI reads aggregate financial metrics from analytics_results
    (totals, billing type breakdown, MBS breakdown)
  → For rejected claims: queries billing_events table directly
    (these records are already stored from CSV import)
  → For unbilled appointments: calls Gentu Healthcare API in
    real-time to get current completed appointments, cross-references
    against billing_events to find appointments with no matching invoice
  → Returns combined response to frontend
```

### CSV Billing Import (manual upload by practice admin)

```
1. Practice admin exports billing CSV from Gentu
2. Uploads to INTELECOR via dashboard or API endpoint
3. CSV adapter parses the file
4. Adapter strips patient names, DOB, Medicare numbers, addresses
   → Keeps: patient_id (Gentu internal), MBS items, amounts, dates, statuses
5. De-identified records upserted into billing_events table
   → New records inserted
   → Existing records updated (payment status may have changed)
6. Financial analytics module re-runs against updated billing data
7. New financial analytics_results snapshot saved
```

---

## How Historical Reporting Works

### Revenue trend (last 6 months)
Each month's pipeline runs produce financial analytics_results rows. The monthly revenue trend chart queries the last 6 monthly snapshots and plots `total_received` and `by_billing_type` from each. The raw billing records in `billing_events` also support direct SQL queries for custom date ranges — since billing data is permanently stored.

### Weekly operations trend (last 10 weeks)
Each week's pipeline runs produce operations analytics_results rows. The trend chart queries the last 10 weekly snapshots and plots `total_completed`, `total_dna`, and `new_patient_count` from each.

### This week vs last week comparison
The overview screen reads the two most recent weekly operations snapshots and displays them side by side.

### Document backlog trend (last 4 weeks)
Each week's pipeline runs produce documents analytics_results rows containing `weekly_created` and `weekly_signed` arrays. The backlog trend chart reads these from the last 4 weekly snapshots.

### What you CANNOT do with this approach
You cannot retroactively compute new patient-level metrics against historical data. If six months from now Andrew asks "what percentage of my echo patients last year were over 65," the system cannot answer that — the individual appointment records with patient ages were never stored. You would need to query Gentu's API for historical data (if their API supports it) and compute on the fly.

This is a deliberate tradeoff. The privacy benefit of not storing patient demographics outweighs the analytical limitation. If patient-level historical analysis becomes a requirement (Phase 3 roadmap), that data would be processed by a local LLM on-premise, not stored in the cloud PostgreSQL database.

---

## Real-Time Pass-Through: Documents & Leakage

### Unsigned letter queue (Documents screen)

When the user navigates to the Documents screen, the frontend makes two API calls:

1. `GET /api/documents/summary` — returns pre-computed aggregates from `analytics_results` (unsigned count, age brackets, backlog trend, average signing time). This is fast because it reads from PostgreSQL.

2. `GET /api/documents/queue` — this endpoint calls the Gentu Letters API in real-time, fetches all letters with status "unsigned", translates them through the adapter, and returns the queue to the frontend. The data passes through the FastAPI process and is returned to the browser. Nothing is written to PostgreSQL.

The user sees a 1-2 second loading state on the queue table while the Gentu API responds. The aggregate metrics above load instantly from the database. This is an acceptable UX tradeoff — the metrics the user scans first (unsigned count, age brackets) are instant, and the detailed queue loads a moment later.

### Revenue leakage flags (Financial screen)

1. `GET /api/financial/summary` — returns pre-computed aggregates from `analytics_results`. Instant.

2. `GET /api/financial/leakage` — this endpoint does two things:
   - Queries `billing_events` for rejected claims and overdue gap payments (these are already in PostgreSQL from CSV import)
   - Calls the Gentu Healthcare API for current completed appointments, then cross-references against `billing_events` to find unbilled appointments
   - Returns the combined leakage flags list

Rejected claims and overdue gaps load instantly (from PostgreSQL). Unbilled appointment detection has a 1-2 second delay (from the Gentu API call). The frontend can render the billing-sourced flags immediately and append the API-sourced flags when they arrive.

---

## Privacy Compliance by Architecture

### APP 3 — Collection Minimisation
The system collects only what is reasonably necessary:
- Billing records: collected because they are the core analytical dataset and have no API alternative. De-identified during import (names, DOB, Medicare numbers stripped).
- Operational data (appointments, documents, referrals): collected transiently for aggregate computation. Not stored. Not written to disk.

### APP 11 — Security and Destruction
Personal information is destroyed once no longer needed:
- Raw API data exists in process memory for the duration of the analytics run (seconds). Garbage collected when the pipeline function returns.
- Billing records retain minimal identifiers (Gentu internal patient IDs). No names, no Medicare numbers, no addresses.
- The `analytics_results` table contains only aggregate metrics — not personal information under the Privacy Act.

### APP 6 — Use and Disclosure
Data is used solely for the purpose it was collected:
- Billing data: used to compute financial analytics for the practice that uploaded it.
- API data: used transiently to compute operational analytics for the practice that authorised the API connection.
- No data is disclosed to third parties, used for marketing, or shared across practices.
- Future cross-practice benchmarking (like Cubiko's Touchstone) would use only aggregate metrics with explicit opt-in — no patient-level data would be involved.

### Breach Impact Assessment
If INTELECOR's PostgreSQL database were compromised, an attacker would obtain:
- Practice configuration (tenant names, contact emails, alert thresholds)
- De-identified billing records (internal patient IDs, MBS items, dollar amounts, dates)
- Aggregate analytics snapshots (counts, percentages, trends)

They would NOT obtain: patient names, dates of birth, Medicare numbers, addresses, phone numbers, clinical notes, diagnoses, medications, or referral reasons. The re-identification risk from billing records with internal IDs is low — an attacker would need independent access to Gentu's patient database to link `pat_10234` to a real person.

This is a materially different breach profile than a system storing full patient demographics (like Cubiko's architecture). The regulatory response, notification obligations, and reputational impact would be proportionally lower.

---

## Tech Stack

```
Backend:
  Python 3.12+        — pipeline processing, analytics modules
  FastAPI              — REST API serving dashboard and real-time pass-through
  SQLAlchemy + Alembic — PostgreSQL ORM and migrations
  Pydantic             — data validation, settings, API schemas
  Celery               — scheduled pipeline runs, email digest tasks
  pandas               — data transformation in analytics modules
  httpx                — async HTTP client for Gentu API calls
  fastapi-users        — JWT authentication and user management
  structlog            — structured JSON logging

Database:
  PostgreSQL 15+       — sole data store (3 tables)
  pg_cron (optional)   — materialised view refresh scheduling

Frontend:
  React 18+            — dashboard UI
  Vite                 — build tool
  Tailwind CSS         — styling
  shadcn/ui            — component primitives
  Recharts             — charts and visualisations

LLM:
  anthropic SDK        — cloud summaries (de-identified aggregates only)
  ollama SDK           — local models (future Phase 3)

Email:
  Resend + Jinja2      — morning digest reports

Infrastructure:
  Docker + compose     — containerised local development
  Managed PostgreSQL   — Railway, Render, or AWS RDS (Sydney region)
```

### Why No Redis

At the scale of a single practice (hundreds of records per day), PostgreSQL handles every query in single-digit milliseconds. Redis would add infrastructure complexity (another service to run, monitor, and maintain) without measurable performance benefit. The `analytics_results` table with a simple index on `(tenant_id, module, period_start)` serves dashboard queries faster than the frontend can render the response.

Add Redis only when: multiple concurrent dashboard users create measurable PostgreSQL load, you need Celery's Redis broker (can use PostgreSQL as Celery broker instead for MVP), or you add real-time WebSocket push updates to the dashboard.

### Why No Data Warehouse

A data warehouse (Snowflake, BigQuery, Redshift) is designed for analytical queries across millions of rows from multiple sources. Your system processes hundreds of rows from one source and pre-computes the analytics before storage. The warehouse would sit between PostgreSQL and the dashboard, adding cost and complexity to serve pre-computed JSON blobs that PostgreSQL already returns in under 5ms.

A warehouse becomes relevant at 50+ practices with cross-practice benchmarking queries, or if you add multiple data sources beyond Gentu that need to be joined at query time.

---

## Multi-Tenancy

Every row in every table has a `tenant_id` column. FastAPI middleware extracts the tenant from the authenticated user's JWT and injects it into every database query. No practice can see another practice's data.

```python
# FastAPI dependency — runs on every request
async def get_current_tenant(token: str = Depends(oauth2_scheme)) -> str:
    user = decode_jwt(token)
    return user.organisation_id  # maps to tenants.id
```

Every SQLAlchemy query is scoped:

```python
results = await session.execute(
    select(AnalyticsResultTable)
    .where(AnalyticsResultTable.tenant_id == tenant_id)
    .where(AnalyticsResultTable.module == "financial")
    .order_by(AnalyticsResultTable.generated_at.desc())
    .limit(1)
)
```

For the MVP with one practice, the tenant_id is hardcoded. When multi-tenant auth is added, the middleware reads it from the JWT. The database queries don't change — they're already scoped.

At scale (50+ practices), evaluate PostgreSQL Row-Level Security for an additional enforcement layer, or schema-per-tenant if compliance audits require physical data isolation.

---

## Pipeline Scheduling

```
Every 15 minutes:
  → Pull appointments, documents, referrals from Gentu API
  → Run analytics modules against in-memory data
  → Save computed results to analytics_results table
  → Discard raw data

Daily at 06:30 AEST:
  → Generate LLM summary from latest analytics_results
  → Input: aggregate metrics only (no patient data)
  → Output: natural language morning briefing text

Daily at 07:00 AEST:
  → Send email digest combining analytics results + LLM summary
  → Recipients defined in tenant config
```

The 15-minute interval matches the polling pattern observed in existing Gentu marketplace partners (i-scribe polls every 15 minutes). This balances data freshness against API rate limits.

---

## Adapter Interface

All data sources implement the same abstract interface. The pipeline doesn't know or care whether data comes from mock files, Gentu's API, or a CSV export.

```python
class BaseAdapter(ABC):
    async def get_appointments(tenant_id, start_date, end_date) -> list[Appointment]
    async def get_billing_events(tenant_id, start_date, end_date) -> list[BillingEvent]
    async def get_documents(tenant_id, start_date, end_date) -> list[Document]
    async def get_referrals(tenant_id, start_date, end_date) -> list[Referral]
    async def get_practitioners(tenant_id) -> list[Practitioner]
```

Three implementations:
- **MockAdapter** — reads from JSON/CSV mock data files (development)
- **GentuAdapter** — calls Gentu REST APIs (production, when partner access granted)
- **CsvBillingAdapter** — parses uploaded billing CSV files (production, for financial data)

The active adapter is set in the tenant's configuration. Swapping from mock to Gentu is a config change, not a code change.

---

## What Changes When Gentu API Access Arrives

1. Fill in the `GentuAdapter` stub with real API calls matching Gentu's endpoint schemas
2. Update tenant config to set `adapter.type: gentu` with API credentials
3. Validate that Pydantic models correctly parse real API responses (field names, data types, enums)
4. Adjust the pipeline polling interval if Gentu's rate limits differ from the assumed 15-minute pattern
5. Implement the real-time pass-through endpoints for documents queue and leakage detection

Everything else — the analytics modules, the database schema, the API routes, the frontend — remains unchanged. The adapter layer isolates all Gentu-specific concerns.

---

## Project Database Schema (SQL)

```sql
CREATE TABLE tenants (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    practice_name TEXT NOT NULL,
    abn         TEXT,
    contact_email TEXT,
    config      JSONB DEFAULT '{}',
    active      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE billing_events (
    invoice_id          TEXT PRIMARY KEY,
    tenant_id           TEXT NOT NULL REFERENCES tenants(id),
    patient_id          TEXT,
    practitioner_id     TEXT,
    provider_number     TEXT,
    location            TEXT,
    appointment_id      TEXT,
    invoice_date        DATE NOT NULL,
    service_date        DATE NOT NULL,
    mbs_item            TEXT NOT NULL,
    item_description    TEXT,
    schedule_fee        NUMERIC(10,2) DEFAULT 0,
    charged_amount      NUMERIC(10,2) DEFAULT 0,
    billing_type        TEXT NOT NULL,
    claim_status        TEXT NOT NULL,
    payment_status      TEXT NOT NULL,
    medicare_benefit    NUMERIC(10,2) DEFAULT 0,
    gap_amount          NUMERIC(10,2) DEFAULT 0,
    patient_paid        NUMERIC(10,2) DEFAULT 0,
    insurer_paid        NUMERIC(10,2) DEFAULT 0,
    dva_amount          NUMERIC(10,2) DEFAULT 0,
    total_received      NUMERIC(10,2) DEFAULT 0,
    outstanding         NUMERIC(10,2) DEFAULT 0,
    claim_submitted_date DATE,
    claim_processed_date DATE,
    payment_received_date DATE,
    referring_doctor    TEXT,
    referring_provider_no TEXT,
    notes               TEXT
);

CREATE INDEX ix_billing_tenant_date ON billing_events(tenant_id, service_date);
CREATE INDEX ix_billing_status ON billing_events(tenant_id, payment_status);
CREATE INDEX ix_billing_mbs ON billing_events(tenant_id, mbs_item);
CREATE INDEX ix_billing_claim ON billing_events(tenant_id, claim_status);

CREATE TABLE analytics_results (
    id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id       TEXT NOT NULL REFERENCES tenants(id),
    module          TEXT NOT NULL,
    period_type     TEXT NOT NULL,
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    results         JSONB NOT NULL,
    generated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_analytics_lookup ON analytics_results(tenant_id, module, period_type, period_start DESC);
```

Three tables. Six indexes. No patient demographics. No clinical data. No appointment records. This is the entire persistent data layer for the platform.
