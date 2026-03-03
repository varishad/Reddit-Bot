-- Migration: Add user roles
-- Created: 2026-03-02

-- UP: Apply changes
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'User';

-- Assign the first user as Admin if they exist
UPDATE users SET role = 'Admin' WHERE id = (SELECT id FROM users ORDER BY created_at ASC LIMIT 1);

-- DOWN: Rollback changes
-- ALTER TABLE users DROP COLUMN IF EXISTS role;
