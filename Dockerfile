FROM python:3.12-slim

# Build deps for asyncpg + runtime deps for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV CHORDTAYLOR_OCR_DET_MODEL=mobile \
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
    PADDLE_MAX_STITCHED_PIXELS=400000 \
    HYBRID_PADDLE_HIGH_RECALL_GAP_FILL=0 \
    HYBRID_GPT_CONTACT_MAX_SIDE=1200 \
    HYBRID_GPT_CROP_BATCH_SIZE=30 \
    RENDER_USE_INPAINT=0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860
CMD ["sh", "-c", "exec uvicorn backend.api.main:app --host 0.0.0.0 --port \"${PORT:-7860}\""]
