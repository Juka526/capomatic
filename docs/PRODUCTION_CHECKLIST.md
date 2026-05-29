# Production Deployment Checklist

Pre-deployment checklist for Capomatic. Work through each section before going live.

---

## 1. Code Quality

- [ ] All tests pass: `python -m pytest`
- [ ] No TypeScript errors: `cd frontend && npx tsc --noEmit`
- [ ] Frontend builds cleanly: `cd frontend && npm run build`
- [ ] No hardcoded `localhost` URLs in committed code
- [ ] No `.env` or `.env.local` files committed to git
- [ ] `.gitignore` covers: `.env`, `storage/`, `node_modules/`, `.next/`, `__pycache__/`

## 2. Security

- [ ] Auth0 secrets are in environment variables, not in code
- [ ] `AUTH0_DOMAIN` and `AUTH0_AUDIENCE` set on backend
- [ ] Frontend only exposes `NEXT_PUBLIC_` prefixed env vars
- [ ] CORS origins restricted to production domain (not `*`)
- [ ] Upload size limit enforced (20MB in `MAX_UPLOAD_BYTES`)
- [ ] Admin endpoints require `require_admin` dependency
- [ ] No debug/development endpoints exposed in production
- [ ] `frontend/.env.local` contains no real secrets (only public client ID)

## 3. Database (PostgreSQL)

- [ ] Production database created and accessible
- [ ] `DATABASE_URL` env var set with production credentials
- [ ] Tables auto-create on first start (via `init_db()` in lifespan)
- [ ] Database user has minimal required permissions (SELECT, INSERT, UPDATE, DELETE)
- [ ] Connection pooling configured if needed (asyncpg handles this)
- [ ] Backups scheduled (daily recommended)

## 4. Auth0 Configuration

- [ ] Single Page Application created in Auth0 dashboard
- [ ] API created with identifier matching `AUTH0_AUDIENCE`
- [ ] Allowed Callback URLs set to production frontend URL
- [ ] Allowed Logout URLs set to production frontend URL
- [ ] Allowed Web Origins set to production frontend URL
- [ ] Token expiration configured (default is fine for MVP)
- [ ] Admin role assigned to admin users via Auth0 dashboard or Rules

## 5. Environment Variables

### Backend (Railway/Render)

- [ ] `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True`
- [ ] `OPENAI_API_KEY=sk-...`
- [ ] `DATABASE_URL=postgresql+asyncpg://...`
- [ ] `AUTH0_DOMAIN=your-domain.auth0.com`
- [ ] `AUTH0_AUDIENCE=https://capomatic-api`
- [ ] `USE_S3=false`
- [ ] `LOCAL_STORAGE_DIR=./storage`
- [ ] Start command: `uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT`

### Frontend (Vercel)

- [ ] `NEXT_PUBLIC_AUTH0_DOMAIN=your-domain.auth0.com`
- [ ] `NEXT_PUBLIC_AUTH0_CLIENT_ID=your-client-id`
- [ ] `NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app`
- [ ] Root directory set to `frontend`

## 6. Backend Deployment

- [ ] PaddleOCR models download on first request (~80MB to `~/.paddleocr/`)
- [ ] Sufficient disk space for `storage/` directory (cached outputs)
- [ ] Sufficient memory for OCR processing (minimum 1GB recommended)
- [ ] Health check endpoint responds: `GET /health` returns `{"status": "ok"}`
- [ ] CORS configured for production frontend domain

## 7. Frontend Deployment

- [ ] `npm run build` succeeds with no errors
- [ ] Environment variables set in Vercel dashboard
- [ ] API URL points to production backend (not localhost)
- [ ] Auth0 redirect URIs match Vercel deployment URL
- [ ] Pages load without console errors: `/`, `/history`, `/admin/dashboard`

## 8. Testing Verification

- [ ] Upload an image and detect chords
- [ ] Select a capo position and render transposition
- [ ] Verify filesystem cache works (second render of same image is instant)
- [ ] Login with Auth0
- [ ] Check job history page shows completed jobs
- [ ] Admin dashboard loads with stats (if admin user)
- [ ] Language toggle works (Korean/English)
- [ ] Guide modal opens from hamburger menu
- [ ] Download transposed image as PNG

## 9. Performance

- [ ] First OCR detection: < 15 seconds
- [ ] Cached render: < 1 second
- [ ] Frontend initial load: < 3 seconds
- [ ] API health check: < 200ms
- [ ] No memory leaks during sustained use

## 10. Post-Deployment

- [ ] Monitor application logs for errors
- [ ] Verify database connections are stable
- [ ] Check storage directory growth (clean up old cache if needed)
- [ ] Set up uptime monitoring on `/health` endpoint
- [ ] Document rollback procedure (redeploy previous git commit)

## Rollback Plan

If issues arise after deployment:

1. **Frontend**: Redeploy previous commit in Vercel dashboard (instant)
2. **Backend**: Redeploy previous commit in Railway/Render dashboard
3. **Database**: Restore from backup if schema changes caused issues
4. **Cache**: Delete `storage/outputs/` to clear filesystem cache

## Storage Maintenance

Filesystem cache grows over time. To clean up:

```bash
# Delete all cached outputs (they will regenerate on next request)
rm -rf storage/outputs/

# Delete outputs older than 30 days
find storage/outputs/ -type f -mtime +30 -delete
```
