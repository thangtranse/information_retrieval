-- Enable pgvector so the stack is ready for future embedding work. This crawler feature does
-- not create vector columns yet; turning the extension on here keeps the database contract
-- explicit and idempotent (CREATE EXTENSION IF NOT EXISTS is safe to re-run on every boot).
CREATE EXTENSION IF NOT EXISTS vector;
