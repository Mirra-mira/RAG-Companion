from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional
from pgvector import Vector


class IFactRepository(ABC):
    """Interface — các Service phụ thuộc vào đây, KHÔNG phụ thuộc trực tiếp
    vào FactRepository cụ thể (Dependency Injection, mục 2.1.1)."""

    @abstractmethod
    def find_by_user_id(self, user_id: UUID) -> list[dict]: ...

    @abstractmethod
    def find_top_k_by_embedding(
        self, user_id: UUID, embedding: list[float], k: int, only_active: bool = True
    ) -> list[dict]: ...

    @abstractmethod
    def insert(self, user_id: UUID, category: str, content: str,
               embedding: list[float], weight: int = 1) -> dict: ...

    @abstractmethod
    def reinforce(self, fact_id: UUID) -> dict: ...

    @abstractmethod
    def supersede(self, fact_id: UUID) -> None: ...

    @abstractmethod
    def update(self, fact_id: UUID, **fields) -> Optional[dict]: ...

    @abstractmethod
    def delete(self, fact_id: UUID) -> None: ...


class FactRepository(IFactRepository):
    """Hiện thực cụ thể dùng PostgreSQL + pgvector (mục 2.4, 3.3)."""

    def __init__(self, get_conn):
        self._get_conn = get_conn

    def find_by_user_id(self, user_id: UUID) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT fact_id, user_id, category, content, weight, status,
                          created_at, updated_at
                   FROM facts WHERE user_id = %s AND status = 'active'
                   ORDER BY updated_at DESC""",
                (user_id,),
            ).fetchall()
            cols = ["fact_id", "user_id", "category", "content", "weight",
                    "status", "created_at", "updated_at"]
            return [dict(zip(cols, r)) for r in rows]

    def find_top_k_by_embedding(self, user_id, embedding, k, only_active=True):
        vec = Vector(embedding)
        status_clause = "AND status = 'active'" if only_active else ""
        with self._get_conn() as conn:
            rows = conn.execute(
                f"""SELECT fact_id, content, category, weight, updated_at,
                           1 - (embedding <=> %s) AS similarity
                    FROM facts
                    WHERE user_id = %s {status_clause}
                    ORDER BY embedding <=> %s
                    LIMIT %s""",
                (vec, user_id, vec, k),
            ).fetchall()
            cols = ["fact_id", "content", "category", "weight", "updated_at", "similarity"]
            return [dict(zip(cols, r)) for r in rows]

    def insert(self, user_id, category, content, embedding, weight=1):
        with self._get_conn() as conn:
            row = conn.execute(
                """INSERT INTO facts (user_id, category, content, embedding, weight)
                   VALUES (%s, %s, %s, %s, %s)
                   RETURNING fact_id, user_id, category, content, weight, status,
                             created_at, updated_at""",
                (user_id, category, content, Vector(embedding), weight),
            ).fetchone()
            conn.commit()
            cols = ["fact_id", "user_id", "category", "content", "weight",
                    "status", "created_at", "updated_at"]
            return dict(zip(cols, row))

    def reinforce(self, fact_id):
        with self._get_conn() as conn:
            row = conn.execute(
                """UPDATE facts SET weight = weight + 1, updated_at = now()
                   WHERE fact_id = %s
                   RETURNING fact_id, content, weight""",
                (fact_id,),
            ).fetchone()
            conn.commit()
            return dict(zip(["fact_id", "content", "weight"], row))

    def supersede(self, fact_id):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE facts SET status = 'superseded', updated_at = now() WHERE fact_id = %s",
                (fact_id,),
            )
            conn.commit()

    def update(self, fact_id, **fields):
        if not fields:
            return None
        set_clause = ", ".join(f"{k} = %s" for k in fields)
        with self._get_conn() as conn:
            row = conn.execute(
                f"""UPDATE facts SET {set_clause}, updated_at = now()
                    WHERE fact_id = %s
                    RETURNING fact_id, user_id, category, content, weight, status,
                              created_at, updated_at""",
                (*fields.values(), fact_id),
            ).fetchone()
            conn.commit()
            if row is None:
                return None
            cols = ["fact_id", "user_id", "category", "content", "weight",
                    "status", "created_at", "updated_at"]
            return dict(zip(cols, row))

    def delete(self, fact_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM facts WHERE fact_id = %s", (fact_id,))
            conn.commit()
