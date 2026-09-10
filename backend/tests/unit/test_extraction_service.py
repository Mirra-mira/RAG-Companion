"""Unit test cho ExtractionService (mục 3.5.1) và MockLLMProvider.
Bao gồm chính các ca đã phân tích thủ công trong quá trình thiết kế:
đồng nghĩa/viết hoa khác, trái nghĩa, từ đệm — xem lại phần thảo luận
Chương 1 (ví dụ "phở"/"Phở"/"phở bò"/"hết thích phở").
"""
import pytest
from unittest.mock import MagicMock
from app.services.extraction_service import ExtractionService
from app.services.llm_provider import MockLLMProvider


@pytest.fixture
def mock_llm():
    return MagicMock()


@pytest.fixture
def service(mock_llm):
    return ExtractionService(mock_llm)


class TestExtractionServiceCleaning:
    def test_lowercases_and_strips_content(self, service, mock_llm):
        mock_llm.extract_facts.return_value = [{"category": "Food", "content": "  Phở Bò  "}]
        result = service.extract("tao thích phở bò")
        assert result == [{"category": "food", "content": "phở bò"}]

    def test_drops_facts_with_empty_content(self, service, mock_llm):
        mock_llm.extract_facts.return_value = [{"category": "food", "content": "   "}]
        assert service.extract("...") == []

    def test_defaults_missing_category_to_misc(self, service, mock_llm):
        mock_llm.extract_facts.return_value = [{"content": "pho"}]
        result = service.extract("x")
        assert result[0]["category"] == "misc"

    def test_empty_llm_output_returns_empty_list(self, service, mock_llm):
        mock_llm.extract_facts.return_value = []
        assert service.extract("hôm nay trời đẹp") == []


class TestMockLLMProviderExtraction:
    """Đúng các ca đã bàn trong quá trình phân tích thiết kế — mock CHỈ nhận
    diện được các mẫu câu định nghĩa sẵn, không phải NLU thật."""

    @pytest.fixture
    def mock(self):
        return MockLLMProvider()

    def test_extracts_like_pattern(self, mock):
        result = mock.extract_facts("tao thich pho lam")
        assert result == [{"category": "preference", "content": "pho"}]

    def test_strips_filler_suffix_lam(self, mock):
        """'lắm' phải bị cắt để 'thích phở lắm' và 'thích phở' cho cùng content"""
        result = mock.extract_facts("tao thich pho")
        assert result[0]["content"] == "pho"

    def test_case_insensitive_extraction(self, mock):
        """'Thich Pho' (viết hoa) phải cho ra content GIỐNG HỆT 'thich pho'
        thường — điều kiện tiên quyết để REINFORCE nhận diện đúng."""
        r1 = mock.extract_facts("Thich Pho")
        r2 = mock.extract_facts("thich pho")
        assert r1[0]["content"] == r2[0]["content"] == "pho"

    def test_dislike_pattern_sets_internal_flag(self, mock):
        mock.extract_facts("tao het thich pho roi")
        assert mock._last_is_dislike is True

    def test_like_pattern_resets_dislike_flag(self, mock):
        mock.extract_facts("tao het thich pho roi")
        mock.extract_facts("tao thich bun bo")
        assert mock._last_is_dislike is False

    def test_no_pattern_match_returns_empty(self, mock):
        """Câu không khớp mẫu nào (kịch bản NOOP) phải trả về [] """
        assert mock.extract_facts("hom nay troi hoi nong nhi") == []

    @pytest.mark.parametrize("sentence,expected", [
        ("tao thich pho lam", "pho"),
        ("tao thich pho qua", "pho"),
        ("tao thich pho that", "pho"),
        ("tao thich pho roi", "pho"),
    ])
    def test_various_filler_words_all_stripped(self, mock, sentence, expected):
        result = mock.extract_facts(sentence)
        assert result[0]["content"] == expected
