"""Unit test cho 4 chien luoc truy hoi (none/keyword/vector/hybrid).

Dung MagicMock de co lap voi DB, embedder, ranker — chi test logic dieu phoi
va mapping ket qua. Chat luong ngu nghia thuc te thuoc Track A (eval harness).
"""
import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.services.retrievers import (
    tokenize, make_retriever,
    NoMemoryRetriever, KeywordRetriever, VectorOnlyRetriever, HybridRetriever,
)


# ------------------------------------------------------- tokenize()
class TestTokenize:
    def test_lowercases_and_splits(self):
        out = tokenize("Phở Bò ngon")
        assert "phở" in out and "bò" in out and "ngon" in out

    def test_removes_stopwords(self):
        out = tokenize("mình thích phở bò")
        assert "mình" not in out and "thích" in out and "phở" in out

    def test_deduplicates(self):
        out = tokenize("phở phở phở bò")
        # Chi giu 1 lan xuat hien dau tien cua moi tu
        assert out.count("phở") == 1
        assert "bò" in out

    def test_ignores_punctuation(self):
        out = tokenize("Phở, bò! ngon?")
        assert set(out) == {"phở", "bò", "ngon"}


# ------------------------------------------------------- NoMemoryRetriever
class TestNoMemoryRetriever:
    def test_returns_empty_list_and_zero_timing(self):
        r = NoMemoryRetriever()
        results, timings = r.retrieve_timed(uuid4(), "bat ky cau hoi gi")
        assert results == []
        assert "total" in timings
        assert timings["total"] == 0.0


# ------------------------------------------------------- KeywordRetriever
class TestKeywordRetriever:
    def test_calls_repo_with_tokenized_query(self):
        repo = MagicMock()
        repo.find_top_k_by_keyword.return_value = []
        r = KeywordRetriever(repo)

        user_id = uuid4()
        r.retrieve_timed(user_id, "mình thích phở bò", top_k=5)

        repo.find_top_k_by_keyword.assert_called_once()
        args, kwargs = repo.find_top_k_by_keyword.call_args
        # Chu ky: (user_id, tokens, k=..., only_active=...)
        assert args[0] == user_id
        tokens = args[1]
        assert "mình" not in tokens         # stopword bi bo
        assert "phở" in tokens and "bò" in tokens
        assert kwargs.get("k") == 5
        assert kwargs.get("only_active") is True

    def test_maps_rank_to_score_and_zero_similarity(self):
        repo = MagicMock()
        repo.find_top_k_by_keyword.return_value = [
            {"fact_id": "a", "content": "pho bo", "category": "food",
             "weight": 1, "updated_at": datetime.now(timezone.utc), "rank": 0.42},
        ]
        r = KeywordRetriever(repo)
        results, timings = r.retrieve_timed(uuid4(), "pho")

        assert len(results) == 1
        assert results[0]["score"] == pytest.approx(0.42)
        assert results[0]["similarity"] == 0.0
        assert "tokenize" in timings and "keyword_search" in timings


# ------------------------------------------------------- VectorOnlyRetriever
class TestVectorOnlyRetriever:
    def test_calls_embed_then_search(self):
        repo = MagicMock()
        embedder = MagicMock()
        embedder.embed.return_value = [0.1] * 768
        repo.find_top_k_by_embedding.return_value = [
            {"fact_id": "x", "content": "y", "category": "c", "weight": 1,
             "updated_at": datetime.now(timezone.utc), "similarity": 0.9},
        ]
        r = VectorOnlyRetriever(repo, embedder)

        user_id = uuid4()
        results, timings = r.retrieve_timed(user_id, "cau hoi")

        embedder.embed.assert_called_once_with("cau hoi")
        repo.find_top_k_by_embedding.assert_called_once()
        assert results[0]["score"] == pytest.approx(0.9)
        assert "embed" in timings and "ann_search" in timings

    def test_filters_by_min_similarity(self, monkeypatch):
        from app.services import retrievers as mod
        monkeypatch.setattr(mod.settings, "MIN_SIMILARITY", 0.5, raising=False)

        repo = MagicMock()
        embedder = MagicMock()
        embedder.embed.return_value = [0.1] * 768
        repo.find_top_k_by_embedding.return_value = [
            {"fact_id": "hi", "content": "a", "category": "c", "weight": 1,
             "updated_at": datetime.now(timezone.utc), "similarity": 0.8},
            {"fact_id": "lo", "content": "b", "category": "c", "weight": 1,
             "updated_at": datetime.now(timezone.utc), "similarity": 0.3},
        ]
        r = VectorOnlyRetriever(repo, embedder)
        results, _ = r.retrieve_timed(uuid4(), "q")

        # Chi fact >= 0.5 duoc giu lai
        assert [r["fact_id"] for r in results] == ["hi"]


# ------------------------------------------------------- HybridRetriever
class TestHybridRetriever:
    def test_pipeline_embed_search_rank(self):
        repo = MagicMock()
        embedder = MagicMock()
        ranker = MagicMock()
        embedder.embed.return_value = [0.1] * 768
        candidates = [
            {"fact_id": "a", "content": "x", "category": "c", "weight": 1,
             "updated_at": datetime.now(timezone.utc), "similarity": 0.9},
        ]
        ranked = [{**candidates[0], "score": 0.85}]
        repo.find_top_k_by_embedding.return_value = candidates
        ranker.rank.return_value = ranked

        r = HybridRetriever(repo, embedder, ranker)
        results, timings = r.retrieve_timed(uuid4(), "query")

        # Dung trinh tu: embed -> ANN -> rank
        embedder.embed.assert_called_once()
        repo.find_top_k_by_embedding.assert_called_once()
        ranker.rank.assert_called_once()
        assert results == ranked
        assert "embed" in timings and "ann_search" in timings and "rank" in timings


# ------------------------------------------------------- Factory
class TestMakeRetriever:
    def test_returns_correct_type_per_kind(self):
        repo, emb, rnk = MagicMock(), MagicMock(), MagicMock()
        assert isinstance(make_retriever("none",    repo, emb, rnk), NoMemoryRetriever)
        assert isinstance(make_retriever("keyword", repo, emb, rnk), KeywordRetriever)
        assert isinstance(make_retriever("vector",  repo, emb, rnk), VectorOnlyRetriever)
        assert isinstance(make_retriever("hybrid",  repo, emb, rnk), HybridRetriever)

    def test_case_insensitive(self):
        assert isinstance(
            make_retriever("HYBRID", MagicMock(), MagicMock(), MagicMock()),
            HybridRetriever,
        )

    def test_raises_on_invalid_kind(self):
        with pytest.raises(ValueError):
            make_retriever("bm25", MagicMock(), MagicMock(), MagicMock())
