import time
from contextlib import contextmanager


class StageTimer:
    """Do thoi gian (ms) tung giai doan cua read/write path.

    Dung chung cho Retriever, DedupService, ChatController va harness danh gia.
    Moi lan goi tao 1 instance moi -> an toan khi FastAPI chay da luong.
    """

    def __init__(self):
        self.ms: dict[str, float] = {}

    @contextmanager
    def stage(self, name: str):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.ms[name] = self.ms.get(name, 0.0) + (time.perf_counter() - t0) * 1000

    def done(self) -> dict[str, float]:
        """Tra ve {stage: ms, ..., 'total': tong}."""
        return {**self.ms, "total": sum(self.ms.values())}
