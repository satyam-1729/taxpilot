# Architecture

## Data Flow

```
Client (Next.js)
    │  HTTPS + JWT
    ▼
FastAPI Gateway ──► Auth (Aadhaar OTP / PAN)
    │
    ├──► Parser Service   (Form 16, AIS, bank stmt → structured JSON)
    │         │
    │         └──► Claude Haiku (extraction) + OCR
    │
    ├──► Reconciler       (AIS vs Form 16 vs user input → mismatches)
    │
    ├──► Interview Agent  (Claude Opus — asks only missing fields)
    │
    ├──► Tax Engine       (deterministic: slabs, regimes, deductions)
    │
    └──► E-Filing Service (IT Dept ERI API → submit ITR JSON → e-verify)

Postgres  ──  filings, users, documents (metadata)
S3        ──  encrypted source docs
Redis     ──  session, rate limit, AIS cache
```

## Why split frontend / backend folders
- Independent deploys (Vercel for FE, Fly/Render for BE)
- Different dep managers (npm vs pip)
- Security boundary — FE never touches tax logic or keys
