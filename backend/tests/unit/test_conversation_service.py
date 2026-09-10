"""Unit test cho ConversationService — bộ nhớ NGẮN HẠN (khác long-term
memory/facts). Test riêng logic ngưỡng maybe_summarize(), không đụng DB thật.
"""
import pytest
from unittest.mock import MagicMock
from app.services.conversation_service import ConversationService
from app.core.config import settings


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def mock_llm():
    return MagicMock()


@pytest.fixture
def service(mock_repo, mock_llm):
    return ConversationService(mock_repo, mock_llm)


class TestMaybeSummarizeThreshold:
    def test_below_threshold_does_nothing(self, service, mock_repo, mock_llm):
        mock_repo.count_unsummarized.return_value = settings.SUMMARIZE_THRESHOLD - 1
        service.maybe_summarize("user1")
        mock_llm.summarize.assert_not_called()
        mock_repo.set_summary.assert_not_called()

    def test_exactly_at_threshold_does_nothing(self, service, mock_repo, mock_llm):
        """Biên: đúng bằng ngưỡng thì CHƯA trigger (code dùng > không >=)."""
        mock_repo.count_unsummarized.return_value = settings.SUMMARIZE_THRESHOLD
        service.maybe_summarize("user1")
        mock_llm.summarize.assert_not_called()

    def test_above_threshold_triggers_summarize(self, service, mock_repo, mock_llm):
        mock_repo.count_unsummarized.return_value = settings.SUMMARIZE_THRESHOLD + 5
        mock_repo.get_oldest_unsummarized.return_value = [
            {"msg_id": "m1", "role": "user", "content": "xin chao"},
            {"msg_id": "m2", "role": "assistant", "content": "chao ban"},
        ]
        mock_repo.get_summary.return_value = ""
        mock_llm.summarize.return_value = "tóm tắt mới"

        service.maybe_summarize("user1")

        mock_llm.summarize.assert_called_once()
        mock_repo.set_summary.assert_called_once_with("user1", "tóm tắt mới")
        mock_repo.mark_summarized.assert_called_once_with(["m1", "m2"])

    def test_compress_count_excludes_recent_turns(self, service, mock_repo, mock_llm):
        """Chỉ nén (total - RECENT_TURNS) turn CŨ NHẤT, giữ lại RECENT_TURNS
        gần nhất — đúng mục đích 'AI trả lời liền mạch' bạn vừa xác nhận."""
        total = settings.SUMMARIZE_THRESHOLD + 10
        mock_repo.count_unsummarized.return_value = total
        mock_repo.get_oldest_unsummarized.return_value = []

        service.maybe_summarize("user1")

        expected_compress_count = total - settings.RECENT_TURNS
        mock_repo.get_oldest_unsummarized.assert_called_once_with("user1", expected_compress_count)

    def test_no_oldest_messages_skips_summarize_call(self, service, mock_repo, mock_llm):
        mock_repo.count_unsummarized.return_value = settings.SUMMARIZE_THRESHOLD + 5
        mock_repo.get_oldest_unsummarized.return_value = []
        service.maybe_summarize("user1")
        mock_llm.summarize.assert_not_called()


class TestBuildContext:
    def test_returns_summary_and_recent_turns(self, service, mock_repo):
        mock_repo.get_summary.return_value = "tóm tắt cũ"
        mock_repo.get_recent_unsummarized.return_value = [{"role": "user", "content": "hi"}]

        summary, recent = service.build_context("user1")

        assert summary == "tóm tắt cũ"
        assert len(recent) == 1
        mock_repo.get_recent_unsummarized.assert_called_once_with("user1", settings.RECENT_TURNS)
