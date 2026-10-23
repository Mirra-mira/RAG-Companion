"""Baseline cho phan GHI: luu moi fact vao DB, KHONG dedup (khong REINFORCE/CONFLICT).

Dung de ablation: bo thanh phan dedup ra khoi he thong de do dong gop cua no.
Cung signature voi DedupService.process() nen thay the truc tiep duoc.
"""
from uuid import UUID
from app.core.timing import StageTimer


class NoDedupService:
    def __init__(self, repo, embedder, llm=None):
        self._repo = repo
        self._embedder = embedder

    def process(self, user_id: UUID, category: str, content: str) -> dict:
        t = StageTimer()
        with t.stage("embed"):
            embedding = self._embedder.embed(content)
        with t.stage("db_write"):
            inserted = self._repo.insert(user_id, category, content, embedding, weight=1)
        return {"action": "ADD", "fact": inserted, "timings": t.done()}
