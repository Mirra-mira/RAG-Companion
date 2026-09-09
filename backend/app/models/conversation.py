from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class MessageOut(BaseModel):
    """1 turn hoi thoai (do frontend hien thi khi tai lich su)."""
    msg_id: UUID
    role: str        # 'user' | 'assistant'
    content: str
    created_at: datetime
