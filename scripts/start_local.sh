#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then
  echo "Create .venv and install backend dependencies first; see README.md." >&2
  exit 1
fi
export PYTHONPATH="$PWD/backend"
export TOKENIZERS_PARALLELISM=false
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8000}" --workers 1 --no-access-log --no-proxy-headers
