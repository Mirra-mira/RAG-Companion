-- ============================================================
-- Schema cho hệ thống bộ nhớ dài hạn (KLTN)
-- Đúng theo ERD Chương 3 (Hình 3.1, Bảng 3.5 - 3.7)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- cho gen_random_uuid()

-- Bảng 3.5: users
CREATE TABLE IF NOT EXISTS users (
    user_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username              VARCHAR(100) NOT NULL,
    -- Tóm tắt các đoạn hội thoại cũ (đã "nén" các turn xa) — dùng làm bộ nhớ
    -- ngắn hạn khi prompt LLM để tránh mất mạch giữa các lượt chat.
    conversation_summary  TEXT NOT NULL DEFAULT '',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Bảng 3.6: facts
CREATE TABLE IF NOT EXISTS facts (
    fact_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    category    VARCHAR(50) NOT NULL,
    content     TEXT NOT NULL,
    embedding   VECTOR(768) NOT NULL,
    weight      INTEGER NOT NULL DEFAULT 1,
    status      VARCHAR(20) NOT NULL DEFAULT 'active',  -- active | superseded
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Chỉ mục vector (mục 2.3) — HNSW cho cosine distance
CREATE INDEX IF NOT EXISTS idx_facts_embedding_hnsw
    ON facts USING hnsw (embedding vector_cosine_ops);

-- Chỉ mục hỗ trợ lọc theo user + trạng thái (đảm bảo FR5 — cô lập theo user_id)
CREATE INDEX IF NOT EXISTS idx_facts_user_status
    ON facts (user_id, status);

-- Bảng 3.7: user_reminders
CREATE TABLE IF NOT EXISTS user_reminders (
    reminder_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    content     TEXT NOT NULL,
    remind_at   TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reminders_user ON user_reminders (user_id);

-- ============================================================
-- Bảng conversations: lưu toàn bộ turn hội thoại (user + assistant)
-- Dùng cho:
--   (1) Frontend đồng bộ chat history giữa các trình duyệt/profile
--   (2) Backend đưa N turn gần nhất vào prompt LLM (bộ nhớ ngắn hạn)
--   (3) Khi số turn chưa tóm tắt > ngưỡng, service tóm tắt sẽ nén các
--       turn cũ vào users.conversation_summary, đánh dấu summarized=true.
-- ============================================================
CREATE TABLE IF NOT EXISTS conversations (
    msg_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role        VARCHAR(10) NOT NULL,     -- 'user' | 'assistant'
    content     TEXT NOT NULL,
    summarized  BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Truy vấn chính: lấy N message gần nhất chưa summarized của 1 user
CREATE INDEX IF NOT EXISTS idx_conv_user_time
    ON conversations (user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_conv_user_summarized
    ON conversations (user_id, summarized, created_at);
