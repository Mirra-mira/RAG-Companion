import math
from datetime import datetime, timezone
from app.core.config import settings


class RankingService:
    """Mục 3.6: score = alpha*similarity + beta*weight_norm + gamma*recency_decay"""

    def __init__(self, alpha=None, beta=None, gamma=None,
                 half_life_days=None):
        self.alpha = alpha if alpha is not None else settings.ALPHA
        self.beta = beta if beta is not None else settings.BETA
        self.gamma = gamma if gamma is not None else settings.GAMMA
        self.half_life_days = half_life_days or settings.RECENCY_HALF_LIFE_DAYS

    def _recency_decay(self, updated_at) -> float:
        # Naive datetime: coi là local time (đúng convention của datetime.now()),
        # convert sang UTC để so sánh nhất quán. Trước đây .replace(tzinfo=utc)
        # gán nhầm timezone khiến máy non-UTC ra age_days âm -> recency > 1.
        if updated_at.tzinfo is None:
            updated_at = updated_at.astimezone(timezone.utc)
        # Clamp age >= 0 phòng lệch đồng hồ hoặc dữ liệu "tương lai" bất thường.
        age_days = max(0.0, (datetime.now(timezone.utc) - updated_at).total_seconds() / 86400)
        return 0.5 ** (age_days / self.half_life_days)

    def rank(self, candidates: list[dict], top_k: int) -> list[dict]:
        if not candidates:
            return []
        max_w = max(c["weight"] for c in candidates) or 1
        scored = []
        for c in candidates:
            weight_norm = c["weight"] / max_w
            recency = self._recency_decay(c["updated_at"])
            score = (self.alpha * c["similarity"]
                     + self.beta * weight_norm
                     + self.gamma * recency)
            scored.append({**c, "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


class RetrievalService:
    """Mục 3.6: lấy top-N ứng viên bằng ANN rồi giao cho RankingService xếp hạng lại."""

    def __init__(self, repo, embedder, ranker: RankingService):
        self._repo = repo
        self._embedder = embedder
        self._ranker = ranker

    def retrieve(self, user_id, query: str, top_n=None, top_k=None) -> list[dict]:
        top_n = top_n or settings.RANK_TOP_N
        top_k = top_k or settings.RANK_TOP_K
        embedding = self._embedder.embed(query)
        candidates = self._repo.find_top_k_by_embedding(
            user_id, embedding, k=top_n, only_active=True
        )
        return self._ranker.rank(candidates, top_k=top_k)
