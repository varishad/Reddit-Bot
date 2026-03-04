-- Migration: Add VPN Location and IP to Accounts
-- Description: Adds vpn_location and vpn_ip columns to track connectivity info per account processing.

-- [UP]
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS vpn_location TEXT;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS vpn_ip TEXT;

-- [DOWN]
-- ALTER TABLE accounts DROP COLUMN IF NOT EXISTS vpn_location;
-- ALTER TABLE accounts DROP COLUMN IF NOT EXISTS vpn_ip;
