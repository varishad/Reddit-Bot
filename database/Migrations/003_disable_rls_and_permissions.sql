-- Migration: 003_disable_rls_and_permissions.sql
-- Description: Disable RLS and grant permissions for service role
-- Date: 2025-01-XX
-- Run after 002_create_indexes.sql

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


