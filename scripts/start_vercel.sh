#!/bin/sh
set -eu

# The packaged source snapshot and embedding model are read-only. Chroma's
# restored index and small operational logs live in this instance's temp dir.
runtime_data=/tmp/placidway-ai-data
mkdir -p "$runtime_data"
[ -e "$runtime_data/snapshot" ] || ln -s /app/data/snapshot "$runtime_data/snapshot"
[ -e "$runtime_data/models" ] || ln -s /app/data/models "$runtime_data/models"
export DATA_DIR="$runtime_data"

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
  --workers 1 --no-access-log --no-proxy-headers
