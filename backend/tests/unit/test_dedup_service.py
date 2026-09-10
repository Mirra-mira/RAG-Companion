"""Unit test cho DedupService (mục 3.5.2, Hình 3.4 Activity Diagram).
Dùng unittest.mock để giả lập Repository/Embedder/LLM — test ĐÚNG LOGIC
điều phối 4 nhánh quyết định, không phụ thuộc DB hay API thật.
"""
import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from app.services.dedup_service import DedupService


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def mock_embedder():
    m = MagicMock()
    m.embed.return_value = [0.1] * 768
    return m


@pytest.fixture
def mock_llm():
    return MagicMock()


@pytest.fixture
def service(mock_repo, mock_embedder, mock_llm):
    return DedupService(mock_repo, mock_embedder, mock_llm)


class TestDedupADD:
    def test_add_when_llm_decides_add(self, service, mock_repo, mock_llm):
        mock_repo.find_top_k_by_embedding.return_value = []
        mock_llm.classify_relationship.return_value = {"decision": "ADD", "target_fact_id": None}
        mock_repo.insert.return_value = {"fact_id": "new1", "content": "pho", "weight": 1}

        result = service.process(uuid4(), "food", "pho")

        assert result["action"] == "ADD"
        mock_repo.insert.assert_called_once()
        mock_repo.reinforce.assert_not_called()
        mock_repo.supersede.assert_not_called()


class TestDedupREINFORCE:
    def test_reinforce_calls_repo_with_correct_target_id(self, service, mock_repo, mock_llm):
        target_id = uuid4()
        mock_repo.find_top_k_by_embedding.return_value = [
            {"fact_id": target_id, "content": "pho", "category": "food",
             "weight": 1, "similarity": 0.99}
        ]
        mock_llm.classify_relationship.return_value = {
            "decision": "REINFORCE", "target_fact_id": str(target_id)
        }
        mock_repo.reinforce.return_value = {"fact_id": target_id, "content": "pho", "weight": 2}

        result = service.process(uuid4(), "food", "pho")

        assert result["action"] == "REINFORCE"
        mock_repo.reinforce.assert_called_once_with(target_id)
        mock_repo.insert.assert_not_called()


class TestDedupCONFLICT:
    def test_conflict_supersedes_old_and_inserts_new(self, service, mock_repo, mock_llm):
        old_id = uuid4()
        mock_repo.find_top_k_by_embedding.return_value = [
            {"fact_id": old_id, "content": "pho", "category": "food",
             "weight": 3, "similarity": 0.98}
        ]
        mock_llm.classify_relationship.return_value = {
            "decision": "CONFLICT", "target_fact_id": str(old_id)
        }
        mock_repo.insert.return_value = {"fact_id": "new2", "content": "khong thich pho", "weight": 1}

        result = service.process(uuid4(), "food", "khong thich pho")

        assert result["action"] == "CONFLICT"
        mock_repo.supersede.assert_called_once_with(old_id)
        mock_repo.insert.assert_called_once()
        # đảm bảo supersede được gọi TRƯỚC insert (đúng thứ tự trong Hình 3.4)
        write_calls = [c[0] for c in mock_repo.method_calls if c[0] in ("supersede", "insert")]
        assert write_calls == ["supersede", "insert"]


class TestDedupNOOP:
    def test_noop_does_not_touch_repository_writes(self, service, mock_repo, mock_llm):
        mock_repo.find_top_k_by_embedding.return_value = []
        mock_llm.classify_relationship.return_value = {"decision": "NOOP", "target_fact_id": None}

        result = service.process(uuid4(), "misc", "hom nay troi dep")

        assert result["action"] == "NOOP"
        assert result["fact"] is None
        mock_repo.insert.assert_not_called()
        mock_repo.reinforce.assert_not_called()
        mock_repo.supersede.assert_not_called()


class TestDedupScoping:
    def test_search_is_scoped_to_correct_user(self, service, mock_repo, mock_llm):
        """Đảm bảo user_id truyền vào process() được dùng đúng cho vector
        search — đây là kiểm chứng trực tiếp cho FR5 (cô lập theo user)."""
        user_id = uuid4()
        mock_repo.find_top_k_by_embedding.return_value = []
        mock_llm.classify_relationship.return_value = {"decision": "ADD", "target_fact_id": None}
        mock_repo.insert.return_value = {"fact_id": "x", "content": "y", "weight": 1}

        service.process(user_id, "food", "pho")

        called_user_id = mock_repo.find_top_k_by_embedding.call_args[0][0]
        assert called_user_id == user_id
