from fastapi import APIRouter, Depends, BackgroundTasks
from uuid import UUID
from app.models.fact import ChatRequest, ChatResponse
from app.models.conversation import MessageOut
from app.core.config import settings
from app.dependencies import (
    get_retrieval_service, get_llm_provider_dep,
    get_extraction_service, get_dedup_service,
    get_conversation_service,
)

router = APIRouter()


def _run_write_path(user_id, message, extraction, dedup, conversation):
    """Luồng ghi — chạy NỀN sau khi đã trả response cho người dùng (mục 3.2).

    Gồm 2 việc:
      (1) Trích xuất fact + dedup (long-term memory).
      (2) Kích hoạt tóm tắt hội thoại nếu số turn chưa summarized vượt ngưỡng.
    """
    facts = extraction.extract(message)
    results = []
    for f in facts:
        outcome = dedup.process(user_id, f["category"], f["content"])
        results.append(outcome)
    print(f"[write-path] user={user_id} extracted={facts} outcomes={results}")

    # Tom tat hoi thoai (neu can) — chay sau vi khong can real-time.
    conversation.maybe_summarize(user_id)


@router.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    background_tasks: BackgroundTasks,
    retrieval=Depends(get_retrieval_service),
    llm=Depends(get_llm_provider_dep),
    extraction=Depends(get_extraction_service),
    dedup=Depends(get_dedup_service),
    conversation=Depends(get_conversation_service),
):
    # Feature flag cho A/B experiment (muc 4.5): khi ENABLE_MEMORY=false,
    # bo qua toan bo lop bo nho de do chat luong LLM baseline.
    if settings.ENABLE_MEMORY:
        # ---- LUỒNG ĐỌC (đồng bộ, real-time) ----
        # 1) Facts dai han lien quan
        retrieved = retrieval.retrieve(req.user_id, req.message)
        # 2) Bo nho ngan han: summary + N turn gan nhat
        summary, recent_turns = conversation.build_context(req.user_id)
    else:
        retrieved, summary, recent_turns = [], "", []

    # 3) LLM tao phan hoi (voi hoac khong voi ngu canh, tuy flag)
    response_text = llm.generate_response(
        req.message, retrieved, summary=summary, recent_turns=recent_turns
    )

    if settings.ENABLE_MEMORY:
        # Luu ca user message va assistant response vao conversations
        # (dong bo — de lich su khong bi rot khi background task loi).
        conversation.append(req.user_id, "user", req.message)
        conversation.append(req.user_id, "assistant", response_text)

        # ---- LUỒNG GHI (bất đồng bộ) ----
        background_tasks.add_task(
            _run_write_path, req.user_id, req.message, extraction, dedup, conversation
        )

    return ChatResponse(response=response_text, retrieved_facts=retrieved)


@router.get("/users/{user_id}/messages", response_model=list[MessageOut])
def list_messages(
    user_id: UUID,
    limit: int = 200,
    conversation=Depends(get_conversation_service),
):
    """Lich su hoi thoai cua 1 user — de frontend dong bo giua cac profile."""
    rows = conversation.list_history(user_id, limit=limit)
    return [
        MessageOut(
            msg_id=r["msg_id"],
            role=r["role"],
            content=r["content"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
