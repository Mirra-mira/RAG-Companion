#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "[setup] Tao venv..."
    python -m venv venv
fi

echo "[setup] Kich hoat venv..."
if [ -f "venv/Scripts/activate" ]; then
    # Git Bash tren Windows
    source venv/Scripts/activate
else
    # Linux / macOS
    source venv/bin/activate
fi

echo "[setup] Cai requirements..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[setup] Da tao .env tu .env.example — nho sua DATABASE_URL va GEMINI_API_KEY."
fi

echo "[setup] Xong. Dung ./run.sh de chay server."
