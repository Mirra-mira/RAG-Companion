from abc import ABC, abstractmethod
import json
import re
from app.core.config import settings


class ILLMProvider(ABC):
    @abstractmethod
    def extract_facts(self, conversation_text: str) -> list[dict]:
        """Trả về list [{"category": str, "content": str}, ...]"""

    @abstractmethod
    def classify_relationship(self, new_fact: dict, candidates: list[dict]) -> dict:
        """Trả về {"decision": "ADD|REINFORCE|CONFLICT|NOOP", "target_fact_id": str|None}"""

    @abstractmethod
    def generate_response(
        self,
        query: str,
        context_facts: list[dict],
        summary: str = "",
        recent_turns: list[dict] = None,
    ) -> str:
        """Sinh phản hồi hội thoại (kiến trúc RAG, mục 2.5).

        Args:
            query: câu hiện tại của user.
            context_facts: các fact dài hạn liên quan (từ RetrievalService).
            summary: tóm tắt các đoạn hội thoại cũ đã bị nén.
            recent_turns: các turn gần nhất (chưa summarized), thứ tự
                cũ → mới. Mỗi turn: {role, content}.
        """

    @abstractmethod
    def summarize(self, prev_summary: str, turns: list[dict]) -> str:
        """Nén các turn cũ vào 1 tóm tắt duy nhất. Nếu đã có prev_summary,
        merge chung. Trả về summary mới."""


class GeminiLLMProvider(ILLMProvider):
    """Bản thật — gọi Gemini (đúng công nghệ đang dùng ở Yuhara / mục 2.4)."""

    def __init__(self):
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # gemini-2.5-flash: model flash stable hien tai (gemini-1.5-flash da bi go).
        self._model = genai.GenerativeModel("gemini-2.5-flash")

    def extract_facts(self, conversation_text: str) -> list[dict]:
        prompt = f"""Trích xuất thông tin cá nhân (sở thích, đặc điểm) từ đoạn hội thoại sau
thành JSON dạng [{{"category": "...", "content": "..."}}]. Nếu không có gì
đáng lưu, trả về [].

Hội thoại: "{conversation_text}"

Chỉ trả JSON, không giải thích thêm."""
        resp = self._model.generate_content(prompt)
        return _safe_json_list(resp.text)

    def classify_relationship(self, new_fact: dict, candidates: list[dict]) -> dict:
        cand_text = "\n".join(
            f'- id={c["fact_id"]}: "{c["content"]}" (category={c["category"]})'
            for c in candidates
        )
        prompt = f"""Fact mới: "{new_fact['content']}" (category={new_fact['category']})

Các fact đã lưu gần nghĩa nhất:
{cand_text}

Xác định quan hệ giữa fact mới và các fact đã lưu, trả về đúng 1 JSON:
{{"decision": "ADD|REINFORCE|CONFLICT|NOOP", "target_fact_id": "<id hoặc null>"}}

- REINFORCE: fact mới trùng ý nghĩa với 1 fact đã lưu (dù khác chữ viết)
- CONFLICT: fact mới mâu thuẫn với 1 fact đã lưu (VD: sở thích đã đổi ngược lại)
- ADD: fact mới, không liên quan đủ mạnh đến fact nào đã lưu
- NOOP: fact không đủ giá trị để lưu

Chỉ trả JSON."""
        resp = self._model.generate_content(prompt)
        return _safe_json_obj(resp.text)

    def generate_response(
        self,
        query: str,
        context_facts: list[dict],
        summary: str = "",
        recent_turns: list[dict] = None,
    ) -> str:
        recent_turns = recent_turns or []
        facts_block = "\n".join(f'- {f["content"]}' for f in context_facts) or "(không có)"
        summary_block = summary.strip() or "(chưa có)"
        # Recent turns: format role: content de LLM hieu day la history
        history_block = (
            "\n".join(f'{t["role"]}: {t["content"]}' for t in recent_turns)
            or "(chưa có)"
        )
        prompt = f"""Bạn là trợ lý ảo, trò chuyện tự nhiên với người dùng.

--- Các thông tin dài hạn đã biết về người dùng ---
{facts_block}

--- Tóm tắt các đoạn hội thoại trước đó ---
{summary_block}

--- Các lượt gần đây ---
{history_block}

--- Lượt hiện tại của người dùng ---
{query}

Trả lời tự nhiên, có tính đến ngữ cảnh phía trên. Không lặp lại tóm tắt."""
        resp = self._model.generate_content(prompt)
        return resp.text.strip()

    def summarize(self, prev_summary: str, turns: list[dict]) -> str:
        # Neu khong co gi de nen, giu nguyen summary cu.
        if not turns:
            return prev_summary
        turns_block = "\n".join(f'{t["role"]}: {t["content"]}' for t in turns)
        prev_block = prev_summary.strip() or "(chưa có tóm tắt trước đó)"
        prompt = f"""Bạn là trợ lý tóm tắt hội thoại.

--- Tóm tắt cũ (nếu có) ---
{prev_block}

--- Các lượt hội thoại mới cần nén vào tóm tắt ---
{turns_block}

Yêu cầu:
- Viết 1 đoạn tóm tắt duy nhất (không quá 200 từ) bao gồm cả tóm tắt cũ và các lượt mới.
- Giữ các thông tin quan trọng: chủ đề, cảm xúc, tên riêng, quyết định.
- Không bịa thông tin ngoài hội thoại.
- Chỉ trả về đoạn tóm tắt, không giải thích thêm."""
        resp = self._model.generate_content(prompt)
        return resp.text.strip()


