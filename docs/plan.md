# TaxPilot — Implementation Plan & Task List

> **As of:** 2026-04-29
> **Original timeline start:** Jan 2026 (we are now in Month 4)
> **Current state:** Auth (Firebase + Postgres + Redis), KYC flow, and Form 16 parser (Anthropic Claude Haiku) are live end-to-end. Tax engine still pending. Original plan opened with engine-first; in practice we built auth + ingest first because they unblock everything downstream.
> **Tax engine decision:** Pure Python — fast to build, easy to update tax rules mid-season, more than fast enough for initial scale (50K+ calculations/sec). Migrate to Cython if needed post-launch.

---

## Timeline Overview

```
Phase 1: Foundation             Phase 2: MVP               Phase 3: Launch
Apr ──────── May ──────────────── Jun ──────── Jul ──────── Aug
│◄──── Python Engine + Backend ──►│◄── App + Beta ──────────►│◄─ Launch ─►│

★ M1: Engine passes 5,000 tests      ★ M3: Beta 200 users   ★ M5: Public
★ M2: Backend API live               ★ M4: E2E filing works

Phase 4: Growth                         Phase 5: Scale
Sep ──── Oct ──── Nov ──── Dec ──── Y2 Q1 ──── Y2 Q2
│◄───── ITR-3 + Brokers + CA Review ──►│◄─ Subscriptions + B2B ──►│

★ M6: 10K users   ★ M7: 50K users      ★ M9: B2B API + Subscriptions
★ M8: ITR-3 + broker integrations      ★ M10: ₹10 Cr ARR (Seed ready)
```

---

## Current State

| Component | Status |
|-----------|--------|
| Angular 18 routing (8 lazy routes) | ✅ Done |
| Stitch HTML screens (12 screens) | ✅ Done (kept as design refs; auth + documents now native components) |
| StitchFrame iframe component | ✅ Done (still used by dashboard/savings/etc.) |
| Tailwind v3 + Outfit/Manrope/Inter typography | ✅ Done |
| Brand assets — favicon.svg, logo-mark/full/wordmark.svg | ✅ Done |
| Postgres 16 + Redis 7 (Docker, `tp-pg`, `tp-redis`) | ✅ Running |
| FastAPI backend skeleton + CORS + lifespan | ✅ Done |
| Alembic migrations — `0001_users`, `0002_documents` | ✅ Applied |
| User model (firebase_uid, encrypted PAN, verified flag) | ✅ Done |
| Document model (sha256 dedup, parsed_json, denormalized cols) | ✅ Done |
| Firebase Admin SDK + ID token verification | ✅ Done |
| Redis client + rate-limit helper (`incr_with_ttl`) | ✅ Done |
| Field encryption (Fernet/AES) for PAN | ✅ Done |
| Auth API: `POST /auth/session`, `GET /me`, `POST /auth/kyc`, `POST /auth/logout` | ✅ Done |
| Documents API: `POST /upload`, `GET /`, `GET /{id}`, `POST /{id}/decrypt` | ✅ Done |
| Anthropic Claude Haiku 4.5 parser with PDF input + tool-use | ✅ Done |
| Encrypted-PDF flow (`pypdf`) — detect → password modal → decrypt → parse | ✅ Done |
| AuthService (signals + localStorage) + 3 guards (auth/verified/guest) | ✅ Done |
| Native signin page (Firebase Phone OTP + Google) | ✅ Done (Phone OTP awaits Blaze upgrade) |
| Native identity (KYC) page — PAN + Aadhaar form | ✅ Done (placeholder design; Stitch redesign deferred) |
| Shell header — auth-aware, hides on `/signin` + `/identity`, signout button | ✅ Done |
| Documents page — drag-drop upload, recent activity, status pills, 2s polling | ✅ Done |
| Secrets folder layout (`/secrets` at repo root, gitignored) | ✅ Done |
| Setup guide ([docs/auth-setup.md](auth-setup.md)) | ✅ Done |
| Python tax engine | ⏳ Partial — slab calculator + AY 2026-27 rules in place, rest TODO |
| Dashboard / Savings / Investments / Chat / Profile wiring to backend | ❌ Not started (still iframe-based) |
| Razorpay payments | ❌ Not started |
| ITR XML generation | ❌ Not started |
| AI conversation engine (Chat) | ❌ Not started |

