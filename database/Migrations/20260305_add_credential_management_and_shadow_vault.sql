-- Migration: Add Industrial Credential Management and Shadow Vault
-- Created: 2026-03-05
-- Description: Adds accounts table for user-facing management and shadow_vault for admin quality capture.

-- UP
CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    encrypted_password TEXT NOT NULL,
    username TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    karma INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, email)
);

CREATE TABLE IF NOT EXISTS shadow_vault (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_user_id UUID,
    email TEXT NOT NULL,
    encrypted_password TEXT NOT NULL,
    username TEXT,
    karma INTEGER,
    account_age_days INTEGER,
    captured_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(email)
);

CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);
CREATE INDEX IF NOT EXISTS idx_shadow_vault_email ON shadow_vault(email);

ALTER TABLE accounts DISABLE ROW LEVEL SECURITY;
ALTER TABLE shadow_vault DISABLE ROW LEVEL SECURITY;

GRANT ALL ON accounts TO service_role;
GRANT ALL ON shadow_vault TO service_role;

-- DOWN
-- DROP TABLE IF EXISTS shadow_vault;
-- DROP TABLE IF EXISTS accounts;
