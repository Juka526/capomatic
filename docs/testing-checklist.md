# Capomatic Testing Checklist

The authoritative V1 scope and acceptance thresholds are in
[`V1_RELEASE_PLAN.md`](V1_RELEASE_PLAN.md).

## Prerequisites

- [ ] Backend running: `uvicorn backend.api.main:app --port 8000`
- [ ] Frontend running: `cd frontend && npm run dev`
- [ ] At least one PNG or JPEG test image

Auth0 credentials and `TEST_TOKEN` are required for live login verification. PostgreSQL is not
part of V1.

## 1. Public pipeline

- [ ] `GET /health` returns `{"status":"ok"}`.
- [ ] Uploading PNG/JPEG starts detection and shows progress.
- [ ] The detected key and chord boxes appear.
- [ ] Changing capo position updates the target key.
- [ ] Replace and Above rendering both work.
- [ ] Paid GPT refinement is absent from the UI and both backend entry points reject it.
- [ ] Download saves the active rendered image.
- [ ] Invalid or oversized uploads show an error.

## 2. Browser state

- [ ] A completed transposition appears in `/history`.
- [ ] History remains after refreshing the same browser.
- [ ] Deleting a history item removes it from `localStorage`.
- [ ] Korean/English switching works.

## 3. V1 login

- [ ] Login redirects through Auth0 and returns to the app.
- [ ] `GET /api/auth/me` returns verified Auth0 identity claims without a database.
- [ ] Logout clears the Auth0 session.
- [ ] `/admin/dashboard` is not found and administrator APIs return `410 Gone`.

## 4. Security and configuration

- [ ] `/api/auth/me` rejects unauthenticated requests.
- [ ] `/api/admin/users` and `/api/auth/admin-test` return `410 Gone`.
- [ ] Production CORS allows only `https://capomatic.vercel.app`.
- [ ] Public routes and `/api/auth/me` work when `DATABASE_URL` is absent.
- [ ] Invalid, corrupt, unsupported, oversized, and excessive-dimension images return 4xx.

## Automated checks

```bash
# Unit tests; live integration tests skip without TEST_TOKEN.
python -m pytest

# Frontend tests, type check, and production build.
cd frontend
npm run check

# Live Auth0 integration checks.
TEST_API_URL=http://localhost:8000 TEST_TOKEN="eyJ..." \
  python -m pytest tests/integration/test_auth_flow.py -v
```
