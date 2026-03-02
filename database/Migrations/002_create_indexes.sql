-- Migration: 002_create_indexes.sql
-- Description: Create indexes for performance
-- Date: 2025-01-XX
-- Run after 001_initial_schema.sql

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


