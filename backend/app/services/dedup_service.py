from uuid import UUID
from app.repositories.fact_repository import IFactRepository
from app.services.embedding_provider import IEmbeddingProvider
from app.services.llm_provider import ILLMProvider
from app.core.config import settings
from app.core.timing import StageTimer


class DedupService:
    """Đúng luồng đã thiết kế ở mục 3.5.2 / Hình 3.4 (Activity Diagram):
    vector search top-k (trong phạm vi user_id) -> LLM phân loại quan hệ
    -> ADD / REINFORCE / CONFLICT / NOOP.

    Ket qua co them key "timings" (ms) cho tung giai doan, phuc vu do do tre.
    """

    def __init__(self, repo: IFactRepository, embedder: IEmbeddingProvider, llm: ILLMProvider):
        self._repo = repo
        self._embedder = embedder
        self._llm = llm

    def process(self, user_id: UUID, category: str, content: str) -> dict:
        t = StageTimer()
        with t.stage("embed"):
            embedding = self._embedder.embed(content)
        with t.stage("ann_search"):
            candidates = self._repo.find_top_k_by_embedding(
                user_id, embedding, k=settings.DEDUP_TOP_K, only_active=True
            )

        new_fact = {"category": category, "content": content}
        with t.stage("llm_classify"):
            decision = self._llm.classify_relationship(new_fact, candidates)

        # --- Validate output cua LLM (LLM co the tra sai dinh dang / id bia) ---
        if not isinstance(decision, dict):
            decision = {}
        action = str(decision.get("decision", "NOOP")).upper()
        target_id = decision.get("target_fact_id")
        valid_ids = {str(c["fact_id"]) for c in candidates}
        if action in ("REINFORCE", "CONFLICT") and str(target_id) not in valid_ids:
            # Target khong nam trong candidates -> khong the gop/thay the an toan.
            # Luu nhu fact moi de khong mat thong tin.
            action, target_id = "ADD", None

        with t.stage("db_write"):
            if action == "REINFORCE":
                result = self._repo.reinforce(UUID(str(target_id)))
                out = {"action": "REINFORCE", "fact": result}
            elif action == "CONFLICT":
                self._repo.supersede(UUID(str(target_id)))
                inserted = self._repo.insert(user_id, category, content, embedding, weight=1)
                out = {"action": "CONFLICT", "superseded_id": str(target_id), "fact": inserted}
            elif action == "ADD":
                inserted = self._repo.insert(user_id, category, content, embedding, weight=1)
                out = {"action": "ADD", "fact": inserted}
            else:
                out = {"action": "NOOP", "fact": None}

        out["timings"] = t.done()
        return out