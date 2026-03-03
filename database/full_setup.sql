-- Reddit Bot Master Database Schema
-- Includes: HWID Locking, Start/End Dates, and Admin Roles
-- Created: 2026-03-02

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. TABLES
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username TEXT, -- Optional display name
    license_key TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    activated_at TIMESTAMP WITH TIME ZONE,
    activation_ip INET,
    machine_id TEXT, -- Unique hardware ID for device locking
    plan_start_date TIMESTAMP WITH TIME ZONE, -- When the plan starts
    plan_end_date TIMESTAMP WITH TIME ZONE, -- When the plan expires
    plan_name VARCHAR(50) DEFAULT 'Monthly Normal', -- Plan type
    role VARCHAR(20) DEFAULT 'User', -- Admin or User
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    last_login_ip INET
);

CREATE TABLE IF NOT EXISTS activations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    activation_code TEXT NOT NULL,
    machine_id TEXT, -- Captured HWID at time of activation
    activated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address INET
);

-- 3. POLICIES (Simple RLS - can be refined)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public Read" ON users FOR SELECT USING (true);
CREATE POLICY "Admin Update" ON users FOR UPDATE WITH CHECK (true);

-- 4. INITIALIZATION
-- Note: Manually update your first user to 'Admin' after registration or run:
-- UPDATE users SET role = 'Admin' WHERE license_key = 'YOUR_KEY_HERE';
