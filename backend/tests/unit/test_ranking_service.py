"""Unit test cho RankingService (mục 3.6).
Không cần DB thật — chỉ test logic tính toán thuần túy.
"""
import pytest
from datetime import datetime, timedelta, timezone
from app.services.ranking_service import RankingService


@pytest.fixture
def ranker():
    # alpha=0.6, beta=0.25, gamma=0.15, half_life=14 ngày (cố định để test tất định)
    return RankingService(alpha=0.6, beta=0.25, gamma=0.15, half_life_days=14)


def _fact(similarity, weight, days_ago=0, fact_id="f1"):
    return {
        "fact_id": fact_id,
        "content": "x",
        "category": "c",
        "weight": weight,
        "similarity": similarity,
        "updated_at": datetime.now(timezone.utc) - timedelta(days=days_ago),
    }


class TestRecencyDecay:
    def test_recency_decay_at_zero_days_is_one(self, ranker):
        """Fact vừa cập nhật (0 ngày tuổi) phải có recency = 1.0"""
        now = datetime.now(timezone.utc)
        assert ranker._recency_decay(now) == pytest.approx(1.0, abs=1e-6)

    def test_recency_decay_at_half_life_is_half(self, ranker):
        """Đúng nửa chu kỳ half-life (14 ngày) -> recency phải = 0.5"""
        t = datetime.now(timezone.utc) - timedelta(days=14)
        assert ranker._recency_decay(t) == pytest.approx(0.5, rel=1e-3)

    def test_recency_decay_handles_naive_datetime(self, ranker):
        """updated_at không có timezone (naive) vẫn phải xử lý được, không crash"""
        naive_now = datetime.now()
        result = ranker._recency_decay(naive_now)
        assert 0.0 <= result <= 1.0


class TestRankFormula:
    def test_empty_candidates_returns_empty(self, ranker):
        assert ranker.rank([], top_k=5) == []

    def test_score_formula_matches_spec(self, ranker):
        """score = alpha*similarity + beta*weight_norm + gamma*recency
        Dùng 1 candidate duy nhất (weight_norm luôn =1 vì max_w = weight)
        và days_ago=0 (recency=1) để kiểm tra công thức bằng tay."""
        candidates = [_fact(similarity=0.8, weight=3, days_ago=0)]
        result = ranker.rank(candidates, top_k=5)
        expected = 0.6 * 0.8 + 0.25 * 1.0 + 0.15 * 1.0
        assert result[0]["score"] == pytest.approx(expected, rel=1e-3)

    def test_higher_weight_ranks_above_higher_similarity_when_close(self, ranker):
        """Fact có similarity thấp hơn nhưng weight cao hơn nhiều VẪN có thể
        thắng nếu chênh lệch weight đủ lớn — kiểm chứng đúng đây là ranking
        tổng hợp, không phải chỉ sort theo similarity thuần túy."""
        low_sim_high_weight = _fact(similarity=0.70, weight=10, fact_id="A")
        high_sim_low_weight = _fact(similarity=0.75, weight=1, fact_id="B")
        result = ranker.rank([low_sim_high_weight, high_sim_low_weight], top_k=2)
        assert result[0]["fact_id"] == "A"

    def test_top_k_truncation(self, ranker):
        candidates = [_fact(similarity=0.5 + i * 0.01, weight=1, fact_id=str(i)) for i in range(10)]
        result = ranker.rank(candidates, top_k=3)
        assert len(result) == 3

    def test_results_sorted_descending(self, ranker):
        candidates = [
            _fact(similarity=0.5, weight=1, fact_id="low"),
            _fact(similarity=0.9, weight=1, fact_id="high"),
            _fact(similarity=0.7, weight=1, fact_id="mid"),
        ]
        result = ranker.rank(candidates, top_k=3)
        scores = [r["score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_older_fact_ranks_lower_all_else_equal(self, ranker):
        """Cùng similarity, cùng weight — fact mới hơn phải có score cao hơn
        (đúng yêu cầu 'có yếu tố thời gian' trong thiết kế mục 3.5.3)."""
        old = _fact(similarity=0.8, weight=1, days_ago=30, fact_id="old")
        new = _fact(similarity=0.8, weight=1, days_ago=0, fact_id="new")
        result = ranker.rank([old, new], top_k=2)
        assert result[0]["fact_id"] == "new"
