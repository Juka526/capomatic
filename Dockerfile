FROM python:3.12-slim

# Build deps for asyncpg + runtime deps for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Disable oneDNN — crashes on Railway's x86 Intel CPUs
ENV FLAGS_use_mkldnn=false
ENV PADDLE_USE_ONEDNN=0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 8080
ENTRYPOINT ["/app/start.sh"]
