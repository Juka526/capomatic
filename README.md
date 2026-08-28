---
title: Capomatic API
emoji: 🎸
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# Capomatic

**Worship team chord transposition tool powered by AI**

Capomatic automatically detects chords in uploaded sheet music images and transposes them to any key. Built for worship teams who need quick, accurate chord sheet transposition.

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![Next.js](https://img.shields.io/badge/next.js-14-black.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- **AI-Powered Detection** - PaddleOCR chord recognition from sheet images
- **Visual Fretboard** - Interactive capo position selector (0-7 frets)
- **Fast Re-rendering** - Detect once, then render multiple keys from the in-memory result
- **Local History** - Keep transposition history in the current browser
- **Optional AI Refinement** - Refine PaddleOCR results with OpenAI when configured
- **Optional User Admin** - Auth0 login and a PostgreSQL-backed user list when configured
- **Bilingual UI** - Korean and English

## Architecture

```text
Browser ──> https://capomatic.vercel.app             Next.js frontend (Vercel)
   └──────> https://juka526-capomatic.hf.space        FastAPI + PaddleOCR (HF Docker Space)
                                                          ├─ OpenAI API (optional refinement)
                                                          └─ Auth0 + PostgreSQL (optional admin)
```

The production service currently runs the public OCR/transposition flow without a
database. History is stored in browser `localStorage`; Auth0 and admin endpoints are
enabled only when the backend database and Auth0 variables are configured.

## Tech Stack

| Layer      | Technology                                      |
|------------|-------------------------------------------------|
| Frontend   | Next.js 16, TypeScript, Tailwind CSS             |
| Backend    | FastAPI, Python 3.12                             |
| OCR        | PaddleOCR 3.x (staff-aware band cropping)        |
| State      | Backend in-memory detection cache + localStorage |
| Optional   | OpenAI, Auth0, PostgreSQL/SQLAlchemy             |
| Deployment | Vercel frontend + Hugging Face Docker Space     |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 14+ and an Auth0 account only for optional auth/admin features

### 1. Clone and install

```bash
git clone https://github.com/Juka526/capomatic.git
cd capomatic

# Backend
pip install -r requirements.txt

# If paddlepaddle fails on Apple Silicon (ARM):
pip install paddlepaddle==3.2.2 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/

# Frontend
cd frontend && npm install && cd ..
```

### 2. Configure environment

```bash
# Backend (root .env)
cp .env.example .env
# Public OCR works with the defaults. Add optional AI/Auth0/database values as needed.

# Frontend
(cd frontend && cp .env.local.example .env.local)
# The default API URL is the local backend.
```

**Backend `.env`:**
```env
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
CORS_ORIGINS=http://localhost:3000
# OPENAI_API_KEY=your-openai-key
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/capomatic
# AUTH0_DOMAIN=your-domain.auth0.com
# AUTH0_AUDIENCE=https://capomatic-api
```

**Frontend `.env.local`:**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
# NEXT_PUBLIC_AUTH0_DOMAIN=your-domain.auth0.com
# NEXT_PUBLIC_AUTH0_CLIENT_ID=your-client-id
```

### 3. Run

```bash
# Terminal 1: Backend
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True uvicorn backend.api.main:app --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

Open http://localhost:3000

## API Endpoints

### Public (no auth)

| Method | Path             | Description                              |
|--------|------------------|------------------------------------------|
| GET    | `/`              | Root liveness probe                      |
| GET    | `/health`        | Liveness probe                           |
| POST   | `/detect`        | Detect chords in image, return JSON      |
| POST   | `/detect/refine` | Refine a cached detection with OpenAI    |
| POST   | `/render`        | Transpose + render from cached detection |
| POST   | `/overlay`       | Legacy: detect + transpose + render PNG  |

### Authenticated

These routes require `DATABASE_URL`, `AUTH0_DOMAIN`, and `AUTH0_AUDIENCE`.

| Method | Path                   | Description                   |
|--------|------------------------|-------------------------------|
| GET    | `/api/auth/me`         | Current user info + role      |
| GET    | `/api/auth/admin-test` | Verify the current admin role |

### Admin only

| Method | Path               | Description             |
|--------|--------------------|-------------------------|
| GET    | `/api/admin/users` | User list with activity |

### Example: detect + render flow

```bash
# Step 1: Detect chords
curl -X POST http://localhost:8000/detect \
  -F "image=@fixtures/images/IMG_4616.PNG" \
  -o detection.json

# Step 2: Render with transposition
curl -X POST http://localhost:8000/render \
  -F "detection_id=<id-from-step-1>" \
  -F "semitones=-2" \
  -F "mode=both" \
  -o render.json
```

### Example: legacy overlay (single call)

```bash
curl -X POST http://localhost:8000/overlay \
  -F "image=@fixtures/images/IMG_4616.PNG" \
  -F "semitones=2" \
  -F "mode=replace" \
  -o output.png
```

## Testing

```bash
# All tests
python -m pytest

# Specific test file
python -m pytest tests/test_render.py -v

# OCR evaluation against fixtures
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True python scripts/eval_ocr.py --engine paddle

# Debug OCR on a single image
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True python scripts/ocr_debug.py "fixtures/images/<filename>"
```

## Deployment

### Frontend (Vercel)

Production: <https://capomatic.vercel.app>

1. Connect the GitHub repository to Vercel.
2. Set the project root directory to `frontend`.
3. Set the production environment variable:
   ```env
   NEXT_PUBLIC_API_URL=https://juka526-capomatic.hf.space
   ```
4. Add `NEXT_PUBLIC_AUTH0_DOMAIN` and `NEXT_PUBLIC_AUTH0_CLIENT_ID` only when Auth0 is enabled.

### Backend (Hugging Face Space)

Space: <https://huggingface.co/spaces/juka526/capomatic>

API: <https://juka526-capomatic.hf.space>

The Space builds the root `Dockerfile` with Docker SDK and listens on port `7860`.
The Dockerfile also pins the production OCR model and canvas thresholds.
Set this Space variable so browsers from the Vercel deployment can call the API:

```env
CORS_ORIGINS=https://capomatic.vercel.app
```

Optional Space configuration:

- Secret: `OPENAI_API_KEY` for GPT refinement.
- Variables: `DATABASE_URL`, `AUTH0_DOMAIN`, and `AUTH0_AUDIENCE` together for auth/admin.

GPT refinement is currently a public endpoint and can incur provider cost. Do not enable the
secret for an open release without an authentication, rate-limit, or budget boundary.

When Vercel Git integration is enabled, pushing to GitHub deploys the frontend. The HF Space
has a separate repository, so verify both platforms' source commits after each release.
See [`docs/PRODUCTION_CHECKLIST.md`](docs/PRODUCTION_CHECKLIST.md) for verification and rollback.

### Auth0 setup (optional)

Auth/admin is not enabled in the current production deployment. The backend creates its user
table when a database is configured, but admin-role bootstrap and database backup/migration
operations must be defined before treating this as a supported production mode.

1. Create a **Single Page Application** in Auth0.
2. Set Allowed Callback URLs, Allowed Logout URLs, and Allowed Web Origins to `https://capomatic.vercel.app`.
3. Create an **API** with identifier `https://capomatic-api`.
4. Add the Auth0 values to both deployment platforms as described above.

## Project Structure

```
capomatic/
├── backend/
│   ├── api/            FastAPI server (endpoints + middleware)
│   ├── auth/           Auth0 JWT verification + role management
│   ├── chords/         Chord parser, transposer, key detection
│   ├── db/             Optional SQLAlchemy user database
│   ├── ocr/            PaddleOCR runner, filter, hybrid detection
│   └── overlay/        Render transposed chords onto sheet image
├── frontend/
│   ├── components/     React components (fretboard, auth, lang)
│   ├── lib/            Auth0, admin API, and i18n helpers
│   ├── pages/          Next.js pages (home, history, admin)
│   └── styles/         Tailwind + custom CSS
├── fixtures/
│   ├── images/         Test images
│   └── labels/         Ground-truth JSON labels
├── scripts/            OCR evaluation and debug tools
├── tests/              Unit + integration tests
└── requirements.txt    Python dependencies
```

## Troubleshooting

- **NumPy 2.x `ImportError`**: PaddleOCR requires NumPy <2. Fix: `pip install "numpy<2"`
- **Apple Silicon**: Use `pip install paddlepaddle==3.2.2 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/`
- **PaddlePaddle 3.3.0+ on x86 Linux**: Crashes with oneDNN PIR error — use 3.2.2 (pinned in requirements.txt)
- **First run slow**: PaddleOCR downloads ~80MB models on first use
- **Port 8000 in use**: `lsof -ti :8000 | xargs kill`
- **`PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK`**: Required for any command that loads PaddleOCR models
- **Clean full-page sheets miss many chords**: keep deployment OCR settings accuracy-safe:
  `PADDLE_MAX_STITCHED_PIXELS=900000`, `PADDLE_STITCH_MAX_SAFE_PIXELS=900000`,
  and `PADDLE_MIN_STITCH_RESIZE_SCALE=0.85`. Oversized stitched OCR canvases
  automatically fall back to per-staff-band OCR to avoid downscaling chord text.

## License

MIT
