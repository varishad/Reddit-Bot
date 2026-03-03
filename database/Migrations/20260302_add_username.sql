-- Migration: Add username column to users table
-- Created: 2026-03-02

-- UP
ALTER TABLE users ADD COLUMN IF NOT EXISTS username TEXT;

-- DOWN
-- ALTER TABLE users DROP COLUMN IF EXISTS username;
