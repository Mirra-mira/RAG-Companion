"""Seed 10 user + vai fact cho moi user de load test co du du lieu doc.
Ghi de: TRUNCATE truoc khi seed.

Chay:
    cd backend
    ./venv/Scripts/python.exe -X utf8 scripts/seed_users.py
"""
import sys
import os
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND_DIR))

# Bat buoc mock LLM khi seed — de tranh call Gemini khong can thiet
os.environ["USE_MOCK_LLM"] = "true"

from fastapi.testclient import TestClient
from app.main import app
from app.core.db import get_conn


N_USERS = 10
FACTS_PER_USER = [
    "tao thich pho lam",
    "tao thich cafe sua da",
    "tao thich guitar",
]


def main():
    print("Truncate DB...")
    with get_conn() as conn:
        conn.execute("TRUNCATE facts, users, conversations CASCADE")
        conn.commit()

    client = TestClient(app)
    for i in range(N_USERS):
        res = client.post("/dev/create-user", json={"username": f"loaduser_{i}"})
        uid = res.json()["user_id"]
        for msg in FACTS_PER_USER:
            client.post("/chat", json={"user_id": uid, "message": msg})
        print(f"  seeded user {i+1}/{N_USERS} ({uid[:8]}...)")

    # Wait background writes
    import time
    time.sleep(3)

    with get_conn() as conn:
        n_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        n_facts = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    print(f"Done: {n_users} users, {n_facts} facts.")


if __name__ == "__main__":
    main()
