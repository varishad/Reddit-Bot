-- Migration: Add reddit_password to session_details
-- Date: 2026-03-02

-- UP
ALTER TABLE session_details ADD COLUMN IF NOT EXISTS reddit_password TEXT;

-- DOWN
-- ALTER TABLE session_details DROP COLUMN reddit_password;
