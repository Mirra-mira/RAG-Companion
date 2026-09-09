from app.services.llm_provider import ILLMProvider


class ExtractionService:
    """Mục 3.5.1: trích xuất fact có cấu trúc từ nội dung hội thoại."""

    def __init__(self, llm: ILLMProvider):
        self._llm = llm

    def extract(self, conversation_text: str) -> list[dict]:
        facts = self._llm.extract_facts(conversation_text)
        cleaned = []
        for f in facts:
            content = f.get("content", "").strip().lower()
            category = f.get("category", "misc").strip().lower()
            if content:
                cleaned.append({"category": category, "content": content})
        return cleaned
