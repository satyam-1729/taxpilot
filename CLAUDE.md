# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TaxPilot is an AI-powered ITR (Income Tax Return) filing assistant for Indian taxpayers. It has a FastAPI backend (tax engine, AI orchestration, e-filing) and an Angular 18 frontend.

## Commands

### Frontend (Angular 18)
```bash
cd frontend
npm install
npm start          # ng serve → http://localhost:4200
npm run build      # production bundle → dist/frontend
npm test           # Karma + Jasmine tests
```

### Backend (FastAPI)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
pytest                    # run all tests
pytest tests/test_foo.py  # run a single test file
pytest -k "test_name"     # run a single test by name
```

## Architecture

The frontend and backend are independently deployable (Vercel for FE, Fly/Render for BE).

**Data flow:** Client → FastAPI Gateway (JWT auth via Aadhaar OTP/PAN) → Parser Service (Form 16/AIS/bank stmt → JSON via Claude Haiku + OCR) → Reconciler (cross-source mismatch detection) → Interview Agent (Claude Opus for missing fields) → Tax Engine (deterministic slab/regime/deduction calc) → E-Filing Service (IT Dept ERI API).

**Storage:** Postgres (filings, users, doc metadata), S3 (encrypted source docs), Redis (session, rate limit, AIS cache).

### Critical Invariants
- **Tax engine is pure & deterministic** — no LLM in the computation path; LLMs only extract data and interview users.
- **Every deduction cites a section** (80C, 80D, 24(b)) — stored with the filing.
- **AY-versioned rules** — tax slabs/limits are keyed by assessment year, never hardcoded globally.
- **PII encrypted at rest** — PAN, Aadhaar, bank numbers use field-level encryption.

### Frontend Pattern
The frontend uses Angular 18 standalone components with lazy-loaded feature routes. Each feature is a folder under `src/app/features/` with its own `*.routes.ts` and `*.page.ts`. Screens are Stitch HTML exports served via a shared `<app-stitch-frame file="...">` iframe component that loads from `public/stitch/`. Adding a new screen means: drop HTML into `public/stitch/`, create a feature folder, wire up the route in `app.routes.ts`.

### Design System (Sovereign Ledger)
- Fonts: **Manrope** (display/headline), **Inter** (body/label)
- Primary: `#000666`, Secondary: `#1b6d24`, Surface: `#f9f9fb`
- Follow the "No-Line Rule" — use layered tonal surfaces rather than borders for sectioning.
