from fastapi import APIRouter, Depends, BackgroundTasks
from uuid import UUID
from app.models.fact import ChatRequest, ChatResponse
from app.models.conversation import MessageOut
from app.core.config import settings
from app.core.timing import StageTimer
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
    t = StageTimer()

    # Feature flag cho A/B experiment (muc 4.5): khi ENABLE_MEMORY=false,
    # bo qua toan bo lop bo nho de do chat luong LLM baseline. Phan do thoi
    # gian van hoat dong — chi khac la retrieval = 0 va khong co key
    # retrieval.<stage>.
    if settings.ENABLE_MEMORY:
        # ---- LUỒNG ĐỌC (đồng bộ, real-time) ----
        # 1) Facts dai han lien quan (retriever tu do thoi gian tung giai doan)
        retrieved, ret_ms = retrieval.retrieve_timed(req.user_id, req.message)
        # 2) Bo nho ngan han: summary + N turn gan nhat
        with t.stage("build_context"):
            summary, recent_turns = conversation.build_context(req.user_id)
    else:
        # Baseline: LLM chi thay cau hoi hien tai, khong fact, khong summary,
        # khong recent turns. ret_ms = None de bo buoc tong hop latency ben duoi.
        retrieved, ret_ms = [], None
        summary, recent_turns = "", []

    # 3) LLM tao phan hoi (voi hoac khong voi ngu canh, tuy flag)
    with t.stage("llm_generate"):
        response_text = llm.generate_response(
            req.message, retrieved, summary=summary, recent_turns=recent_turns
        )

    if settings.ENABLE_MEMORY:
        # Luu ca user message va assistant response vao conversations
        # (dong bo — de lich su khong bi rot khi background task loi).
        with t.stage("save_turns"):
            conversation.append(req.user_id, "user", req.message)
            conversation.append(req.user_id, "assistant", response_text)

        # ---- LUỒNG GHI (bất đồng bộ) ----
        background_tasks.add_task(
            _run_write_path, req.user_id, req.message, extraction, dedup, conversation
        )

    # Tong hop latency — luon tra ve hop le o ca hai nhanh.
    # Nhanh ENABLE_MEMORY=False: khong co key retrieval.<stage>, retrieval = 0.
    if ret_ms is not None:
        latency = {f"retrieval.{k}": v for k, v in ret_ms.items() if k != "total"}
        latency["retrieval"] = ret_ms["total"]
    else:
        latency = {"retrieval": 0.0}
    latency.update(t.ms)
    retrieval_total = ret_ms["total"] if ret_ms is not None else 0.0
    latency["end_to_end"] = retrieval_total + sum(t.ms.values())
    latency = {k: round(v, 1) for k, v in latency.items()}

    return ChatResponse(response=response_text, retrieved_facts=retrieved, latency_ms=latency)


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
