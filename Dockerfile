FROM python:3.12-slim

# Runtime libraries required by OpenCV.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# v6-medium matches production and regressed 0/16 canonical sheets against the
# frozen production baseline in the CI canary (mobile: 11/16). See #9 and #4.
ENV CHORDTAYLOR_OCR_DET_MODEL=v6-medium \
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
    PADDLE_MAX_STITCHED_PIXELS=900000 \
    PADDLE_STITCH_MAX_SAFE_PIXELS=900000 \
    PADDLE_MIN_STITCH_RESIZE_SCALE=0.85 \
    RENDER_USE_INPAINT=0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860
CMD ["sh", "-c", "exec uvicorn backend.api.main:app --host 0.0.0.0 --port \"${PORT:-7860}\""]
