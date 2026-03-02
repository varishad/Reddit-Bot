-- Migration: 001_initial_schema.sql
-- Description: Initial database schema setup
-- Date: 2025-01-XX
-- Run this first to set up the complete database

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
    status VARCHAR(20) NOT NULL,
    username TEXT,
    karma TEXT,
    error_message TEXT,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


