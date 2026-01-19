-- Migration: Create reward program taxonomy
-- File: migrations/004_add_reward_taxonomy.sql
-- Author: WebDataScraper Team
-- Created: January 18, 2026
-- Description: Adds comprehensive reward program taxonomy with proper hierarchy

BEGIN;

-- ============================================================================
-- CREATE REWARD_PROGRAMS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS reward_programs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    program_family TEXT NOT NULL,
    program_name TEXT UNIQUE NOT NULL,
    currency_type TEXT NOT NULL, -- cashback, airline_miles, flexible_points, etc.
    base_valuation DECIMAL NOT NULL, -- cents per point/mile
    transfer_partners JSONB, -- ["Aeroplan", "Marriott", "British Airways"]
    redemption_options JSONB, -- ["travel", "statement", "merchandise"]
    issuer_banks TEXT[], -- ["American Express", "TD"]
    currency_name TEXT, -- "points", "miles", "dollars"
    minimum_redemption INTEGER, -- Minimum points/miles to redeem
    expiry_policy TEXT, -- Expiry rules
    notes TEXT, -- Additional notes
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for reward_programs
CREATE INDEX IF NOT EXISTS idx_reward_programs_currency ON reward_programs(currency_type);
CREATE INDEX IF NOT EXISTS idx_reward_programs_family ON reward_programs(program_family);
CREATE INDEX IF NOT EXISTS idx_reward_programs_active ON reward_programs(is_active);

-- Comments
COMMENT ON TABLE reward_programs IS 'Comprehensive registry of Canadian credit card reward programs';
COMMENT ON COLUMN reward_programs.currency_type IS 'cashback, airline_miles, flexible_points, retail_points, entertainment_points, travel_points, hotel_points';
COMMENT ON COLUMN reward_programs.base_valuation IS 'Base value in cents per point/mile';
COMMENT ON COLUMN reward_programs.transfer_partners IS 'JSON array of transfer partner programs';
COMMENT ON COLUMN reward_programs.redemption_options IS 'JSON array of redemption types available';

-- ============================================================================
-- CREATE POINT_VALUATIONS TABLE
-- ============================================================================

-- Redemption-specific valuations (same program can have different values)
CREATE TABLE IF NOT EXISTS point_valuations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    program_id UUID REFERENCES reward_programs(id) ON DELETE CASCADE,
    redemption_type TEXT NOT NULL, -- 'travel', 'statement', 'merchandise', 'transfer'
    cents_per_point DECIMAL NOT NULL, -- Value for this redemption type
    minimum_redemption INTEGER, -- Minimum points required for this redemption
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_valuations_program ON point_valuations(program_id);
CREATE INDEX IF NOT EXISTS idx_valuations_type ON point_valuations(redemption_type);

COMMENT ON TABLE point_valuations IS 'Redemption-specific valuations for reward programs';
COMMENT ON COLUMN point_valuations.redemption_type IS 'travel, statement, merchandise, transfer, flight, upgrade, etc.';

-- ============================================================================
-- UPDATE CARDS TABLE
-- ============================================================================

-- Add new columns to cards table
ALTER TABLE cards ADD COLUMN IF NOT EXISTS reward_program_family TEXT;
ALTER TABLE cards ADD COLUMN IF NOT EXISTS reward_program_id UUID REFERENCES reward_programs(id);
ALTER TABLE cards ADD COLUMN IF NOT EXISTS currency_type TEXT;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_cards_program_family ON cards(reward_program_family);
CREATE INDEX IF NOT EXISTS idx_cards_program_id ON cards(reward_program_id);
CREATE INDEX IF NOT EXISTS idx_cards_currency_type ON cards(currency_type);

-- Comments
COMMENT ON COLUMN cards.reward_program_family IS 'Program family name (e.g., "Membership Rewards")';
COMMENT ON COLUMN cards.reward_program_id IS 'Foreign key to reward_programs table';
COMMENT ON COLUMN cards.currency_type IS 'Currency type: cashback, airline_miles, flexible_points, etc.';

-- Note: Keep existing reward_program column for backward compatibility
-- It will be deprecated after migration to new taxonomy

COMMIT;
