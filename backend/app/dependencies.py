"""Nơi 'tiêm' (inject) implementation cụ thể vào interface — đúng nguyên tắc
Dependency Injection đã trình bày ở mục 2.1.1. Muốn đổi từ Mock sang Gemini
thật, hoặc đổi PostgreSQL sang công nghệ khác, chỉ cần sửa ở file này,
không cần sửa code trong các Service.
"""
from functools import lru_cache
from app.core.db import get_conn
from app.repositories.fact_repository import FactRepository
from app.repositories.conversation_repository import ConversationRepository
from app.services.embedding_provider import get_embedding_provider
from app.services.llm_provider import get_llm_provider
from app.services.extraction_service import ExtractionService
from app.services.dedup_service import DedupService
from app.services.ranking_service import RankingService, RetrievalService
from app.services.conversation_service import ConversationService


@lru_cache
def get_fact_repository():
    return FactRepository(get_conn)


@lru_cache
def get_embedding_provider_dep():
    return get_embedding_provider()


@lru_cache
def get_llm_provider_dep():
    return get_llm_provider()


@lru_cache
def get_ranking_service():
    return RankingService()


@lru_cache
def get_retrieval_service():
    return RetrievalService(
        get_fact_repository(), get_embedding_provider_dep(), get_ranking_service()
    )


@lru_cache
def get_extraction_service():
    return ExtractionService(get_llm_provider_dep())


@lru_cache
def get_dedup_service():
    return DedupService(
        get_fact_repository(), get_embedding_provider_dep(), get_llm_provider_dep()
    )


@lru_cache
def get_conversation_repository():
    return ConversationRepository(get_conn)


@lru_cache
def get_conversation_service():
    return ConversationService(get_conversation_repository(), get_llm_provider_dep())
