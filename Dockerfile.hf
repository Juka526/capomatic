FROM python:3.12-slim

# Build deps for asyncpg + runtime deps for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860
CMD ["sh", "-c", "exec uvicorn backend.api.main:app --host 0.0.0.0 --port \"${PORT:-7860}\""]
