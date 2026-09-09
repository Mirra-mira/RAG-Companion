from abc import ABC, abstractmethod
import hashlib
import re
from app.core.config import settings


class IEmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]: ...


class GeminiEmbeddingProvider(IEmbeddingProvider):
    """Bản thật — dùng model embedding của Gemini (đúng mục 2.4 khóa luận)."""

    def __init__(self):
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._genai = genai

    def embed(self, text: str) -> list[float]:
        # gemini-embedding-001 la model embedding stable hien tai cua Google
        # (text-embedding-004 da bi go). Model nay tra ve 3072 dims mac dinh,
        # nen set output_dimensionality=768 de khop schema VECTOR(768).
        result = self._genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            output_dimensionality=settings.EMBEDDING_DIM,
        )
        return result["embedding"]


class MockEmbeddingProvider(IEmbeddingProvider):
    """Bản giả lập — KHÔNG hiểu ngữ nghĩa thật, chỉ băm chuỗi đã chuẩn hóa
    (lowercase, bỏ khoảng trắng thừa) thành vector giả định.

    Dùng để test luồng (routing, dedup logic, ranking) khi chưa có API key.
    Hệ quả: chỉ phát hiện đúng REINFORCE khi 2 câu giống nhau sau chuẩn hóa
    (ví dụ "phở" và "Phở"), KHÔNG phát hiện được tương đồng ngữ nghĩa thật
    (ví dụ "phở" và "phở bò") — muốn test đầy đủ như Chương 4 mô tả, cần
    GEMINI_API_KEY thật.
    """

    def __init__(self, dim: int = 768):
        self.dim = dim

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text.strip().lower())

    def embed(self, text: str) -> list[float]:
        norm = self._normalize(text)
        vec = []
        seed = norm.encode("utf-8")
        for i in range(self.dim):
            h = hashlib.sha256(seed + i.to_bytes(4, "little")).digest()
            val = int.from_bytes(h[:4], "little") / 2**32  # [0,1)
            vec.append(val * 2 - 1)  # [-1,1)
        # chuẩn hóa về vector đơn vị để cosine similarity có ý nghĩa
        norm_val = sum(v * v for v in vec) ** 0.5
        return [v / norm_val for v in vec]


def get_embedding_provider() -> IEmbeddingProvider:
    if settings.USE_MOCK_LLM:
        return MockEmbeddingProvider(dim=settings.EMBEDDING_DIM)
    return GeminiEmbeddingProvider()