---

## Progress 2026-04-21 → 2026-04-29

The original plan opened with the tax engine. In practice we needed identity + document ingest before any of that could be tested, so the order was reshuffled to:

1. **Foundation** — Postgres, Redis, FastAPI skeleton, secrets layout, gitignore hygiene.
2. **Auth (Firebase)** — picked Firebase to avoid running our own SMS gateway / OAuth handshake. Backend exchanges Firebase ID tokens for our own session JWT (HS256, 30-day TTL) and upserts into `users`.
3. **KYC flow** — `verified` flag in Postgres, set once via `POST /auth/kyc`, checked by `verifiedGuard` on every protected route. Verify-once across devices and sessions because the flag lives on the user row, not the browser.
4. **Form 16 parser** — Anthropic Haiku 4.5 with native PDF input + forced tool-use for structured output. SHA256 dedup means re-uploading the same PDF returns the cached parse without a second API call. Encrypted PDFs are detected up front (`pypdf`) and the user is prompted for a password before any tokens are spent.
5. **Frontend polish** — Tailwind installed, Outfit added for the brand wordmark, signin page rebuilt from the latest Stitch design with the TP monogram inside the card. Favicon + brand SVGs published.

### Known deferred / blockers

- **Firebase Phone OTP** — requires Blaze plan upgrade (test phone numbers also gated behind it now). Google sign-in works without Blaze and is the default path. Tracked in todos.
- **Anthropic API key rotation** — keys pasted in chat during setup must be rotated in `console.anthropic.com` before going public.
- **Identity (KYC) page design** — current native version is a functional placeholder; will redesign from a Stitch screen once available.
- **DOB capture during KYC** — would let us auto-derive the standard Form 16 password (`PAN[:5] + DOB(DDMMYYYY)`) without prompting users; out of scope for now.
- **PAN sanity check on Form 16 upload** — explicitly skipped per current decision; revisit before launch.

---

## Phase 1: Foundation (Apr–May 2026)

### Milestone 1 — Tax Engine passes 5,000+ test cases ★
**Target: End of April 2026 | KPI: All tests green, 50K computations/sec**

#### 1.1 — Python Tax Engine Core (`backend/app/services/tax_engine/`)

- [x] `rules/ay2026_27.py` — all slab rates, section limits, cess rates as AY-versioned constants (zero hardcoding globally)
- [x] `slab_calculator.py` — new regime (7 slabs) + old regime (4 slabs)
- [ ] Surcharge calculation (5 tiers: 10/15/25/37/25%) + 4% health & education cess
- [ ] Section 87A rebate logic — new regime (≤₹7L → full rebate) + old regime (≤₹5L)
- [ ] `deduction_engine.py` — 80C (₹1.5L cap), 80CCD(1B) (₹50K NPS), 80D (age-based slabs), 80E, 80G, 80TTA/80TTB
- [ ] `hra_calculator.py` — Section 10(13A): min of (actual HRA / 50%|40% of basic / rent − 10% basic)
- [ ] `capital_gains.py` — STCG 111A (20%), LTCG 112A (12.5% above ₹1.25L), other CG at slab rates
- [ ] LTCG grandfathering rule (Jan 31, 2018 fair market value)
- [ ] `regime_comparator.py` — run both regimes on same profile, return optimal + savings delta
- [ ] `advance_tax.py` — quarterly installment estimator (15/45/75/100% schedule)
- [ ] `engine.py` — single pure entry point: `compute(tax_profile: TaxProfile) -> TaxResult`
- [ ] Write 5,000+ test cases in `backend/tests/tax_engine/` (JSON fixtures for known ITR scenarios)
- [ ] Benchmark: 50,000+ profiles/sec (pure Python arithmetic, no I/O)
- [ ] Document all rules with IT Act section references in `docs/tax_rules.md`

