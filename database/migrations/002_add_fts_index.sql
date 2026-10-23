-- Migration 002: GIN index cho keyword search (baseline B1).
-- Idempotent. Chay:
--   docker exec -i kltn-postgres psql -U postgres -d kltn < database/migrations/002_add_fts_index.sql
-- (Nho them dong CREATE INDEX nay vao database/schema.sql de DB dung moi cung co.)
CREATE INDEX IF NOT EXISTS idx_facts_content_fts
    ON facts USING gin (to_tsvector('simple', content));
