-- Migration: Rename encrypted_password to password for plain-text storage
-- Created: 2026-03-05

-- UP Section
ALTER TABLE accounts RENAME COLUMN encrypted_password TO password;
ALTER TABLE shadow_vault RENAME COLUMN encrypted_password TO password;

-- DOWN Section (Rollback)
-- ALTER TABLE accounts RENAME COLUMN password TO encrypted_password;
-- ALTER TABLE shadow_vault RENAME COLUMN password TO encrypted_password;
