#!/usr/bin/env bash
# Linux user services keep the local demonstration alive after the terminal exits.
# This does not prevent machine sleep, guarantee uptime, or create durable cloud hosting.
set -euo pipefail
cd "$(dirname "$0")/.."
project_root="$PWD"
demo_port="${PORT:-8765}"
if [[ ! -x .tools/cloudflared || ! -x .venv/bin/python ]]; then
  echo "Install the Python environment and official cloudflared binary first." >&2
  exit 1
fi
systemd-run --user --unit=placidway-ai-demo --collect \
  --property=Restart=on-failure --property=RestartSec=5 \
  --working-directory="$project_root" --setenv="PORT=$demo_port" \
  /bin/bash "$project_root/scripts/start_local.sh"
systemd-run --user --unit=placidway-ai-tunnel --collect \
  --property=Restart=on-failure --property=RestartSec=10 \
  --working-directory="$project_root" \
  "$project_root/.tools/cloudflared" tunnel --url "http://127.0.0.1:$demo_port" \
  --no-autoupdate --protocol http2 --logfile "$project_root/data/logs/public-tunnel.log"
echo "Demo services started. The public URL appears in data/logs/public-tunnel.log."
echo "Stop with: systemctl --user stop placidway-ai-tunnel placidway-ai-demo"
