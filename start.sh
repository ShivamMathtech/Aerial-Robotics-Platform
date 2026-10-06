#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -c 'import sys; assert (3,11)<=sys.version_info[:2]<=(3,12), "Use Python 3.11 or 3.12"'
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r backend/requirements.txt
printf 'Open http://127.0.0.1:8000 in your browser. Ctrl+C stops the server.\n'
exec .venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