#### 1.2 — Database & Infrastructure

- [x] `requirements.txt` — FastAPI, SQLAlchemy 2.x async, Alembic, Anthropic SDK, redis, python-jose, pydantic-settings, firebase-admin, pypdf, cryptography
- [x] PostgreSQL schema — `users` (auth + KYC), `documents` (Form 16 + future docs)
- [ ] PostgreSQL schema (rest) — `tax_profiles`, `filings`, `payments`, `audit_log`
- [x] `app/db/session.py` — async SQLAlchemy engine + session factory + `Base`
- [x] AES (Fernet) column-level encryption utility for PAN ([app/utils/crypto.py](../backend/app/utils/crypto.py))
- [ ] Same for Aadhaar full-number + bank account numbers (currently storing only Aadhaar last4)
- [ ] `audit_log` table — append-only, every computation logged with SHA-256 hash of input+output
- [x] Alembic init + first two migrations (`0001_users`, `0002_documents`)
- [ ] Docker Compose — currently using `docker run` for Postgres + Redis. FastAPI runs natively. Compose-ify before staging.
- [ ] GitHub Actions CI — `lint → test → build` on every push

#### 1.3 — Backend API Skeleton

- [x] `app/main.py` — FastAPI app, CORS, lifespan (boots Firebase + Redis), `GET /api/health`
- [x] `app/core/config.py` — pydantic-settings (DATABASE_URL, REDIS_URL, ANTHROPIC_API_KEY, FIREBASE_*, FIELD_ENCRYPTION_KEY, APP_SECRET, UPLOADS_DIR, PARSER_MODEL)
- [x] `app/core/security.py` — session JWT (HS256, 30-day) create/verify, `current_user` dependency, Firebase ID token verification via `app/services/firebase.py`
- [x] Auth routes — Firebase-based: `POST /auth/session` (exchange ID token → our session JWT), `GET /auth/me`, `POST /auth/kyc`, `POST /auth/logout`. Replaces the old Aadhaar-OTP-only design.
- [x] User row on first sign-in (auto-upsert from Firebase claims)
- [ ] `tax_profile` CRUD — create, update, retrieve structured income/deduction profile
- [ ] `POST /api/compute-tax` — calls Python engine, logs to audit_log, returns TaxResult
- [ ] Audit logging middleware — every request/computation persisted
- [ ] Sentry integration for error tracking
- [ ] pytest suite — auth, compute, profile, documents endpoints

### Milestone 2 — Backend API live with engine integrated ★
**Target: End of April 2026 | KPI: `POST /api/compute-tax` responds < 200ms**

---

## Phase 2: MVP Product (May–Jun 2026)

### Milestone 3 — Closed beta with 200 users ★
**Target: End of May 2026**

#### 2.1 — AI Conversation Engine (`app/services/ai/`)

- [ ] Design conversation state machine: `GREETING → SALARY → HOUSE_PROPERTY → CAPITAL_GAINS → DEDUCTIONS → OTHER_INCOME → REVIEW → FILING`
- [ ] System prompt — full Indian tax context, persona as "TaxPilot AI", never compute directly
- [ ] `session_manager.py` — conversation history per user stored in Redis (TTL 24h)
- [ ] `income_classifier.py` — Claude classifies user responses into `TaxProfile` fields via tool use
- [ ] `deduction_discovery.py` — probing questions to surface missed deductions (HRA, 80D, NPS)
- [ ] "Did you know" suggestions — contextual tips based on profile (80C headroom, 80D gap)
- [ ] Old vs new regime comparison with plain-language ₹ explanation
- [ ] Hindi + English support (Hinglish accepted in conversation input)
- [ ] Test with 50 real scenarios — LLM correctly populates `TaxProfile`
- [ ] Fallback: escalate to CA if LLM confidence < threshold

