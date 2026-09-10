"""Load test cho muc 4.4.1 doc chuong 4.

Kich ban: 70% GET /users/{id}/facts + 30% POST /chat (dung fixed user pool
duoc seed truoc). VU can duoc set qua CLI: --users N --spawn-rate R --run-time T.

Cach chay (headless, xuat CSV):
    locust -f scripts/locustfile.py --headless --host=http://localhost:8000 \
           --users 10 --spawn-rate 5 --run-time 2m --csv=results/loadtest_10vu

Yeu cau: uvicorn phai chay san o :8000, va da co it nhat 10 user trong DB
(script chinh experiment_ab da tao san, hoac chay scripts/seed_users.py).
"""
import random
from locust import HttpUser, task, between


# Cac tin nhan test — day du de simulate luu luong that, ngan de LLM tra loi nhanh
_CHAT_MESSAGES = [
    "Xin chao ban",
    "Hom nay ban khoe khong",
    "Minh thich pho bo",
    "Ban goi y cho minh mon an di",
    "Cam on ban nhe",
    "Minh dang can giup do",
    "Ke chuyen cho minh nghe",
    "Ban co nho minh ten gi khong",
]


class ChatUser(HttpUser):
    # Wait 1-3s giua cac request cua cung 1 VU — simulate user thuc te
    wait_time = between(1, 3)

    def on_start(self):
        """Lay danh sach user tu /dev/users va pick 1 user ngau nhien cho VU nay."""
        res = self.client.get("/dev/users")
        users = res.json()
        if not users:
            raise RuntimeError("DB khong co user nao — chay scripts/seed_users.py truoc.")
        self.user_id = random.choice(users)["user_id"]

    @task(7)  # 70% weight
    def get_facts(self):
        self.client.get(f"/users/{self.user_id}/facts", name="/users/{id}/facts")

    @task(3)  # 30% weight
    def chat(self):
        msg = random.choice(_CHAT_MESSAGES)
        self.client.post(
            "/chat",
            json={"user_id": self.user_id, "message": msg},
            name="/chat",
        )
