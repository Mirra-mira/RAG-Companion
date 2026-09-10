"""Integration test — gọi qua FastAPI TestClient THẬT, ghi/đọc PostgreSQL
THẬT (không mock DB). Yêu cầu Postgres đã chạy sẵn với schema.sql đã áp dụng
(xem README mục cài đặt). Dùng MockEmbeddingProvider/MockLLMProvider (qua
dependencies.py) để tất định — không cần GEMINI_API_KEY để chạy bộ test này.

Đây là bản pytest hóa của bộ prompt kiểm thử thủ công đã thống nhất trước đó
(nhóm ADD/REINFORCE/CONFLICT/NOOP/multi-user).
"""
import time
import pytest
from fastapi.testclient import TestClient
from app.main import app  # FastAPI instance duoc dinh nghia o main.py
from app.core.db import get_conn


@pytest.fixture(autouse=True)
def clean_db():
    with get_conn() as conn:
        conn.execute("TRUNCATE facts, users CASCADE")
        conn.commit()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def create_user(client, name="test_user"):
    # Endpoint nhan JSON body {"username": ...}, khong phai query string
    res = client.post("/dev/create-user", json={"username": name})
    assert res.status_code == 200
    return res.json()["user_id"]


def chat(client, user_id, message):
    res = client.post("/chat", json={"user_id": user_id, "message": message})
    assert res.status_code == 200
    time.sleep(0.3)  # đợi BackgroundTasks (luồng ghi) chạy xong trong TestClient
    return res.json()


def get_facts(client, user_id):
    res = client.get(f"/users/{user_id}/facts")
    assert res.status_code == 200
    return res.json()


class TestFullDedupFlow:
    """Nhóm 1-3 của bộ prompt: ADD -> REINFORCE -> CONFLICT"""

    def test_1_1_add_new_fact(self, client):
        user_id = create_user(client)
        chat(client, user_id, "tao thich pho lam")
        facts = get_facts(client, user_id)
        assert len(facts) == 1
        assert facts[0]["content"] == "pho"
        assert facts[0]["weight"] == 1
        assert facts[0]["status"] == "active"

    def test_2_1_reinforce_on_case_variant(self, client):
        user_id = create_user(client)
        chat(client, user_id, "tao thich pho lam")
        chat(client, user_id, "Thich Pho")
        facts = get_facts(client, user_id)
        assert len(facts) == 1  # KHÔNG tạo dòng mới
        assert facts[0]["weight"] == 2

    def test_3_1_conflict_supersedes_old_fact(self, client):
        user_id = create_user(client)
        chat(client, user_id, "tao thich pho lam")
        chat(client, user_id, "Thich Pho")
        chat(client, user_id, "tao het thich pho roi")

        res = client.get(f"/users/{user_id}/facts")
        active_facts = res.json()
        # find_by_user_id chỉ trả status='active' -> fact cũ (superseded) không xuất hiện
        assert len(active_facts) == 1
        assert active_facts[0]["weight"] == 1  # dòng MỚI, không phải dòng cũ weight=2


class TestNoopAndIsolation:
    def test_4_3_noop_does_not_create_fact(self, client):
        user_id = create_user(client)
        chat(client, user_id, "hom nay troi hoi nong nhi")
        facts = get_facts(client, user_id)
        assert facts == []

    def test_6_1_multi_user_isolation(self, client):
        user_a = create_user(client, "user_a")
        user_b = create_user(client, "user_b")

        chat(client, user_a, "tao thich pho lam")
        chat(client, user_a, "Thich Pho")  # reinforce -> weight=2 cho A
        chat(client, user_b, "tao thich pho lam")  # fact MỚI, riêng cho B

        facts_a = get_facts(client, user_a)
        facts_b = get_facts(client, user_b)

        assert len(facts_a) == 1 and facts_a[0]["weight"] == 2
        assert len(facts_b) == 1 and facts_b[0]["weight"] == 1  # không bị ảnh hưởng bởi A


class TestReadPathBasics:
    def test_chat_returns_response_even_with_no_facts_yet(self, client):
        user_id = create_user(client)
        data = chat(client, user_id, "xin chao")
        assert "response" in data
        assert data["retrieved_facts"] == []
