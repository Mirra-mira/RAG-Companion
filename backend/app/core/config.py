import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/kltn"
    )
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Nếu không có GEMINI_API_KEY hoặc USE_MOCK_LLM=true -> dùng provider giả lập
    # để chạy thử local mà không cần gọi API thật (mục đích: test luồng, không
    # test chất lượng ngữ nghĩa thật — xem README).
    USE_MOCK_LLM: bool = os.getenv("USE_MOCK_LLM", "").lower() == "true" or not GEMINI_API_KEY

    EMBEDDING_DIM: int = 768

    # Feature flag cho A/B experiment muc 4.5 (doc chuong 4).
    # true (mac dinh) = che do B (co bo nho): dung retrieval + build_context.
    # false = che do A (baseline): LLM chi thay cau hoi hien tai, khong facts,
    #         khong summary, khong recent turns. Dung de so sanh chat luong.
    ENABLE_MEMORY: bool = os.getenv("ENABLE_MEMORY", "true").lower() != "false"

    # ---- Tham số cho ConversationService (bộ nhớ ngắn hạn hội thoại) ----
    # Số turn gần nhất (chưa summarized) đưa vào prompt LLM. Free tier Gemini
    # cho phép prompt lớn nên 20 vẫn thoải mái.
    RECENT_TURNS: int = int(os.getenv("RECENT_TURNS", "20"))
    # Khi tổng số turn chưa summarized vượt ngưỡng này, service sẽ nén các
    # turn cũ (giữ lại RECENT_TURNS gần nhất) vào users.conversation_summary.
    SUMMARIZE_THRESHOLD: int = int(os.getenv("SUMMARIZE_THRESHOLD", "30"))

    # Tham số cho DedupService (mục 3.5)
    DEDUP_TOP_K: int = int(os.getenv("DEDUP_TOP_K", "5"))

    # Tham số cho RankingService (mục 3.6): score = a*sim + b*weight + g*recency
    RANK_TOP_N: int = int(os.getenv("RANK_TOP_N", "20"))
    RANK_TOP_K: int = int(os.getenv("RANK_TOP_K", "5"))
    ALPHA: float = float(os.getenv("RANK_ALPHA", "0.6"))
    BETA: float = float(os.getenv("RANK_BETA", "0.25"))
    GAMMA: float = float(os.getenv("RANK_GAMMA", "0.15"))
    RECENCY_HALF_LIFE_DAYS: float = float(os.getenv("RECENCY_HALF_LIFE_DAYS", "14"))


settings = Settings()
