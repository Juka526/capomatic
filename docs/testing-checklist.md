# Capomatic Testing Checklist

## Prerequisites

- [ ] Backend running: `uvicorn backend.api.main:app --port 8000`
- [ ] Frontend running: `cd frontend && npm run dev`
- [ ] At least one PNG or JPEG test image

PostgreSQL, Auth0, and `TEST_TOKEN` are required only for the optional auth/admin checks.

## 1. Public pipeline

- [ ] `GET /health` returns `{"status":"ok"}`.
- [ ] Uploading PNG/JPEG starts detection and shows progress.
- [ ] The detected key and chord boxes appear.
- [ ] Changing capo position updates the target key.
- [ ] Replace and Above rendering both work.
- [ ] AI refinement works when `OPENAI_API_KEY` is configured.
- [ ] Download saves the active rendered image.
- [ ] Invalid or oversized uploads show an error.

## 2. Browser state

- [ ] A completed transposition appears in `/history`.
- [ ] History remains after refreshing the same browser.
- [ ] Deleting a history item removes it from `localStorage`.
- [ ] Korean/English switching works.

## 3. Optional auth/admin

- [ ] Login redirects through Auth0 and returns to the app.
- [ ] `GET /api/auth/me` returns the current database-backed user.
- [ ] Non-admin users cannot open `/admin/dashboard`.
- [ ] `GET /api/admin/users` returns users for an admin token.
- [ ] Logout clears the Auth0 session.

## 4. Security and configuration

- [ ] `/api/auth/me` rejects unauthenticated requests.
- [ ] `/api/admin/users` rejects non-admin requests.
- [ ] Production CORS allows only `https://capomatic.vercel.app`.
- [ ] Public routes still work when `DATABASE_URL` is absent.
- [ ] Database-backed routes return 503 when the database is not configured.

## Automated checks

```bash
# Unit tests; live integration tests skip without TEST_TOKEN.
python -m pytest

# Frontend type and production build checks.
cd frontend
npx tsc --noEmit
npm run build

# Optional live auth/admin integration checks.
TEST_API_URL=http://localhost:8000 TEST_TOKEN="eyJ..." \
  python -m pytest tests/integration -v
```
