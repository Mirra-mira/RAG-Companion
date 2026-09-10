"""Test các ca khó đã phân tích trong quá trình thiết kế (Chương 1: bẫy tên
riêng, đảo chủ-tân ngữ, "phở" vs "phở bò"). Với MockLLMProvider (regex đơn
giản), các ca này ĐƯỢC KỲ VỌNG THẤT BẠI — dùng xfail để biến giới hạn đã biết
thành bằng chứng kiểm thử tường minh, thay vì chỉ mô tả suông trong văn bản.
Muốn các test này pass thật, cần thay bằng GeminiLLMProvider (xem test
integration/test_real_gemini.py, yêu cầu GEMINI_API_KEY).
"""
import pytest
from app.services.llm_provider import MockLLMProvider


@pytest.fixture
def mock():
    return MockLLMProvider()


class TestKnownLimitations:
    @pytest.mark.xfail(reason="Mock dùng regex string-match, không phân biệt "
                               "được 'phở' (món ăn) và 'Phở' (tên người) — "
                               "cần LLM thật để hiểu ngữ cảnh.")
    def test_named_entity_trap_person_vs_food(self, mock):
        food = mock.extract_facts("tao thich pho")
        person = mock.extract_facts("tao moi quen mot dua ten Pho")
        # Kỳ vọng ĐÚNG: 2 fact này phải được coi là khác loại (category khác),
        # không chỉ khác nội dung — nhưng mock hiện không phân loại được điều này.
        assert food[0]["category"] != person[0].get("category", "preference")

    @pytest.mark.xfail(reason="Mock không phân biệt được 'phở bò' là biến "
                               "thể chi tiết hơn của 'phở', không phải fact "
                               "khác — cần LLM thật để REINFORCE đúng.")
    def test_pho_bo_should_reinforce_pho_not_add_new(self, mock):
        base = mock.extract_facts("tao thich pho")
        detailed = mock.extract_facts("tao thich pho bo")
        # Kỳ vọng ĐÚNG (theo thiết kế mục 3.5.2): 2 câu này nên cùng 1 "đối
        # tượng" phở để bước vector search sau đó có cơ hội tìm thấy nhau.
        assert base[0]["content"] == detailed[0]["content"]

    def test_subject_object_reversal_produces_nonsensical_content(self, mock):
        """Phát hiện thực tế khi viết test (khác giả thuyết ban đầu): vì regex
        chỉ bắt phần văn bản SAU động từ, 2 câu đảo chủ-tân ngữ tình cờ cho
        ra content KHÁC NHAU ('meo' vs 'tao') — không bị gộp nhầm như dự đoán.
        Nhưng vấn đề thật lại nằm ở chỗ khác: khi chủ ngữ câu không phải người
        dùng (mèo yêu tao), phần bắt được lại là đại từ chỉ chính người dùng
        ("tao") — một nội dung fact vô nghĩa nếu hiểu theo nghĩa "sở thích".
        Mock không có cơ chế phát hiện việc này; cần LLM thật hiểu vai trò
        ngữ pháp (ai là chủ thể của tình cảm) để xử lý đúng.
        """
        passive = mock.extract_facts("meo yeu tao")
        assert passive[0]["content"] == "tao"  # nội dung vô nghĩa nhưng mock vẫn lưu bình thường
