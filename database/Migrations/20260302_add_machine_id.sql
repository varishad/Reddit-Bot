-- Migration: Add machine_id for HWID locking
-- Created: 2026-03-02

-- UP: Apply changes
ALTER TABLE users ADD COLUMN IF NOT EXISTS machine_id TEXT;
ALTER TABLE activations ADD COLUMN IF NOT EXISTS machine_id TEXT;

-- DOWN: Rollback changes
-- ALTER TABLE users DROP COLUMN IF EXISTS machine_id;
-- ALTER TABLE activations DROP COLUMN IF EXISTS machine_id;
