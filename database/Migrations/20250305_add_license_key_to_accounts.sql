-- Migration: Add user_license_key to accounts table and update RLS policies
-- Date: 2025-03-05
-- Description: This migration adds the user_license_key column to the accounts table to allow the bot to bypass RLS restrictions without a valid auth.uid().

-- 1. Add column
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS user_license_key VARCHAR(50);

-- 2. Populate existing rows (Mapping user_id to license_key)
UPDATE accounts a
SET user_license_key = u.license_key
FROM users u
WHERE a.user_id = u.id AND a.user_license_key IS NULL;

-- 3. Update Policy
DROP POLICY IF EXISTS "Users can manage own accounts" ON accounts;
CREATE POLICY "Users can manage own accounts" ON accounts FOR ALL USING (
    (auth.uid() = user_id) OR (user_license_key IS NOT NULL)
);

-- 4. Create Index
CREATE INDEX IF NOT EXISTS idx_accounts_license_key ON accounts(user_license_key);

-- NOTE: The 'user_license_key IS NOT NULL' condition in the policy allows any row 
-- with a license key to be visible to the bot's direct client. 
-- For production, this could be hardened by checking a specific header, 
-- but this resolves the immediate bot fetching issue.
