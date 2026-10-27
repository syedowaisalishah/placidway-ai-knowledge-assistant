FROM node:22-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=2 ANONYMIZED_TELEMETRY=False HF_HUB_DISABLE_TELEMETRY=1
COPY backend/requirements-runtime.txt ./backend/requirements-runtime.txt
RUN pip install --no-cache-dir -r backend/requirements-runtime.txt
COPY backend/app ./backend/app
COPY config ./config
COPY scripts ./scripts
COPY data/snapshot ./data/snapshot
RUN python scripts/download_model.py --runtime-only
COPY --from=frontend /build/frontend/out ./frontend/out
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser
ENV PYTHONPATH=/app/backend
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log --no-proxy-headers"]
