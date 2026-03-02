-- Migration: 004_create_functions_and_triggers.sql
-- Description: Create database functions and triggers
-- Date: 2025-01-XX
-- Run after 003_disable_rls_and_permissions.sql

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


