from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID


class FactOut(BaseModel):
    fact_id: UUID
    user_id: UUID
    category: str
    content: str
    weight: int
    status: str
    created_at: datetime
    updated_at: datetime


class FactSearchResult(BaseModel):
    fact_id: UUID
    content: str
    category: str
    similarity: float
    weight: int
    score: float


class FactCreateRequest(BaseModel):
    category: str
    content: str


class ChatRequest(BaseModel):
    user_id: UUID
    message: str


class ChatResponse(BaseModel):
    response: str
    retrieved_facts: list[FactSearchResult] = []
