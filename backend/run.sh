#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "[run] Chua co venv — chay ./setup.sh truoc."
    exit 1
fi

if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# --host 0.0.0.0 de nghe ca IPv4 va IPv6 (fix Failed to fetch khi frontend goi localhost)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
