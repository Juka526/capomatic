# TransChord Testing Checklist

Manual verification checklist for the auth/jobs/admin features.

## Prerequisites

- [ ] PostgreSQL running (`brew services start postgresql@16`)
- [ ] Backend running (`uvicorn backend.api.main:app --port 8000`)
- [ ] Frontend running (`cd frontend && npm run dev`)
- [ ] Auth0 configured and `.env` / `.env.local` populated
- [ ] At least one test image in `fixtures/images/`

---

## 1. Authentication

- [ ] **Login**: Click "Log In" → redirected to Auth0 → login → redirected back
- [ ] **User profile**: After login, name/avatar appears in header
- [ ] **Logout**: Click "Log Out" → redirected to home, login button reappears
- [ ] **Token persistence**: Refresh page → still logged in (localStorage cache)
- [ ] **Protected route**: Navigate to `/history` while logged out → redirected to login

## 2. Core Pipeline (Public — No Auth Required)

- [ ] **Upload**: Drag or click to upload PNG/JPG → detection starts
- [ ] **Detection progress**: Progress bar shows during detection
- [ ] **Key detection**: Detected key badge appears after detection
- [ ] **Transpose slider**: Move capo slider → key display updates
- [ ] **Convert**: Click Convert → both Replace and Above modes rendered
- [ ] **Tab toggle**: Switch between Replace/Above tabs → image swaps
- [ ] **Download**: Download button saves the active tab's image
- [ ] **Clear**: X button resets the upload area
- [ ] **Error handling**: Upload invalid file → error message shown

## 3. Job History (Authenticated)

- [ ] **Auto-save**: After converting, jobs appear in `/history`
- [ ] **Job details**: Each job shows song name, keys, semitones, mode, timestamp
- [ ] **Processing info**: `detected_chords_count`, `processing_time_ms` shown
- [ ] **Delete job**: Delete button removes job from list
- [ ] **Empty state**: New user sees "No jobs yet" message
- [ ] **Pagination**: History loads correctly with many jobs

## 4. Admin Dashboard

- [ ] **Access control**: Non-admin users see "Access Denied" on `/admin/dashboard`
- [ ] **Admin link**: Admin users see "Admin" link in header
- [ ] **Overview tab**: Shows stat cards (users, jobs, cached, hit rate, avg time)
- [ ] **Popular songs tab**: Shows ranked table with key info and request counts
- [ ] **Users tab**: Shows all users with roles and dates
- [ ] **Tab switching**: Tabs switch content correctly

## 5. Caching

- [ ] **Cache miss**: First request processes normally (X-Cache: MISS)
- [ ] **Cache hit**: Same image + semitones + mode → instant response (X-Cache: HIT)
- [ ] **Different params**: Changing semitones or mode → cache miss → reprocess

## 6. Security

- [ ] **Auth endpoints reject unauthenticated**: `/api/auth/me` → 401
- [ ] **Admin endpoints reject non-admin**: `/api/admin/stats` → 403
- [ ] **Ownership check**: Cannot access/delete other users' jobs → 404
- [ ] **Public endpoints still work**: `/health`, `/detect`, `/render`, `/overlay` unchanged

---

## Running Automated Tests

```bash
# Unit tests (no auth required)
python -m pytest tests/ -v --ignore=tests/integration

# Integration tests (requires TEST_TOKEN)
export TEST_TOKEN="eyJ..."
python -m pytest tests/integration/ -v

# Performance benchmarks
python scripts/performance_test.py
```
