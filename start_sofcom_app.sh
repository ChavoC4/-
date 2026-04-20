#!/usr/bin/env bash

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

mkdir -p output

if ! python3 -c "import apscheduler, ddddocr, flask, playwright, dotenv" >/dev/null 2>&1; then
  python3 -m pip install --user -r requirements.txt
fi

python3 -m playwright install chromium >/dev/null 2>&1 || true

if ! pgrep -f "python3 main.py --web --host 127.0.0.1 --port 8080 --no-browser" >/dev/null 2>&1; then
  nohup python3 main.py --web --host 127.0.0.1 --port 8080 --no-browser >> output/app.log 2>&1 &
  sleep 2
fi

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://127.0.0.1:8080" >/dev/null 2>&1 || true
fi
