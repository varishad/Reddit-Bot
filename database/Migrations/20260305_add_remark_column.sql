-- Migration: Add remark column to accounts and shadow_vault
-- Created: 2026-03-05

-- UP Section
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS remark TEXT;
ALTER TABLE shadow_vault ADD COLUMN IF NOT EXISTS remark TEXT;

-- DOWN Section
-- ALTER TABLE accounts DROP COLUMN IF NOT EXISTS remark;
-- ALTER TABLE shadow_vault DROP COLUMN IF NOT EXISTS remark;
