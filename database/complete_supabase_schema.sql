-- Reddit Bot Commercial Version - Complete Supabase Database Schema
-- Run this SQL in your Supabase SQL Editor
-- This is the master schema file - run this to set up the complete database

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (stores user accounts)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    license_key VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN DEFAULT false,
    activated_at TIMESTAMP WITH TIME ZONE,
    activation_ip INET,
    machine_id TEXT, -- Unique hardware ID for device locking
    plan_start_date TIMESTAMP WITH TIME ZONE, -- When the plan starts
    plan_end_date TIMESTAMP WITH TIME ZONE, -- When the plan expires
    plan_name VARCHAR(50) DEFAULT 'Monthly Normal', -- Plan type
    role VARCHAR(20) DEFAULT 'User', -- Admin or User
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    last_login_ip INET,
    total_accounts_processed INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    notes TEXT,
    CONSTRAINT license_key_format CHECK (license_key ~ '^REDDIT-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$')
);

-- Activations table (tracks activation attempts and history)
CREATE TABLE IF NOT EXISTS activations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    license_key VARCHAR(50) NOT NULL,
    activation_ip INET NOT NULL,
    machine_id TEXT, -- Machine ID at time of activation
    activation_code VARCHAR(50) NOT NULL,
    activated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    is_used BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(activation_code)
);

-- Usage logs table (tracks all bot usage)
CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    license_key VARCHAR(50) NOT NULL,
    session_id UUID NOT NULL,
    ip_address INET NOT NULL,
    accounts_processed INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    invalid_count INTEGER DEFAULT 0,
    banned_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    session_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    session_end TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Session details table (detailed per-account processing)
CREATE TABLE IF NOT EXISTS session_details (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    reddit_email TEXT NOT NULL,
    reddit_password TEXT,
    status VARCHAR(20) NOT NULL,
    username TEXT,
    karma TEXT,
    error_message TEXT,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_license_key ON users(license_key);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_activations_code ON activations(activation_code);
CREATE INDEX IF NOT EXISTS idx_activations_license ON activations(license_key);
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_session_id ON usage_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON usage_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_session_details_session_id ON session_details(session_id);
CREATE INDEX IF NOT EXISTS idx_session_details_user_id ON session_details(user_id);

-- DISABLE Row Level Security (RLS) for service role access
-- Since we're using service_role key, RLS can be safely disabled
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE activations DISABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE session_details DISABLE ROW LEVEL SECURITY;

-- Grant explicit permissions to service_role (just to be sure)
GRANT ALL ON users TO service_role;
GRANT ALL ON activations TO service_role;
GRANT ALL ON usage_logs TO service_role;
GRANT ALL ON session_details TO service_role;

-- Function to update user stats after session
CREATE OR REPLACE FUNCTION update_user_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE users
    SET 
        total_accounts_processed = total_accounts_processed + NEW.accounts_processed,
        total_sessions = total_sessions + 1,
        last_login = NEW.session_start,
        last_login_ip = NEW.ip_address
    WHERE id = NEW.user_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists
DROP TRIGGER IF EXISTS trigger_update_user_stats ON usage_logs;

-- Trigger to auto-update user stats
CREATE TRIGGER trigger_update_user_stats
    AFTER INSERT ON usage_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_user_stats();

-- Function to generate license key (for admin use)
CREATE OR REPLACE FUNCTION generate_license_key()
RETURNS TEXT AS $$
DECLARE
    new_key TEXT;
    key_exists BOOLEAN;
BEGIN
    LOOP
        new_key := 'REDDIT-' || 
                   UPPER(SUBSTRING(MD5(RANDOM()::TEXT) FROM 1 FOR 4)) || '-' ||
                   UPPER(SUBSTRING(MD5(RANDOM()::TEXT) FROM 1 FOR 4)) || '-' ||
                   UPPER(SUBSTRING(MD5(RANDOM()::TEXT) FROM 1 FOR 4));
        
        SELECT EXISTS(SELECT 1 FROM users WHERE license_key = new_key) INTO key_exists;
        
        IF NOT key_exists THEN
            EXIT;
        END IF;
    END LOOP;
    
    RETURN new_key;
END;
$$ LANGUAGE plpgsql;
