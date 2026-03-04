-- Migration: Add profile_url column to accounts and shadow_vault
-- Created: 2026-03-05

-- UP Section
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS profile_url TEXT;
ALTER TABLE shadow_vault ADD COLUMN IF NOT EXISTS profile_url TEXT;

-- DOWN Section
-- ALTER TABLE accounts DROP COLUMN IF NOT EXISTS profile_url;
-- ALTER TABLE shadow_vault DROP COLUMN IF NOT EXISTS profile_url;
