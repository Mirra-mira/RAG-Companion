"""Cac chien luoc truy hoi (retrieval) — dung de so sanh baseline o Chuong 4.

  none    : khong bo nho dai han (baseline B0)
  keyword : full-text search PostgreSQL, khop tu khoa (baseline B1)
  vector  : ANN theo cosine, KHONG xep hang lai (baseline B2)
  hybrid  : ANN top-N + RankingService (a*sim + b*weight + g*recency) — DE XUAT

Tat ca tra ve list[dict] co du cac key: fact_id, content, category, weight,
updated_at, similarity, score  -> dung duoc truc tiep trong ChatResponse.
Moi retriever co retrieve_timed() de lay thoi gian tung giai doan (thread-safe
vi khong luu state tren instance).
"""
import re
from abc import ABC, abstractmethod
from app.core.config import settings
from app.core.timing import StageTimer

# Stopword tieng Viet toi thieu. Khong dua "thich", "an"... vao — do la tu mang nghia.
_STOPWORDS = {
    "tôi", "mình", "tớ", "tao", "bạn", "là", "và", "có", "không", "của", "thì",
    "mà", "cho", "với", "một", "những", "các", "được", "đã", "đang", "sẽ", "gì",
    "nào", "nhỉ", "nhé", "ạ", "ơi", "hay", "hơn", "rất", "lắm", "quá", "này",
    "đó", "kia", "thế", "sao", "như", "nên", "để", "khi", "ở", "trong", "ra",
    "vào", "cũng", "còn", "lại",
}


def tokenize(text: str) -> list[str]:
    """Tach tu theo khoang trang/dau cau (giu nguyen dau tieng Viet), bo stopword + trung lap."""
    seen, out = set(), []
    for t in re.findall(r"\w+", text.lower()):
        if t in _STOPWORDS or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _apply_min_similarity(cands: list[dict]) -> list[dict]:
    m = settings.MIN_SIMILARITY
    return [c for c in cands if c["similarity"] >= m] if m > 0 else cands


class IRetriever(ABC):
    name = "base"

    @abstractmethod
    def retrieve_timed(self, user_id, query: str, top_k: int | None = None
                       ) -> tuple[list[dict], dict[str, float]]:
        """Tra ve (ket_qua, timings_ms)."""

    def retrieve(self, user_id, query: str, top_k: int | None = None) -> list[dict]:
        return self.retrieve_timed(user_id, query, top_k)[0]


class NoMemoryRetriever(IRetriever):
    name = "none"

    def retrieve_timed(self, user_id, query, top_k=None):
        return [], StageTimer().done()


class KeywordRetriever(IRetriever):
    name = "keyword"

    def __init__(self, repo):
        self._repo = repo

    def retrieve_timed(self, user_id, query, top_k=None):
        top_k = top_k or settings.RANK_TOP_K
        t = StageTimer()
        with t.stage("tokenize"):
            tokens = tokenize(query)
        with t.stage("keyword_search"):
            rows = self._repo.find_top_k_by_keyword(user_id, tokens, k=top_k, only_active=True)
        results = [{**r, "similarity": 0.0, "score": float(r["rank"])} for r in rows]
        return results, t.done()


class VectorOnlyRetriever(IRetriever):
    name = "vector"

    def __init__(self, repo, embedder):
        self._repo = repo
        self._embedder = embedder

    def retrieve_timed(self, user_id, query, top_k=None):
        top_k = top_k or settings.RANK_TOP_K
        t = StageTimer()
        with t.stage("embed"):
            emb = self._embedder.embed(query)
        with t.stage("ann_search"):
            cands = self._repo.find_top_k_by_embedding(user_id, emb, k=top_k, only_active=True)
        cands = _apply_min_similarity(cands)
        return [{**c, "score": c["similarity"]} for c in cands], t.done()


class HybridRetriever(IRetriever):
    """Thay the RetrievalService cu (muc 3.6)."""
    name = "hybrid"

    def __init__(self, repo, embedder, ranker):
        self._repo = repo
        self._embedder = embedder
        self._ranker = ranker

    def retrieve_timed(self, user_id, query, top_k=None, top_n=None):
        top_n = top_n or settings.RANK_TOP_N
        top_k = top_k or settings.RANK_TOP_K
        t = StageTimer()
        with t.stage("embed"):
            emb = self._embedder.embed(query)
        with t.stage("ann_search"):
            cands = self._repo.find_top_k_by_embedding(user_id, emb, k=top_n, only_active=True)
        cands = _apply_min_similarity(cands)
        with t.stage("rank"):
            results = self._ranker.rank(cands, top_k=top_k)
        return results, t.done()


def make_retriever(kind: str, repo, embedder, ranker) -> IRetriever:
    kind = kind.lower()
    if kind == "none":
        return NoMemoryRetriever()
    if kind == "keyword":
        return KeywordRetriever(repo)
    if kind == "vector":
        return VectorOnlyRetriever(repo, embedder)
    if kind == "hybrid":
        return HybridRetriever(repo, embedder, ranker)
    raise ValueError(f"RETRIEVER_MODE khong hop le: {kind!r} (none|keyword|vector|hybrid)")
