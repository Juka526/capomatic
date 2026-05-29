---
title: TransChord API
emoji: 🎸
colorFrom: orange
colorTo: red
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
- **Job History** - Track all your transpositions
- **User Management** - Auth0 authentication with admin roles
- **Admin Dashboard** - Analytics and popular songs tracking
- **Bilingual UI** - Korean and English

## Architecture

```
+----------------------------------------------------------+
|             Frontend (Next.js on Vercel)                  |
|  +----------+  +----------+  +---------------------+    |
|  |  Pages   |  |Components|  |  Auth0 Provider      |    |
|  | - Home   |  | - Login  |  |  - Authentication    |    |
|  | - History|  | - Fretbd |  |  - Role checks       |    |
|  | - Admin  |  | - Guide  |  |                      |    |
|  +----------+  +----------+  +---------------------+    |
+----------------------------+-----------------------------+
                             | HTTP/REST
                             v
+----------------------------------------------------------+
|          Backend (FastAPI on Railway/Render)              |
|  +----------+  +----------+  +---------------------+    |
|  |   Auth   |  |  Storage |  |  OCR Pipeline        |    |
|  | - JWT    |  | - Local  |  |  - PaddleOCR         |    |
|  | - Roles  |  | - (S3)   |  |  - Staff-aware crop  |    |
|  +----------+  +----------+  +---------------------+    |
|  +----------+  +----------+  +---------------------+    |
|  |   Jobs   |  |   Admin  |  |  File Storage        |    |
|  | - CRUD   |  | - Stats  |  |  - Input/output save |    |
|  | - Track  |  | - Popular|  |  - History downloads |    |
|  +----------+  +----------+  +---------------------+    |
+----------------------------+-----------------------------+
                             |
                             v
                      +--------------+
                      |  PostgreSQL  |
                      |  - Users     |
                      |  - Jobs      |
                      +--------------+
```

## Tech Stack

| Layer    | Technology                                   |
|----------|----------------------------------------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS          |
| Backend  | FastAPI, Python 3.12, SQLAlchemy 2.0          |
| Database | PostgreSQL (asyncpg)                          |
| Auth     | Auth0 (SPA + JWT verification)                |
| OCR      | PaddleOCR 3.x (staff-aware band cropping)     |
| Storage  | Local filesystem (input/output file persistence)|
| Deploy   | Vercel (frontend) + Railway/Render (backend)  |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 14+
- Auth0 account

### 1. Clone and install

```bash
git clone https://github.com/your-username/capomatic.git
cd capomatic

# Backend
pip install -r requirements.txt

# If paddlepaddle fails on Apple Silicon (ARM):
pip install paddlepaddle==3.2.2 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/

# Frontend
cd frontend && npm install && cd ..
```

### 2. Set up PostgreSQL

```bash
createdb capomatic

# Tables are auto-created on first server start via SQLAlchemy
```

### 3. Configure environment

```bash
# Backend (root .env)
cp .env.example .env
# Edit .env with your Auth0 domain, database URL, etc.

# Frontend
cd frontend
cp .env.local.example .env.local
# Edit .env.local with your Auth0 client ID and API URL
```

**Backend `.env`:**
```env
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
OPENAI_API_KEY=your-openai-key
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/capomatic
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_AUDIENCE=https://capomatic-api
USE_S3=false
LOCAL_STORAGE_DIR=./storage
```

**Frontend `.env.local`:**
```env
NEXT_PUBLIC_AUTH0_DOMAIN=your-domain.auth0.com
NEXT_PUBLIC_AUTH0_CLIENT_ID=your-client-id
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4. Run

```bash
# Terminal 1: Backend
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True uvicorn backend.api.main:app --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

Open http://localhost:3000

## API Endpoints

### Public (no auth)

| Method | Path       | Description                             |
|--------|------------|-----------------------------------------|
| GET    | `/health`  | Liveness probe                          |
| POST   | `/detect`  | Detect chords in image, return JSON     |
| POST   | `/render`  | Transpose + render from cached detection|
| POST   | `/overlay` | Legacy: detect + transpose + render PNG |

### Authenticated

| Method | Path              | Description                        |
|--------|-------------------|------------------------------------|
| POST   | `/api/overlay`    | Full pipeline with job tracking    |
| GET    | `/api/jobs`       | List user's job history            |
| DELETE | `/api/jobs/{id}`  | Soft-delete a job                  |
| GET    | `/api/auth/me`    | Current user info + role           |

### Admin only

| Method | Path                 | Description                     |
|--------|----------------------|---------------------------------|
| GET    | `/api/admin/stats`   | Overall statistics              |
| GET    | `/api/admin/popular` | Most transposed songs           |
| GET    | `/api/admin/users`   | User list with activity         |

### Example: detect + render flow

```bash
# Step 1: Detect chords
curl -X POST http://localhost:8000/detect \
  -F "image=@fixtures/images/sample.jpeg" \
  | jq '.detection_id, .original_key'

# Step 2: Render with transposition
curl -X POST http://localhost:8000/render \
  -F "detection_id=<id-from-step-1>" \
  -F "semitones=-2"
```

### Example: legacy overlay (single call)

```bash
curl -X POST http://localhost:8000/overlay \
  -F "image=@fixtures/images/sample.jpeg" \
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

1. Push your repo to GitHub
2. Import project on [vercel.com](https://vercel.com)
3. Set root directory to `frontend`
4. Set environment variables:
   ```
   NEXT_PUBLIC_AUTH0_DOMAIN=your-domain.auth0.com
   NEXT_PUBLIC_AUTH0_CLIENT_ID=your-client-id
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   ```
5. Deploy

### Backend (Railway)

1. Create a new project on [railway.app](https://railway.app)
2. Add PostgreSQL service
3. Connect your GitHub repo
4. Set environment variables:
   ```
   PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
   OPENAI_API_KEY=your-openai-key
   DATABASE_URL=<railway-postgres-url>
   AUTH0_DOMAIN=your-domain.auth0.com
   AUTH0_AUDIENCE=https://capomatic-api
   CORS_ORIGINS=https://your-frontend.vercel.app
   USE_S3=false
   LOCAL_STORAGE_DIR=./storage
   ```
5. The repo includes a `Dockerfile` — Railway auto-detects it, no start command needed

### Auth0 Setup

1. Create a **Single Page Application** in Auth0
2. Set Allowed Callback URLs: `https://your-vercel-domain.vercel.app`
3. Set Allowed Logout URLs: same as above
4. Set Allowed Web Origins: same as above
5. Create an **API** with identifier `https://capomatic-api`
6. Note your Domain and Client ID for env vars

## Project Structure

```
capomatic/
├── backend/
│   ├── api/            FastAPI server (endpoints + middleware)
│   ├── auth/           Auth0 JWT verification + role management
│   ├── chords/         Chord parser, transposer, key detection
│   ├── db/             SQLAlchemy models, database setup, job CRUD
│   ├── ocr/            PaddleOCR runner, filter, hybrid detection
│   ├── overlay/        Render transposed chords onto sheet image
│   └── storage/        File persistence (input/output saves)
├── frontend/
│   ├── components/     React components (fretboard, auth, lang)
│   ├── lib/            Auth0 client, i18n, API helpers
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
- **PaddlePaddle 3.3.0+ on Intel CPU**: Crashes with oneDNN PIR error — use 3.2.2 (pinned in requirements.txt)
- **First run slow**: PaddleOCR downloads ~80MB models on first use
- **Port 8000 in use**: `lsof -ti :8000 | xargs kill`
- **`PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK`**: Required for any command that loads PaddleOCR models

## License

MIT
