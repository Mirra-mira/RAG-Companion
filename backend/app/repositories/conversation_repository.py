"""Repository cho bang conversations + cot conversation_summary tren users.

Tach interface (IConversationRepository) va implementation cu the
(ConversationRepository) — cung nguyen tac Dependency Injection nhu
FactRepository (muc 2.1.1 khoa luan).
"""
from abc import ABC, abstractmethod
from uuid import UUID


class IConversationRepository(ABC):
    @abstractmethod
    def append_message(self, user_id: UUID, role: str, content: str) -> dict:
        """Ghi 1 turn (user hoac assistant). Tra ve dict message vua tao."""

    @abstractmethod
    def get_recent_unsummarized(self, user_id: UUID, limit: int) -> list[dict]:
        """Lay tren <=limit> message chua summarized gan nhat, thu tu tang
        theo created_at (cu → moi) de tien build prompt."""

    @abstractmethod
    def get_all_messages(self, user_id: UUID, limit: int) -> list[dict]:
        """Lay toan bo lich su (bao gom ca da summarized) — phuc vu UI hien thi."""

    @abstractmethod
    def count_unsummarized(self, user_id: UUID) -> int: ...

    @abstractmethod
    def get_oldest_unsummarized(self, user_id: UUID, limit: int) -> list[dict]:
        """Lay <=limit> message chua summarized cu nhat — cac message nay se
        bi nen vao conversation_summary."""

    @abstractmethod
    def mark_summarized(self, msg_ids: list[UUID]) -> None:
        """Danh dau cac message da nen thanh summary."""

    @abstractmethod
    def get_summary(self, user_id: UUID) -> str: ...

    @abstractmethod
    def set_summary(self, user_id: UUID, summary: str) -> None: ...


class ConversationRepository(IConversationRepository):
    _COLS = ["msg_id", "user_id", "role", "content", "summarized", "created_at"]

    def __init__(self, get_conn):
        self._get_conn = get_conn

    def append_message(self, user_id, role, content):
        with self._get_conn() as conn:
            row = conn.execute(
                """INSERT INTO conversations (user_id, role, content)
                   VALUES (%s, %s, %s)
                   RETURNING msg_id, user_id, role, content, summarized, created_at""",
                (user_id, role, content),
            ).fetchone()
            conn.commit()
            return dict(zip(self._COLS, row))

    def get_recent_unsummarized(self, user_id, limit):
        # Lay N moi nhat roi dao lai thu tu de tra ve theo thoi gian tang dan.
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT msg_id, user_id, role, content, summarized, created_at
                   FROM conversations
                   WHERE user_id = %s AND summarized = false
                   ORDER BY created_at DESC
                   LIMIT %s""",
                (user_id, limit),
            ).fetchall()
        rows = list(reversed(rows))
        return [dict(zip(self._COLS, r)) for r in rows]

    def get_all_messages(self, user_id, limit):
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT msg_id, user_id, role, content, summarized, created_at
                   FROM conversations
                   WHERE user_id = %s
                   ORDER BY created_at ASC
                   LIMIT %s""",
                (user_id, limit),
            ).fetchall()
            return [dict(zip(self._COLS, r)) for r in rows]

    def count_unsummarized(self, user_id):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM conversations WHERE user_id = %s AND summarized = false",
                (user_id,),
            ).fetchone()
            return int(row[0])

    def get_oldest_unsummarized(self, user_id, limit):
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT msg_id, user_id, role, content, summarized, created_at
                   FROM conversations
                   WHERE user_id = %s AND summarized = false
                   ORDER BY created_at ASC
                   LIMIT %s""",
                (user_id, limit),
            ).fetchall()
            return [dict(zip(self._COLS, r)) for r in rows]

    def mark_summarized(self, msg_ids):
        if not msg_ids:
            return
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE conversations SET summarized = true WHERE msg_id = ANY(%s)",
                (msg_ids,),
            )
            conn.commit()

    def get_summary(self, user_id):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT conversation_summary FROM users WHERE user_id = %s",
                (user_id,),
            ).fetchone()
            return row[0] if row else ""

    def set_summary(self, user_id, summary):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE users SET conversation_summary = %s WHERE user_id = %s",
                (summary, user_id),
            )
            conn.commit()
