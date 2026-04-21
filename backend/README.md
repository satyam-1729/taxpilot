# TaxPilot Backend

FastAPI service handling document parsing, tax computation, AI orchestration, and e-filing.

## Structure

```
app/
├── api/routes/         # HTTP endpoints (auth, upload, compute, file)
├── core/               # Config, security, logging
├── models/             # SQLAlchemy ORM (User, Filing, Document)
├── schemas/            # Pydantic request/response + ITR JSON schema
├── services/
│   ├── parser/         # Form 16, bank stmt, AIS OCR + LLM extraction
│   ├── tax_engine/     # Slab calc, old vs new regime, deductions
│   ├── ai/             # Claude client, prompt templates, interview agent
│   ├── efiling/        # IT Dept API client, Aadhaar e-verify
│   └── ais/            # AIS/TIS/26AS fetch + reconcile
├── db/                 # Session, migrations (Alembic)
└── utils/              # PAN/Aadhaar validators, currency, date helpers

tests/                  # pytest — heavy focus on tax_engine correctness
scripts/                # Seed tax slabs, deduction limits per AY
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Critical Invariants

- **Tax engine is pure & deterministic** — no LLM in computation path; LLMs only extract & interview.
- **Every deduction cites a section** (80C, 80D, 24(b)) — stored with the filing.
- **AY-versioned rules** — slabs/limits keyed by assessment year, never hardcoded globally.
- **PII encrypted at rest** — PAN, Aadhaar, bank numbers use field-level encryption.
