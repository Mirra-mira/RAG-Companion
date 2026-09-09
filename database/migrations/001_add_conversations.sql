-- ============================================================
-- Migration 001: thêm bảng conversations + cột conversation_summary
-- Chạy trên DB HIỆN CÓ (giữ nguyên data user + facts).
-- Idempotent: chạy nhiều lần không lỗi.
--
-- Cách chạy (container Docker):
--   docker exec -i kltn-postgres psql -U postgres -d kltn < database/migrations/001_add_conversations.sql
-- ============================================================

BEGIN;

-- 1) Thêm cột conversation_summary vào users (nếu chưa có)
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS conversation_summary TEXT NOT NULL DEFAULT '';

-- 2) Tạo bảng conversations (nếu chưa có)
CREATE TABLE IF NOT EXISTS conversations (
    msg_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role        VARCHAR(10) NOT NULL,
    content     TEXT NOT NULL,
    summarized  BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3) Index cho truy vấn "N message gần nhất theo user"
CREATE INDEX IF NOT EXISTS idx_conv_user_time
    ON conversations (user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_conv_user_summarized
    ON conversations (user_id, summarized, created_at);

COMMIT;
