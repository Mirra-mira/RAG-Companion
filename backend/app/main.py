from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.controllers import fact_controller, chat_controller, dev_controller
from app.core.config import settings

app = FastAPI(title="KLTN - Hệ thống bộ nhớ dài hạn cho trợ lý ảo hội thoại")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo local — production nên giới hạn cụ thể
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fact_controller.router, tags=["facts"])
app.include_router(chat_controller.router, tags=["chat"])
app.include_router(dev_controller.router)


@app.get("/health")
def health():
    return {"status": "ok", "mock_mode": settings.USE_MOCK_LLM}
