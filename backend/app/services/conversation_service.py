"""Service quan ly bo nho ngan han cua hoi thoai:
  - luu tung turn (user + assistant) vao conversations
  - build context de nhet vao prompt LLM (summary + N turn gan nhat)
  - khi so turn chua summarized vuot nguong, nen cac turn cu vao
    users.conversation_summary de tranh prompt bi phinh vo han.
"""
from uuid import UUID
from app.repositories.conversation_repository import IConversationRepository
from app.services.llm_provider import ILLMProvider
from app.core.config import settings


class ConversationService:
    def __init__(self, repo: IConversationRepository, llm: ILLMProvider):
        self._repo = repo
        self._llm = llm

    def append(self, user_id: UUID, role: str, content: str) -> dict:
        return self._repo.append_message(user_id, role, content)

    def build_context(self, user_id: UUID) -> tuple[str, list[dict]]:
        """Tra ve (summary, recent_turns) de dua vao prompt LLM."""
        summary = self._repo.get_summary(user_id)
        recent = self._repo.get_recent_unsummarized(user_id, settings.RECENT_TURNS)
        return summary, recent

    def list_history(self, user_id: UUID, limit: int = 200) -> list[dict]:
        """Dung cho frontend hien thi lich su."""
        return self._repo.get_all_messages(user_id, limit)

    def maybe_summarize(self, user_id: UUID) -> None:
        """Neu so turn chua summarized > SUMMARIZE_THRESHOLD, nen cac turn cu
        (giu lai RECENT_TURNS gan nhat) vao summary. Chay o background task.
        """
        total = self._repo.count_unsummarized(user_id)
        if total <= settings.SUMMARIZE_THRESHOLD:
            return

        to_compress_count = total - settings.RECENT_TURNS
        if to_compress_count <= 0:
            return

        oldest = self._repo.get_oldest_unsummarized(user_id, to_compress_count)
        if not oldest:
            return

        prev_summary = self._repo.get_summary(user_id)
        turns_payload = [{"role": m["role"], "content": m["content"]} for m in oldest]
        new_summary = self._llm.summarize(prev_summary, turns_payload)

        self._repo.set_summary(user_id, new_summary)
        self._repo.mark_summarized([m["msg_id"] for m in oldest])
        print(
            f"[summarize] user={user_id} compressed={len(oldest)} "
            f"new_summary_len={len(new_summary)}"
        )
