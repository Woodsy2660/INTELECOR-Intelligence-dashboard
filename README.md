# INTELECOR — Practice Intelligence Platform

A modular practice intelligence and analytics platform for Australian medical specialists, built on top of Gentu practice management software by Magentus.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Data Sources                                           │
│  Gentu API (3 endpoints) + CSV Billing Export            │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│  Adapter Layer         adapters/                        │
│  Translates vendor data → internal Pydantic models      │
│  Mock adapter for development, Gentu adapter for prod   │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│  Normalisation + Storage    db/                         │
│  SQLAlchemy ORM → PostgreSQL (tenant-isolated)          │
│  Alembic migrations                                     │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│  Intelligence Layer     analytics/                      │
│  Financial module (revenue, MBS, leakage detection)     │
│  Operations module (appointments, DNA, utilisation)     │
│  Documents module (unsigned letters, ageing, pipeline)  │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│  Presentation Layer                                     │
│  FastAPI REST API → React Dashboard                     │
│  LLM Summary (Anthropic cloud / Ollama local)           │
│  Email Digest (Resend + Jinja2)                         │
└─────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend | Python 3.12+ / FastAPI | API framework + data pipeline |
| ORM | SQLAlchemy + Alembic | Database access + migrations |
| Validation | Pydantic | Data models + settings |
| Database | PostgreSQL 15+ | Primary data store |
| Cache/Broker | Redis | Task queue broker + API cache |
| Scheduling | Celery | Pipeline jobs, email digests |
| Auth | fastapi-users | JWT auth + user management |
| Frontend | React + Vite + Tailwind | Dashboard UI |
| Charts | Recharts | Data visualisations |
| LLM | Anthropic SDK / Ollama | Natural language summaries |
| Email | Resend + Jinja2 | Morning digest reports |
| Logging | structlog | Structured JSON logging |
| DevOps | Docker + docker-compose | Containerised deployment |

## Quick Start

### Prerequisites
- Docker + Docker Compose
- Python 3.12+
- Node.js 20+ (for frontend)

### 1. Clone and configure
```bash
git clone <repo-url>
cd intelecor
cp .env.example .env
# Edit .env with your values
```

### 2. Start infrastructure
```bash
docker-compose up -d postgres redis
```

### 3. Install Python dependencies
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 4. Run database migrations
```bash
alembic upgrade head
```

### 5. Seed mock data
```bash
python -m db.seed
```

### 6. Start the API
```bash
uvicorn api.main:app --reload --port 8000
```

### 7. Start the frontend (separate terminal)
```bash
cd web
npm install
npm run dev
```

### 8. Start Celery worker (separate terminal)
```bash
celery -A services.celery_app worker --loglevel=info --beat
```

Dashboard available at http://localhost:5173
API docs available at http://localhost:8000/docs

## Project Structure

```
intelecor/
├── api/                     — FastAPI application
│   ├── main.py              — App entry point, middleware, CORS
│   ├── dependencies.py      — Auth, tenant context, DB session
│   ├── routes/
│   │   ├── overview.py      — Overview screen endpoints
│   │   ├── financial.py     — Financial screen endpoints
│   │   ├── operations.py    — Operations screen endpoints
│   │   └── documents.py     — Documents screen endpoints
│
├── models/                  — Pydantic models (API + validation)
│   ├── appointment.py
│   ├── billing.py
│   ├── document.py
│   ├── referral.py
│   ├── practitioner.py
│   └── patient.py
│
├── adapters/                — Data source adapters
│   ├── base.py              — Abstract adapter interface
│   ├── mock_adapter.py      — Mock data for development
│   ├── gentu_adapter.py     — Gentu API (when access granted)
│   └── csv_adapter.py       — CSV billing import
│
├── analytics/               — Analytics modules
│   ├── financial.py         — Revenue, MBS, leakage detection
│   ├── operations.py        — Appointments, DNA, utilisation
│   └── documents.py         — Letters, ageing, pipeline
│
├── services/                — Business logic services
│   ├── pipeline.py          — ETL orchestrator
│   ├── celery_app.py        — Celery configuration + tasks
│   ├── llm_summary.py       — LLM narrative generation
│   └── email_digest.py      — Email report builder
│
├── db/                      — Database layer
│   ├── base.py              — SQLAlchemy base + engine
│   ├── tables.py            — SQLAlchemy table models
│   ├── session.py           — Session management
│   ├── seed.py              — Mock data seeder
│   └── migrations/          — Alembic migration files
│
├── config/
│   └── tenants/
│       └── roy_cardiology.yaml
│
├── data/mock/               — Mock data JSON + CSV files
├── tests/                   — pytest test suite
├── web/                     — React frontend (separate package)
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── .env.example
└── README.md
```

## Data Flow

1. **Celery beat** triggers a pipeline run on schedule (every 15 min)
2. **Pipeline service** calls the active adapter (mock or Gentu)
3. **Adapter** pulls raw data → validates through Pydantic models
4. **Pipeline** stores normalised records in PostgreSQL via SQLAlchemy
5. **Analytics modules** run against stored data, output results to `analytics_results` table
6. **Redis** caches the latest results for fast API responses
7. **FastAPI** serves cached results to the React dashboard
8. **LLM summary** generates narrative text daily from analytics output
9. **Email digest** combines results + summary, sends via Resend

## Multi-Tenancy

Every database table has a `tenant_id` column. FastAPI middleware extracts the tenant from the authenticated user's JWT and injects it into every database query. No practice can see another practice's data.

New practice onboarding:
1. Create tenant record with practice config
2. Set up adapter credentials (Gentu API pairing or CSV import path)
3. Run initial data pull
4. User accounts created and linked to tenant

## Privacy Compliance

- Patient-identifiable data never leaves the local processing environment
- Only de-identified aggregates are sent to cloud LLM for summaries
- All data stored in Australian PostgreSQL region
- Adapter layer strips PII before passing to analytics modules
- Compliant with Australian Privacy Act 1988 and APP guidelines