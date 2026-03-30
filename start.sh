#!/bin/sh
# Disable PIR to avoid oneDNN incompatibility on x86 (Railway)
export FLAGS_enable_pir_in_executor=0
export FLAGS_enable_pir_api=0
exec uvicorn backend.api.main:app --host 0.0.0.0 --port "${PORT:-8080}"