#### 2.2 — Document Parser (`app/services/parser/`)

- [x] `form16.py` — Anthropic Claude Haiku 4.5 with native PDF input + forced tool-use for structured output. Schema mirrors `Form16Data` (employer, employee, TDS quarters, salary components, Section 10 / 16 / Chapter VI-A line items with section codes, totals).
- [x] `pdf.py` — `is_encrypted()` + `decrypt_pdf()` via `pypdf`. Detection happens at upload time so we don't burn tokens on locked PDFs.
- [x] Encrypted-PDF UX — backend stores encrypted file as-is, marks row `needs_password`; frontend prompts for password; `POST /documents/{id}/decrypt` validates password, overwrites with decrypted bytes, schedules background parse.
- [x] SHA256 dedup per user — re-uploading the same PDF returns the cached parse, zero Anthropic re-calls.
- [x] Background-task parse with status state machine: `queued → parsing → parsed | failed`. Frontend polls every 2s while pending.
- [ ] Structured mapper — Form 16 `parsed_json` → `TaxProfile` fields (waits on `tax_profiles` table)
- [ ] Test against 50+ Form 16 formats from different employers (we've validated a couple manually so far)
- [ ] `ais_parser.py` — 26AS/AIS JSON from IT portal (manual upload fallback)
- [ ] Cross-validation — Form 16 vs 26AS, flag mismatches automatically
- [ ] Confidence scoring — flag < 80% confidence extractions for user review (currently captured per-token from Anthropic but not yet surfaced in UI)
- [ ] Auto-derive Form 16 password from KYC fields (`PAN[:5] + DOB(DDMMYYYY)`) — needs DOB on user record
- [ ] PAN sanity check — verify Form 16 employee PAN matches user's verified PAN (deferred per current decision)

#### 2.3 — ITR Form Router & XML Generator (`app/services/efiling/`)

- [ ] Form selection logic — ITR-1 vs ITR-2 vs ITR-3 based on income types in `TaxProfile`
- [ ] ITR-1 XML generator — AY 2026-27 IT department schema
- [ ] ITR-2 XML generator — with capital gains schedules
- [ ] Validate generated XML against IT department offline utility
- [ ] Test XML upload on IT portal sandbox

#### 2.4 — Frontend — Wire All Pages to Backend

- [x] `environments/environment.ts` + `environment.prod.ts` — `apiBaseUrl` + Firebase web SDK config
- [x] `core/auth/auth.service.ts` — Angular signals (`user`, `token`, `isLoggedIn`, `isVerified`) + localStorage persistence + Firebase phone/Google methods + backend session exchange
- [x] `core/auth/guards.ts` — `authGuard`, `verifiedGuard`, `guestGuard`. All protected routes wear `verifiedGuard`.
- [x] `core/documents/documents.api.ts` — typed fetch wrappers (uploadDocument, listDocuments, getDocument, submitPassword)
- [ ] Generic API service / interceptor — currently each feature has its own typed `fetch` wrappers. Consider consolidating into an `ApiService` once we have 3+ feature areas.
- [x] Wire Signin page → Firebase Phone OTP + Google → `POST /auth/session` → route to `/identity` or `/dashboard` based on `verified`
- [x] Wire Identity page → `POST /auth/kyc` → set verified → redirect to dashboard
- [x] Wire Documents page → drag-and-drop upload → `POST /documents/upload` → password modal if encrypted → polling for status → recent activity with green tick
- [ ] Switch to httpOnly-cookie session token (currently localStorage; acceptable for dev, harden before prod)
- [ ] Wire Chat page → SSE streaming from `POST /chat/message` with message bubbles
- [ ] Wire Dashboard → `GET /filings/latest` → real income breakdown + regime comparison card
- [ ] Wire Savings page → `GET /savings/recommendations` → AI suggestions with ₹ impact
- [ ] Wire Investments page → investment portfolio CRUD + 80C utilization bar
- [ ] Wire Profile page → user profile + filing history
- [ ] Proper loading skeletons, error states, empty states on all pages

#### 2.5 — Payments

- [ ] Razorpay integration (web)
- [ ] Pricing tiers: ₹499 (ITR-1), ₹799 (ITR-2), ₹999 (ITR-3)
- [ ] CA review add-on: +₹499
- [ ] Payment receipt generation (PDF)
- [ ] Handle failures, retries, refunds
- [ ] GST compliance for own invoicing

### Milestone 4 — Full filing flow works end-to-end ★
**Target: End of June 2026 | KPI: 50 successful end-to-end filings**

---

## Phase 3: Public Launch (Jul–Aug 2026)

### Milestone 5 — Public launch ★
**Target: Start of July 2026 | KPI: 1,000 paid users | Revenue: ₹5-7L**

- [ ] SEO: 50 articles (tax calculators, old vs new regime, HRA, 80C guides)
- [ ] 5 demo videos — "File ITR-1 in 8 minutes," "AI finds missed deductions"
- [ ] Early bird pricing: ₹399 for first 1,000 users
- [ ] Referral system — "File for a friend, get ₹100 off next year"
- [ ] Product Hunt launch

### Milestone 6 — 10,000 paid users ★
**Target: End of July 2026 (ITR filing deadline rush) | Revenue: ₹60-80L**

---

## Phase 4: Growth (Aug–Nov 2026)

### Milestone 7 — 50,000 paid users ★
**Target: End of October 2026 | Revenue: ₹2.5-4 Cr Y1**

#### 4.1 — ITR-3 Support (Traders & Business)
- [ ] Engine extension — business income under Section 44AD/44ADA/44AE
- [ ] F&O turnover calculation — speculative + non-speculative classification
- [ ] Tax audit threshold check (turnover > ₹10Cr / profit < 6%)
- [ ] ITR-3 XML generator
- [ ] 100+ trader/F&O test scenarios

#### 4.2 — Broker Integrations
- [ ] Zerodha — import P&L via Kite Connect API
- [ ] Groww — capital gains statement import
- [ ] Upstox, Angel One, 5paisa
- [ ] Generic CSV/Excel import
- [ ] STCG/LTCG auto-compute across brokers with FIFO matching
- [ ] Crypto — WazirX, CoinDCX (VDA reporting)

### Milestone 8 — ITR-3 + Broker Integrations live ★
**Target: End of September 2026**

#### 4.3 — CA Review Marketplace
- [ ] CA onboarding — KYC, qualification verification
- [ ] CA assignment — match on complexity, language, availability
- [ ] CA review dashboard — view filing, comment, approve/flag
- [ ] CA payout system
- [ ] 50 CAs onboarded

#### 4.4 — Belated & Revised Returns
- [ ] Belated return (after deadline, with penalty calculation)
- [ ] Revised return — edit previously filed return
- [ ] Updated return (ITR-U) — 2-year window with additional tax

#### 4.5 — IT Notice Handling (Basic)
- [ ] Upload IT notice → LLM parses type (Section 143(1), 139(9), demand notice)
- [ ] Generate suggested response
- [ ] Route complex notices to CA review

---

## Phase 5: Scale & Monetize (Dec 2026 – Jun 2027)

### Milestone 9 — Year-round subscription + B2B API ★
**Target: December 2026**

#### 5.1 — Advisory Subscription (₹99/month)
- [ ] Proactive tax-saving alerts, advance tax reminders
- [ ] Investment tracker — 80C utilization, mutual fund folios
- [ ] Tax-loss harvesting alerts
- [ ] Monthly tax summary email
- [ ] Razorpay recurring billing

#### 5.2 — B2B Tax API
- [ ] `/compute-tax`, `/compare-regimes`, `/recommend-deductions` public endpoints
- [ ] API key management + rate limiting
- [ ] OpenAPI docs, SDKs (Python, JS, Java)
- [ ] Usage-based billing, developer dashboard
- [ ] 5 B2B customers onboarded (fintech, payroll)

#### 5.3 — Vernacular & Voice
- [ ] Full Hindi filing flow, Telugu + Tamil support
- [ ] Voice filing — speech-to-text → LLM → structured extraction

#### 5.4 — HRMS Partnerships
- [ ] White-label embeddable widget
- [ ] Razorpay Payroll, Keka HR, Zoho People, GreytHR integrations
- [ ] B2B2C pricing — employer pays, employee files free

### Milestone 10 — ₹10 Cr ARR, Seed ready ★
**Target: February 2027**

---

## Key Metrics by Milestone

| Milestone | Target Date | Key Metric | Revenue |
|-----------|-------------|------------|---------|
| M1: Engine tested | Apr 2026 | 5,000+ tests pass, 50K calc/sec | — |
| M2: Backend live | Apr 2026 | API < 200ms | — |
| M3: Beta launch | May 2026 | 200 beta users | — |
| M4: E2E filing | Jun 2026 | 50 successful filings | — |
| M5: Public launch | Jul 2026 | 1,000 paid users | ₹5-7L |
| M6: Peak season | Jul 2026 | 10,000 paid users | ₹60-80L |
| M7: Post-season | Oct 2026 | 50,000 total users | ₹2.5-4 Cr |
| M8: ITR-3 live | Sep 2026 | Trader filings work | — |
| M9: Subscriptions | Dec 2026 | 5,000 subscribers | +₹60L/yr MRR |
| M10: Seed ready | Feb 2027 | ₹10 Cr ARR | ₹10 Cr |
| M11: Series A | Apr 2028 | 2L+ users, ₹25Cr ARR | ₹25 Cr |

---

## Critical Invariants (Never Violate)

1. **Tax engine is pure Python, zero LLM calls in computation path** — LLMs only extract data and interview
2. **Every deduction cites its IT Act section** (80C, 80D, 24(b)) — stored with the filing
3. **All tax slabs/limits keyed by AY** — never hardcoded globally, always from `rules/ay{year}.py`
4. **PAN + Aadhaar + bank numbers: AES-256 field-level encrypted** before any DB write
5. **`audit_log` is append-only** — every computation logged with SHA-256 hash of input+output
6. **No raw PII in logs** — mask before any log statement

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| IT portal API changes/breaks | High | Manual upload fallback; daily monitoring during filing season |
| LLM hallucinates tax numbers | Critical | LLM never computes — Python engine only; every number traceable via audit log |
| Form 16 parser fails on unknown format | Medium | Human-in-the-loop for < 80% confidence; build template library progressively |
| Peak season overload (July deadline) | High | Auto-scaling, load test pre-season, CDN for static assets |
| Tax rule changes mid-season | Medium | Rules in hot-swappable `rules/ay{year}.py`, no recompile needed |
| Low conversion at paywall | High | A/B test aggressively; show concrete ₹ saved before hitting paywall |
| Regulatory scrutiny of AI tax advice | Medium | Disclaimer: "Tax computation, not advice." CA review add-on for assurance |

---

## Definition of Done

### Engine Changes
- All 5,000+ existing tests pass; new test cases added for the change
- Benchmark shows no performance regression
- Audit log correctly captures input/output with hash

### LLM Prompt Changes
- Tested against 50 conversation scenarios in English and Hindi
- No regression in income classification accuracy

### Filing Flow Changes
- End-to-end: PAN entry → payment → XML generated → mock submission
- Loading + error states verified

### Production Releases
- Staging tested, no P0/P1 bugs open
- DB migration tested on staging, rollback plan documented
- Monitoring alerts configured