class MockLLMProvider(ILLMProvider):
    """Bản giả lập — dùng luật heuristic đơn giản (KHÔNG phải NLU thật) để
    có thể test luồng ADD/REINFORCE/CONFLICT/NOOP mà không cần gọi API.

    GIỚI HẠN QUAN TRỌNG cần hiểu trước khi dùng: vì MockEmbeddingProvider chỉ
    băm chuỗi (không hiểu ngữ nghĩa), DedupService chỉ tìm ra candidate đúng
    khi phần "đối tượng" (object) trong content GIỐNG HỆT nhau sau chuẩn hóa
    (ví dụ "pho" trong cả 2 câu). Vì vậy Mock này giữ nguyên phần object cho
    cả câu thích/hết thích (để embedding tìm đúng candidate), và dùng một cờ
    nội bộ (_last_is_dislike) — KHÔNG phải cách LLM thật hoạt động — để
    phân biệt REINFORCE và CONFLICT. Đây là simplification chỉ để test luồng,
    không phải test độ chính xác NLU thật (muốn vậy cần GEMINI_API_KEY thật).
    """

    _DISLIKE_PATTERNS = [r"h[ếêe]t th[íi]ch (.+)", r"gh[éẻe]t (.+)", r"ch[áae]n (.+)"]
    _LIKE_PATTERNS = [r"th[íi]ch (.+)", r"m[êếe] (.+)", r"y[êêe]u (.+)"]

    _FILLER_SUFFIX = re.compile(
        r"\s*(l[ắa]m|qu[áa]|th[ậa]t|r[ồo]i|nh[ỉi]|[đd][ấa]y|nh[ ée]|\.|!|\?)+\s*$"
    )

    def __init__(self):
        self._last_is_dislike = False

    def _clean(self, raw: str) -> str:
        content = raw.strip(" .!?")
        prev = None
        while prev != content:
            prev = content
            content = self._FILLER_SUFFIX.sub("", content).strip()
        return content

    def extract_facts(self, conversation_text: str) -> list[dict]:
        text = conversation_text.strip().lower()

        for pat in self._DISLIKE_PATTERNS:
            m = re.search(pat, text)
            if m:
                content = self._clean(m.group(1))
                if content:
                    self._last_is_dislike = True
                    return [{"category": "preference", "content": content}]

        for pat in self._LIKE_PATTERNS:
            m = re.search(pat, text)
            if m:
                content = self._clean(m.group(1))
                if content:
                    self._last_is_dislike = False
                    return [{"category": "preference", "content": content}]

        return []  # không khớp mẫu nào -> không đủ giá trị lưu

    def classify_relationship(self, new_fact: dict, candidates: list[dict]) -> dict:
        is_dislike, self._last_is_dislike = self._last_is_dislike, False
        if not candidates:
            return {"decision": "ADD", "target_fact_id": None}
        best = candidates[0]
        if best["similarity"] > 0.97:
            if is_dislike:
                return {"decision": "CONFLICT", "target_fact_id": str(best["fact_id"])}
            return {"decision": "REINFORCE", "target_fact_id": str(best["fact_id"])}
        return {"decision": "ADD", "target_fact_id": None}

    def generate_response(
        self,
        query: str,
        context_facts: list[dict],
        summary: str = "",
        recent_turns: list[dict] = None,
    ) -> str:
        recent_turns = recent_turns or []
        parts = []
        if summary:
            parts.append(f"[tóm tắt: {summary[:60]}]")
        if recent_turns:
            parts.append(f"[{len(recent_turns)} lượt gần đây]")
        if context_facts:
            names = ", ".join(f'"{f["content"]}"' for f in context_facts[:3])
            parts.append(f"[facts: {names}]")
        prefix = " ".join(parts) if parts else "[MOCK]"
        return f"{prefix} Bạn hỏi: {query}"

    def summarize(self, prev_summary: str, turns: list[dict]) -> str:
        # Mock: noi ngan summary cu + tom luoc turn moi. KHONG phai NLU that.
        if not turns:
            return prev_summary
        turn_snippets = [f'{t["role"]}: {t["content"][:40]}' for t in turns]
        joined = " | ".join(turn_snippets)
        base = prev_summary.strip()
        if base:
            return f"{base} | {joined}"
        return joined


def _safe_json_list(text: str) -> list[dict]:
    text = re.sub(r"```json|```", "", text).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _safe_json_obj(text: str) -> dict:
    text = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"decision": "NOOP", "target_fact_id": None}


def get_llm_provider() -> ILLMProvider:
    if settings.USE_MOCK_LLM:
        return MockLLMProvider()
    return GeminiLLMProvider()
