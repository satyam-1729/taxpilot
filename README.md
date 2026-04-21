# TaxPilot

AI-powered ITR filing assistant for Indian taxpayers.

## Structure

```
taxpilot/
├── frontend/   # Next.js + React (UI/UX)
├── backend/    # FastAPI (tax engine, AI, e-filing)
└── docs/       # Architecture, flows, tax law references
```

## Quick Start

```bash
# Backend
cd backend && uvicorn app.main:app --reload

# Frontend
cd frontend && npm run dev
```

See `frontend/README.md` and `backend/README.md` for details.
