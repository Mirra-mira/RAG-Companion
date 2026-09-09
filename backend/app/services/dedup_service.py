from uuid import UUID
from app.repositories.fact_repository import IFactRepository
from app.services.embedding_provider import IEmbeddingProvider
from app.services.llm_provider import ILLMProvider
from app.core.config import settings


class DedupService:
    """Đúng luồng đã thiết kế ở mục 3.5.2 / Hình 3.4 (Activity Diagram):
    vector search top-k (trong phạm vi user_id) -> LLM phân loại quan hệ
    -> ADD / REINFORCE / CONFLICT / NOOP.
    """

    def __init__(self, repo: IFactRepository, embedder: IEmbeddingProvider, llm: ILLMProvider):
        self._repo = repo
        self._embedder = embedder
        self._llm = llm

    def process(self, user_id: UUID, category: str, content: str) -> dict:
        embedding = self._embedder.embed(content)
        candidates = self._repo.find_top_k_by_embedding(
            user_id, embedding, k=settings.DEDUP_TOP_K, only_active=True
        )

        new_fact = {"category": category, "content": content}
        decision = self._llm.classify_relationship(new_fact, candidates)
        action = decision.get("decision", "NOOP")
        target_id = decision.get("target_fact_id")

        if action == "REINFORCE" and target_id:
            result = self._repo.reinforce(UUID(target_id))
            return {"action": "REINFORCE", "fact": result}

        if action == "CONFLICT" and target_id:
            self._repo.supersede(UUID(target_id))
            inserted = self._repo.insert(user_id, category, content, embedding, weight=1)
            return {"action": "CONFLICT", "superseded_id": target_id, "fact": inserted}

        if action == "ADD":
            inserted = self._repo.insert(user_id, category, content, embedding, weight=1)
            return {"action": "ADD", "fact": inserted}

        return {"action": "NOOP", "fact": None}
