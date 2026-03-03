-- Migration: Add subscription plan dates
-- Created: 2026-03-02

-- UP: Apply changes
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_start_date TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_end_date TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_name VARCHAR(50) DEFAULT 'Monthly Normal';

-- DOWN: Rollback changes
-- ALTER TABLE users DROP COLUMN IF EXISTS plan_start_date;
-- ALTER TABLE users DROP COLUMN IF EXISTS plan_end_date;
-- ALTER TABLE users DROP COLUMN IF EXISTS plan_name;
