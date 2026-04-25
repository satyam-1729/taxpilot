# Auth setup — Firebase + Postgres + Redis

End-to-end checklist to get sign-in and KYC working locally.

## 1. Firebase project (one-time)

1. Open <https://console.firebase.google.com> and create a project (e.g. `taxpilot-dev`).
2. **Authentication → Sign-in method**: enable **Phone** and **Google**.
3. **Project settings → General → Your apps**: register a Web app. Copy the config object — apiKey, authDomain, projectId, storageBucket, messagingSenderId, appId.
4. **Project settings → Service accounts → Generate new private key**. Save the JSON as `backend/firebase-service-account.json` (gitignored).

For phone auth in dev: **Authentication → Settings → Authorized domains** must include `localhost`. To avoid burning real OTPs while testing, add a test phone number under **Authentication → Sign-in method → Phone → Phone numbers for testing** with a fixed code like `123456`.

## 2. Postgres + Redis

Pick one — local installs or Docker.

### Docker (recommended)

```bash
docker run -d --name tp-pg -e POSTGRES_USER=taxpilot -e POSTGRES_PASSWORD=taxpilot -e POSTGRES_DB=taxpilot -p 5432:5432 postgres:16
docker run -d --name tp-redis -p 6379:6379 redis:7
```

### Native

- Postgres 14+: create DB `taxpilot` with user `taxpilot/taxpilot`, or update `DATABASE_URL`.
- Redis 6+: default `localhost:6379` works.

## 3. Backend env vars

```bash
cd backend
cp .env.example .env
# edit .env — at minimum set FIREBASE_PROJECT_ID and FIELD_ENCRYPTION_KEY
```

## 4. Install + migrate + run

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Verify: `curl http://localhost:8000/api/health` → `{"status":"ok","env":"dev"}`.

## 5. Frontend env vars

Edit [src/environments/environment.ts](../frontend/src/environments/environment.ts) and paste the Firebase web config from step 1.3.

```ts
firebase: {
  apiKey: '...',
  authDomain: 'taxpilot-dev.firebaseapp.com',
  projectId: 'taxpilot-dev',
  storageBucket: 'taxpilot-dev.appspot.com',
  messagingSenderId: '...',
  appId: '...'
}
```

## 6. Run frontend

```bash
cd frontend
npm install
npm start
```

Open <http://localhost:4200>. You'll be redirected to `/signin`. Sign in with phone OTP or Google → if first time, you'll land on `/identity` for PAN+Aadhaar → after that, full access to dashboard/etc.

## Auth flow at a glance

```
Browser ──► Firebase (phone or Google) ──► ID token
       ──► POST /api/auth/session { id_token } ──► FastAPI
                                                ├─► firebase_admin.auth.verify_id_token
                                                ├─► Postgres: upsert users row keyed by firebase_uid
                                                └─► Returns { token, user }   (token = our HS256 JWT)
       ──► localStorage 'tp_auth' = { token, user }
       ──► All subsequent /api/* calls send Authorization: Bearer <token>
       ──► Route guards (authGuard, verifiedGuard) read AuthService signals to redirect
```

`verified` is per-user, persisted in Postgres. Once a user completes KYC, future sign-ins skip `/identity` and go straight to `/dashboard`.

## Troubleshooting

- **`Firebase service account JSON not found`** on backend startup: `backend/firebase-service-account.json` is missing. Download from Firebase console.
- **CORS errors in browser**: check `CORS_ORIGINS` includes your frontend URL.
- **`auth/invalid-app-credential`** when sending OTP: check the web SDK config in `environment.ts` matches the Firebase project.
- **`auth/captcha-check-failed`**: reCAPTCHA needs `localhost` in Firebase authorized domains, and the page must be served over `http://localhost` (not `127.0.0.1`).
